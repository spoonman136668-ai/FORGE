package plane

import (
	"context"
	"encoding/json"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"testing"
	"time"
)

type localExecutionRecordingRunner struct {
	spec  ProcessSpec
	calls int
}

func (r *localExecutionRecordingRunner) Run(_ context.Context, spec ProcessSpec, stdout, stderr io.Writer) error {
	r.calls++
	r.spec = spec
	_, _ = io.WriteString(stdout, "safe output\n")
	_, _ = io.WriteString(stderr, "diagnostic stderr\n")
	return nil
}

func TestLocalExecutionBrokerHashBoundTypedArgumentsAndMinimalEnvironment(t *testing.T) {
	root := t.TempDir()
	scriptPath := filepath.Join(root, "operations", "Typed-Proof.ps1")
	if err := os.MkdirAll(filepath.Dir(scriptPath), 0700); err != nil {
		t.Fatal(err)
	}
	script := []byte("param([bool]$Verbose,[int]$Count,[string]$Mode,[string]$Label)\nWrite-Output 'ok'\n")
	if err := os.WriteFile(scriptPath, script, 0600); err != nil {
		t.Fatal(err)
	}
	configDir := filepath.Join(root, "config")
	if err := os.MkdirAll(configDir, 0700); err != nil {
		t.Fatal(err)
	}
	min := int64(1)
	max := int64(5)
	registry := LocalOperationRegistry{
		Schema: localOperationsSchema,
		Operations: []LocalOperation{{
			ID:             "typed-proof",
			Class:          "diagnostic",
			Script:         "operations/Typed-Proof.ps1",
			ScriptSHA256:   digest(script),
			WorkingRoot:    "plane",
			WorkingDir:     ".",
			TimeoutSeconds: 30,
			Arguments: []LocalOperationArgument{
				{Name: "Verbose", Type: "bool", Required: true},
				{Name: "Count", Type: "int", Required: true, Min: &min, Max: &max},
				{Name: "Mode", Type: "enum", Required: true, Enum: []string{"short", "full"}},
				{Name: "Label", Type: "string", Required: true, Pattern: `^[A-Za-z0-9_.-]+$`, MaxLength: 32},
			},
		}},
	}
	raw, err := json.Marshal(registry)
	if err != nil {
		t.Fatal(err)
	}
	if err = os.WriteFile(filepath.Join(configDir, "local-operations.json"), raw, 0600); err != nil {
		t.Fatal(err)
	}

	powershell := filepath.Join(root, "powershell.exe")
	if err = os.WriteFile(powershell, []byte("fixture"), 0600); err != nil {
		t.Fatal(err)
	}

	var c Config
	c.Tools.Powershell = powershell
	c.Execution.LocalOperationsConfig = localOperationsConfigPath
	c.Execution.LocalOperationsSHA256 = digest(raw)
	loaded, err := LoadLocalOperationRegistry(root, c, c.Execution.LocalOperationsConfig)
	if err != nil {
		t.Fatal(err)
	}

	runner := &localExecutionRecordingRunner{}
	engine := &Engine{Root: root, Config: c, runner: runner, localOperations: loaded}

	t.Setenv("CKB_PLANE_GITHUB_TOKEN", "must-not-propagate")
	params := map[string]json.RawMessage{
		"Verbose": json.RawMessage(`true`),
		"Count":   json.RawMessage(`3`),
		"Mode":    json.RawMessage(`"full"`),
		"Label":   json.RawMessage(`"proof-1"`),
	}
	result, err := engine.RunLocalOperation(context.Background(), LocalExecutionRequest{
		RequestID:    "local-exec-proof-1",
		OperationID:  "typed-proof",
		ScriptSHA256: digest(script),
		Parameters:   params,
	})
	if err != nil {
		t.Fatal(err)
	}
	if result.Status != "succeeded" || result.ExitCode != 0 || result.EvidenceManifestSHA256 == "" {
		t.Fatalf("unexpected result: %#v", result)
	}
	if runner.calls != 1 {
		t.Fatalf("runner calls=%d", runner.calls)
	}
	if runner.spec.Program != powershell {
		t.Fatalf("program=%q", runner.spec.Program)
	}
	joined := strings.Join(runner.spec.Args, "\n")
	if strings.Contains(joined, "-Command") || !strings.Contains(joined, "-File") {
		t.Fatalf("unsafe powershell invocation: %#v", runner.spec.Args)
	}
	if !strings.Contains(joined, "-Verbose:$true") || !strings.Contains(joined, "-Count\n3") || !strings.Contains(joined, "-Mode\nfull") || !strings.Contains(joined, "-Label\nproof-1") {
		t.Fatalf("typed args not preserved: %#v", runner.spec.Args)
	}
	for _, entry := range runner.spec.Env {
		if strings.HasPrefix(strings.ToUpper(entry), "CKB_PLANE_GITHUB_TOKEN=") {
			t.Fatalf("credential leaked into child env")
		}
	}
	evidence := filepath.Join(root, "evidence", "local-exec", "local-exec-proof-1")
	if err = VerifyManifest(evidence); err != nil {
		t.Fatalf("evidence verification failed: %v", err)
	}
}

