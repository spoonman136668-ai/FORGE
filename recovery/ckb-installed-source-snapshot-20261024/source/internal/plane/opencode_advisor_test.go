package plane

import (
	"context"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

type captureOpenCodeRunner struct {
	calls int
	spec  ProcessSpec
	err   error
}

func (r *captureOpenCodeRunner) Run(_ context.Context, spec ProcessSpec, _, _ io.Writer) error {
	r.calls++
	r.spec = spec
	return r.err
}

func validOpenCodePacket() OpenCodeAdvisoryPacket {
	return OpenCodeAdvisoryPacket{
		Schema:             openCodeAdvisorPacketSchema,
		RequestID:          "oc_advisory_001",
		SubjectID:          "WO_TEST_001",
		Attempt:            1,
		Purpose:            "Independently analyze the supplied bounded failure evidence.",
		EvidenceSHA256:     strings.Repeat("a", 64),
		DataClassification: "synthetic",
		Context:            "Synthetic compiler failure: expected X, observed Y.",
	}
}

func validOpenCodeAdvisor(t *testing.T, runner ProcessRunner) OpenCodeAdvisor {
	t.Helper()
	return OpenCodeAdvisor{
		Config: OpenCodeAdvisorConfig{
			Enabled:   true,
			Tool:      filepath.Join(t.TempDir(), "opencode.exe"),
			Model:     "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
			APIKeyEnv: "OPENROUTER_API_KEY",
		},
		Runner: runner,
		Replay: NewOpenCodeReplayFence(t.TempDir()),
	}
}

func envValue(env []string, name string) string {
	prefix := name + "="
	for _, entry := range env {
		if strings.HasPrefix(entry, prefix) {
			return strings.TrimPrefix(entry, prefix)
		}
	}
	return ""
}

func TestOpenCodeAdvisorDisabledFailsClosed(t *testing.T) {
	runner := &captureOpenCodeRunner{}
	a := OpenCodeAdvisor{Config: OpenCodeAdvisorConfig{Enabled: false}, Runner: runner}
	err := a.Run(context.Background(), t.TempDir(), validOpenCodePacket(), io.Discard, io.Discard)
	if err == nil || err.Error() != "OPENCODE_ADVISOR_DISABLED" {
		t.Fatalf("unexpected error: %v", err)
	}
	if runner.calls != 0 {
		t.Fatalf("runner called while disabled: %d", runner.calls)
	}
}

func TestOpenCodeAdvisorUsesOneShotReadOnlyIsolatedSpec(t *testing.T) {
	t.Setenv("OPENROUTER_API_KEY", "unit-test-openrouter-secret")
	t.Setenv("AWS_SECRET_ACCESS_KEY", "must-not-pass")
	t.Setenv("OPENCODE_SERVER_PASSWORD", "must-not-pass")
	t.Setenv("OPENCODE_CONFIG_CONTENT", `{"permission":"allow"}`)

	runner := &captureOpenCodeRunner{}
	a := validOpenCodeAdvisor(t, runner)
	requestDir := t.TempDir()
	packet := validOpenCodePacket()
	if err := a.Run(context.Background(), requestDir, packet, io.Discard, io.Discard); err != nil {
		t.Fatal(err)
	}
	if runner.calls != 1 {
		t.Fatalf("runner calls = %d, want 1", runner.calls)
	}
	spec := runner.spec
	if spec.Program != a.Config.Tool {
		t.Fatalf("program = %q, want %q", spec.Program, a.Config.Tool)
	}
	joined := strings.Join(spec.Args, " ")
	for _, required := range []string{"run", "--model openrouter/nvidia/nemotron-3-super-120b-a12b:free", "--agent ckb-advisor", "--format json"} {
		if !strings.Contains(joined, required) {
			t.Fatalf("args missing %q: %q", required, joined)
		}
	}
	for _, forbidden := range []string{"serve", "--attach", "--dangerously-skip-permissions", packet.Context, "unit-test-openrouter-secret"} {
		if strings.Contains(joined, forbidden) {
			t.Fatalf("forbidden process-argument content %q in %q", forbidden, joined)
		}
	}
	if !strings.Contains(spec.Input, packet.Context) {
		t.Fatal("bounded packet context was not delivered through stdin")
	}
	if strings.Contains(spec.Input, "unit-test-openrouter-secret") {
		t.Fatal("provider credential leaked into stdin")
	}
	if got := envValue(spec.Env, "OPENROUTER_API_KEY"); got != "unit-test-openrouter-secret" {
		t.Fatalf("provider credential not explicitly scoped: %q", got)
	}
	for _, forbiddenEnv := range []string{"AWS_SECRET_ACCESS_KEY", "OPENCODE_SERVER_PASSWORD"} {
		if got := envValue(spec.Env, forbiddenEnv); got != "" {
			t.Fatalf("unexpected inherited env %s=%q", forbiddenEnv, got)
		}
	}
	for _, isolated := range []string{"HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "OPENCODE_CONFIG_DIR"} {
		got := envValue(spec.Env, isolated)
		if got == "" {
			t.Fatalf("missing isolated env %s", isolated)
		}
		if !strings.HasPrefix(strings.ToLower(filepath.Clean(got)), strings.ToLower(filepath.Clean(requestDir))) {
			t.Fatalf("%s escaped request directory: %q", isolated, got)
		}
	}
	inline := envValue(spec.Env, "OPENCODE_CONFIG_CONTENT")
	for _, required := range []string{
		`"autoupdate":false`, `"default_agent":"ckb-advisor"`, `"enabled_providers":["openrouter"]`,
		`"permission":{"*":"deny"}`, `"share":"disabled"`, `"snapshot":false`, `"subagent_depth":0`, `"nvidia/nemotron-3-super-120b-a12b:free"`,
	} {
		if !strings.Contains(inline, required) {
			t.Fatalf("inline config missing %s: %s", required, inline)
		}
	}
	if strings.Contains(inline, "unit-test-openrouter-secret") {
		t.Fatal("provider credential leaked into inline config")
	}
}

func TestOpenCodeAdvisorRejectsNonEmptyRequestDirectory(t *testing.T) {
	t.Setenv("OPENROUTER_API_KEY", "unit-test-openrouter-secret")
	runner := &captureOpenCodeRunner{}
	a := validOpenCodeAdvisor(t, runner)
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "unexpected.txt"), []byte("do not expose"), 0600); err != nil {
		t.Fatal(err)
	}
	err := a.Run(context.Background(), dir, validOpenCodePacket(), io.Discard, io.Discard)
	if err == nil || err.Error() != "OPENCODE_ADVISOR_DIRECTORY_NOT_EMPTY" {
		t.Fatalf("unexpected error: %v", err)
	}
	if runner.calls != 0 {
		t.Fatal("runner called for non-empty request directory")
	}
}

