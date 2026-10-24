package plane

import (
	"context"
	"encoding/json"
	"io"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"gopkg.in/yaml.v3"
)

type objectiveResumeWorker struct{}

func (objectiveResumeWorker) Name() string { return "fake" }
func (objectiveResumeWorker) Run(ctx context.Context, dir string, w WorkOrder, out, stderr io.Writer) error {
	b, e := os.ReadFile(filepath.Join(dir, "demo.txt"))
	if e != nil {
		return e
	}
	return os.WriteFile(filepath.Join(dir, "demo.txt"), append(b, []byte("\ncandidate produced by resumed worker\n")...), 0600)
}

func TestObjectiveRetainedContinuationUsesExistingWorkerAndAcceptance(t *testing.T) {
	p, plan := objectiveFixture(t, 2)
	ocPublish(t, p, plan)
	q := plan.Orders[0]
	if e := p.Store.Load([]byte(q.WorkOrderYAML)); e != nil {
		t.Fatal(e)
	}
	if e := p.Authorize(q.ID); e != nil {
		t.Fatal(e)
	}
	j, e := p.Store.Get(q.ID)
	if e != nil {
		t.Fatal(e)
	}
	work, before, e := prepareWorkspace(context.Background(), p.Config.Tools.Git, p.Config.Repos[j.Order.Repo].LocalPath, filepath.Join(p.Root, "workspaces", "retained"), j.Order)
	if e != nil {
		t.Fatal(e)
	}
	ed := filepath.Join(p.Root, "evidence", q.ID, "1")
	if e = os.MkdirAll(ed, 0700); e != nil {
		t.Fatal(e)
	}
	if e = os.WriteFile(filepath.Join(work, "demo.txt"), []byte("useful retained partial work\n"), 0600); e != nil {
		t.Fatal(e)
	}
	if _, e = p.Store.DB.Exec("UPDATE work_orders SET state='BLOCKED',reason='CODEX_QUOTA_EXHAUSTED',attempt=1,workspace=?,evidence=? WHERE id=?", work, ed, q.ID); e != nil {
		t.Fatal(e)
	}
	if _, e = p.Store.DB.Exec("UPDATE queue_items SET state='RUNNING' WHERE id=?", q.ID); e != nil {
		t.Fatal(e)
	}
	if _, e = p.Store.DB.Exec("INSERT INTO worker_attempts VALUES(?,1,'fake',?,?,1)", q.ID, now(), now()); e != nil {
		t.Fatal(e)
	}
	j, e = p.Store.Get(q.ID)
	if e != nil {
		t.Fatal(e)
	}
	if e = writeJSON(filepath.Join(ed, "repo_state_before.json"), before); e != nil {
		t.Fatal(e)
	}
	if _, e = p.capture(j, before); e != nil {
		t.Fatal(e)
	}
	if e = p.Seal(j); e != nil {
		t.Fatal(e)
	}
	manifest, e := os.ReadFile(filepath.Join(ed, "evidence_manifest.json"))
	if e != nil {
		t.Fatal(e)
	}
	ocReconcile(t, p)
	o := ocGet(t, p, plan.ID)
	if o.Status != "WAITING_FOR_EXTERNAL_ORCHESTRATOR" {
		t.Fatal(o)
	}
	p.workers["fake"] = objectiveResumeWorker{}
	ocSteer(t, p, plan.ID, "continue")
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	if e = p.AutonomyTick(ctx); e != nil {
		t.Fatal(e)
	}
	j = wait(t, p, q.ID)
	if j.State != "ACCEPTED" || j.Attempt != 2 || j.Workspace != work {
		t.Fatalf("continuation: %+v", j)
	}
	b, e := os.ReadFile(filepath.Join(work, "demo.txt"))
	if e != nil || !strings.Contains(string(b), "useful retained partial work") {
		t.Fatal("lost retained delta")
	}
	b, e = os.ReadFile(filepath.Join(ed, "evidence_manifest.json"))
	if e != nil || string(b) != string(manifest) {
		t.Fatal("original exhaustion evidence changed")
	}
	if e = p.AutonomyTick(ctx); e != nil {
		t.Fatal(e)
	}
	for i := 0; i < 4; i++ {
		ocReconcile(t, p)
	}
	if ocGet(t, p, plan.ID).Current != plan.Orders[1].ID || ocQueueCount(t, p) != 2 {
		t.Fatal("resumed objective did not advance exactly once")
	}
}

