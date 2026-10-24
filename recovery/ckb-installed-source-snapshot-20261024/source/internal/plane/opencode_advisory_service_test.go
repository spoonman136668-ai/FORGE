package plane

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

type activationAdvisoryRunner struct {
	calls  int
	spec   ProcessSpec
	stdout string
	stderr string
	err    error
}

func (r *activationAdvisoryRunner) Run(_ context.Context, spec ProcessSpec, out, stderr io.Writer) error {
	r.calls++
	r.spec = spec
	if r.stdout != "" {
		if _, err := io.WriteString(out, r.stdout); err != nil {
			return err
		}
	}
	if r.stderr != "" {
		if _, err := io.WriteString(stderr, r.stderr); err != nil {
			return err
		}
	}
	return r.err
}

func activationOpenCodeConfig(t *testing.T) (Config, string) {
	t.Helper()
	root := t.TempDir()
	toolDir := filepath.Join(root, "tool")
	if err := os.Mkdir(toolDir, 0700); err != nil {
		t.Fatal(err)
	}
	tool := filepath.Join(toolDir, "opencode.exe")
	toolBytes := []byte("deterministic-opencode-activation-fixture")
	if err := os.WriteFile(tool, toolBytes, 0700); err != nil {
		t.Fatal(err)
	}
	var cfg Config
	cfg.Tools.OpenCode = tool
	cfg.Advisory.OpenCode = OpenCodeAdvisoryConfig{
		Enabled:          true,
		ManualOnly:       true,
		Model:            "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
		APIKeyEnv:        "OPENROUTER_API_KEY",
		ExecutableSHA256: openCodeBytesSHA256(toolBytes),
		TimeoutSeconds:   30,
	}
	return cfg, root
}

func activationPacket() OpenCodeAdvisoryPacket {
	p := validOpenCodePacket()
	p.RequestID = "activation_advisory_001"
	p.SubjectID = "ACTIVATION_SYNTHETIC"
	p.Context = "Synthetic activation diagnostic: observed 7, expected 8."
	return p
}

func TestOpenCodeActivationManualRunIsolatedAndEvidenceBound(t *testing.T) {
	t.Setenv("OPENROUTER_API_KEY", "activation-test-provider-key")
	t.Setenv("AWS_SECRET_ACCESS_KEY", "must-not-pass")
	cfg, root := activationOpenCodeConfig(t)
	runner := &activationAdvisoryRunner{stdout: "{\"type\":\"text\",\"content\":\"advisory ok\"}\n"}
	service := NewOpenCodeAdvisoryService(root, cfg)
	service.runner = runner

	var stdout, stderr bytes.Buffer
	packet := activationPacket()
	invocation, err := service.Run(context.Background(), packet, &stdout, &stderr)
	if err != nil {
		t.Fatal(err)
	}
	if !invocation.Succeeded || !invocation.WorkspaceRemoved {
		t.Fatalf("unexpected invocation state: %+v", invocation)
	}
	if runner.calls != 1 {
		t.Fatalf("runner calls = %d, want 1", runner.calls)
	}
	if filepath.Clean(runner.spec.Dir) == filepath.Clean(root) {
		t.Fatal("source/control root supplied as OpenCode working directory")
	}
	rel, relErr := filepath.Rel(root, runner.spec.Dir)
	if relErr != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(os.PathSeparator)) || filepath.IsAbs(rel) || !strings.Contains(strings.ToLower(rel), "workspaces") {
		t.Fatalf("request workspace escaped plane root: root=%q dir=%q rel=%q err=%v", root, runner.spec.Dir, rel, relErr)
	}
	if _, err := os.Lstat(runner.spec.Dir); !os.IsNotExist(err) {
		t.Fatalf("request workspace survived invocation: %v", err)
	}
	joined := strings.Join(runner.spec.Args, " ")
	for _, forbidden := range []string{"serve", "--attach", "--dangerously-skip-permissions"} {
		if strings.Contains(joined, forbidden) {
			t.Fatalf("forbidden OpenCode mode in args: %q", joined)
		}
	}
	if got := envValue(runner.spec.Env, "AWS_SECRET_ACCESS_KEY"); got != "" {
		t.Fatalf("unrelated credential inherited: %q", got)
	}
	if got := envValue(runner.spec.Env, "OPENROUTER_API_KEY"); got != "activation-test-provider-key" {
		t.Fatalf("OpenRouter key not explicitly scoped: %q", got)
	}
	if invocation.ProcessOutputLimitBytes != 0 {
		t.Fatalf("test runner seam must not claim the production process cap: %d", invocation.ProcessOutputLimitBytes)
	}
	if stdout.String() != runner.stdout || stderr.Len() != 0 {
		t.Fatalf("unexpected output: stdout=%q stderr=%q", stdout.String(), stderr.String())
	}
	if len(invocation.PacketBindingSHA256) != 64 || len(invocation.ResultBindingSHA256) != 64 {
		t.Fatalf("missing immutable bindings: %+v", invocation)
	}
	resultPath := filepath.Join(invocation.EvidencePath, "result.json")
	evidence, err := os.ReadFile(resultPath)
	if err != nil {
		t.Fatal(err)
	}
	for _, forbidden := range []string{packet.Context, packet.Purpose, "activation-test-provider-key", runner.stdout} {
		if strings.Contains(string(evidence), forbidden) {
			t.Fatalf("durable evidence leaked transient material %q", forbidden)
		}
	}
}

