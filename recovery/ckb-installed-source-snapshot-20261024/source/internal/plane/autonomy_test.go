package plane

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"gopkg.in/yaml.v3"
)

func proofFixture(t *testing.T) (*Engine, QueueOrder, []byte) {
	t.Helper()
	p, w := setup(t)
	source := filepath.Join(t.TempDir(), "seed")
	r := p.Config.Repos[w.Repo]
	if e := os.Rename(r.LocalPath, source); e != nil {
		t.Fatal(e)
	}
	r.LocalPath = source
	p.Config.Repos[w.Repo] = r
	q := QueueOrder{Schema: queueSchema, ID: "QUEUE_PROOF", LogicalStage: "QUEUE_PROOF", Kind: "proof", SourceRepo: w.Repo, BaselineRef: w.Baseline.Ref, BaselineSHA: w.Baseline.SHA}
	raw, _ := json.Marshal(q)
	if e := p.QueueSubmit(raw); e != nil {
		t.Fatal(e)
	}
	return p, q, raw
}
func sourceQueue(t *testing.T, p *Engine, w WorkOrder, id string, deps ...string) QueueOrder {
	t.Helper()
	w.ID = id
	w.Worker.Branch = "codex/" + strings.ToLower(id)
	b, e := yaml.Marshal(w)
	if e != nil {
		t.Fatal(e)
	}
	q := QueueOrder{Schema: queueSchema, ID: id, LogicalStage: id, Kind: "source", WorkOrderYAML: string(b), Dependencies: deps}
	raw, _ := json.Marshal(q)
	if e = p.QueueSubmit(raw); e != nil {
		t.Fatal(e)
	}
	if _, e = p.QueueRun(context.Background(), id, "operator", "source", false); e != nil {
		t.Fatal(e)
	}
	return q
}
func testAuthority(p *Engine) {
	p.Config.Autonomy.Enabled = true
	p.authorityVerifier = func(context.Context) error { return nil }
	_ = p.setSetting("autonomy_authority", "plane")
	_ = p.setSetting("autonomy_generation", "1")
}

