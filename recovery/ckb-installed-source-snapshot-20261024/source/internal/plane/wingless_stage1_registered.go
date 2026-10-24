package plane

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"
)

const (
	winglessStage1RegisteredWorkerName  = "wingless-stage1"
	winglessStage1ServiceRequestSchema  = "ckb-plane.wingless-stage1-service-request.v1"
	winglessStage1ServiceResponseSchema = "ckb-plane.wingless-stage1-service-response.v1"
)

const winglessStage1FenceSchema = `
CREATE TABLE IF NOT EXISTS wingless_stage1_candidate_fences(
	work_order_id TEXT NOT NULL,
	attempt INTEGER NOT NULL,
	request_id TEXT NOT NULL,
	workspace TEXT NOT NULL,
	baseline_sha TEXT NOT NULL,
	work_order_digest TEXT NOT NULL,
	state TEXT NOT NULL,
	candidate_sha256 TEXT NOT NULL DEFAULT '',
	created TEXT NOT NULL,
	updated TEXT NOT NULL,
	PRIMARY KEY(work_order_id,attempt)
);`

type WinglessStage1Config struct {
	Enabled        bool   `yaml:"enabled"`
	ServiceProgram string `yaml:"service_program"`
	ServiceSHA256  string `yaml:"service_sha256"`
	ModelPath      string `yaml:"model_path"`
	ModelSHA256    string `yaml:"model_sha256"`
	ModelBytes     int64  `yaml:"model_bytes"`
	RuntimePath    string `yaml:"runtime_path"`
	RuntimeSHA256  string `yaml:"runtime_sha256"`
}

type WinglessStage1RegisteredConfig struct {
	ServiceProgram string
	ServiceSHA256  string
	ModelPath      string
	ModelSHA256    string
	ModelBytes     int64
	RuntimePath    string
	RuntimeSHA256  string
}

func (c WinglessStage1Config) registered() WinglessStage1RegisteredConfig {
	return WinglessStage1RegisteredConfig{
		ServiceProgram: c.ServiceProgram,
		ServiceSHA256:  c.ServiceSHA256,
		ModelPath:      c.ModelPath,
		ModelSHA256:    c.ModelSHA256,
		ModelBytes:     c.ModelBytes,
		RuntimePath:    c.RuntimePath,
		RuntimeSHA256:  c.RuntimeSHA256,
	}
}

type winglessStage1RegisteredWorker struct {
	engine *Engine
	config WinglessStage1RegisteredConfig
}

var _ Worker = (*winglessStage1RegisteredWorker)(nil)

type winglessStage1OwnershipError struct {
	code  string
	cause error
}

func (e *winglessStage1OwnershipError) Error() string {
	if e == nil {
		return "WINGLESS_STAGE1_OWNERSHIP_UNCERTAIN"
	}
	if e.cause == nil {
		return e.code
	}
	return e.code + ": " + e.cause.Error()
}
func (e *winglessStage1OwnershipError) Unwrap() error           { return e.cause }
func (e *winglessStage1OwnershipError) RetainWorkerLease() bool { return true }

type workerLeaseRetentionError interface {
	error
	RetainWorkerLease() bool
}

func retainWorkerLease(err error) bool {
	if err == nil {
		return false
	}
	var target workerLeaseRetentionError
	return errors.As(err, &target) && target.RetainWorkerLease()
}

func winglessStage1Retain(code string, cause error) error {
	if code == "" {
		code = "WINGLESS_STAGE1_OWNERSHIP_UNCERTAIN"
	}
	return &winglessStage1OwnershipError{code: code, cause: cause}
}