func TestOpenCodeActivationReplayRejectedAcrossServiceRestart(t *testing.T) {
	t.Setenv("OPENROUTER_API_KEY", "activation-test-provider-key")
	cfg, root := activationOpenCodeConfig(t)
	runner := &activationAdvisoryRunner{stdout: "{}\n"}
	packet := activationPacket()

	first := NewOpenCodeAdvisoryService(root, cfg)
	first.runner = runner
	if _, err := first.Run(context.Background(), packet, io.Discard, io.Discard); err != nil {
		t.Fatal(err)
	}

	second := NewOpenCodeAdvisoryService(root, cfg)
	second.runner = runner
	_, err := second.Run(context.Background(), packet, io.Discard, io.Discard)
	if err == nil || err.Error() != "OPENCODE_ADVISORY_DUPLICATE_REQUEST" {
		t.Fatalf("unexpected duplicate result: %v", err)
	}
	if runner.calls != 1 {
		t.Fatalf("duplicate reached runner; calls=%d", runner.calls)
	}

	changed := packet
	changed.Attempt++
	_, err = second.Run(context.Background(), changed, io.Discard, io.Discard)
	if err == nil || err.Error() != "OPENCODE_ADVISORY_REQUEST_BINDING_CHANGED" {
		t.Fatalf("unexpected changed-binding result: %v", err)
	}
	if runner.calls != 1 {
		t.Fatalf("changed binding reached runner; calls=%d", runner.calls)
	}
}

func TestOpenCodeActivationFailsClosedOnConfigAndExecutableDrift(t *testing.T) {
	t.Setenv("OPENROUTER_API_KEY", "activation-test-provider-key")
	cfg, root := activationOpenCodeConfig(t)
	runner := &activationAdvisoryRunner{}
	packet := activationPacket()

	tests := []struct {
		name   string
		mutate func(*Config)
		want   string
	}{
		{"disabled", func(c *Config) { c.Advisory.OpenCode.Enabled = false }, "OPENCODE_ADVISORY_NOT_ENABLED"},
		{"not-manual", func(c *Config) { c.Advisory.OpenCode.ManualOnly = false }, "OPENCODE_ADVISORY_MANUAL_ONLY_REQUIRED"},
		{"bad-provider", func(c *Config) { c.Advisory.OpenCode.Model = "anthropic/example" }, "OPENCODE_ADVISORY_MODEL_INVALID"},
		{"bad-key-env", func(c *Config) { c.Advisory.OpenCode.APIKeyEnv = "OTHER_KEY" }, "OPENCODE_ADVISORY_KEY_ENV_INVALID"},
		{"bad-timeout", func(c *Config) { c.Advisory.OpenCode.TimeoutSeconds = 301 }, "OPENCODE_ADVISORY_TIMEOUT_INVALID"},
		{"sha-drift", func(c *Config) { c.Advisory.OpenCode.ExecutableSHA256 = strings.Repeat("0", 64) }, "OPENCODE_ADVISORY_TOOL_SHA_MISMATCH"},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			changed := cfg
			tc.mutate(&changed)
			service := NewOpenCodeAdvisoryService(root, changed)
			service.runner = runner
			_, err := service.Run(context.Background(), packet, io.Discard, io.Discard)
			if err == nil || err.Error() != tc.want {
				t.Fatalf("got %v, want %s", err, tc.want)
			}
		})
	}
	if runner.calls != 0 {
		t.Fatalf("invalid activation config reached runner: %d", runner.calls)
	}
}

