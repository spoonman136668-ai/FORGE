package plane

import (
	"context"
	"encoding/json"
	"errors"
	"gopkg.in/yaml.v3"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func dkRetryFixture(t *testing.T, queueState, jobState string) (*Engine, QueueOrder, []byte) {
	t.Helper()
	p, w := setup(t)
	testAuthority(p)
	w.ID = "DK_RETRY"
	w.Worker.Branch = "codex/dk-retry"
	yamlBytes, e := yaml.Marshal(w)
	if e != nil {
		t.Fatal(e)
	}
	q := QueueOrder{Schema: queueSchema, ID: w.ID, LogicalStage: w.ID, Kind: "source", WorkOrderYAML: string(yamlBytes)}
	raw, e := json.Marshal(q)
	if e != nil {
		t.Fatal(e)
	}
	if _, e = p.Store.DB.Exec("INSERT INTO queue_items(id,hash,raw,kind,state,mode,authorization,updated) VALUES(?,?,?,'source',?,'source','operator',?)", q.ID, digest(raw), raw, queueState, now()); e != nil {
		t.Fatal(e)
	}
	if e = durableNew(filepath.Join(p.Root, "workorders", "pending", q.ID+".json"), raw); e != nil {
		t.Fatal(e)
	}
	if e := p.Store.Load([]byte(q.WorkOrderYAML)); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE work_orders SET state=?,reason='DK_BLOCKER',attempt=1 WHERE id=?", jobState, q.ID); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE queue_items SET state=?,reason='DK_BLOCKER' WHERE id=?", queueState, q.ID); e != nil {
		t.Fatal(e)
	}
	return p, q, raw
}

func TestDKEligibilityReconciliationNeverSilentIdle(t *testing.T) {
	for _, queueState := range []string{"PENDING", "RETRY_WAIT", "QUEUED"} {
		for _, jobState := range []string{"BLOCKED", "FAILED"} {
			t.Run(queueState+jobState, func(t *testing.T) {
				p, q, _ := dkRetryFixture(t, queueState, jobState)
				_ = p.setSetting("autonomy_status", "IDLE: no authorized eligible work")
				s, e := p.AutonomyStatus()
				if e != nil {
					t.Fatal(e)
				}
				status := s["controller_status"].(string)
				for _, want := range []string{q.ID, "queue_items=" + queueState, "work_orders=" + jobState, "DK_BLOCKER"} {
					if !strings.Contains(status, want) {
						t.Fatalf("missing %s: %s", want, status)
					}
				}
				if e = p.AutonomyTick(context.Background()); e != nil {
					t.Fatal(e)
				}
				s, e = p.AutonomyStatus()
				if e != nil || strings.Contains(s["controller_status"].(string), "IDLE") {
					t.Fatalf("%v %v", s, e)
				}
			})
		}
	}
}

func TestDKRetryRepairsExactHashSource(t *testing.T) {
	for _, state := range []string{"FAILED", "BLOCKED", "PENDING", "RETRY_WAIT"} {
		t.Run(state, func(t *testing.T) {
			p, q, raw := dkRetryFixture(t, state, "BLOCKED")
			if state == "FAILED" {
				if e := p.queueFinish(q.ID, QueueResult{WorkOrderID: q.ID, Disposition: "failed", InputSHA256: digest(raw)}); e != nil {
					t.Fatal(e)
				}
			}
			if _, e := p.RetryQueueOffline(context.Background(), q.ID, "operator", "source"); e != nil {
				t.Fatal(e)
			}
			qs, js := p.queueStates(q.ID)
			if qs != "QUEUED" || js != "DRAFT" {
				t.Fatalf("%s %s", qs, js)
			}
			b, e := os.ReadFile(filepath.Join(p.Root, "workorders", "pending", q.ID+".json"))
			if e != nil || string(b) != string(raw) {
				t.Fatalf("bytes changed: %v", e)
			}
			j, e := p.Store.Get(q.ID)
			if e != nil || j.Attempt != 1 {
				t.Fatalf("retry launched or reset budget: %+v %v", j, e)
			}
			// A blocked baseline is checked again and produces a receipt, not a launch.
			delete(p.Config.Repos, j.Order.Repo)
			if e = p.AutonomyTick(context.Background()); e == nil {
				t.Fatal("missing baseline accepted")
			}
		})
	}
}

