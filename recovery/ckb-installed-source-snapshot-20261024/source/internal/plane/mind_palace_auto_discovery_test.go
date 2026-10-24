package plane

import (
	"context"
	"errors"
	"io"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
)

type mindPalaceAutoRecordingRunner struct {
	mu    sync.Mutex
	calls int
	err   error
}

func (r *mindPalaceAutoRecordingRunner) Run(_ context.Context, _ ProcessSpec, stdout, _ io.Writer) error {
	r.mu.Lock()
	r.calls++
	r.mu.Unlock()
	_, _ = io.WriteString(stdout, `{"schema":"ckb-plane.mind-palace-project-discovery.v1","status":"succeeded"}`+"\n")
	return r.err
}

func (r *mindPalaceAutoRecordingRunner) count() int {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.calls
}

func mindPalaceAutoFixture(t *testing.T, runErr error) (*Engine, *mindPalaceAutoRecordingRunner) {
	t.Helper()
	p, _ := setup(t)
	testAuthority(p)
	p.Config.Autonomy.MindPalaceAutoDiscovery = true
	p.Config.Autonomy.MindPalaceDiscoveryIntervalSeconds = 3600

	if err := os.MkdirAll(filepath.Join(p.Root, "operations"), 0700); err != nil {
		t.Fatal(err)
	}
	script := []byte("Write-Output 'fixture'\n")
	scriptPath := filepath.Join(p.Root, "operations", "Read-MindPalaceProjectDiscovery.ps1")
	if err := os.WriteFile(scriptPath, script, 0600); err != nil {
		t.Fatal(err)
	}
	powershell := filepath.Join(p.Root, "powershell.exe")
	if err := os.WriteFile(powershell, []byte("fixture"), 0600); err != nil {
		t.Fatal(err)
	}
	p.Config.Tools.Powershell = powershell
	op := LocalOperation{
		ID: mindPalaceAutoDiscoveryOperationID, Class: "diagnostic",
		Script:       "operations/Read-MindPalaceProjectDiscovery.ps1",
		ScriptSHA256: digest(script), WorkingRoot: "plane", WorkingDir: ".",
		TimeoutSeconds: 120,
	}
	p.localOperations = &LocalOperationRegistry{
		Schema:     localOperationsSchema,
		Operations: []LocalOperation{op},
		byID:       map[string]LocalOperation{op.ID: op},
	}
	runner := &mindPalaceAutoRecordingRunner{err: runErr}
	p.runner = runner
	if err := p.validateMindPalaceAutoDiscovery(); err != nil {
		t.Fatal(err)
	}
	return p, runner
}

func waitMindPalaceAutoState(t *testing.T, p *Engine, want string) {
	t.Helper()
	deadline := time.Now().Add(3 * time.Second)
	for time.Now().Before(deadline) {
		if p.setting("mind_palace_discovery_state") == want {
			return
		}
		time.Sleep(10 * time.Millisecond)
	}
	t.Fatalf("state=%q want=%q error=%q", p.setting("mind_palace_discovery_state"), want, p.setting("mind_palace_discovery_last_error"))
}

func TestMindPalaceAutoDiscoveryDisabledIsInert(t *testing.T) {
	p, _ := setup(t)
	testAuthority(p)
	if err := p.maybeStartMindPalaceAutoDiscovery(context.Background()); err != nil {
		t.Fatal(err)
	}
	if got := p.setting("mind_palace_discovery_state"); got != "" {
		t.Fatalf("unexpected state %q", got)
	}
}

func TestMindPalaceAutoDiscoveryLaunchesOnceAndThrottles(t *testing.T) {
	p, runner := mindPalaceAutoFixture(t, nil)
	if err := p.maybeStartMindPalaceAutoDiscovery(context.Background()); err != nil {
		t.Fatal(err)
	}
	waitMindPalaceAutoState(t, p, "SUCCEEDED")
	if runner.count() != 1 {
		t.Fatalf("calls=%d", runner.count())
	}
	requestID := p.setting("mind_palace_discovery_last_request_id")
	if !strings.HasPrefix(requestID, "mpdisc-auto-g1-") {
		t.Fatalf("request id=%q", requestID)
	}
	if p.setting("mind_palace_discovery_evidence_manifest_sha256") == "" {
		t.Fatal("missing sealed local-exec evidence hash")
	}
	if err := p.maybeStartMindPalaceAutoDiscovery(context.Background()); err != nil {
		t.Fatal(err)
	}
	time.Sleep(100 * time.Millisecond)
	if runner.count() != 1 {
		t.Fatalf("throttle failed calls=%d", runner.count())
	}
	status := p.mindPalaceAutoDiscoveryStatus()
	if status["state"] != "SUCCEEDED" || status["enabled"] != true {
		t.Fatalf("status=%#v", status)
	}
}