func objectiveFixture(t *testing.T, count int) (*Engine, ObjectivePlan) {
	t.Helper()
	p, w := setup(t)
	testAuthority(p)
	p.Config.Autonomy.ObjectiveController = true
	if e := p.initObjectives(); e != nil {
		t.Fatal(e)
	}
	plan := ObjectivePlan{Schema: objectiveSchema, ID: "OC", Goal: "Bounded source sequence", Envelope: "operator-source-v1"}
	for i := 0; i < count; i++ {
		w.ID = "OC_" + string(rune('A'+i))
		w.Worker.Branch = "codex/" + w.ID
		b, e := yaml.Marshal(w)
		if e != nil {
			t.Fatal(e)
		}
		q := QueueOrder{Schema: queueSchema, ID: w.ID, LogicalStage: w.ID, Kind: "source", WorkOrderYAML: string(b)}
		if i > 0 {
			q.Dependencies = []string{plan.Orders[i-1].ID}
		}
		plan.Orders = append(plan.Orders, q)
	}
	return p, plan
}

func ocCreate(t *testing.T, p *Engine, plan ObjectivePlan) Objective {
	t.Helper()
	v, e := p.ObjectiveControl(context.Background(), 1, ObjectiveRequest{Action: "create", ID: plan.ID, Plan: &plan})
	if e != nil {
		t.Fatal(e)
	}
	return v.(Objective)
}
func ocGet(t *testing.T, p *Engine, id string) Objective {
	t.Helper()
	o, e := p.objectiveGet(id)
	if e != nil {
		t.Fatal(e)
	}
	return o
}
func ocSteer(t *testing.T, p *Engine, id, action string) Objective {
	t.Helper()
	o := ocGet(t, p, id)
	r := ObjectiveRequest{Action: action, ID: id, ExpectedRevision: o.Revision}
	if action == "continue" && o.Handoff != nil {
		r.HandoffSHA256 = digest([]byte(jsonText(o.Handoff)))
	}
	v, e := p.ObjectiveControl(context.Background(), 1, r)
	if e != nil {
		t.Fatal(e)
	}
	return v.(Objective)
}
func ocReconcile(t *testing.T, p *Engine) {
	t.Helper()
	p.queueMu.Lock()
	defer p.queueMu.Unlock()
	if e := p.reconcileObjectives(context.Background()); e != nil {
		t.Fatal(e)
	}
}
func ocQueueCount(t *testing.T, p *Engine) int {
	t.Helper()
	var n int
	if e := p.Store.DB.QueryRow("SELECT count(*) FROM queue_items").Scan(&n); e != nil {
		t.Fatal(e)
	}
	return n
}
func ocPublish(t *testing.T, p *Engine, plan ObjectivePlan) {
	t.Helper()
	ocCreate(t, p, plan)
	ocSteer(t, p, plan.ID, "resume")
	ocReconcile(t, p)
	ocReconcile(t, p)
}

// Fixture accepted state is constructed by the plane's real evidence sealing
// and queue receipt APIs. No worker response is treated as acceptance.
func ocComplete(t *testing.T, p *Engine, id string) {
	t.Helper()
	var raw []byte
	var hash string
	if e := p.Store.DB.QueryRow("SELECT raw,hash FROM queue_items WHERE id=?", id).Scan(&raw, &hash); e != nil {
		t.Fatal(e)
	}
	q, e := p.parseQueue(raw, id)
	if e != nil {
		t.Fatal(e)
	}
	if _, e = p.Store.Get(id); e != nil {
		if e = p.Store.Load([]byte(q.WorkOrderYAML)); e != nil {
			t.Fatal(e)
		}
	}
	ed := filepath.Join(p.Root, "evidence", id, "1")
	if e = os.MkdirAll(ed, 0700); e != nil {
		t.Fatal(e)
	}
	if e = os.WriteFile(filepath.Join(ed, "candidate.diff"), []byte("fixture candidate\n"), 0600); e != nil {
		t.Fatal(e)
	}
	if _, e = p.Store.DB.Exec("UPDATE work_orders SET state='ACCEPTED',reason='LOCAL_CANDIDATE_ACCEPTED',attempt=1,evidence=? WHERE id=?", ed, id); e != nil {
		t.Fatal(e)
	}
	j, e := p.Store.Get(id)
	if e != nil {
		t.Fatal(e)
	}
	if e = p.Seal(j); e != nil {
		t.Fatal(e)
	}
	if e = p.queueFinish(id, QueueResult{WorkOrderID: id, InputSHA256: hash, Disposition: "completed", Authorization: "operator", Mode: "source", Reason: "LOCAL_CANDIDATE_ACCEPTED", Evidence: filepath.Join(p.Root, "evidence", "queue", id, randomID())}); e != nil {
		t.Fatal(e)
	}
}