func TestDKRetryRefusals(t *testing.T) {
	for _, test := range []struct {
		name, want string
		change     func(*Engine, QueueOrder)
	}{
		{"HashMismatch", "QUEUE_RAW_HASH_MISMATCH", func(p *Engine, q QueueOrder) {
			_, _ = p.Store.DB.Exec("UPDATE queue_items SET hash='wrong' WHERE id=?", q.ID)
		}},
		{"AcceptedRefMutation", "ACCEPTED_REF_MUTATION_FORBIDDEN", func(p *Engine, q QueueOrder) { p.Config.Policy.AcceptedRefMutation = true }},
		{"OriginalAuthority", "ORIGINAL_ARCHITECTURE_REMAINS_AUTHORITY", func(p *Engine, q QueueOrder) { _ = p.setSetting("autonomy_authority", "original") }},
		{"GitHubAuthority", "ORIGINAL_REPOSITORY_HAS_ACTIVE_RUNS", func(p *Engine, q QueueOrder) {
			p.authorityVerifier = func(context.Context) error { return errors.New("ORIGINAL_REPOSITORY_HAS_ACTIVE_RUNS") }
		}},
		{"RetryLimit", "RETRY_LIMIT_REACHED", func(p *Engine, q QueueOrder) {
			_, _ = p.Store.DB.Exec("UPDATE work_orders SET attempt=? WHERE id=?", p.Config.Policy.MaxAttempts, q.ID)
		}},
		{"ModifiedNativeBytes", "QUEUE_NATIVE_ORDER_MISMATCH", func(p *Engine, q QueueOrder) {
			_, _ = p.Store.DB.Exec("UPDATE work_orders SET yaml=? WHERE id=?", q.WorkOrderYAML+"\n", q.ID)
		}},
		{"ModifiedDiskBytes", "QUEUE_INPUT_CHANGED", func(p *Engine, q QueueOrder) {
			_ = os.WriteFile(filepath.Join(p.Root, "workorders", "pending", q.ID+".json"), []byte("changed"), 0600)
		}},
	} {
		t.Run(test.name, func(t *testing.T) {
			p, q, _ := dkRetryFixture(t, "FAILED", "FAILED")
			test.change(p, q)
			_, e := p.QueueRetry(context.Background(), q.ID, "operator", "source")
			if e == nil || !strings.Contains(e.Error(), test.want) {
				t.Fatalf("%v", e)
			}
			qs, js := p.queueStates(q.ID)
			if qs != "FAILED" || js != "FAILED" {
				t.Fatalf("refusal mutated states %s %s", qs, js)
			}
		})
	}
}

func TestDKReceiptExplainsPreWorkerFailure(t *testing.T) {
	p, q, _ := dkRetryFixture(t, "QUEUED", "AUTHORIZED")
	p.authorityVerifier = func(context.Context) error { return errors.New("ORIGINAL_REPOSITORY_HAS_ACTIVE_RUNS") }
	if e := p.AutonomyTick(context.Background()); e == nil {
		t.Fatal("expected pre-worker failure")
	}
	var path string
	if e := p.Store.DB.QueryRow("SELECT receipt FROM queue_items WHERE id=?", q.ID).Scan(&path); e != nil {
		t.Fatal(e)
	}
	b, e := os.ReadFile(path)
	if e != nil {
		t.Fatal(e)
	}
	var r QueueResult
	if e = json.Unmarshal(b, &r); e != nil {
		t.Fatal(e)
	}
	if r.QueueStateBefore != "QUEUED" || r.QueueStateAfter != "BLOCKED" || r.WorkOrderStateBefore != "AUTHORIZED" || r.WorkOrderStateAfter != "BLOCKED" || r.Blocker != "ORIGINAL_REPOSITORY_HAS_ACTIVE_RUNS" || r.Blocker != r.Reason || r.WorkerLaunchAttempted || r.SourceHygieneRan || r.ProductionAccepted || filepath.Dir(path) != r.Evidence {
		t.Fatalf("%s", b)
	}
}