func TestAutonomyRefusalDoesNotReadBaseline(t *testing.T) {
	p, q, _ := proofFixture(t)
	p.Config.Tools.Git = "unavailable-git"
	r, e := p.QueueRun(context.Background(), q.ID, "none", "dry-run", false)
	if e == nil || r.Reason != "REFUSED_WITHOUT_AUTHORIZATION" || r.Disposition != "pending" {
		t.Fatalf("%+v %v", r, e)
	}
	if _, e = os.Stat(filepath.Join(p.Root, "workorders", "pending", q.ID+".json")); e != nil {
		t.Fatal(e)
	}
	if _, e = os.Stat(filepath.Join(r.Evidence, "status.json")); e != nil {
		t.Fatal(e)
	}
	var n int
	_ = p.Store.DB.QueryRow("SELECT count(*) FROM work_orders").Scan(&n)
	if n != 0 {
		t.Fatal("refusal loaded a native job")
	}
}
func TestAutonomyProofMaterializesExactBaseline(t *testing.T) {
	for _, mode := range []string{"dry-run", "controlled-proof"} {
		t.Run(mode, func(t *testing.T) {
			p, q, _ := proofFixture(t)
			retainWindowsFailureEvidence(t, p.Root)
			seed := p.Config.Repos[q.SourceRepo].LocalPath
			writeTestFile(t, filepath.Join(seed, "later.txt"), "later head must not enter proof\n")
			for _, args := range [][]string{{"add", "later.txt"}, {"-c", "user.name=Test", "-c", "user.email=test@localhost", "commit", "-m", "later head"}} {
				if _, e := git(p.Config.Tools.Git, seed, args...); e != nil {
					t.Fatal(e)
				}
			}
			before, e := p.profileWorkspaceRepoState(context.Background(), seed)
			if e != nil {
				t.Fatal(e)
			}
			result, e := p.QueueRun(context.Background(), q.ID, "test", mode, false)
			if e != nil {
				t.Fatal(e)
			}
			if result.Disposition != "completed" || result.ProductionAccepted {
				t.Fatal(result)
			}
			if _, e = os.Stat(filepath.Join(result.Workspace, "later.txt")); !os.IsNotExist(e) {
				t.Fatal("copied current HEAD instead of baseline")
			}
			if mode == "controlled-proof" {
				head, e := git(p.Config.Tools.Git, result.Workspace, "rev-parse", "HEAD")
				if e != nil || head != q.BaselineSHA {
					t.Fatal(head, e)
				}
			}
			after, e := p.profileWorkspaceRepoState(context.Background(), seed)
			if e != nil || jsonText(before) != jsonText(after) {
				t.Fatal("seed changed", e)
			}
			if _, e = os.Stat(filepath.Join(p.Root, "workorders", "completed", q.ID+".json")); e != nil {
				t.Fatal(e)
			}
		})
	}
}
func TestAutonomyBadBaselineAndDestinationPreservePending(t *testing.T) {
	for _, kind := range []string{"baseline", "destination"} {
		t.Run(kind, func(t *testing.T) {
			p, q, raw := proofFixture(t)
			if kind == "baseline" {
				q.BaselineSHA = strings.Repeat("0", 40)
				raw, _ = json.Marshal(q)
				_ = os.WriteFile(filepath.Join(p.Root, "workorders", "pending", q.ID+".json"), raw, 0600)
			} else {
				path, _ := p.queuePath("completed", q.ID)
				if e := durableNew(path, raw); e != nil {
					t.Fatal(e)
				}
			}
			if _, e := p.QueueRun(context.Background(), q.ID, "test", "dry-run", false); e == nil {
				t.Fatal("expected refusal")
			}
			if _, e := os.Stat(filepath.Join(p.Root, "workorders", "pending", q.ID+".json")); e != nil {
				t.Fatal(e)
			}
		})
	}
}
func TestAutonomyCompetingProofConsumers(t *testing.T) {
	p, q, _ := proofFixture(t)
	var wg sync.WaitGroup
	results := make(chan error, 2)
	for i := 0; i < 2; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			_, e := p.QueueRun(context.Background(), q.ID, "test", "dry-run", false)
			results <- e
		}()
	}
	wg.Wait()
	close(results)
	success := 0
	for e := range results {
		if e == nil {
			success++
		}
	}
	if success != 1 {
		t.Fatalf("successes=%d", success)
	}
}
func TestAutonomyFinalizeRecoveryDoesNotRerun(t *testing.T) {
	p, q, raw := proofFixture(t)
	if _, _, e := p.queueClaim(q.ID, "test", "dry-run"); e != nil {
		t.Fatal(e)
	}
	dst, _ := p.queuePath("completed", q.ID)
	if e := durableNew(dst, raw); e != nil {
		t.Fatal(e)
	}
	receipt := filepath.Join(p.Root, "evidence", "queue", q.ID, "recovered.json")
	result := QueueResult{InputSHA256: digest(raw), Disposition: "completed"}
	receiptRaw, _ := json.Marshal(result)
	if _, e := p.Store.DB.Exec("INSERT INTO queue_receipts VALUES(?,?,?)", q.ID, digest(receiptRaw), receiptRaw); e != nil {
		t.Fatal(e)
	}
	_, e := p.Store.DB.Exec("UPDATE queue_items SET state='FINALIZING',reason='completed',receipt=? WHERE id=?", receipt, q.ID)
	if e != nil {
		t.Fatal(e)
	}
	p.Config.Tools.Git = "never-run"
	if e = p.AutonomyTick(context.Background()); e != nil {
		t.Fatal(e)
	}
	var state string
	_ = p.Store.DB.QueryRow("SELECT state FROM queue_items WHERE id=?", q.ID).Scan(&state)
	if state != "COMPLETED" {
		t.Fatal(state)
	}
}
func TestAutonomySourceAuthorityRefusesBeforeAuthorization(t *testing.T) {
	p, w := setup(t)
	p.Config.Autonomy.Enabled = true
	w.ID = "NO_AUTH"
	rawYAML, _ := yaml.Marshal(w)
	q := QueueOrder{Schema: queueSchema, ID: w.ID, LogicalStage: w.ID, Kind: "source", WorkOrderYAML: string(rawYAML)}
	raw, _ := json.Marshal(q)
	if e := p.QueueSubmit(raw); e != nil {
		t.Fatal(e)
	}
	if _, e := p.QueueRun(context.Background(), q.ID, "operator", "source", false); e == nil {
		t.Fatal("source authorized under original authority")
	}
	var n int
	_ = p.Store.DB.QueryRow("SELECT count(*) FROM queue_items").Scan(&n)
	if n != 0 {
		t.Fatal("refused request left authorized queue item")
	}
}
func TestAutonomyTwoStageContinuationAndExport(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)
	sourceQueue(t, p, w, "STAGE_Z")
	sourceQueue(t, p, w, "STAGE_A", "STAGE_Z")
	for _, id := range []string{"STAGE_Z", "STAGE_A"} {
		if e := p.AutonomyTick(context.Background()); e != nil {
			t.Fatal(e)
		}
		j := wait(t, p, id)
		if j.State != "ACCEPTED" {
			t.Fatalf("%+v", j)
		}
		if e := p.AutonomyTick(context.Background()); e != nil {
			t.Fatal(e)
		}
		var state string
		_ = p.Store.DB.QueryRow("SELECT state FROM queue_items WHERE id=?", id).Scan(&state)
		if state != "COMPLETED" {
			t.Fatal(state)
		}
	}
	out, e := p.ExportCandidateOffline(context.Background(), "STAGE_A")
	if e != nil {
		t.Fatal(e)
	}
	if out["published"] != false || out["accepted_ref_mutated"] != false {
		t.Fatal(out)
	}
	if _, e = p.ExportCandidateOffline(context.Background(), "STAGE_A"); e != nil {
		t.Fatal("idempotent export", e)
	}
}
func TestAutonomyUnknownFailureBlocksWithoutRetry(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)
	p.workers["fake"] = FakeWorker{Fail: true}
	sourceQueue(t, p, w, "FAILED_JOB")
	if e := p.AutonomyTick(context.Background()); e != nil {
		t.Fatal(e)
	}
	wait(t, p, "FAILED_JOB")
	for i := 0; i < 3; i++ {
		if e := p.AutonomyTick(context.Background()); e != nil {
			t.Fatal(e)
		}
	}
	var action string
	_ = p.Store.DB.QueryRow("SELECT action FROM recovery_decisions WHERE work_order_id='FAILED_JOB'").Scan(&action)
	if action != "operator-blocked" {
		t.Fatal(action)
	}
	j, _ := p.Store.Get("FAILED_JOB")
	if j.Attempt != 1 {
		t.Fatal("blind retry")
	}
}
func TestAutonomyContextHashBinding(t *testing.T) {
	p, w := setup(t)
	ref := t.TempDir()
	writeTestFile(t, filepath.Join(ref, "guide.md"), "approved reference")
	p.Config.Repos["knowledge"] = Repo{LocalPath: ref, Mode: "knowledge"}
	w.ContextFiles = []ContextFile{{Repo: "knowledge", Path: "guide.md", SHA256: digest([]byte("approved reference"))}}
	if _, e := p.contextFor(w); e != nil {
		t.Fatal(e)
	}
	writeTestFile(t, filepath.Join(ref, "guide.md"), "changed")
	if _, e := p.contextFor(w); e == nil {
		t.Fatal("stale context accepted")
	}
}
func TestAutonomyControlRequestDeduplicationAndGeneration(t *testing.T) {
	p, _ := setup(t)
	testAuthority(p)
	p.Config.Autonomy.RemoteControl = true
	p.bridge = &WebUIBridge{Config: BridgeConfig{ControlEnabled: true}}
	c := BridgeCommand{ID: "pause-once", Action: "pause", Generation: 1}
	first, e := p.controlRequest(context.Background(), c)
	if e != nil {
		t.Fatal(e)
	}
	second, e := p.controlRequest(context.Background(), c)
	if e != nil || jsonText(first) != jsonText(second) {
		t.Fatal(second, e)
	}
	c.Action = "resume"
	if _, e = p.controlRequest(context.Background(), c); e == nil {
		t.Fatal("changed request reused")
	}
	c.ID = "new-id"
	c.Generation = 2
	if _, e = p.controlRequest(context.Background(), c); e == nil {
		t.Fatal("stale authority accepted")
	}
}
func TestAutonomyDependencyWaitDoesNotLoadWorker(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)
	sourceQueue(t, p, w, "WAITING", "MISSING")
	if e := p.AutonomyTick(context.Background()); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.Get("WAITING"); !errors.Is(e, os.ErrNotExist) && e == nil {
		t.Fatal("premature native job")
	}
}
func TestAutonomyNoProgressRequestsOwnedCancellation(t *testing.T) {
	p, _ := setup(t)
	p.Config.Autonomy.MaxNoProgressSeconds = 1
	ctx, cancel := context.WithCancel(context.Background())
	p.cancels["STALLED"] = cancel
	defer delete(p.cancels, "STALLED")
	_, e := p.Store.DB.Exec("INSERT INTO worker_progress VALUES(?,?)", "STALLED", time.Now().Add(-time.Minute).UTC().Format(time.RFC3339Nano))
	if e != nil {
		t.Fatal(e)
	}
	if e = p.monitorProgress("STALLED"); e != nil {
		t.Fatal(e)
	}
	if ctx.Err() == nil {
		t.Fatal("no progress did not cancel owned process")
	}
}