func TestObjectiveCreatePersistReload(t *testing.T) {
	p, plan := objectiveFixture(t, 2)
	o := ocCreate(t, p, plan)
	if o.Status != "PENDING" || o.Total != 2 || ocQueueCount(t, p) != 0 {
		t.Fatal(o)
	}
	s, e := OpenStore(filepath.Join(p.Root, p.Config.State.SQLitePath))
	if e != nil {
		t.Fatal(e)
	}
	defer s.DB.Close()
	copy := &Engine{Store: s}
	got, e := copy.objectiveGet(o.ID)
	if e != nil || jsonText(got) != jsonText(o) {
		t.Fatalf("%+v %v", got, e)
	}
}

func TestObjectivePauseResumeStopCancel(t *testing.T) {
	for _, action := range []string{"pause", "stop-after-current", "cancel"} {
		t.Run(action, func(t *testing.T) {
			p, plan := objectiveFixture(t, 2)
			ocCreate(t, p, plan)
			ocSteer(t, p, plan.ID, "resume")
			ocReconcile(t, p)
			ocSteer(t, p, plan.ID, action)
			ocReconcile(t, p)
			if ocQueueCount(t, p) != 0 {
				t.Fatal("dispatch crossed steering")
			}
			if action != "cancel" {
				ocSteer(t, p, plan.ID, "resume")
				ocReconcile(t, p)
				if ocQueueCount(t, p) != 1 {
					t.Fatal("resume did not publish")
				}
			}
		})
	}
}

func TestObjectivePauseAfterQueueBeforeDispatch(t *testing.T) {
	p, plan := objectiveFixture(t, 1)
	ocPublish(t, p, plan)
	ocSteer(t, p, plan.ID, "pause")
	p.queueMu.Lock()
	ok, e := p.objectiveMayStart(context.Background(), plan.Orders[0].ID)
	p.queueMu.Unlock()
	if e != nil || ok {
		t.Fatalf("allowed=%v error=%v", ok, e)
	}
	ocSteer(t, p, plan.ID, "resume")
	p.queueMu.Lock()
	ok, e = p.objectiveMayStart(context.Background(), plan.Orders[0].ID)
	p.queueMu.Unlock()
	if e != nil || !ok {
		t.Fatalf("allowed=%v error=%v", ok, e)
	}
}

func TestObjectiveSingleSuccessorCompletionReplay(t *testing.T) {
	p, plan := objectiveFixture(t, 3)
	ocPublish(t, p, plan)
	for _, q := range plan.Orders {
		ocComplete(t, p, q.ID)
		for i := 0; i < 8; i++ {
			ocReconcile(t, p)
		}
	}
	o := ocGet(t, p, plan.ID)
	if o.Status != "COMPLETED" || o.Next != 3 || ocQueueCount(t, p) != 3 {
		t.Fatal(o)
	}
	rev := o.Revision
	for i := 0; i < 10; i++ {
		ocReconcile(t, p)
	}
	if ocGet(t, p, plan.ID).Revision != rev {
		t.Fatal("terminal reconciliation changed state")
	}
}

func TestObjectiveRestartAtIntentAndFilePublication(t *testing.T) {
	for _, filePublished := range []bool{false, true} {
		t.Run(map[bool]string{false: "intent", true: "file"}[filePublished], func(t *testing.T) {
			p, plan := objectiveFixture(t, 1)
			ocCreate(t, p, plan)
			ocSteer(t, p, plan.ID, "resume")
			ocReconcile(t, p)
			if filePublished {
				b, _ := json.Marshal(plan.Orders[0])
				path, e := p.queuePath("pending", plan.Orders[0].ID)
				if e != nil {
					t.Fatal(e)
				}
				if e = durableNew(path, b); e != nil {
					t.Fatal(e)
				}
			}
			// Reopen the same DB using a fresh Engine; the mutex and transient
			// predecessor observation do not survive this restart.
			s, e := OpenStore(filepath.Join(p.Root, p.Config.State.SQLitePath))
			if e != nil {
				t.Fatal(e)
			}
			defer s.DB.Close()
			r := &Engine{Store: s, Config: p.Config, Root: p.Root, authorityVerifier: p.authorityVerifier, cancels: map[string]context.CancelFunc{}}
			ocReconcile(t, r)
			ocReconcile(t, r)
			if ocQueueCount(t, r) != 1 {
				t.Fatal("restart lost/duplicated successor")
			}
		})
	}
}

