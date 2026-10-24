package plane

import (
	"database/sql"
	"errors"
	"fmt"
	_ "modernc.org/sqlite"
	"os"
	"path/filepath"
	"time"
)

const schema = `
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
CREATE TABLE IF NOT EXISTS evidence_seals(work_order_id TEXT,attempt INTEGER,manifest_sha256 TEXT,PRIMARY KEY(work_order_id,attempt));
CREATE TABLE IF NOT EXISTS process_records(id INTEGER PRIMARY KEY,work_order_id TEXT,attempt INTEGER,pid INTEGER,finished INTEGER);
CREATE TABLE IF NOT EXISTS work_orders(id TEXT PRIMARY KEY, yaml BLOB NOT NULL,state TEXT NOT NULL,attempt INTEGER NOT NULL DEFAULT 0,reason TEXT NOT NULL DEFAULT '',workspace TEXT NOT NULL DEFAULT '',evidence TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS authorization_contracts(work_order_id TEXT PRIMARY KEY,digest TEXT,created TEXT);
CREATE TABLE IF NOT EXISTS authorizations(id INTEGER PRIMARY KEY,work_order_id TEXT NOT NULL,created TEXT NOT NULL,operator TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS worker_leases(work_order_id TEXT PRIMARY KEY,attempt INTEGER NOT NULL,owner TEXT NOT NULL,created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS worker_attempts(work_order_id TEXT,attempt INTEGER,worker TEXT,started TEXT,finished TEXT,exit_code INTEGER,PRIMARY KEY(work_order_id,attempt));
CREATE TABLE IF NOT EXISTS acceptance_runs(id INTEGER PRIMARY KEY,work_order_id TEXT,attempt INTEGER,result TEXT,created TEXT);
CREATE TABLE IF NOT EXISTS acceptance_checks(id INTEGER PRIMARY KEY,run_id INTEGER,name TEXT,pass INTEGER,detail TEXT);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,timestamp TEXT,work_order_id TEXT,attempt_id INTEGER,type TEXT,severity TEXT,message TEXT,structured_json TEXT);
CREATE TABLE IF NOT EXISTS artifacts(work_order_id TEXT,attempt INTEGER,path TEXT,sha256 TEXT,PRIMARY KEY(work_order_id,attempt,path));
CREATE TABLE IF NOT EXISTS repo_registry(name TEXT PRIMARY KEY,config_json TEXT);
CREATE TABLE IF NOT EXISTS tool_registry(name TEXT PRIMARY KEY,path TEXT);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
INSERT OR IGNORE INTO settings VALUES('paused','false');
`

type Store struct{ DB *sql.DB }

