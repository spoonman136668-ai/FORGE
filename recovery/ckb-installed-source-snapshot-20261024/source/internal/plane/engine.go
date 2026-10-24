package plane

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"time"
)

type Engine struct {
	shuttingDown      bool
	shutdown          context.CancelFunc
	controllerLoop    bool
	Store             *Store
	Config            Config
	Root              string
	Profile           *DispatchProfile
	bridge            *WebUIBridge
	authorityVerifier func(context.Context) error
	queueMu           sync.Mutex
	mu                sync.Mutex
	cancels           map[string]context.CancelFunc
	cancelReasons     map[string]string
	workers           map[string]Worker
	runner            ProcessRunner
	shadowRunner      ProcessRunner
	shadowSlots       chan struct{}
	shadowWG          sync.WaitGroup
	localOperations   *LocalOperationRegistry
}

func NewEngine(c Config, root string) (*Engine, error) {
	ip := net.ParseIP(c.Server.Bind)
	if ip == nil || !ip.IsLoopback() || c.Server.Port < 1 || c.Server.Port > 65535 {
		return nil, errors.New("CONFIG_INVALID: valid loopback address and port required")
	}
	if c.Policy.AcceptedRefMutation || c.Policy.RuntimeLaunchAllowed || c.Policy.ArbitraryShell {
		return nil, errors.New("CONFIG_INVALID: prohibited policy cannot be enabled in v1")
	}
	if c.Policy.MaxAttempts < 1 || c.Policy.MaxAttempts > 10 {
		return nil, errors.New("CONFIG_INVALID: max attempts must be 1..10")
	}
	root, e := filepath.Abs(root)
	if e != nil {
		return nil, e
	}
	var selectedProfile *DispatchProfile
	if c.Profile.Name != "" {
		profile, err := LoadDispatchProfile(root, c.Profile.Name)
		if err != nil {
			return nil, err
		}
		c, err = ApplyDispatchProfile(c, profile)
		if err != nil {
			return nil, err
		}
		selectedProfile = &profile
	}
	db := c.State.SQLitePath
	if db == "" {
		return nil, errors.New("CONFIG_INVALID: sqlite_path required")
	}
	if !filepath.IsAbs(db) {
		db = filepath.Join(root, db)
	}
	s, e := OpenStore(db)
	if e != nil {
		return nil, e
	}
	p := &Engine{Store: s, Config: c, Root: root, Profile: selectedProfile, cancels: map[string]context.CancelFunc{}, cancelReasons: map[string]string{}, workers: map[string]Worker{"fake": FakeWorker{}, "codex": CodexAdapter{}}}
	for k, r := range c.Repos {
		if r.LocalPath != "" && !filepath.IsAbs(r.LocalPath) {
			r.LocalPath = filepath.Join(root, r.LocalPath)
			c.Repos[k] = r
		}
		if _, e = s.DB.Exec("INSERT OR REPLACE INTO repo_registry VALUES(?,?)", k, jsonText(r)); e != nil {
			s.DB.Close()
			return nil, e
		}
	}
	for k, v := range map[string]string{"git": c.Tools.Git, "go": c.Tools.Go, "powershell": c.Tools.Powershell, "codex": c.Tools.Codex, "node": c.Tools.Node} {
		if _, e = s.DB.Exec("INSERT OR REPLACE INTO tool_registry VALUES(?,?)", k, v); e != nil {
			s.DB.Close()
			return nil, e
		}
	}
	p.Config = c
	p.runner = SupervisedRunner{}
	p.shadowRunner = SupervisedRunner{HostEnv: minimalEnv()}
	p.shadowSlots = make(chan struct{}, openCodeShadowCapacity(c.Advisory.OpenCode.Shadow.MaxConcurrent))
	if p.Config.WinglessStage1.Enabled {
		if e := p.RegisterWinglessStage1(p.Config.WinglessStage1.registered()); e != nil {
			s.DB.Close()
			return nil, e
		}
	}
	if c.Execution.LocalOperationsConfig != "" {
		registry, err := LoadLocalOperationRegistry(root, c, c.Execution.LocalOperationsConfig)
		if err != nil {
			s.DB.Close()
			return nil, err
		}
		p.localOperations = registry
	}
	if e := p.initAutonomy(); e != nil {
		s.DB.Close()
		return nil, e
	}
	if e := p.initObjectives(); e != nil {
		s.DB.Close()
		return nil, e
	}
	if e := p.validateMindPalaceAutoDiscovery(); e != nil {
		s.DB.Close()
		return nil, e
	}
	return p, nil
}