type repairFixtureWorker struct{ calls int }

func (w *repairFixtureWorker) Name() string { return "fake" }
func (w *repairFixtureWorker) Run(ctx context.Context, dir string, order WorkOrder, out, stderr io.Writer) error {
	w.calls++
	text := "wrong\n"
	if w.calls > 1 {
		text = "candidate produced after bounded repair\n"
	}
	return os.WriteFile(filepath.Join(dir, "demo.txt"), []byte(text), 0600)
}
func TestAutonomyBoundedRepairAndLimit(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)
	worker := &repairFixtureWorker{}
	p.workers["fake"] = worker
	sourceQueue(t, p, w, "REPAIR")
	if e := p.AutonomyTick(context.Background()); e != nil {
		t.Fatal(e)
	}
	j := wait(t, p, "REPAIR")
	if j.State != "REJECTED_RETRYABLE" {
		t.Fatal(j.State, j.Reason)
	}
	if e := p.AutonomyTick(context.Background()); e != nil {
		t.Fatal(e)
	}
	var action string
	_ = p.Store.DB.QueryRow("SELECT action FROM recovery_decisions WHERE work_order_id='REPAIR'").Scan(&action)
	if action != "bounded-repair" {
		t.Fatal(action)
	}
	_, _ = p.Store.DB.Exec("UPDATE queue_items SET next_retry=? WHERE id='REPAIR'", time.Now().Add(-time.Minute).UTC().Format(time.RFC3339Nano))
	if e := p.AutonomyTick(context.Background()); e != nil {
		t.Fatal(e)
	}
	j = wait(t, p, "REPAIR")
	if j.State != "ACCEPTED" || j.Attempt != 2 {
		t.Fatal(j.State, j.Reason, j.Attempt)
	}
	if e := p.AutonomyTick(context.Background()); e != nil {
		t.Fatal(e)
	}
	var n int
	_ = p.Store.DB.QueryRow("SELECT count(*) FROM recovery_decisions WHERE work_order_id='REPAIR'").Scan(&n)
	if n != 1 {
		t.Fatal("duplicate recovery decision")
	}
}
func TestAutonomyNativeAPIQueueAndAuthentication(t *testing.T) {
	p, q, _ := proofFixture(t)
	p.Config.Autonomy.Enabled = true
	handler := p.Handler("test-token")
	request := httptest.NewRequest("GET", "http://127.0.0.1:8791/api/native", nil)
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, request)
	if rr.Code != 401 {
		t.Fatal(rr.Code)
	}
	request = httptest.NewRequest("GET", "http://127.0.0.1:8791/api/native", nil)
	request.Header.Set("Authorization", "Bearer test-token")
	rr = httptest.NewRecorder()
	handler.ServeHTTP(rr, request)
	if rr.Code != 200 || !strings.Contains(rr.Body.String(), q.ID) {
		t.Fatal(rr.Code, rr.Body.String())
	}
	request = httptest.NewRequest("POST", "http://127.0.0.1:8791/api/native", strings.NewReader(`{"action":"run","id":"QUEUE_PROOF","authorization":"none","mode":"dry-run"}`))
	request.Header.Set("Authorization", "Bearer test-token")
	rr = httptest.NewRecorder()
	handler.ServeHTTP(rr, request)
	if rr.Code != 409 || !strings.Contains(rr.Body.String(), "REFUSED_WITHOUT_AUTHORIZATION") {
		t.Fatal(rr.Code, rr.Body.String())
	}
}
func TestAutonomySourceNeedsFocusedContract(t *testing.T) {
	p, w := setup(t)
	w.RequiredTests.FocusedGo = nil
	rawYAML, _ := yaml.Marshal(w)
	q := QueueOrder{Schema: queueSchema, ID: w.ID, LogicalStage: w.ID, Kind: "source", WorkOrderYAML: string(rawYAML)}
	raw, _ := json.Marshal(q)
	if e := p.QueueSubmit(raw); e == nil {
		t.Fatal("source contract without focused tests accepted")
	}
}
func TestAutonomySupervisorSandboxSyntaxBinding(t *testing.T) {
	p, _ := setup(t)
	args := acceptanceSandboxArgs("go.exe", "temp", []string{"test", "./..."})
	p.Config.Autonomy.Enabled = true
	p.Config.Execution.SandboxSyntax = "native"
	got := p.sandboxArgs(args)
	joined := strings.Join(got, " ")
	if strings.Contains(joined, "sandbox windows") || !strings.Contains(joined, "sandbox -- go.exe test") {
		t.Fatal(got)
	}
	if !strings.Contains(joined, "sandbox_workspace_write.network_access=false") {
		t.Fatal("sandbox policy changed")
	}
	p.Config.Execution.SandboxSyntax = "windows-subcommand"
	if !strings.Contains(strings.Join(p.sandboxArgs(args), " "), "sandbox windows --") {
		t.Fatal("subcommand syntax lost")
	}
}