func TestObjectiveRestartAfterCompletionBeforeSuccessor(t *testing.T) {
	p, plan := objectiveFixture(t, 2)
	ocPublish(t, p, plan)
	ocComplete(t, p, plan.Orders[0].ID)
	s, e := OpenStore(filepath.Join(p.Root, p.Config.State.SQLitePath))
	if e != nil {
		t.Fatal(e)
	}
	defer s.DB.Close()
	r := &Engine{Store: s, Config: p.Config, Root: p.Root, authorityVerifier: p.authorityVerifier, cancels: map[string]context.CancelFunc{}}
	for i := 0; i < 8; i++ {
		ocReconcile(t, r)
	}
	if ocQueueCount(t, r) != 2 || ocGet(t, r, plan.ID).Current != plan.Orders[1].ID {
		t.Fatal("completion restart failed")
	}
}

func TestObjectiveRepairReplayDoesNotDuplicate(t *testing.T) {
	p, plan := objectiveFixture(t, 2)
	ocPublish(t, p, plan)
	if _, e := p.Store.DB.Exec("UPDATE queue_items SET state='RETRY_WAIT',reason='bounded-repair' WHERE id=?", plan.Orders[0].ID); e != nil {
		t.Fatal(e)
	}
	for i := 0; i < 4; i++ {
		ocReconcile(t, p)
	}
	if ocQueueCount(t, p) != 1 {
		t.Fatal("advanced before repair acceptance")
	}
	ocComplete(t, p, plan.Orders[0].ID)
	for i := 0; i < 8; i++ {
		ocReconcile(t, p)
	}
	if ocQueueCount(t, p) != 2 {
		t.Fatal("repair replay duplicated successor")
	}
}

func TestObjectiveHardFailuresRemainBlocked(t *testing.T) {
	for _, reason := range []string{"SOURCE_HYGIENE_FAILED", "POLICY_REJECTED", "AUTHORIZATION_BLOCKED", "STALE_LEASE", "UNKNOWN_FAILURE", "CODEX_PROVIDER_UNAVAILABLE"} {
		t.Run(reason, func(t *testing.T) {
			p, plan := objectiveFixture(t, 2)
			ocPublish(t, p, plan)
			if _, e := p.Store.DB.Exec("UPDATE queue_items SET state='BLOCKED',reason=? WHERE id=?", reason, plan.Orders[0].ID); e != nil {
				t.Fatal(e)
			}
			ocReconcile(t, p)
			o := ocGet(t, p, plan.ID)
			if o.Status != "BLOCKED" || o.Blocker != reason || ocQueueCount(t, p) != 1 {
				t.Fatal(o)
			}
			if _, e := p.ObjectiveControl(context.Background(), 1, ObjectiveRequest{Action: "resume", ID: o.ID, ExpectedRevision: o.Revision}); e == nil {
				t.Fatal("resume cleared hard block")
			}
		})
	}
}

func TestObjectiveGenerationAndPolicyMismatch(t *testing.T) {
	for _, what := range []string{"generation", "contract", "unknown"} {
		t.Run(what, func(t *testing.T) {
			p, plan := objectiveFixture(t, 1)
			ocCreate(t, p, plan)
			ocSteer(t, p, plan.ID, "resume")
			ocReconcile(t, p)
			switch what {
			case "generation":
				if e := p.setSetting("autonomy_generation", "2"); e != nil {
					t.Fatal(e)
				}
			case "contract":
				p.Config.Policy.MaxAttempts++
			case "unknown":
				if _, e := p.Store.DB.Exec("UPDATE objective_stages SET state='SURPRISE'"); e != nil {
					t.Fatal(e)
				}
			}
			ocReconcile(t, p)
			if ocQueueCount(t, p) != 0 || ocGet(t, p, plan.ID).Status != "BLOCKED" {
				t.Fatal("failed open")
			}
		})
	}
}