// RunController is the queue-consuming controller entrypoint. The legacy serve
// command remains an HTTP/status surface only and must not dispatch queued source
// work merely because the WebUI bridge is up.
func (p *Engine) RunController() error {
	p.controllerLoop = true
	return p.Serve()
}

func (p *Engine) shouldRunAutonomyLoop() bool {
	return p.Config.Autonomy.Enabled && p.controllerLoop
}

func (p *Engine) materializationContext() (context.Context, context.CancelFunc) {
	timeout := p.attemptTimeout()
	if timeout <= 0 {
		timeout = 20 * time.Minute
	}
	if timeout > 20*time.Minute {
		timeout = 20 * time.Minute
	}
	return context.WithTimeout(context.Background(), timeout)
}

func LoadConfig(file string) (Config, error) {
	var c Config
	b, e := os.ReadFile(file)
	if e != nil {
		return c, e
	}
	e = decodeYAML(b, &c)
	return c, e
}
func (p *Engine) Ready(id string) error {
	var leased int
	if e := p.Store.DB.QueryRow("SELECT count(*) FROM worker_leases WHERE work_order_id=?", id).Scan(&leased); e != nil {
		return e
	}
	if leased > 0 {
		return errors.New("ATTEMPT_STILL_OWNED")
	}
	j, e := p.Store.Get(id)
	if e != nil {
		return e
	}
	if j.State != "AUTHORIZED" && j.State != "REJECTED_RETRYABLE" {
		return errors.New("requires AUTHORIZED or REJECTED_RETRYABLE")
	}
	preWorkerRetryEscape := j.Reason == preWorkerRetryAuthorizedReason
	workerCancelRetryEscape := j.Reason == workerCancelRetryAuthorizedReason
	workerAuthRetryEscape := j.Reason == workerAuthRetryAuthorizedReason
	retryDecision := p.retryDecisionNow(id, j.Attempt, j.Reason)
	if retryDecision.HardStop && !preWorkerRetryEscape && !workerCancelRetryEscape && !workerAuthRetryEscape {
		return p.Store.Move(id, "BLOCKED", "RETRY_LIMIT_REACHED")
	}
	if e = p.verifyContract(j.Order); e != nil {
		return e
	}
	if e = p.ensureLocalCandidateBaseline(context.Background(), j.Order); e != nil {
		_ = p.Store.Move(id, "BLOCKED", e.Error())
		return e
	}
	r, ok := p.Config.Repos[j.Order.Repo]
	if !ok {
		return p.Store.Move(id, "BLOCKED", "REPO_UNAVAILABLE")
	}
	if e = checkRepo(p.Config.Tools.Git, r, j.Order); e != nil {
		_ = p.Store.Move(id, "BLOCKED", e.Error())
		return e
	}
	if e = p.validateBaselineAcceptanceContract(r, j.Order); e != nil {
		_ = p.Store.Move(id, "BLOCKED", e.Error())
		return e
	}
	readyReason := "Baseline verified; awaiting dispatch"
	if preWorkerRetryEscape {
		readyReason = preWorkerRetryAuthorizedReason
	} else if workerCancelRetryEscape {
		readyReason = workerCancelRetryAuthorizedReason
	} else if workerAuthRetryEscape {
		readyReason = workerAuthRetryAuthorizedReason
	}
	return p.Store.Move(id, "READY", readyReason)
}
func (p *Engine) Dispatch(id string) error {
	if allowed, e := p.objectiveMayStart(context.Background(), id); e != nil {
		return e
	} else if !allowed {
		return errors.New("OBJECTIVE_DISPATCH_HELD")
	}
	if p.Config.Autonomy.Enabled {
		if e := p.sourceAuthority(context.Background()); e != nil {
			return e
		}
		var state, auth string
		if e := p.Store.DB.QueryRow("SELECT state,authorization FROM queue_items WHERE id=?", id).Scan(&state, &auth); e != nil || state != "RUNNING" || auth != "operator" {
			return errors.New("NATIVE_QUEUE_AUTHORIZATION_REQUIRED")
		}
	}
	p.mu.Lock()
	defer p.mu.Unlock()
	if p.shuttingDown {
		return errors.New("CONTROLLER_STOPPING")
	}
	j, e := p.Store.Get(id)
	if e != nil {
		return e
	}
	if j.State == "AUTHORIZED" {
		if e = p.Ready(id); e != nil {
			return e
		}
		j, e = p.Store.Get(id)
		if e != nil {
			return e
		}
	}
	if j.State != "READY" {
		return fmt.Errorf("dispatch requires READY; %s", j.State)
	}
	r := p.Config.Repos[j.Order.Repo]
	if _, exists := p.workers[j.Order.Worker.Preferred]; !exists {
		return errors.New("WORKER_UNAVAILABLE")
	}
	switch j.Order.Worker.Preferred {
	case "codex":
		if e = p.realPreflight(j.Order); e != nil {
			return e
		}
	case "fake":
		if r.Mode != "demo" {
			return errors.New("CONFIG_INVALID: fake worker requires an explicit demo repository")
		}
	case winglessStage1RegisteredWorkerName:
		// The Stage-1 worker performs its own hash-pinned service/model preflight.
	default:
		return errors.New("WORKER_UNAVAILABLE")
	}
	if _, active := p.cancels[id]; active {
		return errors.New("ATTEMPT_STILL_OWNED")
	}

	if e = p.ensureLocalCandidateBaseline(context.Background(), j.Order); e != nil {
		_ = p.Store.Move(id, "BLOCKED", e.Error())
		return e
	}
	if e = checkRepo(p.Config.Tools.Git, r, j.Order); e != nil {
		_ = p.Store.Move(id, "BLOCKED", e.Error())
		return e
	}
	dispatchRetryDecision := p.retryDecisionNow(id, j.Attempt, j.Reason)
	n, e := p.Store.Lease(id, j.Order.Worker.Preferred, dispatchRetryDecision.EffectiveBudget)
	if e != nil {
		return e
	}
	ctx, cancel := context.WithTimeout(context.Background(), p.attemptTimeout())
	p.cancels[id] = cancel
	if p.cancelReasons == nil {
		p.cancelReasons = map[string]string{}
	}
	p.cancelReasons[id] = ""
	go p.run(ctx, id, n)
	return nil
}
func (p *Engine) run(ctx context.Context, id string, n int) {
	defer func() {
		p.mu.Lock()
		if c := p.cancels[id]; c != nil {
			c()
		}
		delete(p.cancels, id)
		delete(p.cancelReasons, id)
		p.mu.Unlock()
	}()
	j, e := p.Store.Get(id)
	if e != nil {
		return
	}
	workerLaunchAttempted := false
	queueBefore, jobBefore := p.queueStates(id)
	defer func() {
		if !p.Config.Autonomy.Enabled || workerLaunchAttempted {
			return
		}
		current, er := p.Store.Get(id)
		if er != nil || (current.State != "BLOCKED" && current.State != "REJECTED_RETRYABLE") {
			return
		}
		var item QueueItem
		item.ID = id
		if er = p.Store.DB.QueryRow("SELECT hash,mode,authorization FROM queue_items WHERE id=?", id).Scan(&item.Hash, &item.Mode, &item.Authorization); er != nil {
			return
		}
		if er = p.preWorkerFailure(item, queueBefore, jobBefore, current.Reason); er != nil {
			_ = p.setSetting("autonomy_status", "RECEIPT_WRITE_FAILED: "+er.Error())
		}
	}()
	evidence := filepath.Join(p.Root, "evidence", id, fmt.Sprint(n))
	defer func() {
		current, er := p.Store.Get(id)
		if er != nil || current.State == "ACCEPTED" {
			return
		}
		if current.State != "BLOCKED" && current.State != "REJECTED_RETRYABLE" {
			return
		}
		if _, er = os.Stat(evidence); er != nil {
			return
		}
		current.Evidence = evidence
		if _, er = os.Stat(filepath.Join(evidence, "acceptance_result.json")); os.IsNotExist(er) {
			_ = writeJSON(filepath.Join(evidence, "acceptance_result.json"), map[string]any{"state": current.State, "reason": current.Reason, "acceptance_ran": false})
			_ = writeJSON(filepath.Join(evidence, "acceptance_checks.json"), []Check{})
		}
		_ = p.Seal(current)
	}()
	runID := randomID()
	root := filepath.Join(p.Root, "workspaces", "s", runID)
	finish := func(code string) {

		_, countErr := p.consumedWorkerAttempts(id)
		if countErr != nil {
			_ = p.Store.Move(id, "BLOCKED", "ATTEMPT_BUDGET_STATE_UNAVAILABLE")
			return
		}
		state := "BLOCKED"
		retryDecision := p.retryDecisionNow(id, n, code)
		if retryDecision.FailureRetryable && retryDecision.MayRetry {
			state = "REJECTED_RETRYABLE"
		}
		if retryDecision.HardStop && retryDecision.FailureRetryable && !retryDecision.ExternalHandoff {
			code = "RETRY_LIMIT_REACHED: " + code
		}
		_ = p.Store.Move(id, state, code)
	}
	retainLease := false
	defer func() {
		if !retainLease {
			_, _ = p.Store.DB.Exec("DELETE FROM worker_leases WHERE work_order_id=? AND attempt=?", id, n)
		}
	}()
	if e = os.MkdirAll(evidence, 0700); e != nil {
		finish("EVIDENCE_WRITE_FAILED")
		return
	}
	if _, e = p.Store.DB.Exec("UPDATE work_orders SET evidence=? WHERE id=?", evidence, id); e != nil {
		finish("STATE_WRITE_FAILED")
		return
	}
	raw, _ := json.MarshalIndent(j.Order, "", "  ")
	// Preserve original YAML bytes, not a reconstructed authorization document.
	var source []byte
	if e = p.Store.DB.QueryRow("SELECT yaml FROM work_orders WHERE id=?", id).Scan(&source); e != nil {
		finish("STATE_READ_FAILED")
		return
	}
	for name, data := range map[string][]byte{"work_order.yaml": source, "resolved_work_order.json": raw, "resolved_config.json": []byte(jsonText(p.Config))} {
		if e = os.WriteFile(filepath.Join(evidence, name), data, 0600); e != nil {
			finish("EVIDENCE_WRITE_FAILED")
			return
		}
	}
	// Persist the short source-workspace root before materialization. If Git
	// fails before the worktree exists, queue receipts can still point at the
	// exact isolated attempt root rather than losing the path in a generic
	// REPO_UNAVAILABLE blocker.
	if _, e = p.Store.DB.Exec("UPDATE work_orders SET workspace=? WHERE id=?", root, id); e != nil {
		finish("STATE_WRITE_FAILED")
		return
	}
	// DN: mark progress before source materialization starts. AutonomyTick can
	// observe a RUNNING owned attempt before the worker process launches; without
	// this heartbeat, the no-progress monitor can cancel the attempt while Git is
	// still creating the isolated private repository/worktree.
	if _, e = p.Store.DB.Exec("INSERT OR REPLACE INTO worker_progress VALUES(?,?)", id, now()); e != nil {
		finish("STATE_WRITE_FAILED")
		return
	}
	sourceRepoPath := p.Config.Repos[j.Order.Repo].LocalPath
	materializationCtx, materializationCancel := p.materializationContext()
	work, before, e := p.prepareObjectiveWorkspace(materializationCtx, sourceRepoPath, root, j, n)
	materializationCancel()
	if e != nil {
		blocker := materializationBlocker(e)
		if before.Baseline != "" || before.SourceRefs != "" || before.AttemptRefs != "" || before.Head != "" || before.Status != "" {
			_ = writeJSON(filepath.Join(evidence, "repo_state_before.json"), before)
		}
		if er := writeMaterializationError(evidence, materializationDiagnostic{
			Err:            e,
			Blocker:        blocker,
			SourceRepoPath: sourceRepoPath,
			WorkspaceRoot:  root,
			PrivateRepo:    filepath.Join(root, "repository"),
			Worktree:       filepath.Join(root, "worktree"),
			BaselineRef:    j.Order.Baseline.Ref,
			BaselineSHA:    j.Order.Baseline.SHA,
			WorkerBranch:   j.Order.Worker.Branch,
			Attempt:        n,
			RunID:          runID,
		}); er != nil {
			finish("EVIDENCE_WRITE_FAILED")
			return
		}
		finish(blocker)
		return
	}
	if e = writeJSON(filepath.Join(evidence, "repo_state_before.json"), before); e != nil {
		finish("EVIDENCE_WRITE_FAILED")
		return
	}
	if _, e = p.Store.DB.Exec("UPDATE work_orders SET workspace=? WHERE id=?", work, id); e != nil {
		finish("STATE_WRITE_FAILED")
		return
	}
	// Refresh progress before the visible ENGINEERING transition. AutonomyTick may
	// observe the new job state before the adapter is invoked; this closes the
	// post-materialization race that can otherwise cancel a just-starting worker.
	if _, e = p.Store.DB.Exec("INSERT OR REPLACE INTO worker_progress VALUES(?,?)", id, now()); e != nil {
		finish("STATE_WRITE_FAILED")
		return
	}
	if e = p.Store.Move(id, "ENGINEERING", "Worker editing isolated attempt worktree"); e != nil {
		return
	}
	stdout, e := os.OpenFile(filepath.Join(evidence, "worker_stdout.log"), os.O_CREATE|os.O_WRONLY|os.O_EXCL, 0600)
	if e != nil {
		finish("EVIDENCE_WRITE_FAILED")
		return
	}
	defer stdout.Close()
	stderr, e := os.OpenFile(filepath.Join(evidence, "worker_stderr.log"), os.O_CREATE|os.O_WRONLY|os.O_EXCL, 0600)
	if e != nil {
		finish("EVIDENCE_WRITE_FAILED")
		return
	}
	defer stderr.Close()
	worker := p.workers[j.Order.Worker.Preferred]
	if j.Order.Worker.Preferred == "codex" {
		feedback := previousAttemptFeedback(p.Root, id, n)

		referenceContext, er := p.contextFor(j.Order)
		if er != nil {
			finish("CONTEXT_HASH_CHANGED")
			return
		}
		worker = CodexAdapter{Context: referenceContext, Tool: p.Config.Tools.Codex, Home: p.Config.Execution.CodexHome, Runner: p.runnerFor(j), Feedback: feedback}
	}
	_, _ = p.Store.DB.Exec("INSERT OR REPLACE INTO worker_progress VALUES(?,?)", id, now())
	if _, e = p.Store.DB.Exec("INSERT INTO events(timestamp,work_order_id,attempt_id,type,severity,message,structured_json) VALUES(?,?,?,'WORKER_LAUNCH_ATTEMPTED','INFO','Worker invocation begins','{}')", now(), id, n); e != nil {
		finish("WORKER_LAUNCH_JOURNAL_FAILED")
		return
	}
	workerLaunchAttempted = true
	p.launchOpenCodeShadow(ctx, id, n, j.Order)
	e = worker.Run(ctx, work, j.Order, &progressWriter{p: p, id: id, dest: stdout}, &progressWriter{p: p, id: id, dest: stderr})
	if retainWorkerLease(e) {
		retainLease = true
	}
	stdout.Close()
	stderr.Close()
	code := ""
	exit := exitCode(e)
	if e != nil {
		code = workerExitFailure(j.Order.Worker.Preferred, p.Root, evidence)
	}
	if errors.Is(ctx.Err(), context.DeadlineExceeded) {
		code = "WORKER_TIMEOUT"
	}
	cancelReason := ""
	if errors.Is(ctx.Err(), context.Canceled) {
		cancelReason = p.attemptCancelReason(id)
		code = "WORKER_CANCELLED"
		if cancelReason != "" {
			code = "WORKER_CANCELLED: " + cancelReason
		}
	}
	if p.Config.Autonomy.ObjectiveController && j.Order.Worker.Preferred == "codex" && code == "WORKER_EXIT_NONZERO" {
		if classified := codexFailure(evidence); classified != "" {
			code = classified
		}
	}
	if e = writeJSON(filepath.Join(evidence, "worker_exit.json"), map[string]any{"exit_code": exit, "failure_class": failureClass(code), "failure_reason": code, "cancel_reason": cancelReason, "finished": now()}); e != nil {
		finish("EVIDENCE_WRITE_FAILED")
		return
	}
	_, _ = p.Store.DB.Exec("UPDATE worker_attempts SET finished=?,exit_code=? WHERE work_order_id=? AND attempt=?", now(), exit, id, n)
	j, _ = p.Store.Get(id)
	paths, pathErr := changed(p.Config.Tools.Git, work, j.Order.Baseline.SHA)
	if pathErr != nil {
		finish("CANDIDATE_READ_FAILED")
		return
	}
	for _, name := range paths {
		if !j.Order.Allows(name) {
			_ = os.WriteFile(filepath.Join(evidence, "changed_files.txt"), []byte(strings.Join(paths, "\n")), 0600)
			finish("FORBIDDEN_PATH_MODIFIED")
			_ = p.Seal(j)
			return
		}
	}
	files, err := p.capture(j, before)
	if err != nil {
		finish("EVIDENCE_WRITE_FAILED")
		return
	}
	if code != "" {
		finish(code)
		_ = p.Seal(j)
		return
	}
	if len(files) == 0 {
		finish("NO_DIFF_PRODUCED")
		_ = p.Seal(j)
		return
	}
	if e = p.Store.Move(id, "CANDIDATE", "Candidate captured; deterministic acceptance pending"); e != nil {
		return
	}
	// Retain ownership through acceptance and evidence sealing.
	if e = p.acceptContext(ctx, id); e != nil {
		j, _ = p.Store.Get(id)
		if j.State == "ACCEPTING" {
			_ = p.Store.Move(id, "BLOCKED", "ACCEPTANCE_INTERNAL_ERROR")
		}
	}
}