func TestAutonomyAuthorizationBindsContentBeforeClaim(t *testing.T) {
	p, q, _ := proofFixture(t)
	_, e := p.QueueRun(context.Background(), q.ID, "test", "dry-run", false, strings.Repeat("0", 64))
	if e == nil || !strings.Contains(e.Error(), "WORK_ORDER_CONTENT_CHANGED") {
		t.Fatal(e)
	}
	var count int
	if e = p.Store.DB.QueryRow("SELECT count(*) FROM queue_items").Scan(&count); e != nil || count != 0 {
		t.Fatal(count, e)
	}
	if _, e = os.Stat(filepath.Join(p.Root, "workorders", "pending", q.ID+".json")); e != nil {
		t.Fatal(e)
	}
}

func TestAutonomyWrongModeDoesNotClaimQueue(t *testing.T) {
	p, q, _ := proofFixture(t)
	testAuthority(p)
	_, e := p.QueueRun(context.Background(), q.ID, "operator", "source", false)
	if e == nil || !strings.Contains(e.Error(), "QUEUE_KIND_MODE_MISMATCH") {
		t.Fatal(e)
	}
	var count int
	if e = p.Store.DB.QueryRow("SELECT count(*) FROM queue_items").Scan(&count); e != nil || count != 0 {
		t.Fatal(count, e)
	}
}

