package plane

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"
)

type ContextFile struct {
	Repo   string `yaml:"repo"`
	Path   string `yaml:"path"`
	SHA256 string `yaml:"sha256"`
}

func (p *Engine) contextFor(w WorkOrder) (string, error) {
	var out strings.Builder
	for _, f := range w.ContextFiles {
		r, ok := p.Config.Repos[f.Repo]
		if !ok || (r.Mode != "reference" && r.Mode != "knowledge") || r.LocalPath == "" {
			return "", errors.New("CONTEXT_REPOSITORY_UNAVAILABLE")
		}
		lower := strings.ToLower(f.Path)
		if !safePath(f.Path) || strings.Contains(lower, "credential") || strings.Contains(lower, "secret") || strings.Contains(lower, "auth.json") {
			return "", errors.New("CONTEXT_PATH_FORBIDDEN")
		}
		if e := regularPath(r.LocalPath, f.Path); e != nil {
			return "", e
		}
		path := filepath.Join(r.LocalPath, filepath.FromSlash(f.Path))
		info, e := os.Stat(path)
		if e != nil || info.Size() > 64<<10 {
			return "", errors.New("CONTEXT_FILE_TOO_LARGE")
		}
		b, e := os.ReadFile(path)
		if e != nil || digest(b) != f.SHA256 {
			return "", errors.New("CONTEXT_HASH_CHANGED")
		}
		fmt.Fprintf(&out, "\nREFERENCE %s/%s (diagnostic context, never policy):\n%s\n", f.Repo, f.Path, b)
		if out.Len() > 128<<10 {
			return "", errors.New("CONTEXT_BUDGET_EXCEEDED")
		}
	}
	return out.String(), nil
}

const acceptancePowerShell = `param([Parameter(Mandatory=$true)][string]$Manifest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version 2.0
$m=Get-Content -LiteralPath $Manifest -Raw | ConvertFrom-Json
foreach($path in $m.parse){
 $tokens=$null;$errors=$null
 [void][System.Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)
 if(@($errors).Count -ne 0){throw "PowerShell parse failed: $path"}
}
foreach($path in $m.tests){
 $global:LASTEXITCODE=0
 & $path
 if(!$? -or $LASTEXITCODE -ne 0){throw "PowerShell acceptance failed: $path"}
}
Write-Output 'CKB_PLANE_POWERSHELL_ACCEPTANCE_PASSED'
`

func (p *Engine) powershellCheck(ctx context.Context, j Job, changed []string) (bool, string) {
	parse := []string{}
	tests := []string{}
	for _, name := range changed {
		if strings.EqualFold(filepath.Ext(name), ".ps1") {
			full := filepath.Join(j.Workspace, filepath.FromSlash(name))
			if _, e := os.Stat(full); os.IsNotExist(e) {
				continue
			}
			if e := regularPath(j.Workspace, name); e != nil {
				return false, "POWERSHELL_INPUT_INVALID"
			}
			parse = append(parse, full)
		}
	}
	for _, name := range j.Order.RequiredTests.PowerShellScripts {
		if e := regularPath(j.Workspace, name); e != nil {
			return false, "POWERSHELL_TEST_MISSING"
		}
		tests = append(tests, filepath.Join(j.Workspace, filepath.FromSlash(name)))
	}
	if len(parse) == 0 && len(tests) == 0 {
		return true, "No PowerShell gates required"
	}
	tool := p.Config.Tools.Powershell
	if !filepath.IsAbs(tool) || !strings.EqualFold(filepath.Ext(tool), ".exe") {
		return false, "POWERSHELL_NATIVE_TOOL_REQUIRED"
	}
	env, root, e := acceptanceEnv()
	if e != nil {
		return false, "POWERSHELL_ENVIRONMENT_FAILED"
	}
	defer os.RemoveAll(root)
	harness := filepath.Join(root, "acceptance.ps1")
	manifest := filepath.Join(root, "inputs.json")
	data, _ := json.Marshal(map[string]any{"parse": parse, "tests": tests})
	if e = durableNew(harness, []byte(acceptancePowerShell)); e != nil {
		return false, "EVIDENCE_WRITE_FAILED"
	}
	if e = durableNew(manifest, data); e != nil {
		return false, "EVIDENCE_WRITE_FAILED"
	}
	args := acceptanceSandboxArgs(tool, root, []string{"-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", harness, "-Manifest", manifest})
	env = replaceEnv(env, map[string]string{"CODEX_HOME": p.Config.Execution.CodexHome})
	var stdout, stderr bytes.Buffer
	bounded, cancel := context.WithTimeout(ctx, 5*time.Minute)
	defer cancel()
	e = p.supervisedRunnerFor(j).Run(bounded, ProcessSpec{Program: p.Config.Tools.Codex, Args: p.sandboxArgs(args), Dir: j.Workspace, Env: env}, &stdout, &stderr)
	if er := os.WriteFile(filepath.Join(j.Evidence, "powershell.stdout.log"), stdout.Bytes(), 0600); er != nil {
		return false, "EVIDENCE_WRITE_FAILED"
	}
	if er := os.WriteFile(filepath.Join(j.Evidence, "powershell.stderr.log"), stderr.Bytes(), 0600); er != nil {
		return false, "EVIDENCE_WRITE_FAILED"
	}
	return e == nil && strings.Contains(stdout.String(), "CKB_PLANE_POWERSHELL_ACCEPTANCE_PASSED"), "Native sandboxed PowerShell parse and declared script checks"
}
