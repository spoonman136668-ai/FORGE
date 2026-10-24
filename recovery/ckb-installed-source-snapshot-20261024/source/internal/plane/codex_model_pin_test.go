package plane

import (
	"bytes"
	"context"
	"io"
	"slices"
	"strings"
	"testing"
)

type codexModelCaptureRunner struct {
	spec ProcessSpec
}

func (r *codexModelCaptureRunner) Run(_ context.Context, s ProcessSpec, _, _ io.Writer) error {
	r.spec = s
	return nil
}

func TestCodexWorkerPinsAndReportsTerraModel(t *testing.T) {
	runner := &codexModelCaptureRunner{}
	var stdout bytes.Buffer
	adapter := CodexAdapter{
		Tool:   "codex.exe",
		Home:   "C:\\codex-home",
		Runner: runner,
	}
	if err := adapter.Run(context.Background(), t.TempDir(), WorkOrder{}, &stdout, io.Discard); err != nil {
		t.Fatal(err)
	}
	want := []string{"exec", "-m", codexWorkerModel}
	found := false
	for i := 0; i+len(want) <= len(runner.spec.Args); i++ {
		if slices.Equal(runner.spec.Args[i:i+len(want)], want) {
			found = true
			break
		}
	}
	if !found {
		t.Fatalf("Codex invocation does not pin model: args=%q", runner.spec.Args)
	}
	if codexWorkerModel != "gpt-5.6-terra" {
		t.Fatalf("unexpected pinned model %q", codexWorkerModel)
	}
	if !strings.Contains(stdout.String(), "CKB_PLANE_CODEX_MODEL="+codexWorkerModel) {
		t.Fatalf("worker stdout lacks model observability marker: %q", stdout.String())
	}
}