func validateWinglessStage1RegisteredConfig(c WinglessStage1RegisteredConfig) error {
	for name, path := range map[string]string{
		"service": c.ServiceProgram,
		"model":   c.ModelPath,
		"runtime": c.RuntimePath,
	} {
		if path == "" || !filepath.IsAbs(path) || filepath.Clean(path) != path || strings.ContainsAny(path, "\x00\r\n") {
			return fmt.Errorf("WINGLESS_STAGE1_%s_PATH_INVALID", strings.ToUpper(name))
		}
	}
	if !winglessStage1DormantValidSHA256(c.ServiceSHA256) ||
		!winglessStage1DormantValidSHA256(c.ModelSHA256) ||
		!winglessStage1DormantValidSHA256(c.RuntimeSHA256) ||
		c.ModelBytes < 1 {
		return errors.New("WINGLESS_STAGE1_IDENTITY_INVALID")
	}
	return nil
}

func (p *Engine) RegisterWinglessStage1(c WinglessStage1RegisteredConfig) error {
	if p == nil || p.Store == nil || p.Store.DB == nil {
		return errors.New("WINGLESS_STAGE1_REGISTRATION_ENGINE_INVALID")
	}
	if err := validateWinglessStage1RegisteredConfig(c); err != nil {
		return err
	}
	for _, path := range []string{c.ServiceProgram, c.ModelPath, c.RuntimePath} {
		info, err := os.Lstat(path)
		if err != nil || !info.Mode().IsRegular() {
			return errors.New("WINGLESS_STAGE1_REGISTRATION_ARTIFACT_UNAVAILABLE")
		}
		if rp, err := winglessStage1IsReparse(path); err != nil || rp {
			return errors.New("WINGLESS_STAGE1_REGISTRATION_REPARSE_PROHIBITED")
		}
	}
	if _, err := p.Store.DB.Exec(winglessStage1FenceSchema); err != nil {
		return fmt.Errorf("WINGLESS_STAGE1_FENCE_SCHEMA_FAILED: %w", err)
	}

	p.mu.Lock()
	defer p.mu.Unlock()
	if p.workers == nil {
		p.workers = map[string]Worker{}
	}
	if _, exists := p.workers[winglessStage1RegisteredWorkerName]; exists {
		return errors.New("WINGLESS_STAGE1_ALREADY_REGISTERED")
	}
	p.workers[winglessStage1RegisteredWorkerName] = &winglessStage1RegisteredWorker{engine: p, config: c}
	return nil
}

func (w *winglessStage1RegisteredWorker) Name() string { return winglessStage1RegisteredWorkerName }

type winglessStage1ServiceRequest struct {
	Schema               string   `json:"schema"`
	WorkOrderID          string   `json:"work_order_id"`
	Title                string   `json:"title"`
	Instructions         []string `json:"instructions"`
	Attempt              int      `json:"attempt"`
	BaselineSHA          string   `json:"baseline_sha"`
	WorkerBranch         string   `json:"worker_branch"`
	AllowedPaths         []string `json:"allowed_paths"`
	ForbiddenPaths       []string `json:"forbidden_paths"`
	ProtectAcceptedRefs  bool     `json:"protect_accepted_refs"`
	RequireCleanBaseline bool     `json:"require_clean_baseline"`
	Workspace            string   `json:"workspace"`
	ProductionPath       string   `json:"production_path"`
	BeforeSHA256         string   `json:"before_sha256"`
	SourceText           string   `json:"source_text"`
	ModelPath            string   `json:"model_path"`
	ModelSHA256          string   `json:"model_sha256"`
	ModelBytes           int64    `json:"model_bytes"`
	RuntimePath          string   `json:"runtime_path"`
	RuntimeSHA256        string   `json:"runtime_sha256"`
}

type winglessStage1ServiceApplicationPlan struct {
	WorkOrderID          string `json:"work_order_id"`
	RequestID            string `json:"request_id"`
	Workspace            string `json:"workspace"`
	Path                 string `json:"path"`
	ExpectedBeforeSHA256 string `json:"expected_before_sha256"`
	ExpectedAfterSHA256  string `json:"expected_after_sha256"`
	Content              string `json:"content"`
	ApplicationAuthority string `json:"application_authority"`
	AcceptanceAuthority  string `json:"acceptance_authority"`
	TrustCeiling         string `json:"trust_ceiling"`
}

