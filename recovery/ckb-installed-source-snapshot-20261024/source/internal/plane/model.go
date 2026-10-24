package plane

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"path"
	"regexp"
	"strings"

	"github.com/bmatcuk/doublestar/v4"
	"gopkg.in/yaml.v3"
)

type Repo struct {
	Remote    string `yaml:"remote"`
	LocalPath string `yaml:"local_path"`
	Mode      string `yaml:"mode"`
}
type OpenCodeShadowConfig struct {
	Enabled                bool   `yaml:"enabled"`
	AllowWorkOrderMetadata bool   `yaml:"allow_work_order_metadata"`
	SidecarExecutable      string `yaml:"sidecar_executable"`
	SidecarConfig          string `yaml:"sidecar_config"`
	SidecarSHA256          string `yaml:"sidecar_sha256"`
	SidecarConfigSHA256    string `yaml:"sidecar_config_sha256"`
	OpenCodeSHA256         string `yaml:"opencode_sha256"`
	Model                  string `yaml:"model"`
	TimeoutSeconds         int    `yaml:"timeout_seconds"`
	MaxConcurrent          int    `yaml:"max_concurrent"`
}

type OpenCodeAdvisoryConfig struct {
	Enabled          bool                 `yaml:"enabled"`
	ManualOnly       bool                 `yaml:"manual_only"`
	Model            string               `yaml:"model"`
	APIKeyEnv        string               `yaml:"api_key_env"`
	ExecutableSHA256 string               `yaml:"executable_sha256"`
	TimeoutSeconds   int                  `yaml:"timeout_seconds"`
	Shadow           OpenCodeShadowConfig `yaml:"shadow"`
}

type Config struct {
	Autonomy AutonomyConfig `yaml:"autonomy"`
	Server   struct {
		Bind string `yaml:"bind"`
		Port int    `yaml:"port"`
	} `yaml:"server"`
	State struct {
		SQLitePath string `yaml:"sqlite_path"`
	} `yaml:"state"`
	Profile struct {
		Name string `yaml:"name"`
	} `yaml:"profile"`
	WinglessStage1 WinglessStage1Config `yaml:"wingless_stage1"`
	Advisory       struct {
		OpenCode OpenCodeAdvisoryConfig `yaml:"opencode"`
	} `yaml:"advisory"`
	Repos     map[string]Repo `yaml:"repos"`
	Execution struct {
		SandboxSyntax         string `yaml:"sandbox_syntax"`
		Enabled               bool   `yaml:"enabled"`
		CodexHome             string `yaml:"codex_home"`
		TimeoutSeconds        int    `yaml:"timeout_seconds"`
		LocalOperationsConfig string `yaml:"local_operations_config"`
		LocalOperationsSHA256 string `yaml:"local_operations_sha256"`
	} `yaml:"execution"`
	Tools struct {
		Git        string `yaml:"git"`
		Go         string `yaml:"go"`
		Powershell string `yaml:"powershell"`
		Codex      string `yaml:"codex"`
		OpenCode   string `yaml:"opencode"`

		Node           string `yaml:"node"`
		PlaywrightRoot string `yaml:"playwright_root"`
	} `yaml:"tools"`
	Policy struct {
		AcceptedRefMutation        bool                       `yaml:"accepted_ref_mutation"`
		RuntimeLaunchAllowed       bool                       `yaml:"runtime_launch_allowed"`
		ArbitraryShell             bool                       `yaml:"arbitrary_shell_from_webui"`
		MaxAttempts                int                        `yaml:"max_attempts_per_work_order"`
		RetryOverride              RetryBudgetOverride        `yaml:"retry_override"`
		TemporaryNoIdleRetryWindow TemporaryNoIdleRetryWindow `yaml:"temporary_no_idle_retry_window"`
	} `yaml:"policy"`
}
type WorkOrder struct {
	ID           string        `yaml:"id"`
	Title        string        `yaml:"title"`
	ContextFiles []ContextFile `yaml:"context_files"`
	Instructions []string      `yaml:"instructions" json:"instructions,omitempty"`
	Repo         string        `yaml:"repo"`
	Baseline     struct {
		Ref string `yaml:"ref"`
		SHA string `yaml:"sha"`
	} `yaml:"baseline"`
	Worker struct {
		Branch    string `yaml:"branch"`
		Preferred string `yaml:"preferred"`
	} `yaml:"worker"`
	Scope struct {
		Allowed   []string `yaml:"allowed_paths"`
		Forbidden []string `yaml:"forbidden_paths"`
	} `yaml:"scope"`
	RequiredPaths []string `yaml:"required_paths"`
	Preserve      []string `yaml:"preserve"`
	RequiredTests struct {
		PowerShellScripts []string `yaml:"powershell_scripts"`
		FocusedGo         []string `yaml:"focused_go"`
		Packages          []string `yaml:"go_packages"`
	} `yaml:"required_tests"`
	Acceptance struct {
		All         bool `yaml:"run_go_test_all"`
		Browser     bool `yaml:"run_playwright"`
		ProtectRefs bool `yaml:"protect_accepted_refs"`
		Clean       bool `yaml:"require_clean_baseline"`
	} `yaml:"acceptance"`
	Forbidden []string   `yaml:"forbidden"`
	UI        UIContract `yaml:"ui"`
}