func TestObjectivePriorityAndUnrelatedActiveWork(t *testing.T) {
	p, a := objectiveFixture(t, 1)
	b := a
	b.ID = "OC2"
	b.Orders = append([]QueueOrder(nil), a.Orders...)
	b.Orders[0].ID = "OTHER"
	b.Orders[0].LogicalStage = "OTHER"
	w, e := ParseOrder([]byte(b.Orders[0].WorkOrderYAML))
	if e != nil {
		t.Fatal(e)
	}
	w.ID = "OTHER"
	w.Worker.Branch = "codex/other"
	raw, _ := yaml.Marshal(w)
	b.Orders[0].WorkOrderYAML = string(raw)
	ocCreate(t, p, a)
	ocCreate(t, p, b)
	ocSteer(t, p, a.ID, "resume")
	o := ocSteer(t, p, b.ID, "resume")
	priority := 10
	if _, e = p.ObjectiveControl(context.Background(), 1, ObjectiveRequest{Action: "priority", ID: o.ID, ExpectedRevision: o.Revision, Priority: &priority}); e != nil {
		t.Fatal(e)
	}
	ocReconcile(t, p)
	ocReconcile(t, p)
	if ocGet(t, p, b.ID).Current != "OTHER" || ocGet(t, p, a.ID).Current != "" {
		t.Fatal("priority did not choose idle successor")
	}
	priority = 100
	o = ocGet(t, p, a.ID)
	if _, e = p.ObjectiveControl(context.Background(), 1, ObjectiveRequest{Action: "priority", ID: o.ID, ExpectedRevision: o.Revision, Priority: &priority}); e != nil {
		t.Fatal(e)
	}
	ocReconcile(t, p)
	if ocQueueCount(t, p) != 1 {
		t.Fatal("priority preempted unrelated work")
	}
}

func TestObjectiveConcurrentPauseAndReconcile(t *testing.T) {
	p, plan := objectiveFixture(t, 1)
	ocCreate(t, p, plan)
	ocSteer(t, p, plan.ID, "resume")
	ocReconcile(t, p)
	o := ocGet(t, p, plan.ID)
	var wg sync.WaitGroup
	errs := make(chan error, 2)
	wg.Add(2)
	go func() {
		defer wg.Done()
		p.queueMu.Lock()
		defer p.queueMu.Unlock()
		errs <- p.reconcileObjectives(context.Background())
	}()
	go func() {
		defer wg.Done()
		_, e := p.ObjectiveControl(context.Background(), 1, ObjectiveRequest{Action: "pause", ID: o.ID, ExpectedRevision: o.Revision})
		errs <- e
	}()
	wg.Wait()
	close(errs)
	for e := range errs {
		if e != nil && !strings.Contains(e.Error(), "OBJECTIVE_REVISION_CONFLICT") {
			t.Fatal(e)
		}
	}
	// A stale steering command is explicitly rejected, never silently lost.
	if !ocGet(t, p, plan.ID).Paused {
		ocSteer(t, p, plan.ID, "pause")
	}
	ocReconcile(t, p)
	p.queueMu.Lock()
	allowed, e := p.objectiveMayStart(context.Background(), plan.Orders[0].ID)
	p.queueMu.Unlock()
	if allowed || e != nil {
		t.Fatalf("pause lost: %v %v", allowed, e)
	}
}

func TestObjectiveStopAfterAcceptance(t *testing.T) {
	p, plan := objectiveFixture(t, 2)
	ocPublish(t, p, plan)
	ocSteer(t, p, plan.ID, "stop-after-current")
	ocComplete(t, p, plan.Orders[0].ID)
	for i := 0; i < 5; i++ {
		ocReconcile(t, p)
	}
	o := ocGet(t, p, plan.ID)
	if o.Status != "PAUSED" || o.Next != 1 || ocQueueCount(t, p) != 1 {
		t.Fatal(o)
	}
}

func TestObjectiveUnverifiedPassCannotAdvance(t *testing.T) {
	p, plan := objectiveFixture(t, 2)
	ocPublish(t, p, plan)
	if _, e := p.Store.DB.Exec("UPDATE queue_items SET state='COMPLETED'"); e != nil {
		t.Fatal(e)
	}
	ocReconcile(t, p)
	if ocGet(t, p, plan.ID).Status != "BLOCKED" || ocQueueCount(t, p) != 1 {
		t.Fatal("trusted unverified pass")
	}
}