type winglessStage1ServiceResponse struct {
	Schema                     string                               `json:"schema"`
	RequestID                  string                               `json:"request_id"`
	ModelPolicyID              string                               `json:"model_policy_id"`
	ModelSHA256                string                               `json:"model_sha256"`
	RuntimeSHA256              string                               `json:"runtime_sha256"`
	InferenceAttempts          int                                  `json:"inference_attempts"`
	RepairRetries              int                                  `json:"repair_retries"`
	FallbackInvocations        int                                  `json:"fallback_invocations"`
	ModelProcessStarts         int                                  `json:"model_process_starts"`
	ModelProcessFinishes       int                                  `json:"model_process_finishes"`
	ModelStoppedBeforeResponse bool                                 `json:"model_stopped_before_response"`
	RawCandidate               string                               `json:"raw_candidate"`
	ValidatedContentSHA256     string                               `json:"validated_content_sha256"`
	ApplicationPlan            winglessStage1ServiceApplicationPlan `json:"application_plan"`
	Error                      string                               `json:"error"`
}

func (w *winglessStage1RegisteredWorker) Run(ctx context.Context, workspace string, o WorkOrder, stdout, stderr io.Writer) (runErr error) {
	if w == nil || w.engine == nil || w.engine.Store == nil {
		return errors.New("WINGLESS_STAGE1_WORKER_INVALID")
	}
	if ctx == nil || stdout == nil || stderr == nil {
		return errors.New("WINGLESS_STAGE1_WORKER_BOUNDARY_INVALID")
	}
	if err := ctx.Err(); err != nil {
		return err
	}
	if o.Worker.Preferred != winglessStage1RegisteredWorkerName {
		return errors.New("WINGLESS_STAGE1_WORKER_IDENTITY_MISMATCH")
	}
	attempt, err := w.currentAttempt(workspace, o)
	if err != nil {
		return err
	}
	binding, err := NewWinglessStage1Binding(WinglessStage1FrozenSource, o, attempt, workspace)
	if err != nil {
		return err
	}
	if err := w.claimFence(binding); err != nil {
		return err
	}
	fenceTerminal := false
	defer func() {
		if fenceTerminal || runErr == nil || retainWorkerLease(runErr) {
			return
		}
		if err := w.cancelFence(binding); err != nil {
			runErr = winglessStage1Retain("WINGLESS_STAGE1_FENCE_UNCERTAIN", errors.Join(runErr, err))
		}
	}()

	source, err := os.ReadFile(filepath.Join(workspace, filepath.FromSlash(binding.ProductionPath)))
	if err != nil {
		return err
	}
	req := winglessStage1ServiceRequest{
		Schema:      winglessStage1ServiceRequestSchema,
		WorkOrderID: o.ID, Title: o.Title, Instructions: append([]string(nil), o.Instructions...),
		Attempt: attempt, BaselineSHA: o.Baseline.SHA, WorkerBranch: o.Worker.Branch,
		AllowedPaths: append([]string(nil), o.Scope.Allowed...), ForbiddenPaths: append([]string(nil), o.Scope.Forbidden...),
		ProtectAcceptedRefs: o.Acceptance.ProtectRefs, RequireCleanBaseline: o.Acceptance.Clean,
		Workspace: workspace, ProductionPath: binding.ProductionPath, BeforeSHA256: binding.BeforeSHA256, SourceText: string(source),
		ModelPath: w.config.ModelPath, ModelSHA256: w.config.ModelSHA256, ModelBytes: w.config.ModelBytes,
		RuntimePath: w.config.RuntimePath, RuntimeSHA256: w.config.RuntimeSHA256,
	}
	raw, err := json.Marshal(req)
	if err != nil {
		return err
	}

	launcher := WinglessStage1DormantLauncher{Runner: w.engine.runner, StartupTimeout: 20 * time.Second}
	handle, err := launcher.Start(ctx, w.config.ServiceProgram, w.config.ServiceSHA256)
	if err != nil {
		if handle != nil && handle.State() != winglessStage1DormantStateClosed {
			return winglessStage1Retain("WINGLESS_STAGE1_SERVICE_OWNERSHIP_UNCERTAIN", err)
		}
		return err
	}
	responseRaw, exchangeErr := handle.Exchange(ctx, raw)
	closeErr := handle.Close()
	if closeErr != nil {
		return winglessStage1Retain("WINGLESS_STAGE1_SERVICE_OWNERSHIP_UNCERTAIN", errors.Join(exchangeErr, closeErr))
	}
	if exchangeErr != nil {
		return exchangeErr
	}
	if handle.State() != winglessStage1DormantStateClosed {
		return winglessStage1Retain("WINGLESS_STAGE1_SERVICE_OWNERSHIP_UNCERTAIN", errors.New("service not confirmed closed"))
	}

	var resp winglessStage1ServiceResponse
	d := json.NewDecoder(bytes.NewReader(responseRaw))
	d.DisallowUnknownFields()
	if err := d.Decode(&resp); err != nil {
		return err
	}
	var extra any
	if err := d.Decode(&extra); err != io.EOF {
		return errors.New("WINGLESS_STAGE1_SERVICE_RESPONSE_TRAILING_DATA")
	}
	if resp.Error != "" {
		return fmt.Errorf("WINGLESS_STAGE1_SERVICE_ERROR: %s", resp.Error)
	}
	if resp.Schema != winglessStage1ServiceResponseSchema || resp.RequestID == "" ||
		resp.ModelPolicyID != WinglessStage1PreferredModel ||
		resp.ModelSHA256 != w.config.ModelSHA256 || resp.RuntimeSHA256 != w.config.RuntimeSHA256 ||
		resp.InferenceAttempts != 1 || resp.RepairRetries != 0 || resp.FallbackInvocations != 0 ||
		resp.ModelProcessStarts != 1 || resp.ModelProcessFinishes != 1 || !resp.ModelStoppedBeforeResponse {
		return errors.New("WINGLESS_STAGE1_SERVICE_RESPONSE_POLICY_INVALID")
	}

	plan, err := PrepareWinglessStage1ExternalPlan(binding, []byte(resp.RawCandidate))
	if err != nil {
		return err
	}
	if resp.ValidatedContentSHA256 != plan.ExpectedAfterSHA256 || !sameWinglessStage1ServicePlan(resp.ApplicationPlan, plan) {
		return errors.New("WINGLESS_STAGE1_CROSS_SEAM_PLAN_MISMATCH")
	}
	if err := w.markCandidateReady(binding, plan.ExpectedAfterSHA256); err != nil {
		return winglessStage1Retain("WINGLESS_STAGE1_FENCE_UNCERTAIN", err)
	}
	if err := ApplyWinglessStage1ExternalPlan(binding, plan); err != nil {
		return err
	}
	if err := w.consumeFence(binding, plan.ExpectedAfterSHA256); err != nil {
		return winglessStage1Retain("WINGLESS_STAGE1_FENCE_UNCERTAIN", err)
	}
	fenceTerminal = true
	_, err = fmt.Fprintf(stdout, "wingless-stage1 request=%s postimage=%s acceptance=%s\n", plan.RequestID, plan.ExpectedAfterSHA256, plan.AcceptanceAuthority)
	return err
}

