package plane

import (
	"context"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"errors"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

func (p *Engine) contract(w WorkOrder) string {
	tools := map[string]string{}
	for name, file := range map[string]string{"git": p.Config.Tools.Git, "go": p.Config.Tools.Go, "codex": p.Config.Tools.Codex, "node": p.Config.Tools.Node, "powershell": p.Config.Tools.Powershell} {
		if file == "" {
			continue
		}
		resolved, e := exec.LookPath(file)
		if e != nil {
			tools[name] = "UNAVAILABLE"
			continue
		}
		f, e := os.Open(resolved)
		if e != nil {
			tools[name] = "UNREADABLE"
			continue
		}
		h := sha256.New()
		_, e = io.Copy(h, f)
		f.Close()
		if e != nil {
			tools[name] = "UNREADABLE"
		} else {
			tools[name] = resolved + ":" + hex.EncodeToString(h.Sum(nil))
		}
	}
	return digest([]byte(jsonText(struct {
		Order  WorkOrder
		Config Config
		Tools  map[string]string
	}{w, p.Config, tools})))
}
func (p *Engine) Authorize(id string) error {
	j, e := p.Store.Get(id)
	if e != nil {
		return e
	}
	tx, e := p.Store.DB.Begin()
	if e != nil {
		return e
	}
	defer tx.Rollback()
	r, e := tx.Exec("UPDATE work_orders SET state='AUTHORIZED',reason=CASE WHEN reason IN (?,?,?) THEN reason ELSE 'Explicit local authorization bound to order and configuration' END WHERE id=? AND state='DRAFT'", preWorkerRetryAuthorizedReason, workerCancelRetryAuthorizedReason, workerAuthRetryAuthorizedReason, id)
	if e != nil {
		return e
	}
	n, _ := r.RowsAffected()
	if n != 1 {
		return errors.New("authorization requires DRAFT")
	}
	if _, e = tx.Exec("INSERT INTO authorizations(work_order_id,created,operator) VALUES(?,?,'local-operator')", id, now()); e != nil {
		return e
	}
	if _, e = tx.Exec("INSERT INTO authorization_contracts VALUES(?,?,?)", id, p.contract(j.Order), now()); e != nil {
		return e
	}
	if e = event(tx, id, j.Attempt, "AUTHORIZED", "Immutable work-order/configuration contract recorded"); e != nil {
		return e
	}
	return tx.Commit()
}
func (p *Engine) verifyContract(w WorkOrder) error {
	var hash string
	e := p.Store.DB.QueryRow("SELECT digest FROM authorization_contracts WHERE work_order_id=?", w.ID).Scan(&hash)
	if errors.Is(e, sql.ErrNoRows) && p.Config.Repos[w.Repo].Mode == "demo" && w.Worker.Preferred == "fake" {
		return nil
	}
	if e != nil || hash != p.contract(w) {
		return errors.New("AUTHORIZATION_CONTRACT_CHANGED")
	}
	return nil
}
func (p *Engine) realPreflight(w WorkOrder) error {
	if e := p.verifyContract(w); e != nil {
		return e
	}
	return p.realEnvironmentPreflight(w)
}

// Qualification exercises tools on a synthetic fixture without authorizing a source job.
func (p *Engine) realEnvironmentPreflight(w WorkOrder) error {
	if !p.Config.Autonomy.Enabled {
		if _, e := os.Stat(filepath.Join(p.Root, "state", "autonomy-managed.json")); e == nil {
			return errors.New("LEGACY_EXECUTION_DISABLED_USE_AUTONOMY_CONTROLLER")
		}
	}
	if _, e := p.contextFor(w); e != nil {
		return e
	}
	if p.Config.Repos[w.Repo].Mode != "engineering" {
		return errors.New("CONFIG_INVALID: Codex requires engineering registry mode")
	}
	if !p.Config.Execution.Enabled {
		return errors.New("EXECUTION_NOT_CONFIGURED: execution.enabled is false")
	}
	if runtime.GOOS != "windows" || runtime.GOARCH != "amd64" {
		return errors.New("WINDOWS_AUTHORITY_REQUIRED")
	}
	home := p.Config.Execution.CodexHome
	if !filepath.IsAbs(home) {
		return errors.New("CONFIG_INVALID: absolute dedicated codex_home required")
	}
	for _, r := range p.Config.Repos {
		if r.LocalPath != "" && (pathWithin(home, r.LocalPath) || pathWithin(r.LocalPath, home)) {
			return errors.New("CONFIG_INVALID: authentication profile overlaps a repository")
		}
	}
	for _, name := range []string{"workspaces", "acceptance", "evidence"} {
		if pathWithin(home, filepath.Join(p.Root, name)) {
			return errors.New("CONFIG_INVALID: authentication profile overlaps execution data")
		}
	}
	info, e := os.Stat(home)
	if e != nil || !info.IsDir() {
		return errors.New("CODEX_PROFILE_UNAVAILABLE")
	}
	if _, e := scrubCodexProfile(home, defaultCodexProfileDenylist()); e != nil {
		return errors.New("CODEX_PROFILE_NOT_ISOLATED: unexpected customization")
	}
	// Do not load authentication material. Reject ambient customization, hooks,
	// plugins and MCP configuration in this dedicated execution profile.
	for _, name := range []string{"config.toml", "config.json", "skills", "plugins", "rules", "AGENTS.md"} {
		if _, e := os.Lstat(filepath.Join(home, name)); !os.IsNotExist(e) {
			return errors.New("CODEX_PROFILE_NOT_ISOLATED: unexpected customization")
		}
	}
	for _, tool := range []string{p.Config.Tools.Codex, p.Config.Tools.Go, p.Config.Tools.Git} {
		if !filepath.IsAbs(tool) || !strings.EqualFold(filepath.Ext(tool), ".exe") {
			return errors.New("CONFIG_INVALID: real execution requires absolute native executable paths")
		}
		if i, e := os.Stat(tool); e != nil || !i.Mode().IsRegular() {
			return errors.New("TOOL_UNAVAILABLE")
		}
	}
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, p.Config.Tools.Go, "version")
	cmd.Env = minimalEnv()
	out, e := cmd.Output()
	if e != nil || strings.TrimSpace(string(out)) != "go version go1.25.5 windows/amd64" {
		return errors.New("WINDOWS_TOOLCHAIN_MISMATCH")
	}
	r := p.Config.Repos[w.Repo]
	for _, name := range []string{".codex", ".agents"} {
		if _, e := os.Lstat(filepath.Join(r.LocalPath, name)); !os.IsNotExist(e) {
			return errors.New("PROJECT_EXECUTION_CONFIG_PRESENT")
		}
	}
	return nil
}

func pathWithin(child, parent string) bool {
	c := strings.ToLower(filepath.Clean(child))
	p := strings.ToLower(filepath.Clean(parent))
	return c == p || strings.HasPrefix(c, p+string(filepath.Separator))
}

func (p *Engine) guardLegacyExecution() error {
	if p.Config.Autonomy.Enabled {
		return errors.New("LEGACY_EXECUTION_DISABLED_USE_AUTONOMY_CONTROLLER")
	}
	if _, e := os.Lstat(filepath.Join(p.Root, "state", "autonomy-managed.json")); !os.IsNotExist(e) {
		return errors.New("LEGACY_EXECUTION_DISABLED_USE_AUTONOMY_CONTROLLER")
	}
	return nil
}
