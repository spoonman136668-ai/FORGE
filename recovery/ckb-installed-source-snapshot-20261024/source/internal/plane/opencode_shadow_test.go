package plane

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"gopkg.in/yaml.v3"
)

type openCodeShadowTestRunner func(context.Context, ProcessSpec, io.Writer, io.Writer) error

func (f openCodeShadowTestRunner) Run(ctx context.Context, spec ProcessSpec, out, stderr io.Writer) error {
	return f(ctx, spec, out, stderr)
}

func waitOpenCodeShadow(t *testing.T, p *Engine) {
	t.Helper()
	done := make(chan struct{})
	go func() {
		p.shadowWG.Wait()
		close(done)
	}()
	select {
	case <-done:
	case <-time.After(10 * time.Second):
		t.Fatal("shadow advisory did not finish")
	}
}

func readOpenCodeShadowResult(t *testing.T, p *Engine, id string, attempt int) (openCodeShadowResult, []byte) {
	t.Helper()
	requestID := openCodeShadowRequestID(id, attempt, p.Config.Advisory.OpenCode.Shadow.Model)
	path := openCodeShadowResultPath(p.Root, id, attempt, requestID)
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	var result openCodeShadowResult
	if err = json.Unmarshal(raw, &result); err != nil {
		t.Fatal(err)
	}
	return result, raw
}