func sameWinglessStage1ServicePlan(w winglessStage1ServiceApplicationPlan, p WinglessStage1ExternalPlan) bool {
	return w.WorkOrderID == p.WorkOrderID && w.RequestID == p.RequestID && w.Workspace == p.Workspace &&
		w.Path == p.Path && w.ExpectedBeforeSHA256 == p.ExpectedBeforeSHA256 && w.ExpectedAfterSHA256 == p.ExpectedAfterSHA256 &&
		w.Content == p.Content && w.ApplicationAuthority == p.ApplicationAuthority &&
		w.AcceptanceAuthority == p.AcceptanceAuthority && w.TrustCeiling == p.TrustCeiling
}

func (w *winglessStage1RegisteredWorker) currentAttempt(workspace string, o WorkOrder) (int, error) {
	var leaseAttempt, orderAttempt int
	var owner, state, storedWorkspace string
	if err := w.engine.Store.DB.QueryRow("SELECT attempt,owner FROM worker_leases WHERE work_order_id=?", o.ID).Scan(&leaseAttempt, &owner); err != nil {
		return 0, fmt.Errorf("WINGLESS_STAGE1_ATTEMPT_LEASE_MISSING: %w", err)
	}
	if err := w.engine.Store.DB.QueryRow("SELECT state,attempt,workspace FROM work_orders WHERE id=?", o.ID).Scan(&state, &orderAttempt, &storedWorkspace); err != nil {
		return 0, fmt.Errorf("WINGLESS_STAGE1_ATTEMPT_STATE_MISSING: %w", err)
	}
	if owner != winglessStage1RegisteredWorkerName || leaseAttempt < 1 || orderAttempt != leaseAttempt || state != "ENGINEERING" || storedWorkspace != workspace {
		return 0, errors.New("WINGLESS_STAGE1_ATTEMPT_IDENTITY_MISMATCH")
	}
	return leaseAttempt, nil
}