func TestOpenCodeActivationPacketParserIsExact(t *testing.T) {
	packet := activationPacket()
	raw, err := json.Marshal(packet)
	if err != nil {
		t.Fatal(err)
	}
	parsed, err := ParseOpenCodeAdvisoryPacket(raw)
	if err != nil {
		t.Fatal(err)
	}
	if parsed.RequestID != packet.RequestID || parsed.Context != packet.Context {
		t.Fatalf("parsed packet mismatch: %+v", parsed)
	}

	var fields map[string]any
	if err := json.Unmarshal(raw, &fields); err != nil {
		t.Fatal(err)
	}
	fields["unexpected"] = true
	unknown, _ := json.Marshal(fields)
	if _, err = ParseOpenCodeAdvisoryPacket(unknown); err == nil || err.Error() != "OPENCODE_ADVISORY_PACKET_JSON_INVALID" {
		t.Fatalf("unknown field accepted: %v", err)
	}
	if _, err = ParseOpenCodeAdvisoryPacket(append(raw, raw...)); err == nil || err.Error() != "OPENCODE_ADVISORY_PACKET_JSON_INVALID" {
		t.Fatalf("multiple documents accepted: %v", err)
	}
}

func TestOpenCodeActivationCredentialLeakFailsClosedWithoutEmission(t *testing.T) {
	const key = "activation-test-provider-key"
	t.Setenv("OPENROUTER_API_KEY", key)
	cfg, root := activationOpenCodeConfig(t)
	runner := &activationAdvisoryRunner{stdout: "provider accidentally echoed " + key}
	service := NewOpenCodeAdvisoryService(root, cfg)
	service.runner = runner

	var stdout, stderr bytes.Buffer
	invocation, err := service.Run(context.Background(), activationPacket(), &stdout, &stderr)
	if err == nil || err.Error() != "OPENCODE_ADVISORY_CREDENTIAL_LEAK_DETECTED" {
		t.Fatalf("unexpected leak result: %v", err)
	}
	if stdout.Len() != 0 || stderr.Len() != 0 {
		t.Fatal("credential-bearing output was emitted to caller")
	}
	if invocation.Succeeded || strings.Contains(invocation.Failure, key) {
		t.Fatalf("credential leaked into invocation metadata: %+v", invocation)
	}
	evidence, readErr := os.ReadFile(filepath.Join(invocation.EvidencePath, "result.json"))
	if readErr != nil {
		t.Fatal(readErr)
	}
	if strings.Contains(string(evidence), key) || strings.Contains(string(evidence), runner.stdout) {
		t.Fatal("credential-bearing output persisted in evidence")
	}
}

func TestOpenCodeActivationRunnerFailurePersistsDigestOnlyEvidence(t *testing.T) {
	t.Setenv("OPENROUTER_API_KEY", "activation-test-provider-key")
	cfg, root := activationOpenCodeConfig(t)
	rawProviderError := "{\"type\":\"error\",\"error\":{\"name\":\"APIError\",\"data\":{\"message\":\"synthetic provider detail that must not escape\",\"statusCode\":404,\"isRetryable\":false,\"responseHeaders\":{\"set-cookie\":\"sensitive-cookie\"},\"responseBody\":\"sensitive-account-id\"}}}\n"
	runner := &activationAdvisoryRunner{stdout: rawProviderError, stderr: "synthetic provider failure\n", err: errors.New("synthetic failure")}
	service := NewOpenCodeAdvisoryService(root, cfg)
	service.runner = runner

	var stdout, stderr bytes.Buffer
	invocation, err := service.Run(context.Background(), activationPacket(), &stdout, &stderr)
	if err == nil {
		t.Fatal("runner failure unexpectedly succeeded")
	}
	if stdout.Len() != 0 || stderr.Len() != 0 {
		t.Fatalf("raw provider failure escaped to caller: stdout=%q stderr=%q", stdout.String(), stderr.String())
	}
	if invocation.ProviderErrorName != "APIError" || invocation.ProviderErrorCategory != "provider_not_found" || invocation.ProviderErrorStatus != 404 || invocation.ProviderErrorRetryable == nil || *invocation.ProviderErrorRetryable {
		t.Fatalf("provider failure classification missing or incorrect: %+v", invocation)
	}
	evidence, readErr := os.ReadFile(filepath.Join(invocation.EvidencePath, "result.json"))
	if readErr != nil {
		t.Fatal(readErr)
	}
	for _, forbidden := range []string{rawProviderError, runner.stderr, "sensitive-cookie", "sensitive-account-id", "synthetic provider detail that must not escape"} {
		if strings.Contains(string(evidence), forbidden) {
			t.Fatalf("provider failure detail persisted instead of digest-only metadata: %q", forbidden)
		}
	}
	if invocation.StdoutBytes == 0 || invocation.StderrBytes == 0 || len(invocation.StdoutSHA256) != 64 || len(invocation.StderrSHA256) != 64 {
		t.Fatalf("provider failure digest metadata missing: %+v", invocation)
	}
}