func TestObjectiveExhaustionPreservesStateAndBlocksRetry(t *testing.T) {
	p, plan := objectiveFixture(t, 2)
	ocPublish(t, p, plan)
	q := plan.Orders[0]
	if e := p.Store.Load([]byte(q.WorkOrderYAML)); e != nil {
		t.Fatal(e)
	}
	work := filepath.Join(p.Root, "workspaces", "retained")
	ed := filepath.Join(p.Root, "evidence", q.ID, "1")
	for _, dir := range []string{work, ed} {
		if e := os.MkdirAll(dir, 0700); e != nil {
			t.Fatal(e)
		}
	}
	if e := os.WriteFile(filepath.Join(work, "useful.txt"), []byte("retain this delta"), 0600); e != nil {
		t.Fatal(e)
	}
	if e := os.WriteFile(filepath.Join(ed, "candidate.diff"), []byte("retained diff"), 0600); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE work_orders SET state='BLOCKED',reason='CODEX_QUOTA_EXHAUSTED',attempt=1,workspace=?,evidence=? WHERE id=?", work, ed, q.ID); e != nil {
		t.Fatal(e)
	}
	if _, e := p.Store.DB.Exec("UPDATE queue_items SET state='RUNNING' WHERE id=?", q.ID); e != nil {
		t.Fatal(e)
	}
	j, e := p.Store.Get(q.ID)
	if e != nil {
		t.Fatal(e)
	}
	if e = writeJSON(filepath.Join(ed, "candidate_inventory.json"), []CandidateEntry{{Path: "useful.txt", SHA256: digest([]byte("retain this delta"))}}); e != nil {
		t.Fatal(e)
	}
	if e = p.Seal(j); e != nil {
		t.Fatal(e)
	}
	ocReconcile(t, p)
	o := ocGet(t, p, plan.ID)
	if o.Status != "WAITING_FOR_EXTERNAL_ORCHESTRATOR" || o.Handoff == nil || o.Handoff.Workspace != work || o.Handoff.DeltaSHA != digest([]byte("retained diff")) {
		t.Fatal(o)
	}
	if _, e = p.QueueRetry(context.Background(), q.ID, "operator", "source"); e == nil {
		t.Fatal("quota entered generic retry")
	}
	if _, e = p.ObjectiveControl(context.Background(), 1, ObjectiveRequest{Action: "continue", ID: o.ID, ExpectedRevision: o.Revision}); e == nil {
		t.Fatal("unaccepted external continuation advanced")
	}
	for i := 0; i < 4; i++ {
		ocReconcile(t, p)
	}
	b, e := os.ReadFile(filepath.Join(work, "useful.txt"))
	if e != nil || string(b) != "retain this delta" || ocQueueCount(t, p) != 1 {
		t.Fatal("retained state changed")
	}

}

func TestObjectiveCodexClassification(t *testing.T) {
	for _, tc := range []struct {
		name, log string
		want      bool
	}{
		{"explicit", `{"type":"error","code":"CODEX_QUOTA_EXHAUSTED"}`, true},
		{"usage", `{"type":"error","message":"You've hit your usage limit. Try later."}`, true},
		{"nested", `{"type":"turn.failed","error":{"code":"insufficient_quota"}}`, true},
		{"source_quote", `{"type":"item.completed","message":"You've hit your usage limit."}`, false},
		{"provider_unavailable", `{"type":"error","code":"service_unavailable"}`, false},
		{"plain_text", "CODEX_QUOTA_EXHAUSTED in source snippet", false},
	} {
		t.Run(tc.name, func(t *testing.T) {
			dir := t.TempDir()
			if e := os.WriteFile(filepath.Join(dir, "worker_stdout.log"), []byte(tc.log), 0600); e != nil {
				t.Fatal(e)
			}
			if got := codexExhaustion(dir); got != tc.want {
				t.Fatalf("got %v want %v", got, tc.want)
			}
		})
	}
	if retryable("CODEX_QUOTA_EXHAUSTED") {
		t.Fatal("quota must not be retryable")
	}
}