func TestOpenCodeAdvisorRejectsMissingReplayFence(t *testing.T) {
	t.Setenv("OPENROUTER_API_KEY", "unit-test-openrouter-secret")
	runner := &captureOpenCodeRunner{}
	a := validOpenCodeAdvisor(t, runner)
	a.Replay = nil
	err := a.Run(context.Background(), t.TempDir(), validOpenCodePacket(), io.Discard, io.Discard)
	if err == nil || err.Error() != "OPENCODE_ADVISORY_REPLAY_FENCE_REQUIRED" {
		t.Fatalf("unexpected error: %v", err)
	}
	if runner.calls != 0 {
		t.Fatal("runner called without replay fence")
	}
}

func TestOpenCodeAdvisorReplayFencePersistsAcrossAdvisorRestart(t *testing.T) {
	t.Setenv("OPENROUTER_API_KEY", "unit-test-openrouter-secret")
	replayDir := t.TempDir()
	packet := validOpenCodePacket()

	firstRunner := &captureOpenCodeRunner{}
	first := validOpenCodeAdvisor(t, firstRunner)
	first.Replay = NewOpenCodeReplayFence(replayDir)
	if err := first.Run(context.Background(), t.TempDir(), packet, io.Discard, io.Discard); err != nil {
		t.Fatal(err)
	}
	if firstRunner.calls != 1 {
		t.Fatalf("first runner calls = %d", firstRunner.calls)
	}

	secondRunner := &captureOpenCodeRunner{}
	second := validOpenCodeAdvisor(t, secondRunner)
	second.Config.Tool = first.Config.Tool
	second.Replay = NewOpenCodeReplayFence(replayDir)
	err := second.Run(context.Background(), t.TempDir(), packet, io.Discard, io.Discard)
	if err == nil || err.Error() != "OPENCODE_ADVISORY_DUPLICATE_REQUEST" {
		t.Fatalf("unexpected replay result: %v", err)
	}
	if secondRunner.calls != 0 {
		t.Fatal("duplicate replay reached runner")
	}
}

