package plane

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"os"
	"path"
	"path/filepath"
	"strings"
	"unicode/utf8"
)

const (
	WinglessStage1FrozenSource = "8152e8c57826007c1e84aa396107afd40ba28ef4"

	WinglessStage1TaskClass            = "bounded_single_file_repair"
	WinglessStage1CandidateFormat      = "write_text_json_schema"
	WinglessStage1ApplicationAuthority = "external"
	WinglessStage1AcceptanceAuthority  = "external_required"
	WinglessStage1PreferredModel       = "qwen3-coder-30ba3b-q3km"
	WinglessStage1SecondaryModel       = "devstral-small-2-24b-iq3m"
	WinglessStage1TrustCeiling         = "stage_1_only"
)

// WinglessStage1Binding is an inactive, plane-owned projection of the sealed
// Wingless Stage-1 eligibility boundary. Constructing it does not register a
// worker, invoke a backend, apply an edit, run a test, retry work, accept a
// candidate, mutate a queue, or mutate accepted refs.
type WinglessStage1Binding struct {
	SourceCommit         string `json:"source_commit"`
	WorkOrderID          string `json:"work_order_id"`
	Attempt              int    `json:"attempt"`
	Workspace            string `json:"workspace"`
	BaselineSHA          string `json:"baseline_sha"`
	WorkOrderDigest      string `json:"work_order_digest"`
	ProductionPath       string `json:"production_path"`
	BeforeSHA256         string `json:"before_sha256"`
	TaskClass            string `json:"task_class"`
	CandidateFormat      string `json:"candidate_format"`
	ExactPreimage        bool   `json:"exact_preimage"`
	TestsMutable         bool   `json:"tests_mutable"`
	ApplicationAuthority string `json:"application_authority"`
	AcceptanceAuthority  string `json:"acceptance_authority"`
	ModelRepairRetries   int    `json:"model_repair_retries"`
	PreferredModel       string `json:"preferred_model"`
	SecondaryModel       string `json:"secondary_model"`
	TrustCeiling         string `json:"trust_ceiling"`
	ChangesArchitecture  bool   `json:"changes_architecture"`
	ChangesAuthority     bool   `json:"changes_authority"`
	LiveAction           bool   `json:"live_action"`
	ArbitraryShell       bool   `json:"arbitrary_shell"`
	ModelEditAuthority   bool   `json:"model_edit_authority"`
	ModelTestAuthority   bool   `json:"model_test_authority"`
}