func decodeYAML(b []byte, v any) error {
	d := yaml.NewDecoder(bytes.NewReader(b))
	d.KnownFields(true)
	if err := d.Decode(v); err != nil {
		return err
	}
	var extra any
	if err := d.Decode(&extra); err != io.EOF {
		return errors.New("exactly one YAML document required")
	}
	return nil
}
func ParseOrder(b []byte) (WorkOrder, error) {
	var w WorkOrder
	err := decodeYAML(b, &w)
	if err == nil {
		err = w.Validate()
	}
	return w, err
}

var safeID = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9_-]{0,119}$`)
var shaRE = regexp.MustCompile(`^[0-9a-f]{40}$`)

func safePath(s string) bool {
	return s != "" && !strings.ContainsAny(s, "\\:\x00\r\n") && !strings.HasPrefix(s, "/") && path.Clean(s) == s && s != ".." && !strings.HasPrefix(s, "../")
}
func (w WorkOrder) Validate() error {
	if !safeID.MatchString(w.ID) || !safeID.MatchString(w.Repo) || w.Title == "" {
		return errors.New("CONFIG_INVALID: id, repo and title required")
	}
	if !shaRE.MatchString(w.Baseline.SHA) || !baselineRefAllowed(w.Baseline.Ref) || !safePath(w.Baseline.Ref) {
		return errors.New("CONFIG_INVALID: exact accepted ref and 40-character SHA required")
	}
	if !strings.HasPrefix(w.Worker.Branch, "codex/") || !safePath(w.Worker.Branch) || strings.Contains(w.Worker.Branch, "..") || strings.ContainsAny(w.Worker.Branch, " ~^?*[@{") {
		return errors.New("CONFIG_INVALID: invalid worker branch")
	}
	if w.Worker.Preferred != "fake" && w.Worker.Preferred != "codex" && w.Worker.Preferred != winglessStage1RegisteredWorkerName {
		return errors.New("CONFIG_INVALID: unknown worker")
	}
	if len(w.Scope.Allowed) == 0 || !w.Acceptance.ProtectRefs || !w.Acceptance.Clean {
		return errors.New("CONFIG_INVALID: bounded scope and protection gates required")
	}
	for _, p := range append(append([]string{}, w.Scope.Allowed...), w.Scope.Forbidden...) {
		if !safePath(p) || !doublestar.ValidatePattern(p) {
			return fmt.Errorf("CONFIG_INVALID: invalid pattern %q", p)
		}
	}
	for _, f := range w.ContextFiles {
		if !safeID.MatchString(f.Repo) || !safePath(f.Path) || len(f.SHA256) != 64 || strings.Trim(f.SHA256, "0123456789abcdef") != "" {
			return errors.New("CONTEXT_CONTRACT_INVALID")
		}
	}
	for _, path := range w.RequiredTests.PowerShellScripts {
		if !safePath(path) || !strings.HasSuffix(strings.ToLower(path), ".ps1") {
			return errors.New("POWERSHELL_TEST_CONTRACT_INVALID")
		}
	}
	for _, s := range w.RequiredTests.FocusedGo {
		if _, err := regexp.Compile(s); err != nil || !strings.HasPrefix(s, "^Test") || !strings.HasSuffix(s, "$") {
			return errors.New("CONFIG_INVALID: focused tests must be anchored Test expressions")
		}
	}
	for _, pkg := range w.RequiredTests.Packages {
		if pkg != "./..." && !regexp.MustCompile(`^\./[A-Za-z0-9_/-]+$`).MatchString(pkg) {
			return errors.New("CONFIG_INVALID: invalid Go package")
		}
		if pkg != "./..." && strings.Contains(pkg, "..") {
			return errors.New("CONFIG_INVALID: invalid Go package")
		}
	}
	for _, name := range w.RequiredPaths {
		if !safePath(name) || !w.Allows(name) {
			return errors.New("REQUIRED_PATH_INVALID")
		}
	}
	if w.UI.Root != "" && !safePath(w.UI.Root) {
		return errors.New("CONFIG_INVALID: invalid UI root")
	}
	for _, page := range w.UI.Pages {
		if !safePath(page.Path) || len(page.CriticalIDs) == 0 {
			return errors.New("CONFIG_INVALID: UI page path and critical IDs required")
		}
		for _, id := range append(append([]string{}, page.CriticalIDs...), page.ChartID) {
			if id != "" && !regexp.MustCompile(`^[A-Za-z][A-Za-z0-9_:-]*$`).MatchString(id) {
				return errors.New("CONFIG_INVALID: invalid element ID")
			}
		}
	}
	return nil
}

var hardForbidden = []string{".git/**", ".github/**", "**/.git/**", "**/*credential*", "**/*secret*", "**/*coinbase*", "pkg/risk.go", "pkg/accounting.go", "pkg/reconciliation*", "pkg/broker*", "**/*.exe", "**/*.dll"}

func (w WorkOrder) Allows(p string) bool {
	if !safePath(p) {
		return false
	}
	p = strings.ToLower(p)
	for _, pat := range append(append([]string{}, hardForbidden...), w.Scope.Forbidden...) {
		if ok, _ := doublestar.Match(strings.ToLower(pat), p); ok {
			return false
		}
	}
	for _, pat := range w.Scope.Allowed {
		if ok, _ := doublestar.Match(strings.ToLower(pat), p); ok {
			return true
		}
	}
	return false
}
func transition(from, to string) bool {
	allowed := map[string][]string{"DRAFT": {"AUTHORIZED"}, "AUTHORIZED": {"READY", "BLOCKED"}, "READY": {"DISPATCHED", "BLOCKED"}, "DISPATCHED": {"ENGINEERING", "BLOCKED"}, "ENGINEERING": {"CANDIDATE", "REJECTED_RETRYABLE", "BLOCKED"}, "CANDIDATE": {"ACCEPTING", "BLOCKED"}, "ACCEPTING": {"ACCEPTED", "REJECTED_RETRYABLE", "BLOCKED"}, "REJECTED_RETRYABLE": {"READY", "BLOCKED"}}
	for _, s := range allowed[from] {
		if s == to {
			return true
		}
	}
	return false
}
func failureClass(code string) string {
	if i := strings.Index(code, ":"); i >= 0 {
		return strings.TrimSpace(code[:i])
	}
	return code
}

func retryable(code string) bool {
	switch failureClass(code) {
	case "WORKER_EXIT_NONZERO", "WORKER_TIMEOUT", "WORKER_CANCELLED", "NO_DIFF_PRODUCED", "FOCUSED_TEST_FAILED", "GO_TEST_FAILED", "GO_TEST_ASSERTION_FAILED", "GO_TEST_TIMEOUT", "GO_TEST_INFRASTRUCTURE_FAILED", "GO_CACHE_ACCESS_FAILED", "PLAYWRIGHT_FAILED", "POWERSHELL_ACCEPTANCE_FAILED":
		return true
	}
	return false
}
func jsonText(v any) string { b, _ := json.Marshal(v); return string(b) }

type Job struct {
	ID        string    `json:"id"`
	Order     WorkOrder `json:"order"`
	State     string    `json:"state"`
	Attempt   int       `json:"attempt"`
	Reason    string    `json:"reason"`
	Workspace string    `json:"workspace"`
	Evidence  string    `json:"evidence"`
	Checks    []Check   `json:"checks"`
}
type Check struct {
	Name   string `json:"name"`
	Pass   bool   `json:"pass"`
	Detail string `json:"detail"`
}

type UIContract struct {
	Root    string              `yaml:"root"`
	Pages   []UIPage            `yaml:"pages"`
	Markers map[string][]string `yaml:"markers"`
}
type UIPage struct {
	Path        string   `yaml:"path"`
	CriticalIDs []string `yaml:"critical_ids"`
	ChartID     string   `yaml:"chart_id"`
}