type materializationDiagnostic struct {
	Err            error
	Blocker        string
	SourceRepoPath string
	WorkspaceRoot  string
	PrivateRepo    string
	Worktree       string
	BaselineRef    string
	BaselineSHA    string
	WorkerBranch   string
	Attempt        int
	RunID          string
}

func materializationBlocker(err error) string {
	if err == nil {
		return "WORKSPACE_MATERIALIZATION_FAILED"
	}
	msg := err.Error()
	if strings.HasPrefix(msg, "WORKSPACE_MATERIALIZATION_FAILED") {
		return msg
	}
	return "WORKSPACE_MATERIALIZATION_FAILED: " + msg
}

func writeMaterializationError(evidence string, d materializationDiagnostic) error {
	underlying := ""
	if d.Err != nil {
		underlying = d.Err.Error()
	}
	detail := map[string]any{
		"blocker":                 d.Blocker,
		"underlying_error":        underlying,
		"source_repo_path":        d.SourceRepoPath,
		"workspace_root":          d.WorkspaceRoot,
		"private_repo_path":       d.PrivateRepo,
		"worktree_path":           d.Worktree,
		"baseline_ref":            d.BaselineRef,
		"baseline_sha":            d.BaselineSHA,
		"worker_branch":           d.WorkerBranch,
		"attempt":                 d.Attempt,
		"run_id":                  d.RunID,
		"production_accepted":     false,
		"worker_launch_attempted": false,
		"source_hygiene_ran":      false,
	}
	var gitFailure *gitCommandError
	if errors.As(d.Err, &gitFailure) {
		detail["git_operation"] = gitFailure.operation
		detail["git_output"] = gitFailure.output
	}
	return writeJSON(filepath.Join(evidence, "materialization-error.json"), detail)
}