func TestOpenCodeAdvisorReplayFenceRejectsChangedBinding(t *testing.T) {
	t.Setenv("OPENROUTER_API_KEY", "unit-test-openrouter-secret")
	replayDir := t.TempDir()
	packet := validOpenCodePacket()

	firstRunner := &captureOpenCodeRunner{}
	first := validOpenCodeAdvisor(t, firstRunner)
	first.Replay = NewOpenCodeReplayFence(replayDir)
	if err := first.Run(context.Background(), t.TempDir(), packet, io.Discard, io.Discard); err != nil {
		t.Fatal(err)
	}

	tests := []struct {
		name   string
		mutate func(*OpenCodeAdvisor, *OpenCodeAdvisoryPacket)
	}{
		{"attempt", func(_ *OpenCodeAdvisor, p *OpenCodeAdvisoryPacket) { p.Attempt++ }},
		{"evidence", func(_ *OpenCodeAdvisor, p *OpenCodeAdvisoryPacket) { p.EvidenceSHA256 = strings.Repeat("b", 64) }},
		{"model", func(a *OpenCodeAdvisor, _ *OpenCodeAdvisoryPacket) { a.Config.Model = "openrouter/nvidia/nemotron-3-super-120b-a12b:free-next" }},
		{"tool", func(a *OpenCodeAdvisor, _ *OpenCodeAdvisoryPacket) { a.Config.Tool = filepath.Join(t.TempDir(), "replacement-opencode.exe") }},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			changed := packet
			runner := &captureOpenCodeRunner{}
			a := validOpenCodeAdvisor(t, runner)
			a.Config.Tool = first.Config.Tool
			a.Replay = NewOpenCodeReplayFence(replayDir)
			tc.mutate(&a, &changed)
			err := a.Run(context.Background(), t.TempDir(), changed, io.Discard, io.Discard)
			if err == nil || err.Error() != "OPENCODE_ADVISORY_REQUEST_BINDING_CHANGED" {
				t.Fatalf("unexpected binding result: %v", err)
			}
			if runner.calls != 0 {
				t.Fatal("changed request binding reached runner")
			}
		})
	}
}

func TestOpenCodeAdvisorReplayClaimStoresDigestOnly(t *testing.T) {
	replayDir := t.TempDir()
	packet := validOpenCodePacket()
	fence := NewOpenCodeReplayFence(replayDir)
	tool := filepath.Join(t.TempDir(), "opencode.exe")
	model := "openrouter/nvidia/nemotron-3-super-120b-a12b:free"
	if err := fence.Claim(packet, tool, model); err != nil {
		t.Fatal(err)
	}
	entries, err := os.ReadDir(replayDir)
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) != 1 {
		t.Fatalf("claim files = %d, want 1", len(entries))
	}
	b, err := os.ReadFile(filepath.Join(replayDir, entries[0].Name()))
	if err != nil {
		t.Fatal(err)
	}
	text := strings.TrimSpace(string(b))
	if len(text) != 64 || strings.Trim(text, "0123456789abcdef") != "" {
		t.Fatalf("claim is not a SHA-256 digest: %q", text)
	}
	for _, forbidden := range []string{packet.RequestID, packet.SubjectID, packet.Context, packet.Purpose, packet.EvidenceSHA256, tool, model} {
		if strings.Contains(string(b), forbidden) || strings.Contains(entries[0].Name(), forbidden) {
			t.Fatalf("claim leaked binding material %q", forbidden)
		}
	}
}

func TestOpenCodeAdvisorRejectsUnclassifiedOrOversizedContext(t *testing.T) {
	packet := validOpenCodePacket()
	packet.DataClassification = "private"
	if err := packet.Validate(); err == nil || err.Error() != "OPENCODE_ADVISORY_DATA_CLASSIFICATION_INVALID" {
		t.Fatalf("unexpected classification result: %v", err)
	}
	packet = validOpenCodePacket()
	packet.Context = strings.Repeat("x", openCodeAdvisorMaxContext+1)
	if err := packet.Validate(); err == nil || err.Error() != "OPENCODE_ADVISORY_CONTEXT_INVALID" {
		t.Fatalf("unexpected context result: %v", err)
	}
}

func TestOpenCodeAdvisorRejectsUnapprovedProviderAndKeyBinding(t *testing.T) {
	a := OpenCodeAdvisor{Config: OpenCodeAdvisorConfig{
		Enabled: true, Tool: filepath.Join(t.TempDir(), "opencode.exe"), Model: "anthropic/claude-sonnet", APIKeyEnv: "OPENROUTER_API_KEY",
	}}
	if err := a.validate(); err == nil || err.Error() != "OPENCODE_ADVISOR_MODEL_INVALID" {
		t.Fatalf("unexpected provider result: %v", err)
	}
	a.Config.Model = "openrouter/nvidia/nemotron-3-super-120b-a12b:free"
	a.Config.APIKeyEnv = "SOME_OTHER_KEY"
	if err := a.validate(); err == nil || err.Error() != "OPENCODE_ADVISOR_KEY_ENV_INVALID" {
		t.Fatalf("unexpected key binding result: %v", err)
	}
}