func configureOpenCodeShadowFixture(t *testing.T, p *Engine, allowMetadata bool, runner ProcessRunner) OpenCodeShadowConfig {
	t.Helper()
	root := filepath.Join(t.TempDir(), "sidecar")
	bin := filepath.Join(root, "bin")
	configDir := filepath.Join(root, "config")
	toolDir := filepath.Join(root, "tool")
	for _, dir := range []string{bin, configDir, toolDir} {
		if err := os.MkdirAll(dir, 0700); err != nil {
			t.Fatal(err)
		}
	}
	sidecar := filepath.Join(bin, "ckb-plane-advisory.exe")
	tool := filepath.Join(toolDir, "opencode.exe")
	if err := os.WriteFile(sidecar, []byte("synthetic-sidecar"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(tool, []byte("synthetic-opencode"), 0600); err != nil {
		t.Fatal(err)
	}
	sidecarSHA, err := openCodeFileSHA256(sidecar)
	if err != nil {
		t.Fatal(err)
	}
	toolSHA, err := openCodeFileSHA256(tool)
	if err != nil {
		t.Fatal(err)
	}
	model := "openrouter/nvidia/nemotron-3-super-120b-a12b:free"
	var sidecarConfig Config
	sidecarConfig.Advisory.OpenCode.Enabled = true
	sidecarConfig.Advisory.OpenCode.ManualOnly = true
	sidecarConfig.Advisory.OpenCode.Model = model
	sidecarConfig.Advisory.OpenCode.APIKeyEnv = "OPENROUTER_API_KEY"
	sidecarConfig.Advisory.OpenCode.ExecutableSHA256 = toolSHA
	sidecarConfig.Advisory.OpenCode.TimeoutSeconds = 30
	sidecarConfig.Tools.OpenCode = tool
	configRaw, err := yaml.Marshal(sidecarConfig)
	if err != nil {
		t.Fatal(err)
	}
	configPath := filepath.Join(configDir, "autonomy.yaml")
	if err = os.WriteFile(configPath, configRaw, 0600); err != nil {
		t.Fatal(err)
	}
	configSHA, err := openCodeFileSHA256(configPath)
	if err != nil {
		t.Fatal(err)
	}
	cfg := OpenCodeShadowConfig{
		Enabled:                true,
		AllowWorkOrderMetadata: allowMetadata,
		SidecarExecutable:      sidecar,
		SidecarConfig:          configPath,
		SidecarSHA256:          sidecarSHA,
		SidecarConfigSHA256:    configSHA,
		OpenCodeSHA256:         toolSHA,
		Model:                  model,
		TimeoutSeconds:         5,
		MaxConcurrent:          1,
	}
	p.Config.Advisory.OpenCode.Shadow = cfg
	p.shadowSlots = make(chan struct{}, 1)
	p.shadowRunner = runner
	return cfg
}

func TestOpenCodeShadowHostEnvironmentExcludesControllerCredential(t *testing.T) {
	t.Setenv("CKB_PLANE_GITHUB_TOKEN", "controller-token-sentinel")
	p, _ := setup(t)
	runner, ok := p.shadowRunner.(SupervisedRunner)
	if !ok {
		t.Fatalf("unexpected production shadow runner type %T", p.shadowRunner)
	}
	joined := strings.Join(runner.HostEnv, "\n")
	if strings.Contains(joined, "CKB_PLANE_GITHUB_TOKEN") || strings.Contains(joined, "controller-token-sentinel") {
		t.Fatal("controller credential propagated into supervised shadow host")
	}
}

func TestOpenCodeShadowMetadataDeniedNeverInvokesRunner(t *testing.T) {
	p, order := setup(t)
	var called atomic.Bool
	p.Config.Advisory.OpenCode.Shadow = OpenCodeShadowConfig{
		Enabled:       true,
		Model:         "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
		MaxConcurrent: 1,
	}
	p.shadowSlots = make(chan struct{}, 1)
	p.shadowRunner = openCodeShadowTestRunner(func(context.Context, ProcessSpec, io.Writer, io.Writer) error {
		called.Store(true)
		return errors.New("runner must not be called")
	})

	p.launchOpenCodeShadow(context.Background(), order.ID, 1, order)
	waitOpenCodeShadow(t, p)

	if called.Load() {
		t.Fatal("provider runner invoked despite metadata deny policy")
	}
	result, _ := readOpenCodeShadowResult(t, p, order.ID, 1)
	if result.Status != "skipped" || result.Reason != "DATA_POLICY_NOT_APPROVED" || result.MetadataSent {
		t.Fatalf("unexpected result: %+v", result)
	}
}

func TestOpenCodeShadowFailureCannotBlockAuthoritativeWorkerAndStripsControllerCredentials(t *testing.T) {
	p, order := setup(t)
	var mu sync.Mutex
	var observedEnv []string
	cfg := configureOpenCodeShadowFixture(t, p, true, openCodeShadowTestRunner(func(_ context.Context, spec ProcessSpec, _, _ io.Writer) error {
		mu.Lock()
		observedEnv = append([]string(nil), spec.Env...)
		mu.Unlock()
		return errors.New("synthetic provider outage")
	}))
	t.Setenv("OPENROUTER_API_KEY", "shadow-key-only")
	t.Setenv("CKB_PLANE_GITHUB_TOKEN", "must-not-reach-shadow")

	load(t, p, order)
	if err := p.Dispatch(order.ID); err != nil {
		t.Fatal(err)
	}
	job := wait(t, p, order.ID)
	waitOpenCodeShadow(t, p)

	if job.State != "ACCEPTED" {
		t.Fatalf("authoritative worker did not complete independently: state=%s reason=%q", job.State, job.Reason)
	}
	result, _ := readOpenCodeShadowResult(t, p, order.ID, 1)
	if result.Status != "failed" && result.Status != "cancelled" {
		t.Fatalf("expected independent shadow failure/cancel, got %+v", result)
	}
	mu.Lock()
	env := append([]string(nil), observedEnv...)
	mu.Unlock()
	joined := strings.Join(env, "\n")
	if !strings.Contains(joined, "OPENROUTER_API_KEY=shadow-key-only") {
		t.Fatal("shadow OpenRouter credential missing")
	}
	if strings.Contains(joined, "CKB_PLANE_GITHUB_TOKEN") || strings.Contains(joined, "must-not-reach-shadow") {
		t.Fatal("controller GitHub credential propagated into advisory process")
	}
	if result.QueueAuthorityGranted || result.AcceptanceAuthorityGranted || result.PromotionAuthorityGranted || result.AdvisoryRequiredForWork {
		t.Fatalf("shadow gained authority: %+v; cfg=%+v", result, cfg)
	}
}

func TestOpenCodeShadowSuccessPersistsDigestOnlyEvidence(t *testing.T) {
	p, order := setup(t)
	order.Repo = "SECRET_REPO_SENTINEL"
	order.Baseline.Ref = "accepted/SECRET_BASELINE_REF"
	order.Baseline.SHA = strings.Repeat("a", 40)
	order.Worker.Branch = "codex/SECRET_BRANCH"
	order.Instructions = []string{"INSTRUCTION_SENTINEL_FOR_PROVIDER_ONLY"}

	const providerOutput = "RAW_PROVIDER_OUTPUT_SENTINEL"
	const key = "shadow-key-secret"
	var packetRaw []byte
	cfg := configureOpenCodeShadowFixture(t, p, true, openCodeShadowTestRunner(func(_ context.Context, spec ProcessSpec, out, _ io.Writer) error {
		for i := 0; i+1 < len(spec.Args); i++ {
			if spec.Args[i] == "--file" {
				packetRaw, _ = os.ReadFile(spec.Args[i+1])
			}
		}
		invocation := OpenCodeAdvisoryInvocation{
			Schema:                   "ckb-plane.opencode-advisory-invocation.v1",
			RequestID:                openCodeShadowRequestID(order.ID, 2, p.Config.Advisory.OpenCode.Shadow.Model),
			Model:                    p.Config.Advisory.OpenCode.Shadow.Model,
			ToolSHA256:               p.Config.Advisory.OpenCode.Shadow.OpenCodeSHA256,
			StdoutSHA256:             openCodeBytesSHA256([]byte(providerOutput)),
			StderrSHA256:             openCodeBytesSHA256(nil),
			ResultBindingSHA256:      strings.Repeat("c", 64),
			WorkspaceRemoved:         true,
			SourceWorkspaceSupplied:  false,
			QueueAuthorityGranted:    false,
			AcceptanceAuthorityGranted: false,
			PromotionAuthorityGranted: false,
			Succeeded:                true,
		}
		payload := openCodeShadowCLIResult{Invocation: invocation, Stdout: providerOutput}
		return json.NewEncoder(out).Encode(payload)
	}))
	t.Setenv("OPENROUTER_API_KEY", key)

	p.launchOpenCodeShadow(context.Background(), order.ID, 2, order)
	waitOpenCodeShadow(t, p)

	if len(packetRaw) == 0 {
		t.Fatal("shadow packet was not observed")
	}
	packetText := string(packetRaw)
	for _, forbidden := range []string{order.Repo, order.Baseline.Ref, order.Baseline.SHA, order.Worker.Branch} {
		if strings.Contains(packetText, forbidden) {
			t.Fatalf("forbidden work-order identity leaked into provider packet: %q", forbidden)
		}
	}
	if !strings.Contains(packetText, "INSTRUCTION_SENTINEL_FOR_PROVIDER_ONLY") {
		t.Fatal("approved bounded metadata missing from provider packet")
	}

	result, raw := readOpenCodeShadowResult(t, p, order.ID, 2)
	if result.Status != "succeeded" || !result.MetadataSent {
		t.Fatalf("unexpected result: %+v", result)
	}
	if result.StdoutSHA256 != openCodeBytesSHA256([]byte(providerOutput)) || result.ResultBindingSHA256 != strings.Repeat("c", 64) {
		t.Fatalf("digest metadata missing: %+v", result)
	}
	evidence := string(raw)
	for _, forbidden := range []string{providerOutput, key, "INSTRUCTION_SENTINEL_FOR_PROVIDER_ONLY"} {
		if strings.Contains(evidence, forbidden) {
			t.Fatalf("raw/sensitive shadow material persisted: %q", forbidden)
		}
	}
	workspacePacket := filepath.Join(p.Root, "workspaces", "opencode-shadow", openCodeShadowRequestID(order.ID, 2, cfg.Model)+".json")
	if _, err := os.Stat(workspacePacket); !os.IsNotExist(err) {
		t.Fatalf("shadow packet was not removed: %v", err)
	}
}

func TestOpenCodeShadowCapacityBusySkipsWithoutBlocking(t *testing.T) {
	p, order := setup(t)
	started := make(chan struct{})
	release := make(chan struct{})
	var once sync.Once
	cfg := configureOpenCodeShadowFixture(t, p, true, openCodeShadowTestRunner(func(ctx context.Context, _ ProcessSpec, _ io.Writer, _ io.Writer) error {
		once.Do(func() { close(started) })
		select {
		case <-release:
			return errors.New("synthetic release")
		case <-ctx.Done():
			return ctx.Err()
		}
	}))
	t.Setenv("OPENROUTER_API_KEY", "shadow-capacity-key")

	p.launchOpenCodeShadow(context.Background(), order.ID, 3, order)
	select {
	case <-started:
	case <-time.After(5 * time.Second):
		t.Fatal("first shadow did not start")
	}

	second := order
	second.ID = "DEMO2"
	p.launchOpenCodeShadow(context.Background(), second.ID, 3, second)

	deadline := time.Now().Add(5 * time.Second)
	var secondResult openCodeShadowResult
	for time.Now().Before(deadline) {
		path := openCodeShadowResultPath(p.Root, second.ID, 3, openCodeShadowRequestID(second.ID, 3, cfg.Model))
		raw, err := os.ReadFile(path)
		if err == nil {
			if err = json.Unmarshal(raw, &secondResult); err != nil {
				t.Fatal(err)
			}
			break
		}
		time.Sleep(10 * time.Millisecond)
	}
	if secondResult.Status != "skipped" || secondResult.Reason != "CAPACITY_BUSY" {
		t.Fatalf("capacity saturation did not degrade to skip: %+v", secondResult)
	}

	close(release)
	waitOpenCodeShadow(t, p)
}
type openCodeShadowGateWorker struct {
	started chan<- struct{}
	release <-chan struct{}
}

func (w openCodeShadowGateWorker) Name() string { return "fake" }

func (w openCodeShadowGateWorker) Run(ctx context.Context, dir string, order WorkOrder, out, stderr io.Writer) error {
	if w.started != nil {
		close(w.started)
	}
	select {
	case <-w.release:
		return (FakeWorker{}).Run(ctx, dir, order, out, stderr)
	case <-ctx.Done():
		return ctx.Err()
	}
}

func TestOpenCodeShadowQ8WindowsProviderIntegration(t *testing.T) {
	if os.Getenv("CKB_OPENCODE_Q8_PROVIDER") != "1" {
		t.Skip("Q8 real-provider qualification is opt-in")
	}
	sidecar := os.Getenv("CKB_OPENCODE_Q8_SIDECAR_EXE")
	sidecarConfig := os.Getenv("CKB_OPENCODE_Q8_SIDECAR_CONFIG")
	hostExecutable := os.Getenv("CKB_OPENCODE_Q8_PLANE_EXE")
	openCodeSHA := os.Getenv("CKB_OPENCODE_Q8_OPENCODE_SHA256")
	model := os.Getenv("CKB_OPENCODE_Q8_MODEL")
	suffix := os.Getenv("CKB_OPENCODE_Q8_REQUEST_SUFFIX")
	if sidecar == "" || sidecarConfig == "" || hostExecutable == "" || openCodeSHA == "" || model == "" || suffix == "" {
		t.Fatal("Q8 provider qualification environment incomplete")
	}
	if !filepath.IsAbs(hostExecutable) {
		t.Fatal("Q8 plane host executable must be absolute")
	}
	hostInfo, hostErr := os.Lstat(hostExecutable)
	if hostErr != nil || !hostInfo.Mode().IsRegular() || hostInfo.Mode()&os.ModeSymlink != 0 {
		t.Fatalf("invalid Q8 plane host executable: %v", hostErr)
	}
	if !safeID.MatchString("Q8SHADOW_" + suffix) {
		t.Fatal("Q8 request suffix is not safe")
	}
	sidecarSHA, err := openCodeFileSHA256(sidecar)
	if err != nil {
		t.Fatal(err)
	}
	configSHA, err := openCodeFileSHA256(sidecarConfig)
	if err != nil {
		t.Fatal(err)
	}

	p, order := setup(t)
	order.ID = "Q8SHADOW_" + suffix
	started := make(chan struct{})
	release := make(chan struct{})
	p.workers["fake"] = openCodeShadowGateWorker{started: started, release: release}
	p.Config.Advisory.OpenCode.Shadow = OpenCodeShadowConfig{
		Enabled:                true,
		AllowWorkOrderMetadata: true,
		SidecarExecutable:      sidecar,
		SidecarConfig:          sidecarConfig,
		SidecarSHA256:          sidecarSHA,
		SidecarConfigSHA256:    configSHA,
		OpenCodeSHA256:         openCodeSHA,
		Model:                  model,
		TimeoutSeconds:         45,
		MaxConcurrent:          1,
	}
	p.shadowSlots = make(chan struct{}, 1)
	p.shadowRunner = SupervisedRunner{HostExecutable: hostExecutable, HostEnv: minimalEnv()}

	load(t, p, order)
	if err = p.Dispatch(order.ID); err != nil {
		t.Fatal(err)
	}

	select {
	case <-started:
	case <-time.After(30 * time.Second):
		t.Fatal("Q8 authoritative worker did not reach post-shadow launch point")
	}

	shadowDone := make(chan struct{})
	go func() {
		p.shadowWG.Wait()
		close(shadowDone)
	}()
	select {
	case <-shadowDone:
	case <-time.After(75 * time.Second):
		t.Fatal("Q8 real-provider shadow did not finish")
	}

	result, raw := readOpenCodeShadowResult(t, p, order.ID, 1)
	if result.Status != "succeeded" || result.Reason != "" || !result.MetadataSent {
		t.Fatalf("unexpected Q8 shadow result: %+v", result)
	}
	if result.StdoutSHA256 == "" || result.ResultBindingSHA256 == "" {
		t.Fatalf("Q8 digest binding missing: %+v", result)
	}
	if result.SourceWorkspaceSupplied || result.QueueAuthorityGranted || result.AcceptanceAuthorityGranted || result.PromotionAuthorityGranted || result.AdvisoryRequiredForWork {
		t.Fatalf("Q8 shadow crossed authority boundary: %+v", result)
	}
	for _, forbidden := range append([]string{order.Repo, order.Baseline.Ref, order.Baseline.SHA, order.Worker.Branch}, order.Instructions...) {
		if forbidden != "" && strings.Contains(string(raw), forbidden) {
			t.Fatalf("Q8 persisted provider-bound work-order material: %q", forbidden)
		}
	}

	close(release)
	job := wait(t, p, order.ID)
	if job.State != "ACCEPTED" {
		t.Fatalf("authoritative worker was not independently accepted: state=%s reason=%q", job.State, job.Reason)
	}
}