func (p *Engine) cancelAttempt(id, reason string) error {
	p.mu.Lock()
	defer p.mu.Unlock()
	c, ok := p.cancels[id]
	if !ok {
		return errors.New("no active attempt owned by this service")
	}
	if reason != "" {
		if p.cancelReasons == nil {
			p.cancelReasons = map[string]string{}
		}
		p.cancelReasons[id] = reason
	}
	c()
	return nil
}

func (p *Engine) cancelAllAttempts(reason string) {
	p.mu.Lock()
	defer p.mu.Unlock()
	for id, c := range p.cancels {
		if reason != "" {
			if p.cancelReasons == nil {
				p.cancelReasons = map[string]string{}
			}
			p.cancelReasons[id] = reason
		}
		c()
	}
}

func (p *Engine) attemptCancelReason(id string) string {
	p.mu.Lock()
	defer p.mu.Unlock()
	if p.cancelReasons == nil {
		return ""
	}
	return p.cancelReasons[id]
}

func (p *Engine) Cancel(id string) error {
	return p.cancelAttempt(id, "OPERATOR_CANCELLED")
}
func (p *Engine) Retry(id string) error {
	if e := p.Ready(id); e != nil {
		return e
	}
	return p.Dispatch(id)
}
func (p *Engine) Wait(ctx context.Context, id string) (Job, error) {
	tick := time.NewTicker(20 * time.Millisecond)
	defer tick.Stop()
	for {
		j, e := p.Store.Get(id)
		if e != nil {
			return j, e
		}
		switch j.State {
		case "ACCEPTED", "BLOCKED", "REJECTED_RETRYABLE":
			return j, nil
		}
		select {
		case <-ctx.Done():
			return j, ctx.Err()
		case <-tick.C:
		}
	}
}
func (p *Engine) Why() string {
	jobs, e := p.Store.List()
	if e != nil {
		return "BLOCKED: state unavailable"
	}
	var paused string
	_ = p.Store.DB.QueryRow("SELECT value FROM settings WHERE key='paused'").Scan(&paused)
	for _, j := range jobs {
		if strings.Contains("|DISPATCHED|ENGINEERING|ACCEPTING|", "|"+j.State+"|") {
			return "RUNNING: " + j.ID + " ΓÇö " + j.Reason
		}
	}
	if paused == "true" {
		return "IDLE: dispatch paused"
	}
	for _, j := range jobs {
		if j.State == "BLOCKED" || j.State == "REJECTED_RETRYABLE" {
			return j.State + ": " + j.ID + " ΓÇö " + j.Reason
		}
	}
	for _, j := range jobs {
		if j.State == "READY" || j.State == "AUTHORIZED" || j.State == "CANDIDATE" {
			return "IDLE: " + j.ID + " awaits explicit action (" + j.State + ")"
		}
	}
	return "IDLE: no authorized READY work orders"
}

func (p *Engine) attemptTimeout() time.Duration {
	n := p.Config.Execution.TimeoutSeconds
	if n <= 0 {
		n = 1200
	}
	if n > 7200 {
		n = 7200
	}
	return time.Duration(n) * time.Second
}
func (p *Engine) Authority() string {
	if p.Config.Execution.Enabled && runtime.GOOS == "windows" {
		return "WINDOWS SOURCE ACCEPTANCE"
	}
	return "DEMO / REAL EXECUTION NOT READY"
}
