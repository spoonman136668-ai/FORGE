package plane

import (
	"strings"
	"testing"
	"time"

	"gopkg.in/yaml.v3"
)

func configureTemporaryNoIdleWindow(p *Engine, expires time.Time) {
	p.Config.Autonomy.Enabled = false
	p.Config.Policy.MaxAttempts = 3
	p.Config.Policy.TemporaryNoIdleRetryWindow = TemporaryNoIdleRetryWindow{
		Enabled:   true,
		ExpiresAt: expires.UTC().Format(time.RFC3339),
	}
}

func loadRetryPolicyJobAtAttempt(t *testing.T, p *Engine, w WorkOrder, state string, attempt int, reason string) {
	t.Helper()
	b, err := yaml.Marshal(w)
	if err != nil {
		t.Fatal(err)
	}
	if err = p.Store.Load(b); err != nil {
		t.Fatal(err)
	}
	if _, err = p.Store.DB.Exec("UPDATE work_orders SET state=?,attempt=?,reason=? WHERE id=?", state, attempt, reason, w.ID); err != nil {
		t.Fatal(err)
	}
}

func TestRetryPolicyWindowEngineAllowsAttemptFour(t *testing.T) {
	p, w := setup(t)
	configureTemporaryNoIdleWindow(p, time.Now().UTC().Add(time.Hour))
	p.workers["fake"] = FakeWorker{Fail: true}
	loadRetryPolicyJobAtAttempt(t, p, w, "REJECTED_RETRYABLE", 3, "WORKER_EXIT_NONZERO")

	if err := p.Ready(w.ID); err != nil {
		t.Fatalf("ready attempt four: %v", err)
	}
	ready, err := p.Store.Get(w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if ready.State != "READY" {
		t.Fatalf("attempt four did not clear Ready: state=%s reason=%q", ready.State, ready.Reason)
	}

	if err = p.Dispatch(w.ID); err != nil {
		t.Fatalf("dispatch attempt four: %v", err)
	}
	job := wait(t, p, w.ID)
	if job.Attempt != 4 {
		t.Fatalf("attempt=%d want=4 state=%s reason=%q", job.Attempt, job.State, job.Reason)
	}
	if job.State != "REJECTED_RETRYABLE" {
		t.Fatalf("state=%s want=REJECTED_RETRYABLE reason=%q", job.State, job.Reason)
	}
	if strings.Contains(job.Reason, "RETRY_LIMIT_REACHED") {
		t.Fatalf("attempt four hit old global count gate: %q", job.Reason)
	}
}

func TestRetryPolicyExpiredWindowEngineRestoresAttemptThreeStop(t *testing.T) {
	p, w := setup(t)
	configureTemporaryNoIdleWindow(p, time.Now().UTC().Add(-time.Second))
	loadRetryPolicyJobAtAttempt(t, p, w, "REJECTED_RETRYABLE", 3, "WORKER_EXIT_NONZERO")

	if err := p.Ready(w.ID); err != nil {
		t.Fatalf("ready should durably block rather than return error: %v", err)
	}
	job, err := p.Store.Get(w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if job.State != "BLOCKED" || job.Reason != "RETRY_LIMIT_REACHED" {
		t.Fatalf("expired window did not restore normal cap: state=%s reason=%q", job.State, job.Reason)
	}
}

func TestRetryPolicyDisabledWindowEngineStillStopsAtThree(t *testing.T) {
	p, w := setup(t)
	p.Config.Autonomy.Enabled = false
	p.Config.Policy.MaxAttempts = 3
	p.Config.Policy.TemporaryNoIdleRetryWindow = TemporaryNoIdleRetryWindow{}
	loadRetryPolicyJobAtAttempt(t, p, w, "REJECTED_RETRYABLE", 3, "WORKER_EXIT_NONZERO")

	if err := p.Ready(w.ID); err != nil {
		t.Fatalf("ready should durably block rather than return error: %v", err)
	}
	job, err := p.Store.Get(w.ID)
	if err != nil {
		t.Fatal(err)
	}
	if job.State != "BLOCKED" || job.Reason != "RETRY_LIMIT_REACHED" {
		t.Fatalf("default cap changed: state=%s reason=%q", job.State, job.Reason)
	}
}