func (w *winglessStage1RegisteredWorker) claimFence(b WinglessStage1Binding) error {
	_, err := w.engine.Store.DB.Exec(
		"INSERT INTO wingless_stage1_candidate_fences(work_order_id,attempt,request_id,workspace,baseline_sha,work_order_digest,state,created,updated) VALUES(?,?,?,?,?,?,'EXCHANGING',?,?)",
		b.WorkOrderID, b.Attempt, fmt.Sprintf("%s-wingless-%d", b.WorkOrderID, b.Attempt), b.Workspace, b.BaselineSHA, b.WorkOrderDigest, now(), now(),
	)
	if err != nil {
		return winglessStage1Retain("WINGLESS_STAGE1_ATTEMPT_REPLAY_REFUSED", err)
	}
	return nil
}

func (w *winglessStage1RegisteredWorker) markCandidateReady(b WinglessStage1Binding, sha string) error {
	r, err := w.engine.Store.DB.Exec(
		"UPDATE wingless_stage1_candidate_fences SET state='CANDIDATE_READY',candidate_sha256=?,updated=? WHERE work_order_id=? AND attempt=? AND workspace=? AND baseline_sha=? AND work_order_digest=? AND state='EXCHANGING'",
		sha, now(), b.WorkOrderID, b.Attempt, b.Workspace, b.BaselineSHA, b.WorkOrderDigest,
	)
	if err != nil {
		return err
	}
	n, err := r.RowsAffected()
	if err != nil || n != 1 {
		return errors.New("WINGLESS_STAGE1_FENCE_READY_TRANSITION_FAILED")
	}
	return nil
}

func (w *winglessStage1RegisteredWorker) consumeFence(b WinglessStage1Binding, sha string) error {
	r, err := w.engine.Store.DB.Exec(
		"UPDATE wingless_stage1_candidate_fences SET state='CONSUMED',updated=? WHERE work_order_id=? AND attempt=? AND candidate_sha256=? AND state='CANDIDATE_READY'",
		now(), b.WorkOrderID, b.Attempt, sha,
	)
	if err != nil {
		return err
	}
	n, err := r.RowsAffected()
	if err != nil || n != 1 {
		return errors.New("WINGLESS_STAGE1_FENCE_CONSUME_TRANSITION_FAILED")
	}
	return nil
}

func (w *winglessStage1RegisteredWorker) cancelFence(b WinglessStage1Binding) error {
	_, err := w.engine.Store.DB.Exec(
		"UPDATE wingless_stage1_candidate_fences SET state='CANCELED',updated=? WHERE work_order_id=? AND attempt=? AND state IN ('EXCHANGING','CANDIDATE_READY')",
		now(), b.WorkOrderID, b.Attempt,
	)
	return err
}