// NewWinglessStage1Binding performs only deterministic plane-side validation
// and current-file hashing in the already materialized plane-owned workspace.
// The caller must obtain sourceCommit from trusted external Git inspection.
func NewWinglessStage1Binding(sourceCommit string, order WorkOrder, attempt int, workspace string) (WinglessStage1Binding, error) {
	var out WinglessStage1Binding

	if sourceCommit != WinglessStage1FrozenSource {
		return out, errors.New("WINGLESS_STAGE1_SOURCE_IDENTITY_MISMATCH")
	}
	if err := order.Validate(); err != nil {
		return out, err
	}
	if attempt < 1 {
		return out, errors.New("WINGLESS_STAGE1_ATTEMPT_INVALID")
	}
	if !filepath.IsAbs(workspace) || filepath.Clean(workspace) != workspace || strings.ContainsAny(workspace, "\x00\r\n") {
		return out, errors.New("WINGLESS_STAGE1_WORKSPACE_INVALID")
	}
	if len(order.Scope.Allowed) != 1 {
		return out, errors.New("WINGLESS_STAGE1_REQUIRES_ONE_PRODUCTION_PATH")
	}

	productionPath := order.Scope.Allowed[0]
	if !winglessStage1ConcreteRepoPath(productionPath) {
		return out, errors.New("WINGLESS_STAGE1_PRODUCTION_PATH_INVALID")
	}
	if winglessStage1TestPath(productionPath) {
		return out, errors.New("WINGLESS_STAGE1_TEST_PATH_PROHIBITED")
	}
	if !order.Allows(productionPath) {
		return out, errors.New("WINGLESS_STAGE1_PRODUCTION_PATH_NOT_ALLOWED")
	}

	target, err := winglessStage1BoundTarget(workspace, productionPath)
	if err != nil {
		return out, err
	}
	info, err := os.Lstat(target)
	if err != nil {
		return out, fmt.Errorf("WINGLESS_STAGE1_PREIMAGE_UNAVAILABLE: %w", err)
	}
	if !info.Mode().IsRegular() {
		return out, errors.New("WINGLESS_STAGE1_PREIMAGE_NOT_REGULAR")
	}
	bytes, err := os.ReadFile(target)
	if err != nil {
		return out, fmt.Errorf("WINGLESS_STAGE1_PREIMAGE_UNREADABLE: %w", err)
	}
	h := sha256.Sum256(bytes)
	before := hex.EncodeToString(h[:])

	out = WinglessStage1Binding{
		SourceCommit:         sourceCommit,
		WorkOrderID:          order.ID,
		Attempt:              attempt,
		Workspace:            workspace,
		BaselineSHA:          order.Baseline.SHA,
		WorkOrderDigest:      digest([]byte(jsonText(order))),
		ProductionPath:       productionPath,
		BeforeSHA256:         before,
		TaskClass:            WinglessStage1TaskClass,
		CandidateFormat:      WinglessStage1CandidateFormat,
		ExactPreimage:        true,
		TestsMutable:         false,
		ApplicationAuthority: WinglessStage1ApplicationAuthority,
		AcceptanceAuthority:  WinglessStage1AcceptanceAuthority,
		ModelRepairRetries:   0,
		PreferredModel:       WinglessStage1PreferredModel,
		SecondaryModel:       WinglessStage1SecondaryModel,
		TrustCeiling:         WinglessStage1TrustCeiling,
		ChangesArchitecture:  false,
		ChangesAuthority:     false,
		LiveAction:           false,
		ArbitraryShell:       false,
		ModelEditAuthority:   false,
		ModelTestAuthority:   false,
	}
	return out, nil
}

// ValidateWinglessStage1WriteText narrows candidate translation to the sealed
// Stage-1 operation: exactly one write_text against the exact bound path and
// exact current-file preimage. It performs no filesystem mutation.
type WinglessStage1WriteText struct {
	Type                 string `json:"type"`
	Path                 string `json:"path"`
	ExpectedBeforeSHA256 string `json:"expected_before_sha256"`
	Content              string `json:"content"`
}

func ValidateWinglessStage1WriteText(binding WinglessStage1Binding, candidate WinglessStage1WriteText) error {
	if binding.SourceCommit != WinglessStage1FrozenSource || binding.ApplicationAuthority != WinglessStage1ApplicationAuthority || binding.AcceptanceAuthority != WinglessStage1AcceptanceAuthority {
		return errors.New("WINGLESS_STAGE1_BINDING_INVALID")
	}
	if binding.ModelRepairRetries != 0 || binding.TestsMutable || binding.ModelEditAuthority || binding.ModelTestAuthority || binding.LiveAction || binding.ArbitraryShell || binding.ChangesArchitecture || binding.ChangesAuthority {
		return errors.New("WINGLESS_STAGE1_AUTHORITY_WIDENING")
	}
	if candidate.Type != "write_text" {
		return errors.New("WINGLESS_STAGE1_OPERATION_NOT_ALLOWED")
	}
	if candidate.Path != binding.ProductionPath {
		return errors.New("WINGLESS_STAGE1_CANDIDATE_PATH_MISMATCH")
	}
	if candidate.ExpectedBeforeSHA256 != binding.BeforeSHA256 {
		return errors.New("WINGLESS_STAGE1_CANDIDATE_PREIMAGE_MISMATCH")
	}
	if candidate.Content == "" || len(candidate.Content) > 262144 || !utf8.ValidString(candidate.Content) || strings.ContainsRune(candidate.Content, '\x00') {
		return errors.New("WINGLESS_STAGE1_CANDIDATE_CONTENT_INVALID")
	}
	return nil
}