func TestMindPalaceAutoDiscoveryFailureDoesNotPausePlane(t *testing.T) {
	p, runner := mindPalaceAutoFixture(t, errors.New("fixture failure"))
	if err := p.setSetting("paused", "false"); err != nil {
		t.Fatal(err)
	}
	if err := p.maybeStartMindPalaceAutoDiscovery(context.Background()); err != nil {
		t.Fatal(err)
	}
	waitMindPalaceAutoState(t, p, "FAILED")
	if runner.count() != 1 {
		t.Fatalf("calls=%d", runner.count())
	}
	if p.setting("paused") != "false" {
		t.Fatal("diagnostic failure changed plane pause state")
	}
	if !strings.Contains(p.setting("mind_palace_discovery_last_error"), "fixture failure") {
		t.Fatalf("error=%q", p.setting("mind_palace_discovery_last_error"))
	}
}

func TestMindPalaceAutoDiscoveryRecoversStaleRunWithoutDuplicateSpin(t *testing.T) {
	p, runner := mindPalaceAutoFixture(t, nil)
	old := time.Now().UTC().Add(-2 * time.Hour).Format(time.RFC3339Nano)
	if err := p.setSetting("mind_palace_discovery_last_attempt_at", old); err != nil {
		t.Fatal(err)
	}
	if err := p.setSetting("mind_palace_discovery_state", "RUNNING"); err != nil {
		t.Fatal(err)
	}
	if err := p.maybeStartMindPalaceAutoDiscovery(context.Background()); err != nil {
		t.Fatal(err)
	}
	waitMindPalaceAutoState(t, p, "SUCCEEDED")
	if runner.count() != 1 {
		t.Fatalf("calls=%d", runner.count())
	}
}

func TestMindPalaceAutoDiscoveryValidationIsFailClosed(t *testing.T) {
	p, _ := mindPalaceAutoFixture(t, nil)
	p.Config.Autonomy.MindPalaceDiscoveryIntervalSeconds = 3599
	if err := p.validateMindPalaceAutoDiscovery(); err == nil || err.Error() != "MIND_PALACE_AUTO_DISCOVERY_INTERVAL_INVALID" {
		t.Fatalf("unexpected interval validation: %v", err)
	}
	p.Config.Autonomy.MindPalaceDiscoveryIntervalSeconds = 3600
	op := p.localOperations.byID[mindPalaceAutoDiscoveryOperationID]
	op.Arguments = []LocalOperationArgument{{Name: "Mode", Type: "enum", Enum: []string{"x"}}}
	p.localOperations.byID[mindPalaceAutoDiscoveryOperationID] = op
	if err := p.validateMindPalaceAutoDiscovery(); err == nil || err.Error() != "MIND_PALACE_AUTO_DISCOVERY_OPERATION_CONTRACT_INVALID" {
		t.Fatalf("unexpected operation validation: %v", err)
	}
}

func TestMindPalaceAutoDiscoverySchedulerErrorBacksOffWithoutPause(t *testing.T) {
	p, _ := mindPalaceAutoFixture(t, nil)
	if err := p.setSetting("paused", "false"); err != nil {
		t.Fatal(err)
	}
	if err := p.setSetting("mind_palace_discovery_last_attempt_at", "not-a-time"); err != nil {
		t.Fatal(err)
	}
	err := p.maybeStartMindPalaceAutoDiscovery(context.Background())
	if err == nil || err.Error() != "MIND_PALACE_AUTO_DISCOVERY_STATE_INVALID" {
		t.Fatalf("unexpected scheduler error: %v", err)
	}
	p.recordMindPalaceAutoDiscoverySchedulerError(err)
	if p.setting("paused") != "false" {
		t.Fatal("scheduler error changed plane pause state")
	}
	if p.setting("mind_palace_discovery_state") != "ERROR" {
		t.Fatalf("state=%q", p.setting("mind_palace_discovery_state"))
	}
	op := p.localOperations.byID[mindPalaceAutoDiscoveryOperationID]
	due, err := p.mindPalaceAutoDiscoveryDue(time.Now().UTC().Add(10*time.Second), op)
	if err != nil {
		t.Fatal(err)
	}
	if due {
		t.Fatal("scheduler error retried inside one-hour backoff")
	}
}

func TestMindPalaceAutoDiscoveryAutonomyTickIntegrationPreservesPause(t *testing.T) {
	p, runner := mindPalaceAutoFixture(t, nil)
	if err := p.setSetting("paused", "true"); err != nil {
		t.Fatal(err)
	}
	if err := p.AutonomyTick(context.Background()); err != nil {
		t.Fatal(err)
	}
	waitMindPalaceAutoState(t, p, "SUCCEEDED")
	if runner.count() != 1 {
		t.Fatalf("calls=%d", runner.count())
	}
	if p.setting("paused") != "true" {
		t.Fatal("automatic diagnostic changed pause state")
	}
}
