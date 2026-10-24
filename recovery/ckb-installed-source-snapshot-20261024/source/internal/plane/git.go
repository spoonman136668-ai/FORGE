package plane

import (
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

func git(tool, dir string, args ...string) (string, error) {
	return gitContext(context.Background(), tool, dir, args...)
}

func gitContext(parent context.Context, tool, dir string, args ...string) (string, error) {
	ctx, cancel := context.WithTimeout(parent, 2*time.Minute)
	defer cancel()
	a := append([]string{"-c", "core.hooksPath=", "-c", "core.fsmonitor=false", "-c", "core.longpaths=true", "-c", "protocol.file.allow=always"}, args...)
	c := exec.CommandContext(ctx, tool, a...)
	c.Dir = dir
	c.WaitDelay = 2 * time.Second
	c.Env = append(os.Environ(), "GIT_TERMINAL_PROMPT=0", "GIT_CONFIG_NOSYSTEM=1")
	b, e := c.CombinedOutput()
	if e != nil {
		operation := "command"
		if len(args) > 0 {
			operation = args[0]
		}
		output := strings.TrimSpace(string(b))
		if len(output) > 4096 {
			output = output[len(output)-4096:]
		}
		return "", &gitCommandError{operation: operation, output: output, cause: e}
	}
	if len(args) > 0 {
		for _, arg := range args {
			if arg == "-z" {
				return string(b), nil
			}
		}
	}
	return strings.TrimSpace(string(b)), nil
}

func refs(tool, dir string) (string, error) {
	return refsContext(context.Background(), tool, dir)
}

func refsContext(ctx context.Context, tool, dir string) (string, error) {
	return gitContext(ctx, tool, dir, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads/accepted/", "refs/tags/accepted/", "refs/remotes/origin/accepted/")
}

func baseline(tool, dir string, w WorkOrder) error {
	if id, ok := localCandidateBaselineID(w.Baseline.Ref); ok {
		refName := "refs/ckb-plane/candidates/" + id
		v, e := git(tool, dir, "rev-parse", "--verify", refName+"^{commit}")
		if e != nil || v != w.Baseline.SHA {
			return errors.New("BASELINE_MISMATCH")
		}
		return nil
	} // Resolve the exact accepted baseline from local heads/tags or a read-only
	// remote-tracking origin ref. R4a clean source clones intentionally carry
	// refs/remotes/origin/accepted/... rather than creating or moving local
	// accepted refs. Multiple matching refs are acceptable only when every
	// resolved candidate points at the required SHA; conflicting refs fail closed.
	type resolvedBaseline struct {
		ref string
		sha string
	}
	var found []resolvedBaseline
	for _, prefix := range []string{"refs/heads/", "refs/tags/", "refs/remotes/origin/"} {
		refName := prefix + w.Baseline.Ref
		v, e := git(tool, dir, "rev-parse", "--verify", refName+"^{commit}")
		if e == nil {
			found = append(found, resolvedBaseline{ref: refName, sha: v})
		}
	}
	if len(found) == 0 {
		return errors.New("BASELINE_MISMATCH")
	}
	for _, r := range found {
		if r.sha != w.Baseline.SHA {
			return errors.New("BASELINE_MISMATCH")
		}
	}
	return nil
}
func checkRepo(tool string, r Repo, w WorkOrder) error {
	if r.Mode != "engineering" && r.Mode != "demo" {
		return errors.New("REPO_UNAVAILABLE: registry entry is not engineering or demo")
	}
	if strings.TrimSpace(r.LocalPath) == "" {
		return errors.New("REPO_UNAVAILABLE: local engineering repository missing")
	}
	if _, e := os.Stat(r.LocalPath); e != nil {
		return errors.New("REPO_UNAVAILABLE: local engineering repository missing")
	}
	if _, e := git(tool, r.LocalPath, "rev-parse", "--git-dir"); e != nil {
		return errors.New("REPO_UNAVAILABLE: local engineering path is not a git repository")
	}
	if e := baseline(tool, r.LocalPath, w); e != nil {
		return e
	}
	// The registered source checkout is an object/provenance source only.
	// Worker bytes are fetched by exact pinned SHA into a private repository.
	// Verify Git can inspect the checkout, but do not treat unrelated mutable
	// working-tree state as candidate input.
	if _, e := git(tool, r.LocalPath, "status", "--porcelain"); e != nil {
		return e
	}
	if r.Remote != "" {
		remote, e := git(tool, r.LocalPath, "remote", "get-url", "origin")
		if e != nil || remote != r.Remote {
			return errors.New("REPO_UNAVAILABLE: origin differs from registry")
		}
	}
	// Same-named branches in the registered source checkout are also not worker
	// state. The isolated private repository creates the work-order branch from
	// the exact pinned baseline and never imports the source checkout's branch.
	return nil
}

type RepoState struct {
	Baseline    string `json:"baseline"`
	SourceRefs  string `json:"source_refs"`
	AttemptRefs string `json:"attempt_refs"`
	Head        string `json:"head"`
	Status      string `json:"status"`
}

func prepare(ctx context.Context, tool, source, root string, w WorkOrder) (string, RepoState, error) {
	var before RepoState
	if e := os.MkdirAll(root, 0o700); e != nil {
		return "", before, e
	}
	before.Baseline = w.Baseline.SHA
	var e error
	before.SourceRefs, e = refsContext(ctx, tool, source)
	if e != nil {
		return "", before, e
	}

	privateRepo := filepath.Join(root, "repository")
	work := filepath.Join(root, "worktree")
	if _, statErr := os.Stat(privateRepo); !os.IsNotExist(statErr) {
		return "", before, errors.New("WORKSPACE_COLLISION: private repository path already exists")
	}
	if _, statErr := os.Stat(work); !os.IsNotExist(statErr) {
		return "", before, errors.New("WORKSPACE_COLLISION: private worktree path already exists")
	}

	// R4a3: use the Windows-safe materialization pattern already proven by R3c2.
	// Avoid local clone remote-tracking refs such as refs/remotes/origin/accepted/...
	// because those can create long nested paths on Windows. Fetch only the exact
	// verified baseline object into a private repository, then create the worker
	// branch in an isolated worktree. No remote is configured in the private repo.
	if _, e = gitContext(ctx, tool, "", "init", "--quiet", "--", privateRepo); e != nil {
		return "", before, e
	}
	if _, e = gitContext(ctx, tool, privateRepo, "fetch", "--no-tags", "--", source, w.Baseline.SHA); e != nil {
		return "", before, e
	}
	if _, e = gitContext(ctx, tool, privateRepo, "rev-parse", "--verify", w.Baseline.SHA+"^{commit}"); e != nil {
		return "", before, errors.New("BASELINE_MISMATCH")
	}
	if _, e = gitContext(ctx, tool, privateRepo, "worktree", "add", "-b", w.Worker.Branch, work, w.Baseline.SHA); e != nil {
		return "", before, e
	}
	before.AttemptRefs, e = refsContext(ctx, tool, work)
	if e != nil {
		return "", before, e
	}
	before.Head, e = gitContext(ctx, tool, work, "rev-parse", "HEAD")
	if e != nil {
		return "", before, e
	}
	before.Status, e = gitContext(ctx, tool, work, "status", "--porcelain")
	if e != nil || before.Status != "" {
		return "", before, errors.New("SOURCE_HYGIENE_FAILED")
	}
	return work, before, nil
}

var prepareWorkspace = prepare

func changed(tool, dir, base string) ([]string, error) {
	// Include committed, staged, unstaged, untracked and ignored files; do not parse quoted status output.
	var result []string
	seen := map[string]bool{}
	for _, args := range [][]string{{"diff", "--name-only", "--no-renames", "-z", base, "--"}, {"ls-files", "--others", "-z"}} {
		s, e := git(tool, dir, args...)
		if e != nil {
			return nil, e
		}
		for _, p := range strings.Split(s, "\x00") {
			if p != "" && !seen[p] {
				seen[p] = true
				result = append(result, p)
			}
		}
	}
	return result, nil
}

// Keep raw Git output out of ordinary status/mailbox errors. Local proof
// diagnostics can explicitly retain the bounded output from local Git commands.
type gitCommandError struct {
	operation string
	output    string
	cause     error
}

func (e *gitCommandError) Error() string {
	return fmt.Sprintf("git %s failed: %v", e.operation, e.cause)
}
func (e *gitCommandError) Unwrap() error { return e.cause }
