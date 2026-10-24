package plane

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

func writeJSON(p string, v any) error {
	b, e := json.MarshalIndent(v, "", "  ")
	if e != nil {
		return e
	}
	return os.WriteFile(p, append(b, '\n'), 0600)
}
func digest(b []byte) string { h := sha256.Sum256(b); return hex.EncodeToString(h[:]) }
func (p *Engine) capture(j Job, before RepoState) ([]string, error) {
	tool := p.Config.Tools.Git
	files, e := changed(tool, j.Workspace, j.Order.Baseline.SHA)
	if e != nil {
		return nil, e
	}
	sort.Strings(files)
	if e = p.candidateIndex(j, files); e != nil {
		return nil, e
	}
	patch, e := git(tool, j.Workspace, "diff", "--binary", "--no-ext-diff", "--no-textconv", j.Order.Baseline.SHA, "--")
	if e != nil {
		return nil, e
	}
	if e = os.WriteFile(filepath.Join(j.Evidence, "candidate.diff"), []byte(patch), 0600); e != nil {
		return nil, e
	}
	// Untracked files are kept separately; candidate.diff is explicitly tracked-only.
	for _, name := range files {
		if !safePath(name) {
			return nil, fmt.Errorf("unsafe candidate path")
		}
		info, e := os.Lstat(filepath.Join(j.Workspace, filepath.FromSlash(name)))
		if os.IsNotExist(e) {
			continue
		}
		if e != nil {
			return nil, e
		}
		if !info.Mode().IsRegular() {
			return nil, fmt.Errorf("candidate contains non-regular file")
		}
		if info.Size() > 4<<20 {
			return nil, fmt.Errorf("candidate file exceeds 4 MiB")
		}
		b, e := os.ReadFile(filepath.Join(j.Workspace, filepath.FromSlash(name)))
		if e != nil {
			return nil, e
		}
		dest := filepath.Join(j.Evidence, "candidate_files", filepath.FromSlash(name))
		if e = os.MkdirAll(filepath.Dir(dest), 0700); e != nil {
			return nil, e
		}
		if e = os.WriteFile(dest, b, 0600); e != nil {
			return nil, e
		}
	}
	if e = os.WriteFile(filepath.Join(j.Evidence, "changed_files.txt"), []byte(strings.Join(files, "\n")+"\n"), 0600); e != nil {
		return nil, e
	}
	after := RepoState{Baseline: before.Baseline}
	after.Head, e = git(tool, j.Workspace, "rev-parse", "HEAD")
	if e != nil {
		return nil, e
	}
	after.SourceRefs, e = refs(tool, p.Config.Repos[j.Order.Repo].LocalPath)
	if e != nil {
		return nil, e
	}
	after.AttemptRefs, e = refs(tool, j.Workspace)
	if e != nil {
		return nil, e
	}
	after.Status, e = git(tool, j.Workspace, "status", "--porcelain")
	if e != nil {
		return nil, e
	}
	return files, writeJSON(filepath.Join(j.Evidence, "repo_state_after.json"), after)
}
func Manifest(dir string) (map[string]string, error) {
	m := map[string]string{}
	e := filepath.WalkDir(dir, func(p string, d os.DirEntry, e error) error {
		if e != nil {
			return e
		}
		if d.IsDir() {
			return nil
		}
		rel, e := filepath.Rel(dir, p)
		if e != nil {
			return e
		}
		if rel == "evidence_manifest.json" {
			return nil
		}
		if d.Type()&os.ModeSymlink != 0 {
			return fmt.Errorf("evidence symlink prohibited")
		}
		b, e := os.ReadFile(p)
		if e != nil {
			return e
		}
		m[filepath.ToSlash(rel)] = digest(b)
		return nil
	})
	return m, e
}
func VerifyManifest(dir string) error {
	b, e := os.ReadFile(filepath.Join(dir, "evidence_manifest.json"))
	if e != nil {
		return e
	}
	var expected map[string]string
	if e = json.Unmarshal(b, &expected); e != nil {
		return e
	}
	actual, e := Manifest(dir)
	if e != nil {
		return e
	}
	if len(actual) != len(expected) {
		return fmt.Errorf("evidence manifest inventory mismatch")
	}
	for k, v := range actual {
		if expected[k] != v {
			return fmt.Errorf("evidence hash mismatch: %s", k)
		}
	}
	return nil
}
func (p *Engine) Seal(j Job) error {
	var events []Event
	var after int64
	for {
		batch, err := p.Store.Events(after)
		if err != nil {
			return err
		}
		events = append(events, batch...)
		if len(batch) < 500 {
			break
		}
		after = batch[len(batch)-1].ID
	}
	var e error
	var b strings.Builder
	for _, v := range events {
		if v.WorkOrderID == j.ID && v.Attempt == j.Attempt {
			b.WriteString(jsonText(v))
			b.WriteByte('\n')
		}
	}
	if e = os.WriteFile(filepath.Join(j.Evidence, "events.jsonl"), []byte(b.String()), 0600); e != nil {
		return e
	}
	current, e := p.Store.Get(j.ID)
	if e != nil {
		return e
	}
	if j.State == "ACCEPTED" || j.State == "BLOCKED" || j.State == "REJECTED_RETRYABLE" {
		current.State = j.State
		current.Reason = j.Reason
	}
	if e = writeJSON(filepath.Join(j.Evidence, "attempt_result.json"), map[string]any{"state": current.State, "reason": current.Reason, "attempt": current.Attempt}); e != nil {
		return e
	}
	m, e := Manifest(j.Evidence)
	if e != nil {
		return e
	}
	if e = writeJSON(filepath.Join(j.Evidence, "evidence_manifest.json"), m); e != nil {
		return e
	}
	if e = VerifyManifest(j.Evidence); e != nil {
		return e
	}
	manifestBytes, e := os.ReadFile(filepath.Join(j.Evidence, "evidence_manifest.json"))
	if e != nil {
		return e
	}
	if _, e = p.Store.DB.Exec("INSERT OR REPLACE INTO evidence_seals VALUES(?,?,?)", j.ID, j.Attempt, digest(manifestBytes)); e != nil {
		return e
	}
	for name, hash := range m {
		if _, e = p.Store.DB.Exec("INSERT OR REPLACE INTO artifacts VALUES(?,?,?,?)", j.ID, j.Attempt, name, hash); e != nil {
			return e
		}
	}
	return nil
}

func (p *Engine) VerifyEvidence(j Job) error {
	if e := VerifyManifest(j.Evidence); e != nil {
		return e
	}
	var expected string
	if e := p.Store.DB.QueryRow("SELECT manifest_sha256 FROM evidence_seals WHERE work_order_id=? AND attempt=?", j.ID, j.Attempt).Scan(&expected); e != nil {
		return e
	}
	b, e := os.ReadFile(filepath.Join(j.Evidence, "evidence_manifest.json"))
	if e != nil {
		return e
	}
	if digest(b) != expected {
		return fmt.Errorf("EVIDENCE_ANCHOR_MISMATCH")
	}
	return nil
}
