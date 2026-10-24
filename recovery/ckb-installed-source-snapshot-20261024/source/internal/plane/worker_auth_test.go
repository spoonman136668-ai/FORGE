package plane

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"testing"
)

func TestWorkerAuthRetryEvidence(t *testing.T) {
	for _, tc := range []struct {
		name, file, value string
		above             int
		allowed           bool
	}{
		{"legacy", "", "", 0, true},
		{"above_limit", "", "", 2, true},
		{"future", "worker_exit.json", `{"exit_code":1,"failure_class":"WORKER_AUTH_UNAVAILABLE"}`, 0, true},
		{"ordinary", "worker_stderr.log", "ordinary failure", 0, false},
		{"diff", "candidate.diff", "diff --git a/x b/x", 0, false},
		{"files", "changed_files.txt", "x", 0, false},
		{"zero_exit", "worker_exit.json", `{"exit_code":0,"failure_class":"WORKER_EXIT_NONZERO"}`, 0, false},
		{"acceptance", "acceptance_result.json", `{"acceptance_ran":true}`, 0, false},
		{"missing_acceptance_flag", "acceptance_result.json", `{}`, 0, false},
		{"accepted", "acceptance_result.json", `{"acceptance_ran":false,"production_accepted":true}`, 0, false},
		{"identity", "work_order.yaml", "wrong", 0, false},
		{"lease", "", "", 0, false},
		{"hash", "", "", 0, false},
		{"outside", "", "", 0, false},
		{"stale", "", "", 0, false},
	} {
		t.Run(tc.name, func(t *testing.T) {
			p, w := setup(t)
			testAuthority(p)
			w.Worker.Preferred = "codex"
			q := sourceQueue(t, p, w, "AUTH_RETRY")
			// sourceQueue preserves the supplied worker selection.
			if e := p.Store.Load([]byte(q.WorkOrderYAML)); e != nil {
				t.Fatal(e)
			}
			max := p.Config.Policy.MaxAttempts
			n := max + tc.above
			evidence := filepath.Join(p.Root, "evidence", q.ID, fmt.Sprint(n))
			if e := os.MkdirAll(evidence, 0700); e != nil {
				t.Fatal(e)
			}
			files := map[string]string{
				"worker_exit.json":  `{"exit_code":1,"failure_class":"WORKER_EXIT_NONZERO"}`,
				"worker_stdout.log": "", "worker_stderr.log": "refresh_token_invalidated",
				"candidate.diff": "", "changed_files.txt": "\n",
				"acceptance_result.json": `{"acceptance_ran":false}`,
				"work_order.yaml":        q.WorkOrderYAML,
			}
			if tc.file != "" {
				files[tc.file] = tc.value
			}
			for name, value := range files {
				if e := os.WriteFile(filepath.Join(evidence, name), []byte(value), 0600); e != nil {
					t.Fatal(e)
				}
			}
			original, e := Manifest(evidence)
			if e != nil {
				t.Fatal(e)
			}
			exec := func(query string, args ...any) {
				t.Helper()
				if _, e := p.Store.DB.Exec(query, args...); e != nil {
					t.Fatal(e)
				}
			}
			exec("UPDATE work_orders SET state='BLOCKED',attempt=?,reason='WORKER_EXIT_NONZERO',evidence=? WHERE id=?", n, evidence, q.ID)
			exec("INSERT INTO worker_attempts(work_order_id,attempt,worker,started,finished,exit_code) VALUES(?,?,'codex',?,?,1)", q.ID, n, now(), now())
			exec("UPDATE queue_items SET state='FAILED' WHERE id=?", q.ID)
			var hash string
			if e := p.Store.DB.QueryRow("SELECT hash FROM queue_items WHERE id=?", q.ID).Scan(&hash); e != nil {
				t.Fatal(e)
			}
			if tc.name == "hash" {
				hash = "changed"
			}
			raw := []byte(jsonText(QueueResult{WorkOrderID: q.ID, InputSHA256: hash, WorkerLaunchAttempted: true}))
			exec("INSERT OR REPLACE INTO queue_receipts VALUES(?,?,?)", q.ID, digest(raw), raw)
			if tc.name == "lease" {
				exec("INSERT INTO worker_leases VALUES(?,?,?,?)", q.ID, n, "codex", now())
			}
			if tc.name == "outside" {
				exec("UPDATE work_orders SET evidence=? WHERE id=?", t.TempDir(), q.ID)
			}
			if tc.name == "stale" {
				exec("UPDATE work_orders SET attempt=? WHERE id=?", n+1, q.ID)
			}
			v, e := p.QueueRetry(context.Background(), q.ID, "operator", "source")
			if !tc.allowed {
				if e == nil {
					t.Fatal("unsafe auth escape allowed")
				}
				return
			}
			if e != nil {
				t.Fatal(e)
			}
			if v.(map[string]any)["worker_auth_retry_escape"] != true {
				t.Fatal(v)
			}
			exec("UPDATE queue_items SET state='RUNNING' WHERE id=?", q.ID)
			if e := p.Authorize(q.ID); e != nil {
				t.Fatal(e)
			}
			j, e := p.Store.Get(q.ID)
			if e != nil || j.Reason != workerAuthRetryAuthorizedReason {
				t.Fatalf("authorize: %+v %v", j, e)
			}
			if e := p.Ready(q.ID); e != nil {
				t.Fatal(e)
			}
			j, e = p.Store.Get(q.ID)
			if e != nil || j.Reason != workerAuthRetryAuthorizedReason {
				t.Fatalf("ready: %+v %v", j, e)
			}
			next, e := p.Store.Lease(q.ID, "codex", max)
			if e != nil || next != n+1 {
				t.Fatalf("lease: %d %v", next, e)
			}
			if p.Config.Policy.MaxAttempts != max {
				t.Fatal("global limit changed")
			}
			after, e := Manifest(evidence)
			if e != nil || jsonText(original) != jsonText(after) {
				t.Fatal("historical evidence changed", e)
			}
			var events int
			if e := p.Store.DB.QueryRow("SELECT count(*) FROM events WHERE work_order_id=? AND type=?", q.ID, workerAuthRetryAuthorizedReason).Scan(&events); e != nil || events != 1 {
				t.Fatal("missing durable auth reason", e)
			}
		})
	}
}

func TestWorkerAuthClassification(t *testing.T) {
	root := t.TempDir()
	for _, marker := range []string{"token_revoked", "refresh_token_invalidated", "refresh token was revoked", "access token could not be refreshed because your refresh token was revoked"} {
		for _, stream := range []string{"worker_stdout.log", "worker_stderr.log"} {
			for _, name := range []string{"worker_stdout.log", "worker_stderr.log"} {
				if e := os.WriteFile(filepath.Join(root, name), nil, 0600); e != nil {
					t.Fatal(e)
				}
			}
			if e := os.WriteFile(filepath.Join(root, stream), []byte(marker), 0600); e != nil {
				t.Fatal(e)
			}
			if got := workerExitFailure("codex", root, root); got != "WORKER_AUTH_UNAVAILABLE" || retryable(got) {
				t.Fatalf("classification %s", got)
			}
			if got := workerExitFailure("mock", root, root); got != "WORKER_EXIT_NONZERO" {
				t.Fatal(got)
			}
		}
	}

}