func TestLocalExecutionBrokerRejectsHashDriftUnknownArgumentsAndUnsafeValues(t *testing.T) {
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, "operations"), 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(root, "config"), 0700); err != nil {
		t.Fatal(err)
	}
	script := []byte("param([string]$Label)\n")
	if err := os.WriteFile(filepath.Join(root, "operations", "Proof.ps1"), script, 0600); err != nil {
		t.Fatal(err)
	}
	registry := map[string]any{
		"schema": localOperationsSchema,
		"operations": []any{map[string]any{
			"id":              "proof",
			"class":           "diagnostic",
			"script":          "operations/Proof.ps1",
			"script_sha256":   digest(script),
			"working_root":    "plane",
			"working_dir":     ".",
			"timeout_seconds": 30,
			"arguments": []any{map[string]any{
				"name": "Label", "type": "string", "required": true,
				"pattern": `^[A-Za-z0-9_.-]+$`, "max_length": 32,
			}},
		}},
	}
	raw, _ := json.Marshal(registry)
	if err := os.WriteFile(filepath.Join(root, "config", "local-operations.json"), raw, 0600); err != nil {
		t.Fatal(err)
	}
	powershell := filepath.Join(root, "powershell.exe")
	if err := os.WriteFile(powershell, []byte("fixture"), 0600); err != nil {
		t.Fatal(err)
	}
	var c Config
	c.Tools.Powershell = powershell
	c.Execution.LocalOperationsConfig = localOperationsConfigPath
	c.Execution.LocalOperationsSHA256 = digest(raw)
	loaded, err := LoadLocalOperationRegistry(root, c, c.Execution.LocalOperationsConfig)
	if err != nil {
		t.Fatal(err)
	}
	runner := &localExecutionRecordingRunner{}
	engine := &Engine{Root: root, Config: c, runner: runner, localOperations: loaded}

	_, err = engine.RunLocalOperation(context.Background(), LocalExecutionRequest{
		RequestID: "hash-drift", OperationID: "proof",
		ScriptSHA256: strings.Repeat("0", 64),
		Parameters:   map[string]json.RawMessage{"Label": json.RawMessage(`"safe"`)},
	})
	if err == nil || !strings.Contains(err.Error(), "LOCAL_EXEC_SCRIPT_HASH_MISMATCH") {
		t.Fatalf("expected hash refusal, got %v", err)
	}
	if runner.calls != 0 {
		t.Fatal("runner launched on hash mismatch")
	}

	_, err = engine.RunLocalOperation(context.Background(), LocalExecutionRequest{
		RequestID: "unknown-arg", OperationID: "proof",
		ScriptSHA256: digest(script),
		Parameters:   map[string]json.RawMessage{"Label": json.RawMessage(`"safe"`), "Extra": json.RawMessage(`"x"`)},
	})
	if err == nil || !strings.Contains(err.Error(), "LOCAL_EXEC_ARGUMENT_UNKNOWN") {
		t.Fatalf("expected unknown argument refusal, got %v", err)
	}
	if runner.calls != 0 {
		t.Fatal("runner launched on unknown argument")
	}

	_, err = engine.RunLocalOperation(context.Background(), LocalExecutionRequest{
		RequestID: "unsafe-value", OperationID: "proof",
		ScriptSHA256: digest(script),
		Parameters:   map[string]json.RawMessage{"Label": json.RawMessage(`"safe;Get-ChildItem"`)},
	})
	if err == nil || !strings.Contains(err.Error(), "LOCAL_EXEC_ARGUMENT_UNSAFE") {
		t.Fatalf("expected unsafe value refusal, got %v", err)
	}
	if runner.calls != 0 {
		t.Fatal("runner launched on unsafe argument")
	}
}