func TestDKOperatorDecisionNeverConsumed(t *testing.T) {
	p, q, _ := dkRetryFixture(t, "RETRY_WAIT", "REJECTED_RETRYABLE")
	if _, e := p.Store.DB.Exec("INSERT INTO recovery_decisions VALUES(?,1,'operator-blocked','DK_BLOCKER',?)", q.ID, now()); e != nil {
		t.Fatal(e)
	}
	for i := 0; i < 4; i++ {
		if e := p.AutonomyTick(context.Background()); e != nil {
			t.Fatal(e)
		}
		qs, js := p.queueStates(q.ID)
		if qs != "BLOCKED" || js != "BLOCKED" {
			t.Fatalf("%s %s", qs, js)
		}
	}
	if _, e := os.Stat(filepath.Join(p.Root, "workorders", "pending", q.ID+".json")); e != nil {
		t.Fatal("operator decision consumed", e)
	}
}

func TestDKStaleLockChecksSupervisors(t *testing.T) {
	p, _ := setup(t)
	path := filepath.Join(p.Root, "state", "controller.lock")
	if e := os.WriteFile(path, []byte("stale"), 0600); e != nil {
		t.Fatal(e)
	}
	if e := os.WriteFile(filepath.Join(p.Root, "state", "controller.pid"), []byte("2147483647"), 0600); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("INSERT INTO process_records(work_order_id,attempt,pid,finished) VALUES('DK',1,?,0)", os.Getpid()); e != nil {
		t.Fatal(e)
	}
	if f, e := p.controllerLock(); e == nil {
		f.Close()
		t.Fatal("live supervisor lock reclaimed")
	} else if !strings.Contains(e.Error(), "evidence=") {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE process_records SET finished=1"); e != nil {
		t.Fatal(e)
	}
	f, e := p.controllerLock()
	if e != nil {
		t.Fatal(e)
	}
	defer f.Close()
	if other, e := p.controllerLock(); e == nil {
		other.Close()
		t.Fatal("live controller lock reclaimed")
	}
}

func TestDKReceiptPersistsStateTransition(t *testing.T) {
	p, q, raw := dkRetryFixture(t, "QUEUED", "AUTHORIZED")
	item := QueueItem{ID: q.ID, Hash: digest(raw), Mode: "source", Authorization: "operator"}
	if e := p.preWorkerFailure(item, "QUEUED", "AUTHORIZED", "REPO_UNAVAILABLE"); e != nil {
		t.Fatal(e)
	}
	var path string
	if e := p.Store.DB.QueryRow("SELECT receipt FROM queue_items WHERE id=?", q.ID).Scan(&path); e != nil {
		t.Fatal(e)
	}
	b, e := os.ReadFile(path)
	if e != nil {
		t.Fatal(e)
	}
	var r QueueResult
	if e = json.Unmarshal(b, &r); e != nil {
		t.Fatal(e)
	}
	qs, js := p.queueStates(q.ID)
	if r.QueueStateBefore != "QUEUED" || r.WorkOrderStateBefore != "AUTHORIZED" || r.QueueStateAfter != qs || r.WorkOrderStateAfter != js || qs != "BLOCKED" || js != "BLOCKED" || r.Blocker != "REPO_UNAVAILABLE" || r.WorkerLaunchAttempted || r.SourceHygieneRan || r.ProductionAccepted || r.Evidence != filepath.Dir(path) {
		t.Fatalf("%s", b)
	}
	var journal []byte
	if e = p.Store.DB.QueryRow("SELECT raw FROM queue_receipts WHERE work_order_id=?", q.ID).Scan(&journal); e != nil || string(journal) != string(b) {
		t.Fatalf("receipt journal mismatch: %v", e)
	}
}

func TestDKOperatorDecisionBlockedJobNeverConsumed(t *testing.T) {
	p, q, _ := dkRetryFixture(t, "RUNNING", "BLOCKED")
	if _, e := p.Store.DB.Exec("INSERT INTO recovery_decisions VALUES(?,1,'operator-blocked','DK_BLOCKER',?)", q.ID, now()); e != nil {
		t.Fatal(e)
	}
	if e := p.AutonomyTick(context.Background()); e != nil {
		t.Fatal(e)
	}
	qs, js := p.queueStates(q.ID)
	if qs != "BLOCKED" || js != "BLOCKED" {
		t.Fatalf("%s %s", qs, js)
	}
}