func TestObjectiveDisabledAndStrictInput(t *testing.T) {
	p, plan := objectiveFixture(t, 1)
	p.Config.Autonomy.ObjectiveController = false
	if _, e := p.ObjectiveControl(context.Background(), 1, ObjectiveRequest{Action: "create", ID: plan.ID, Plan: &plan}); e == nil {
		t.Fatal("disabled feature accepted create")
	}
	for _, raw := range []string{`{"action":"pause","action":"resume","objective_id":"OC","expected_revision":1}`, `{"action":"pause","objective_id":"OC","expected_revision":1,"shell":"go"}`} {
		var r ObjectiveRequest
		if e := bridgeDecode([]byte(raw), &r); e == nil {
			t.Fatal("ambiguous input accepted")
		}
	}
}

func TestObjectiveMailboxSteeringReplayAndGeneration(t *testing.T) {
	p, plan := objectiveFixture(t, 1)
	p.Config.Autonomy.RemoteControl = true
	b, m := bridgeTest(t)
	b.Config.ControlEnabled = true
	p.AttachBridge(b)
	c := bridgeTestCommand("objective-create", "objective")
	c.Generation = 1
	c.Objective = &ObjectiveRequest{Action: "create", ID: plan.ID, Plan: &plan}
	putCommand(m, c)
	if e := b.Once(context.Background()); e != nil {
		t.Fatal(e)
	}
	r := getResult(t, m, c.ID)
	if r.Status != "completed" && r.Status != "succeeded" {
		t.Fatalf("mailbox result: %+v", r)
	}
	o := ocGet(t, p, plan.ID)
	rev := o.Revision
	if e := b.Once(context.Background()); e != nil {
		t.Fatal(e)
	}
	if ocGet(t, p, plan.ID).Revision != rev {
		t.Fatal("mailbox replay changed objective")
	}
	c = bridgeTestCommand("objective-resume", "objective")
	c.Generation = 1
	c.Objective = &ObjectiveRequest{Action: "resume", ID: plan.ID, ExpectedRevision: rev}
	putCommand(m, c)
	if e := b.Once(context.Background()); e != nil {
		t.Fatal(e)
	}
	if ocGet(t, p, plan.ID).Status != "RUNNING" {
		t.Fatal("remote resume missing")
	}
	c = bridgeTestCommand("objective-stale", "objective")
	c.Generation = 2
	c.Objective = &ObjectiveRequest{Action: "cancel", ID: plan.ID, ExpectedRevision: ocGet(t, p, plan.ID).Revision}
	putCommand(m, c)
	if e := b.Once(context.Background()); e != nil {
		t.Fatal(e)
	}
	if ocGet(t, p, plan.ID).Status == "CANCELLED" {
		t.Fatal("stale generation cancelled objective")
	}
}

func TestObjectiveLeaseTransactionHonorsLatePause(t *testing.T) {
	p, plan := objectiveFixture(t, 1)
	ocPublish(t, p, plan)
	q := plan.Orders[0]
	if e := p.Store.Load([]byte(q.WorkOrderYAML)); e != nil {
		t.Fatal(e)
	}
	if e := p.Authorize(q.ID); e != nil {
		t.Fatal(e)
	}
	if e := p.Ready(q.ID); e != nil {
		t.Fatal(e)
	}
	p.queueMu.Lock()
	allowed, e := p.objectiveMayStart(context.Background(), q.ID)
	p.queueMu.Unlock()
	if e != nil || !allowed {
		t.Fatal(e)
	}
	ocSteer(t, p, plan.ID, "pause")
	if _, e = p.Store.Lease(q.ID, "test", p.Config.Policy.MaxAttempts); e == nil {
		t.Fatal("lease crossed late pause")
	}
}

func TestObjectiveDisableCannotReleaseQueuedObjective(t *testing.T) {
	p, plan := objectiveFixture(t, 1)
	ocPublish(t, p, plan)
	p.Config.Autonomy.ObjectiveController = false
	ok, e := p.objectiveMayStart(context.Background(), plan.Orders[0].ID)
	if e != nil || ok {
		t.Fatalf("disabled queue escaped: %v %v", ok, e)
	}
}