func TestLocalExecutionRegistryRejectsSecretArgumentsAndReparseScript(t *testing.T) {
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, "operations"), 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(root, "config"), 0700); err != nil {
		t.Fatal(err)
	}
	script := []byte("param([string]$ApiToken)\n")
	if err := os.WriteFile(filepath.Join(root, "operations", "Bad.ps1"), script, 0600); err != nil {
		t.Fatal(err)
	}
	registry := map[string]any{
		"schema": localOperationsSchema,
		"operations": []any{map[string]any{
			"id":              "bad",
			"class":           "diagnostic",
			"script":          "operations/Bad.ps1",
			"script_sha256":   digest(script),
			"working_root":    "plane",
			"working_dir":     ".",
			"timeout_seconds": 30,
			"arguments": []any{map[string]any{
				"name": "ApiToken", "type": "string", "required": true,
				"pattern": `^[A-Za-z0-9]+$`, "max_length": 32,
			}},
		}},
	}
	raw, _ := json.Marshal(registry)
	if err := os.WriteFile(filepath.Join(root, "config", "local-operations.json"), raw, 0600); err != nil {
		t.Fatal(err)
	}
	var c Config
	c.Execution.LocalOperationsConfig = localOperationsConfigPath
	c.Execution.LocalOperationsSHA256 = digest(raw)
	_, err := LoadLocalOperationRegistry(root, c, c.Execution.LocalOperationsConfig)
	if err == nil || !strings.Contains(err.Error(), "secret-like argument prohibited") {
		t.Fatalf("expected secret-like argument refusal, got %v", err)
	}
}

func TestLocalExecutionCaptureIsBounded(t *testing.T) {
	capture := &localCapture{limit: 4}
	n, err := capture.Write([]byte("abcdef"))
	if err != nil || n != 6 {
		t.Fatalf("write n=%d err=%v", n, err)
	}
	if capture.buf.String() != "abcd" || !capture.truncated {
		t.Fatalf("capture=%q truncated=%v", capture.buf.String(), capture.truncated)
	}
}

func TestLocalExecutionResultTimestampsAreBounded(t *testing.T) {
	now := time.Now().UTC()
	result := LocalExecutionResult{StartedAt: now, FinishedAt: now}
	if result.FinishedAt.Before(result.StartedAt) {
		t.Fatal("invalid timestamps")
	}
}

func TestLocalExecutionRegistryRejectsCapabilityShapingArguments(t *testing.T) {
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, "operations"), 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(root, "config"), 0700); err != nil {
		t.Fatal(err)
	}
	script := []byte("param([string]$Command)\n")
	if err := os.WriteFile(filepath.Join(root, "operations", "Bad.ps1"), script, 0600); err != nil {
		t.Fatal(err)
	}
	registry := map[string]any{
		"schema": localOperationsSchema,
		"operations": []any{map[string]any{
			"id": "bad-command", "class": "diagnostic",
			"script": "operations/Bad.ps1", "script_sha256": digest(script),
			"working_root": "plane", "working_dir": ".", "timeout_seconds": 30,
			"arguments": []any{map[string]any{
				"name": "Command", "type": "string", "required": true,
				"pattern": `^[A-Za-z0-9_.-]+$`, "max_length": 32,
			}},
		}},
	}
	raw, _ := json.Marshal(registry)
	if err := os.WriteFile(filepath.Join(root, "config", "local-operations.json"), raw, 0600); err != nil {
		t.Fatal(err)
	}
	var c Config
	c.Execution.LocalOperationsConfig = localOperationsConfigPath
	c.Execution.LocalOperationsSHA256 = digest(raw)
	_, err := LoadLocalOperationRegistry(root, c, c.Execution.LocalOperationsConfig)
	if err == nil || !strings.Contains(err.Error(), "capability-shaping argument prohibited") {
		t.Fatalf("expected capability-shaping argument refusal, got %v", err)
	}
}

func TestLocalExecutionStringRejectsPathLikeValues(t *testing.T) {
	pattern := regexp.MustCompile(`^.+$`)
	for _, value := range []string{`C:\\Users\\camar`, `../escape`, `/absolute/path`} {
		if err := validateLocalString(value, 64, pattern); err == nil || err.Error() != "LOCAL_EXEC_ARGUMENT_UNSAFE" {
			t.Fatalf("expected path-like value %q to be unsafe, got %v", value, err)
		}
	}
}
