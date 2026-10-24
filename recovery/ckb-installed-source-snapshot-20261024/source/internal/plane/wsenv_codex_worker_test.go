package plane

import (
	"context"
	"io"
	"strings"
	"testing"
)

type wsenvCodexRecordingRunner struct {
	spec ProcessSpec
}

func (r *wsenvCodexRecordingRunner) Run(_ context.Context, spec ProcessSpec, _, _ io.Writer) error {
	r.spec = spec
	return nil
}

func TestCodexWorkerEnvironmentPreservesWindowsRootsWithoutExpandingMinimalEnv(t *testing.T) {
	t.Setenv("SYSTEMDRIVE", "Q:")
	t.Setenv("PROGRAMDATA", `Q:\ProgramData`)
	t.Setenv("CKB_TEST_SECRET", "must-not-leak")

	for _, entry := range minimalEnv() {
		upper := strings.ToUpper(entry)
		if strings.HasPrefix(upper, "SYSTEMDRIVE=") || strings.HasPrefix(upper, "PROGRAMDATA=") {
			t.Fatalf("shared minimalEnv unexpectedly expanded: %q", entry)
		}
		if strings.HasPrefix(upper, "CKB_TEST_SECRET=") {
			t.Fatalf("shared minimalEnv leaked secret: %q", entry)
		}
	}

	runner := &wsenvCodexRecordingRunner{}
	worker := CodexAdapter{Tool: "codex", Home: t.TempDir(), Runner: runner}
	if err := worker.Run(context.Background(), t.TempDir(), WorkOrder{}, io.Discard, io.Discard); err != nil {
		t.Fatal(err)
	}

	values := map[string]string{}
	for _, entry := range runner.spec.Env {
		key, value, ok := strings.Cut(entry, "=")
		if ok {
			values[strings.ToUpper(key)] = value
		}
	}

	if got := values["SYSTEMDRIVE"]; got != "Q:" {
		t.Fatalf("Codex SYSTEMDRIVE=%q, want Q:", got)
	}
	if got := values["PROGRAMDATA"]; got != `Q:\ProgramData` {
		t.Fatalf(`Codex PROGRAMDATA=%q, want Q:\ProgramData`, got)
	}
	if _, leaked := values["CKB_TEST_SECRET"]; leaked {
		t.Fatal("Codex worker leaked unapproved environment variable")
	}
}
