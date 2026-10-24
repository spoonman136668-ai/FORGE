package plane

import (
	"archive/tar"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

type CandidateEntry struct {
	Path    string `json:"path"`
	SHA256  string `json:"sha256,omitempty"`
	Deleted bool   `json:"deleted"`
}

func regularPath(root, name string) error {
	if !safePath(name) {
		return errors.New("unsafe source path")
	}
	cur := root
	for _, part := range strings.Split(name, "/") {
		cur = filepath.Join(cur, part)
		info, e := os.Lstat(cur)
		if e != nil {
			return e
		}
		if info.Mode()&os.ModeSymlink != 0 {
			return errors.New("symlink source path")
		}
	}
	info, e := os.Stat(cur)
	if e != nil {
		return e
	}
	if !info.Mode().IsRegular() {
		return errors.New("non-regular source file")
	}
	return nil
}
func (p *Engine) candidateIndex(j Job, files []string) error {
	entries := []CandidateEntry{}
	for _, name := range files {
		f := filepath.Join(j.Workspace, filepath.FromSlash(name))
		if _, e := os.Lstat(f); os.IsNotExist(e) {
			entries = append(entries, CandidateEntry{Path: name, Deleted: true})
			continue
		}
		if e := regularPath(j.Workspace, name); e != nil {
			return e
		}
		b, e := os.ReadFile(f)
		if e != nil {
			return e
		}
		entries = append(entries, CandidateEntry{Path: name, SHA256: digest(b)})
	}
	return writeJSON(filepath.Join(j.Evidence, "candidate_inventory.json"), entries)
}
func (p *Engine) freeze(ctx context.Context, j Job) (string, map[string]string, error) {
	b, e := os.ReadFile(filepath.Join(j.Evidence, "candidate_inventory.json"))
	if e != nil {
		return "", nil, e
	}
	var entries []CandidateEntry
	if e = json.Unmarshal(b, &entries); e != nil {
		return "", nil, e
	}
	dir := filepath.Join(p.Root, "acceptance", j.ID, fmt.Sprint(j.Attempt))
	if e = os.MkdirAll(filepath.Dir(dir), 0700); e != nil {
		return "", nil, e
	}
	if e = os.Mkdir(dir, 0700); e != nil {
		return "", nil, errors.New("ACCEPTANCE_WORKSPACE_ALREADY_EXISTS")
	}
	if e = p.exportBaseline(ctx, p.Config.Repos[j.Order.Repo].LocalPath, j.Order.Baseline.SHA, dir); e != nil {
		return "", nil, e
	}
	seen := map[string]bool{}
	for _, entry := range entries {
		if !j.Order.Allows(entry.Path) || seen[strings.ToLower(entry.Path)] {
			return "", nil, errors.New("FORBIDDEN_PATH_MODIFIED")
		}
		seen[strings.ToLower(entry.Path)] = true
		dst := filepath.Join(dir, filepath.FromSlash(entry.Path))
		if entry.Deleted {
			if e = os.Remove(dst); e != nil {
				return "", nil, e
			}
			continue
		}
		src := filepath.Join(j.Evidence, "candidate_files", filepath.FromSlash(entry.Path))
		data, e := os.ReadFile(src)
		if e != nil || digest(data) != entry.SHA256 {
			return "", nil, errors.New("CANDIDATE_HASH_MISMATCH")
		}
		if e = os.MkdirAll(filepath.Dir(dst), 0700); e != nil {
			return "", nil, e
		}
		if e = os.WriteFile(dst, data, 0600); e != nil {
			return "", nil, e
		}
	}
	inv, e := treeInventory(dir)
	if e != nil {
		return "", nil, e
	}
	if e = writeJSON(filepath.Join(j.Evidence, "acceptance_input.json"), inv); e != nil {
		return "", nil, e
	}
	return dir, inv, nil
}
func (p *Engine) exportBaseline(parent context.Context, repo, sha, dst string) error {
	ctx, cancel := context.WithTimeout(parent, time.Minute)
	defer cancel()
	cmd := exec.CommandContext(ctx, p.Config.Tools.Git, "-c", "core.hooksPath=", "archive", "--format=tar", sha)
	cmd.Dir = repo
	cmd.WaitDelay = 2 * time.Second
	pipe, e := cmd.StdoutPipe()
	if e != nil {
		return e
	}
	if e = cmd.Start(); e != nil {
		return e
	}
	waited := false
	defer func() {
		_ = pipe.Close()
		if !waited {
			_ = cmd.Process.Kill()
			_ = cmd.Wait()
		}
	}()
	tr := tar.NewReader(pipe)
	var total int64
	for {
		h, e := tr.Next()
		if e == io.EOF {
			break
		}
		if e != nil {
			return e
		}
		if h.Typeflag == tar.TypeXGlobalHeader {
			continue
		}
		name := strings.TrimSuffix(h.Name, "/")
		if !safePath(name) {
			return errors.New("unsafe baseline archive path")
		}
		dstFile := filepath.Join(dst, filepath.FromSlash(name))
		switch h.Typeflag {
		case tar.TypeDir:
			if e = os.MkdirAll(dstFile, 0700); e != nil {
				return e
			}
		case tar.TypeReg:
			if h.Size > 16<<20 {
				return errors.New("baseline file too large")
			}
			total += h.Size
			if total > 512<<20 {
				return errors.New("baseline snapshot too large")
			}
			if e = os.MkdirAll(filepath.Dir(dstFile), 0700); e != nil {
				return e
			}
			f, e := os.OpenFile(dstFile, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
			if e != nil {
				return e
			}
			_, e = io.CopyN(f, tr, h.Size)
			ce := f.Close()
			if e != nil {
				return e
			}
			if ce != nil {
				return ce
			}
		default:
			return errors.New("baseline symlinks/submodules/special files are not supported")
		}
	}
	// tar.Reader returns EOF at the archive end marker, not necessarily at the
	// underlying pipe EOF. Git may still be writing block padding. Drain it before
	// Wait so a small Windows pipe cannot deadlock producer and consumer.
	if _, e = io.Copy(io.Discard, pipe); e != nil {
		return fmt.Errorf("git archive drain: %w", e)
	}
	e = cmd.Wait()
	waited = true
	if parent.Err() != nil {
		return parent.Err()
	}
	if ctx.Err() != nil {
		return ctx.Err()
	}
	if e != nil {
		return fmt.Errorf("git archive exit: %w", e)
	}
	return nil
}
func treeInventory(dir string) (map[string]string, error) {
	m := map[string]string{}
	e := filepath.WalkDir(dir, func(p string, d os.DirEntry, e error) error {
		if e != nil {
			return e
		}
		if p == dir {
			return nil
		}
		rel, e := filepath.Rel(dir, p)
		if e != nil {
			return e
		}
		rel = filepath.ToSlash(rel)
		if d.Type()&os.ModeSymlink != 0 {
			return errors.New("snapshot symlink")
		}
		if d.IsDir() {
			return nil
		}
		if !safePath(rel) {
			return errors.New("snapshot path")
		}
		b, e := os.ReadFile(p)
		if e != nil {
			return e
		}
		m[rel] = digest(b)
		return nil
	})
	return m, e
}
func sameInventory(a, b map[string]string) bool {
	if len(a) != len(b) {
		return false
	}
	for k, v := range a {
		if b[k] != v {
			return false
		}
	}
	return true
}
func sortedKeys(m map[string]string) []string {
	keys := []string{}
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}
