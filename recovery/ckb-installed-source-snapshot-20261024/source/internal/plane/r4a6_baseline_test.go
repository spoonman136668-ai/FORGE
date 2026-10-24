package plane

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestR4a6BaselineAcceptsOriginAcceptedRemoteTrackingRef(t *testing.T) {
	gitTool, err := exec.LookPath("git")
	if err != nil {
		t.Skipf("git not available: %v", err)
	}
	repo := filepath.Join(t.TempDir(), "repo")
	if err := os.MkdirAll(repo, 0o700); err != nil {
		t.Fatal(err)
	}
	r4a6Git(t, gitTool, repo, "init")
	r4a6Git(t, gitTool, repo, "config", "user.email", "r4a6@example.invalid")
	r4a6Git(t, gitTool, repo, "config", "user.name", "R4a6 Test")
	if err := os.WriteFile(filepath.Join(repo, "README.md"), []byte("r4a6 baseline\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	r4a6Git(t, gitTool, repo, "add", "README.md")
	r4a6Git(t, gitTool, repo, "commit", "-m", "r4a6 baseline")
	sha := r4a6Git(t, gitTool, repo, "rev-parse", "HEAD")

	remoteAcceptedRef := "refs/remotes/origin/" + r4aBaselineRef
	r4a6Git(t, gitTool, repo, "update-ref", remoteAcceptedRef, sha)
	if _, err := gitContext(context.Background(), gitTool, repo, "rev-parse", "--verify", "refs/heads/"+r4aBaselineRef+"^{commit}"); err == nil {
		t.Fatal("test fixture unexpectedly has a local accepted branch")
	}

	var w WorkOrder
	w.Baseline.Ref = r4aBaselineRef
	w.Baseline.SHA = sha
	if err := baseline(gitTool, repo, w); err != nil {
		t.Fatalf("baseline rejected remote-tracking accepted ref at required SHA: %v", err)
	}
}

func r4a6Git(t *testing.T, gitTool, dir string, args ...string) string {
	t.Helper()
	out, err := gitContext(context.Background(), gitTool, dir, args...)
	if err != nil {
		t.Fatalf("git %v failed: %v", args, err)
	}
	return strings.TrimSpace(out)
}