func TestAutonomyLostAuthorityDoesNotCompleteSource(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)
	sourceQueue(t, p, w, "AUTHORITY_LOST")
	if e := p.AutonomyTick(context.Background()); e != nil {
		t.Fatal(e)
	}
	if j := wait(t, p, "AUTHORITY_LOST"); j.State != "ACCEPTED" {
		t.Fatal(j)
	}
	p.authorityVerifier = func(context.Context) error { return errors.New("AUTHORITY_LOST") }
	if e := p.AutonomyTick(context.Background()); e == nil {
		t.Fatal("queue completed without authority")
	}
	if _, e := os.Stat(filepath.Join(p.Root, "workorders", "pending", "AUTHORITY_LOST.json")); e != nil {
		t.Fatal(e)
	}
}

func TestAutonomyManagedInstallBlocksLegacyExecution(t *testing.T) {
	p, _ := setup(t)
	if e := p.guardLegacyExecution(); e != nil {
		t.Fatal(e)
	}
	writeTestFile(t, filepath.Join(p.Root, "state", "autonomy-managed.json"), "{}")
	if _, e := p.WorkerProofSelectedProfile(context.Background(), "unused"); e == nil || !strings.Contains(e.Error(), "LEGACY_EXECUTION_DISABLED") {
		t.Fatal(e)
	}
	if _, e := p.ReplaySelectedProfile(context.Background(), "unused"); e == nil || !strings.Contains(e.Error(), "LEGACY_EXECUTION_DISABLED") {
		t.Fatal(e)
	}
	if e := p.Serve(); e == nil || !strings.Contains(e.Error(), "LEGACY_EXECUTION_DISABLED") {
		t.Fatal(e)
	}
}

func TestAutonomyProofEvidenceRoundTrip(t *testing.T) {
	p, q, _ := proofFixture(t)
	result, e := p.QueueRun(context.Background(), q.ID, "test", "controlled-proof", false)
	if e != nil {
		t.Fatal(e)
	}
	b, _ := bridgeTest(t)
	p.AttachBridge(b)
	v, e := b.snapshot(context.Background(), BridgeCommand{Action: "evidence", WorkOrderID: q.ID})
	if e != nil || v.(map[string]any)["verified_now"] != true {
		t.Fatal(v, e)
	}
	if e = os.WriteFile(filepath.Join(result.Evidence, "queue-result.json"), []byte("changed"), 0600); e != nil {
		t.Fatal(e)
	}
	if _, e = b.snapshot(context.Background(), BridgeCommand{Action: "evidence", WorkOrderID: q.ID}); e == nil {
		t.Fatal("corrupt proof receipt accepted")
	}
}