// WinglessStage1PlaneEdit is a non-executing plane-owned application plan.
// It is deliberately incapable of representing delete, create, multiple-file,
// shell, test, retry, acceptance, promotion, or live operations.
type WinglessStage1PlaneEdit struct {
	Type                 string `json:"type"`
	Path                 string `json:"path"`
	ExpectedBeforeSHA256 string `json:"expected_before_sha256"`
	AfterSHA256          string `json:"after_sha256"`
	Content              string `json:"content"`
}

// BuildWinglessStage1PlaneEdit rechecks the current workspace preimage before
// producing a single non-executing write_text plan. It never writes the file.
func BuildWinglessStage1PlaneEdit(binding WinglessStage1Binding, candidate WinglessStage1WriteText) (WinglessStage1PlaneEdit, error) {
	var plan WinglessStage1PlaneEdit
	if err := ValidateWinglessStage1WriteText(binding, candidate); err != nil {
		return plan, err
	}
	target, err := winglessStage1BoundTarget(binding.Workspace, binding.ProductionPath)
	if err != nil {
		return plan, err
	}
	current, err := os.ReadFile(target)
	if err != nil {
		return plan, fmt.Errorf("WINGLESS_STAGE1_PREIMAGE_UNREADABLE: %w", err)
	}
	before := sha256.Sum256(current)
	if hex.EncodeToString(before[:]) != binding.BeforeSHA256 {
		return plan, errors.New("WINGLESS_STAGE1_CURRENT_PREIMAGE_MISMATCH")
	}
	if candidate.Content == string(current) {
		return plan, errors.New("WINGLESS_STAGE1_NOOP_CANDIDATE")
	}
	after := sha256.Sum256([]byte(candidate.Content))
	plan = WinglessStage1PlaneEdit{
		Type:                 "write_text",
		Path:                 binding.ProductionPath,
		ExpectedBeforeSHA256: binding.BeforeSHA256,
		AfterSHA256:          hex.EncodeToString(after[:]),
		Content:              candidate.Content,
	}
	return plan, nil
}

func winglessStage1ConcreteRepoPath(p string) bool {
	if !safePath(p) || strings.ContainsAny(p, "*?[]{}!") {
		return false
	}
	clean := path.Clean(p)
	return clean == p && clean != "." && clean != ".." && !strings.HasPrefix(clean, "../")
}

func winglessStage1TestPath(p string) bool {
	lower := strings.ToLower(path.Clean(p))
	base := path.Base(lower)
	if strings.HasSuffix(base, "_test.go") || strings.Contains(base, ".test.") || strings.Contains(base, ".spec.") {
		return true
	}
	for _, segment := range strings.Split(lower, "/") {
		switch segment {
		case "test", "tests", "__tests__":
			return true
		}
	}
	return false
}

func winglessStage1BoundTarget(workspace, productionPath string) (string, error) {
	rootInfo, err := os.Lstat(workspace)
	if err != nil || !rootInfo.IsDir() {
		return "", errors.New("WINGLESS_STAGE1_WORKSPACE_UNAVAILABLE")
	}
	if rp, err := winglessStage1IsReparse(workspace); err != nil || rp {
		return "", errors.New("WINGLESS_STAGE1_WORKSPACE_REPARSE_PROHIBITED")
	}

	target := filepath.Join(workspace, filepath.FromSlash(productionPath))
	rel, err := filepath.Rel(workspace, target)
	if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) || filepath.IsAbs(rel) {
		return "", errors.New("WINGLESS_STAGE1_PATH_ESCAPE")
	}

	current := workspace
	for _, part := range strings.Split(filepath.FromSlash(productionPath), string(filepath.Separator)) {
		current = filepath.Join(current, part)
		if rp, err := winglessStage1IsReparse(current); err != nil {
			return "", fmt.Errorf("WINGLESS_STAGE1_PATH_UNAVAILABLE: %w", err)
		} else if rp {
			return "", errors.New("WINGLESS_STAGE1_REPARSE_PROHIBITED")
		}
	}
	return target, nil
}
