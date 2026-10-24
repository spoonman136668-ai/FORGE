package plane

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

func (p *Engine) controllerLock() (*os.File, error) {
	if info, e := os.Stat(filepath.Join(p.Root, "state", "service.lock")); e == nil && info.IsDir() {
		return nil, p.lockEvidence("LEGACY_SERVICE_LOCK_PRESENT: controller ownership cannot be verified")
	}
	dir := filepath.Join(p.Root, "state")
	if e := os.MkdirAll(dir, 0700); e != nil {
		return nil, e
	}
	f, e := os.OpenFile(filepath.Join(dir, "controller.lock"), os.O_CREATE|os.O_RDWR, 0600)
	if e != nil {
		return nil, e
	}
	if e = lockFile(f); e != nil {
		f.Close()
		return nil, p.lockEvidence("SERVICE_LOCKED: controller already owns this state root")
	}
	// The OS lock is the controller liveness authority. Never unlink it: doing
	// so could create two independently locked inodes. Reuse only after checking
	// the previous owner and every unfinished supervisor.
	b, e := os.ReadFile(filepath.Join(dir, "controller.pid"))
	if e == nil {
		pid, er := strconv.Atoi(strings.TrimSpace(string(b)))
		if er != nil || pid <= 0 || (pid != os.Getpid() && processAlive(pid)) {
			f.Close()
			return nil, p.lockEvidence("CONTROLLER_PID_LIVE_OR_UNVERIFIED: " + strings.TrimSpace(string(b)))
		}
	} else if !os.IsNotExist(e) {
		f.Close()
		return nil, e
	}
	if e = p.noLiveSupervisors(); e != nil {
		f.Close()
		return nil, p.lockEvidence(e.Error())
	}
	if e = os.WriteFile(filepath.Join(dir, "controller.pid"), []byte(strconv.Itoa(os.Getpid())), 0600); e != nil {
		f.Close()
		return nil, e
	}
	return f, nil
}

func (p *Engine) lockEvidence(reason string) error {
	path := filepath.Join(p.Root, "evidence", "controller", randomID(), "stale-lock.json")
	if e := os.MkdirAll(filepath.Dir(path), 0700); e != nil {
		return errors.Join(errors.New(reason), e)
	}
	e := writeJSON(path, map[string]any{"blocker": reason, "evidence": path, "lock_cleaned": false, "production_accepted": false})
	if e != nil {
		return errors.Join(errors.New(reason), e)
	}
	return fmt.Errorf("%s; evidence=%s", reason, path)
}

func (p *Engine) noLiveSupervisors() error {
	rows, e := p.Store.DB.Query("SELECT pid FROM process_records WHERE finished=0")
	if e != nil {
		return e
	}
	defer rows.Close()
	for rows.Next() {
		var pid int
		if e = rows.Scan(&pid); e != nil {
			return e
		}
		if pid <= 0 || processAlive(pid) {
			return fmt.Errorf("RECOVERY_WAITING_FOR_SUPERVISOR: process %d remains alive or unverified", pid)
		}
	}
	return rows.Err()
}

// Recover only while holding the controller OS lock. Never reclaim a live/unknown
// supervisor, kill a reused PID, or convert a partial acceptance into success.
func (p *Engine) recoverInterrupted() error {
	rows, e := p.Store.DB.Query("SELECT pid FROM process_records WHERE finished=0")
	if e != nil {
		return e
	}
	var pids []int
	for rows.Next() {
		var pid int
		if e = rows.Scan(&pid); e != nil {
			rows.Close()
			return e
		}
		pids = append(pids, pid)
	}
	e = rows.Err()
	rows.Close()
	if e != nil {
		return e
	}
	for _, pid := range pids {
		if processAlive(pid) {
			return fmt.Errorf("RECOVERY_WAITING_FOR_SUPERVISOR: process %d remains alive or unverified", pid)
		}
	}
	jobs, e := p.Store.List()
	if e != nil {
		return e
	}
	for _, j := range jobs {
		switch j.State {
		case "DISPATCHED", "ENGINEERING", "CANDIDATE", "ACCEPTING":
			if held, e := p.recoverObjectiveHold(j); e != nil {
				return e
			} else if held {
				continue
			}
			tx, e := p.Store.DB.Begin()
			if e != nil {
				return e
			}
			state := "REJECTED_RETRYABLE"
			reason := "CONTROLLER_INTERRUPTED: previous supervisor confirmed absent; explicit retry required"
			recoveryDecision := p.retryDecisionNow(j.ID, j.Attempt, "CONTROLLER_INTERRUPTED")
			if recoveryDecision.HardStop {
				state = "BLOCKED"
				reason = "RETRY_LIMIT_REACHED: CONTROLLER_INTERRUPTED"
			}
			if _, e = tx.Exec("UPDATE work_orders SET state=?,reason=? WHERE id=? AND attempt=?", state, reason, j.ID, j.Attempt); e != nil {
				tx.Rollback()
				return e
			}
			if e = event(tx, j.ID, j.Attempt, "RECOVERED_INTERRUPTED", reason); e != nil {
				tx.Rollback()
				return e
			}
			if _, e = tx.Exec("DELETE FROM worker_leases WHERE work_order_id=?", j.ID); e != nil {
				tx.Rollback()
				return e
			}
			if _, e = tx.Exec("UPDATE acceptance_runs SET result='INTERRUPTED' WHERE work_order_id=? AND attempt=? AND result='SEALING'", j.ID, j.Attempt); e != nil {
				tx.Rollback()
				return e
			}
			if e = tx.Commit(); e != nil {
				return e
			}
		}
	}
	_, e = p.Store.DB.Exec("UPDATE process_records SET finished=1 WHERE finished=0")
	return e
}
func (p *Engine) runnerFor(j Job) ProcessRunner {
	if _, ok := p.runner.(SupervisedRunner); p.runner != nil && !ok {
		return p.runner
	}
	return p.supervisedRunnerFor(j)
}

// Deterministic acceptance must never use the worker adapter or its test double.
// Both lanes retain the native process supervisor and durable ownership records.
func (p *Engine) supervisedRunnerFor(j Job) ProcessRunner {
	if p.Store == nil {
		return SupervisedRunner{}
	}
	return SupervisedRunner{OnStart: func(pid int) error {
		_, e := p.Store.DB.Exec("INSERT INTO process_records(work_order_id,attempt,pid,finished) VALUES(?,?,?,0)", j.ID, j.Attempt, pid)
		return e
	}, OnFinish: func(pid int) {
		_, _ = p.Store.DB.Exec("UPDATE process_records SET finished=1 WHERE work_order_id=? AND attempt=? AND pid=?", j.ID, j.Attempt, pid)
	}}
}
