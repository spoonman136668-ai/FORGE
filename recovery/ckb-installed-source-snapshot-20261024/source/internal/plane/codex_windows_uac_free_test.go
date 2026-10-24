package plane

import (
	"reflect"
	"strings"
	"testing"
)

func TestCodexPolicyArgsUseNonInteractiveUnelevatedWindowsSandbox(t *testing.T) {
	got := policyArgs()
	want := []string{
		"-c", `approval_policy="never"`,
		"-c", `sandbox_mode="workspace-write"`,
		"-c", "sandbox_workspace_write.network_access=false",
		"-c", `windows.sandbox="unelevated"`,
	}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("policyArgs()=%q want=%q", got, want)
	}
	for _, arg := range got {
		if strings.Contains(arg, `windows.sandbox="elevated"`) {
			t.Fatalf("UAC-prone elevated sandbox must not be used by unattended workers: %q", got)
		}
	}
}

func TestCodexPolicyArgsKeepSandboxAndNetworkDenial(t *testing.T) {
	joined := strings.Join(policyArgs(), "\n")
	for _, required := range []string{
		`approval_policy="never"`,
		`sandbox_mode="workspace-write"`,
		"sandbox_workspace_write.network_access=false",
		`windows.sandbox="unelevated"`,
	} {
		if !strings.Contains(joined, required) {
			t.Fatalf("missing required Codex worker policy %q in %q", required, policyArgs())
		}
	}
}
