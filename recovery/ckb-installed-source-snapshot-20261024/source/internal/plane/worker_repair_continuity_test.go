package plane

import (
	"context"
	"io"
	"strings"
	"testing"
)

type repairContinuationCaptureRunner struct {
	spec ProcessSpec
}

func (r *repairContinuationCaptureRunner) Run(_ context.Context, spec ProcessSpec, _, _ io.Writer) error {
	r.spec = spec
	return nil
}

func TestCodexRepairContinuationPromptIsExplicitAndScoped(t *testing.T) {
	runner := &repairContinuationCaptureRunner{}
	adapter := CodexAdapter{
		Tool:     "codex",
		Home:     "test-home",
		Runner:   runner,
		Feedback: "GO_TEST_FAILED\n--- FAIL: TestR64Continuity",
	}

	if err := adapter.Run(context.Background(), t.TempDir(), WorkOrder{}, io.Discard, io.Discard); err != nil {
		t.Fatal(err)
	}

	for _, want := range []string{
		"REPAIR CONTINUATION:",
		"unchanged work-order scope",
		"smallest in-scope correction",
		"do not blindly repeat the previous approach",
		"grant no additional authority",
		"PREVIOUS ATTEMPT DIAGNOSTICS",
		"GO_TEST_FAILED",
		"TestR64Continuity",
	} {
		if !strings.Contains(runner.spec.Input, want) {
			t.Fatalf("repair continuation prompt missing %q: %q", want, runner.spec.Input)
		}
	}
}

func TestCodexRepairContinuationPromptAbsentWithoutFeedback(t *testing.T) {
	runner := &repairContinuationCaptureRunner{}
	adapter := CodexAdapter{Tool: "codex", Home: "test-home", Runner: runner}
	if err := adapter.Run(context.Background(), t.TempDir(), WorkOrder{}, io.Discard, io.Discard); err != nil {
		t.Fatal(err)
	}
	if strings.Contains(runner.spec.Input, "REPAIR CONTINUATION:") {
		t.Fatalf("first-pass worker was incorrectly placed in repair continuation mode: %q", runner.spec.Input)
	}
}
