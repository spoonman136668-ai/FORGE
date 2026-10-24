//go:build windows

package plane

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func makeOpenCodeJunction(t *testing.T, link, target string) {
	t.Helper()
	cmd := exec.Command(os.Getenv("COMSPEC"), "/d", "/c", "mklink", "/J", link, target)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("mklink /J failed: %v: %s", err, strings.TrimSpace(string(out)))
	}
	t.Cleanup(func() {
		_ = exec.Command(os.Getenv("COMSPEC"), "/d", "/c", "rmdir", link).Run()
	})
}

func TestOpenCodeAdvisorRejectsJunctionWorkspace(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(root, "target")
	link := filepath.Join(root, "workspace-junction")
	if err := os.Mkdir(target, 0700); err != nil {
		t.Fatal(err)
	}
	makeOpenCodeJunction(t, link, target)

	err := validateOpenCodePrivatePath(link, true)
	if err == nil || err.Error() != "OPENCODE_ADVISOR_WORKSPACE_REPARSE_UNSAFE" {
		t.Fatalf("unexpected junction result: %v", err)
	}
}

func TestOpenCodeAdvisorRejectsJunctionAncestor(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(root, "target")
	child := filepath.Join(target, "child")
	link := filepath.Join(root, "ancestor-junction")
	if err := os.MkdirAll(child, 0700); err != nil {
		t.Fatal(err)
	}
	makeOpenCodeJunction(t, link, target)

	err := validateOpenCodePrivatePath(filepath.Join(link, "child"), true)
	if err == nil || err.Error() != "OPENCODE_ADVISOR_WORKSPACE_REPARSE_UNSAFE" {
		t.Fatalf("unexpected ancestor-junction result: %v", err)
	}
}

func TestOpenCodeAdvisorRejectsJunctionReplayFence(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(root, "claims-target")
	link := filepath.Join(root, "claims-junction")
	if err := os.Mkdir(target, 0700); err != nil {
		t.Fatal(err)
	}
	makeOpenCodeJunction(t, link, target)

	err := NewOpenCodeReplayFence(link).Claim(validOpenCodePacket(), filepath.Join(root, "opencode.exe"), "openrouter/stealth/union-alpha")
	if err == nil || !strings.HasPrefix(err.Error(), "OPENCODE_ADVISORY_REPLAY_FENCE_UNSAFE: OPENCODE_ADVISOR_WORKSPACE_REPARSE_UNSAFE") {
		t.Fatalf("unexpected replay junction result: %v", err)
	}
}

func TestOpenCodeAdvisorAcceptsNormalPrivateWorkspace(t *testing.T) {
	workspace := t.TempDir()
	if err := validateOpenCodePrivatePath(workspace, true); err != nil {
		t.Fatalf("normal private workspace rejected: %v", err)
	}
}


func TestOpenCodeActivationRejectsJunctionToolParent(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(root, "tool-target")
	link := filepath.Join(root, "tool-junction")
	if err := os.Mkdir(target, 0700); err != nil {
		t.Fatal(err)
	}
	toolBytes := []byte("junction-tool-fixture")
	if err := os.WriteFile(filepath.Join(target, "opencode.exe"), toolBytes, 0700); err != nil {
		t.Fatal(err)
	}
	makeOpenCodeJunction(t, link, target)

	cfg, serviceRoot := activationOpenCodeConfig(t)
	cfg.Tools.OpenCode = filepath.Join(link, "opencode.exe")
	cfg.Advisory.OpenCode.ExecutableSHA256 = openCodeBytesSHA256(toolBytes)
	_, _, err := validateOpenCodeActivationConfig(serviceRoot, cfg)
	if err == nil || !strings.HasPrefix(err.Error(), "OPENCODE_ADVISORY_TOOL_PATH_UNSAFE: OPENCODE_ADVISOR_WORKSPACE_REPARSE_UNSAFE") {
		t.Fatalf("unexpected junction tool-parent result: %v", err)
	}
}