func OpenStore(p string) (*Store, error) {
	if err := os.MkdirAll(filepath.Dir(p), 0700); err != nil {
		return nil, err
	}
	d, err := sql.Open("sqlite", p)
	if err != nil {
		return nil, err
	}
	d.SetMaxOpenConns(1)
	if _, err = d.Exec(schema); err != nil {
		d.Close()
		return nil, err
	}
	return &Store{d}, nil
}
func now() string { return time.Now().UTC().Format(time.RFC3339Nano) }
func event(tx *sql.Tx, id string, attempt int, typ, msg string) error {
	_, e := tx.Exec("INSERT INTO events(timestamp,work_order_id,attempt_id,type,severity,message,structured_json) VALUES(?,?,?,?,?,?,?)", now(), id, attempt, typ, "INFO", msg, "{}")
	return e
}
func (s *Store) Load(b []byte) error {
	w, e := ParseOrder(b)
	if e != nil {
		return e
	}
	tx, e := s.DB.Begin()
	if e != nil {
		return e
	}
	defer tx.Rollback()
	if _, e = tx.Exec("INSERT INTO work_orders(id,yaml,state) VALUES(?,?,'DRAFT')", w.ID, b); e != nil {
		return e
	}
	if e = event(tx, w.ID, 0, "LOADED", "Awaiting local operator authorization"); e != nil {
		return e
	}
	return tx.Commit()
}
func (s *Store) Get(id string) (Job, error) {
	var j Job
	var b []byte
	e := s.DB.QueryRow("SELECT id,yaml,state,attempt,reason,workspace,evidence FROM work_orders WHERE id=?", id).Scan(&j.ID, &b, &j.State, &j.Attempt, &j.Reason, &j.Workspace, &j.Evidence)
	if e != nil {
		return j, e
	}
	j.Order, e = ParseOrder(b)
	return j, e
}
func (s *Store) List() ([]Job, error) {
	rows, e := s.DB.Query("SELECT id FROM work_orders ORDER BY rowid")
	if e != nil {
		return nil, e
	}
	var ids []string
	for rows.Next() {
		var id string
		if e = rows.Scan(&id); e != nil {
			rows.Close()
			return nil, e
		}
		ids = append(ids, id)
	}
	e = rows.Err()
	rows.Close()
	if e != nil {
		return nil, e
	}
	jobs := []Job{}
	for _, id := range ids {
		j, e := s.Get(id)
		if e != nil {
			return nil, e
		}
		jobs = append(jobs, j)
	}
	return jobs, nil
}
func (s *Store) Move(id, to, reason string) error {
	tx, e := s.DB.Begin()
	if e != nil {
		return e
	}
	defer tx.Rollback()
	var from string
	var n int
	if e = tx.QueryRow("SELECT state,attempt FROM work_orders WHERE id=?", id).Scan(&from, &n); e != nil {
		return e
	}
	if !transition(from, to) {
		return fmt.Errorf("invalid transition %s -> %s", from, to)
	}
	if _, e = tx.Exec("UPDATE work_orders SET state=?,reason=? WHERE id=?", to, reason, id); e != nil {
		return e
	}
	if e = event(tx, id, n, to, reason); e != nil {
		return e
	}
	return tx.Commit()
}
func (s *Store) Authorize(id string) error {
	tx, e := s.DB.Begin()
	if e != nil {
		return e
	}
	defer tx.Rollback()
	var state, reason string
	if e = tx.QueryRow("SELECT state,reason FROM work_orders WHERE id=?", id).Scan(&state, &reason); e != nil {
		return e
	}
	if state != "DRAFT" {
		return errors.New("authorization requires DRAFT")
	}
	authorizationReason := "Explicit local authorization"
	if reason == preWorkerRetryAuthorizedReason || reason == workerCancelRetryAuthorizedReason || reason == workerAuthRetryAuthorizedReason {
		authorizationReason = reason
	}
	r, e := tx.Exec("UPDATE work_orders SET state='AUTHORIZED',reason=? WHERE id=? AND state='DRAFT'", authorizationReason, id)
	if e != nil {
		return e
	}
	n, _ := r.RowsAffected()
	if n != 1 {
		return errors.New("authorization requires DRAFT")
	}
	if _, e = tx.Exec("INSERT INTO authorizations(work_order_id,created,operator) VALUES(?,?,'local-operator')", id, now()); e != nil {
		return e
	}
	if e = event(tx, id, 0, "AUTHORIZED", "Explicit local operator action"); e != nil {
		return e
	}
	return tx.Commit()
}
func (s *Store) Lease(id, owner string, max int) (int, error) {
	tx, e := s.DB.Begin()
	if e != nil {
		return 0, e
	}
	defer tx.Rollback()
	var state, reason, paused string
	var n, consumed int
	if e = tx.QueryRow("SELECT state,attempt,reason FROM work_orders WHERE id=?", id).Scan(&state, &n, &reason); e != nil {
		return 0, e
	}
	if e = tx.QueryRow("SELECT value FROM settings WHERE key='paused'").Scan(&paused); e != nil {
		return 0, e
	}
	if e = tx.QueryRow("SELECT count(DISTINCT attempt_id) FROM events WHERE work_order_id=? AND type='WORKER_LAUNCH_ATTEMPTED'", id).Scan(&consumed); e != nil {
		return 0, e
	}
	if paused == "true" {
		return 0, errors.New("dispatch paused")
	}
	if state != "READY" {
		return 0, fmt.Errorf("dispatch requires READY, found %s", state)
	}
        if e = objectiveLeaseGate(tx, id, n); e != nil {
                return 0, e
        }
        if consumed >= max && reason != preWorkerRetryAuthorizedReason && reason != workerCancelRetryAuthorizedReason && reason != workerAuthRetryAuthorizedReason {
		return 0, errors.New("RETRY_LIMIT_REACHED")
	}
	n++
	if _, e = tx.Exec("INSERT INTO worker_leases VALUES(?,?,?,?)", id, n, owner, now()); e != nil {
		return 0, fmt.Errorf("already leased: %w", e)
	}
	if _, e = tx.Exec("UPDATE work_orders SET state='DISPATCHED',attempt=?,reason='Worker lease acquired' WHERE id=?", n, id); e != nil {
		return 0, e
	}
	if _, e = tx.Exec("INSERT INTO worker_attempts(work_order_id,attempt,worker,started) VALUES(?,?,?,?)", id, n, owner, now()); e != nil {
		return 0, e
	}
	if e = event(tx, id, n, "DISPATCHED", "Worker lease acquired"); e != nil {
		return 0, e
	}
	return n, tx.Commit()
}
func (s *Store) Pause(p bool) error {
	_, e := s.DB.Exec("UPDATE settings SET value=? WHERE key='paused'", fmt.Sprint(p))
	return e
}

type Event struct {
	ID          int64  `json:"id"`
	Timestamp   string `json:"timestamp"`
	WorkOrderID string `json:"work_order_id"`
	Attempt     int    `json:"attempt_id"`
	Type        string `json:"type"`
	Severity    string `json:"severity"`
	Message     string `json:"message"`
	Structured  string `json:"structured_json"`
}

func (s *Store) Events(after int64) ([]Event, error) {
	rows, e := s.DB.Query("SELECT id,timestamp,work_order_id,attempt_id,type,severity,message,structured_json FROM events WHERE id>? ORDER BY id LIMIT 500", after)
	if e != nil {
		return nil, e
	}
	defer rows.Close()
	out := []Event{}
	for rows.Next() {
		var v Event
		if e = rows.Scan(&v.ID, &v.Timestamp, &v.WorkOrderID, &v.Attempt, &v.Type, &v.Severity, &v.Message, &v.Structured); e != nil {
			return nil, e
		}
		out = append(out, v)
	}
	return out, rows.Err()
}