func TestObjectiveCrashDuringExhaustionCaptureRetainsPartialEvidence(t *testing.T) {
	p, plan := objectiveFixture(t, 1)
	w, e := ParseOrder([]byte(plan.Orders[0].WorkOrderYAML))
	if e != nil {
		t.Fatal(e)
	}
	w.Worker.Preferred = "codex"
	raw, _ := yaml.Marshal(w)
	plan.Orders[0].WorkOrderYAML = string(raw)
	ocPublish(t, p, plan)
	q := plan.Orders[0]
	if e = p.Store.Load([]byte(q.WorkOrderYAML)); e != nil {
		t.Fatal(e)
	}
	ed := filepath.Join(p.Root, "evidence", q.ID, "1")
	work := filepath.Join(p.Root, "workspaces", "partial")
	for _, dir := range []string{ed, work} {
		if e = os.MkdirAll(dir, 0700); e != nil {
			t.Fatal(e)
		}
	}
	if e = os.WriteFile(filepath.Join(ed, "worker_stdout.log"), []byte(`{"type":"error","code":"usage_limit_reached"}`), 0600); e != nil {
		t.Fatal(e)
	}
	if e = os.WriteFile(filepath.Join(work, "partial.txt"), []byte("keep"), 0600); e != nil {
		t.Fatal(e)
	}
	if _, e = p.Store.DB.Exec("UPDATE work_orders SET state='ENGINEERING',attempt=1,workspace=?,evidence=? WHERE id=?", work, ed, q.ID); e != nil {
		t.Fatal(e)
	}
	if e = p.recoverInterrupted(); e != nil {
		t.Fatal(e)
	}
	o := ocGet(t, p, plan.ID)
	if o.Status != "WAITING_FOR_EXTERNAL_ORCHESTRATOR" || o.Handoff == nil || o.Handoff.EvidenceComplete {
		t.Fatal(o)
	}
	for i := 0; i < 3; i++ {
		ocReconcile(t, p)
	}
	j, e := p.Store.Get(q.ID)
	if e != nil || j.State != "BLOCKED" || j.Workspace != work {
		t.Fatalf("%+v %v", j, e)
	}
	if _, e = p.QueueRetry(context.Background(), q.ID, "operator", "source"); e == nil {
		t.Fatal("partial exhaustion entered blind retry")
	}
}

func TestObjectiveQueuePublicationRollbackIsReplayable(t *testing.T) {
	p, plan := objectiveFixture(t, 1)
	ocCreate(t, p, plan)
	ocSteer(t, p, plan.ID, "resume")
	ocReconcile(t, p)
	if _, e := p.Store.DB.Exec("CREATE TRIGGER oc_fail BEFORE UPDATE ON objectives BEGIN SELECT RAISE(ABORT,'injected commit boundary'); END;"); e != nil {
		t.Fatal(e)
	}
	p.queueMu.Lock()
	e := p.reconcileObjectives(context.Background())
	p.queueMu.Unlock()
	if e == nil {
		t.Fatal("fault did not fire")
	}
	if ocQueueCount(t, p) != 0 || ocGet(t, p, plan.ID).Current != "" {
		t.Fatal("partial transaction became authoritative")
	}
	if _, e = p.Store.DB.Exec("DROP TRIGGER oc_fail"); e != nil {
		t.Fatal(e)
	}
	ocReconcile(t, p)
	ocReconcile(t, p)
	if ocQueueCount(t, p) != 1 {
		t.Fatal("rollback recovery duplicated/lost work")
	}
}

type objectiveBlockingWorker struct{ started chan struct{} }

func (objectiveBlockingWorker) Name() string { return "fake" }
func (w objectiveBlockingWorker) Run(ctx context.Context, dir string, o WorkOrder, out, stderr io.Writer) error {
	close(w.started)
	<-ctx.Done()
	return ctx.Err()
}
func TestObjectiveCancelOwnedWorkerPreventsSuccessor(t *testing.T) {
	p, plan := objectiveFixture(t, 2)
	ocPublish(t, p, plan)
	started := make(chan struct{})
	p.workers["fake"] = objectiveBlockingWorker{started: started}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	if e := p.AutonomyTick(ctx); e != nil {
		t.Fatal(e)
	}
	select {
	case <-started:
	case <-ctx.Done():
		t.Fatal(ctx.Err())
	}
	ocSteer(t, p, plan.ID, "cancel")
	_ = wait(t, p, plan.Orders[0].ID)
	for i := 0; i < 3; i++ {
		ocReconcile(t, p)
	}
	if ocGet(t, p, plan.ID).Status != "CANCELLED" || ocQueueCount(t, p) != 1 {
		t.Fatal("cancelled objective advanced")
	}
}
