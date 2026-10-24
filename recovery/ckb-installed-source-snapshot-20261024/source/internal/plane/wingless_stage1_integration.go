package plane

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"strings"
	"unicode/utf8"
)

const (
	winglessStage1MaxCandidateJSONBytes = 262144
	WinglessStage1PostimageVerified     = "postimage_verified"
)

// WinglessStage1ExternalPlan is immutable plane-owned application data derived
// from one strictly validated sealed Stage-1 write_text candidate. It carries
// no test, retry, acceptance, promotion, queue, transport, or live authority.
type WinglessStage1ExternalPlan struct {
	SourceCommit         string `json:"source_commit"`
	WorkOrderID          string `json:"work_order_id"`
	RequestID            string `json:"request_id"`
	Attempt              int    `json:"attempt"`
	Workspace            string `json:"workspace"`
	BaselineSHA          string `json:"baseline_sha"`
	WorkOrderDigest      string `json:"work_order_digest"`
	Path                 string `json:"path"`
	ExpectedBeforeSHA256 string `json:"expected_before_sha256"`
	ExpectedAfterSHA256  string `json:"expected_after_sha256"`
	Content              string `json:"content"`
	ApplicationAuthority string `json:"application_authority"`
	AcceptanceAuthority  string `json:"acceptance_authority"`
	TrustCeiling         string `json:"trust_ceiling"`
}

// WinglessStage1PostimageEvidence proves only that plane-observed bytes match
// the bound application plan. Acceptance deliberately remains external_required.
type WinglessStage1PostimageEvidence struct {
	WorkOrderID          string `json:"work_order_id"`
	RequestID            string `json:"request_id"`
	Workspace            string `json:"workspace"`
	Path                 string `json:"path"`
	ExpectedBeforeSHA256 string `json:"expected_before_sha256"`
	ExpectedAfterSHA256  string `json:"expected_after_sha256"`
	ObservedAfterSHA256  string `json:"observed_after_sha256"`
	Status               string `json:"status"`
	Acceptance           string `json:"acceptance"`
	TrustCeiling         string `json:"trust_ceiling"`
}

func winglessStage1SHA256(b []byte) string {
	h := sha256.Sum256(b)
	return hex.EncodeToString(h[:])
}

func winglessStage1RequestID(b WinglessStage1Binding) string {
	return fmt.Sprintf("%s-wingless-%d", b.WorkOrderID, b.Attempt)
}

func validateWinglessStage1BindingContract(b WinglessStage1Binding) error {
	if b.SourceCommit != WinglessStage1FrozenSource || b.WorkOrderID == "" || b.Attempt < 1 || b.Workspace == "" || b.BaselineSHA == "" || b.WorkOrderDigest == "" || b.ProductionPath == "" || b.BeforeSHA256 == "" {
		return errors.New("WINGLESS_STAGE1_BINDING_INVALID")
	}
	if b.TaskClass != WinglessStage1TaskClass || b.CandidateFormat != WinglessStage1CandidateFormat || !b.ExactPreimage || b.TestsMutable || b.ApplicationAuthority != WinglessStage1ApplicationAuthority || b.AcceptanceAuthority != WinglessStage1AcceptanceAuthority || b.ModelRepairRetries != 0 {
		return errors.New("WINGLESS_STAGE1_BINDING_INVALID")
	}
	if b.PreferredModel != WinglessStage1PreferredModel || b.SecondaryModel != WinglessStage1SecondaryModel || b.TrustCeiling != WinglessStage1TrustCeiling {
		return errors.New("WINGLESS_STAGE1_BINDING_INVALID")
	}
	if b.ChangesArchitecture || b.ChangesAuthority || b.LiveAction || b.ArbitraryShell || b.ModelEditAuthority || b.ModelTestAuthority {
		return errors.New("WINGLESS_STAGE1_AUTHORITY_WIDENING")
	}
	if !winglessStage1ConcreteRepoPath(b.ProductionPath) || winglessStage1TestPath(b.ProductionPath) {
		return errors.New("WINGLESS_STAGE1_PRODUCTION_PATH_INVALID")
	}
	if len(b.BeforeSHA256) != 64 || strings.Trim(b.BeforeSHA256, "0123456789abcdef") != "" {
		return errors.New("WINGLESS_STAGE1_PREIMAGE_INVALID")
	}
	return nil
}

// DecodeWinglessStage1WriteText mirrors the sealed Stage-1 validator boundary:
// bounded non-NUL UTF-8 JSON, unknown fields rejected, and exactly one object.
// It performs no filesystem mutation.
func DecodeWinglessStage1WriteText(raw []byte) (WinglessStage1WriteText, error) {
	var op WinglessStage1WriteText
	if len(raw) == 0 || len(raw) > winglessStage1MaxCandidateJSONBytes {
		return op, errors.New("WINGLESS_STAGE1_CANDIDATE_JSON_LIMIT")
	}
	if !utf8.Valid(raw) || bytes.IndexByte(raw, 0) >= 0 {
		return op, errors.New("WINGLESS_STAGE1_CANDIDATE_JSON_INVALID")
	}
	d := json.NewDecoder(bytes.NewReader(raw))
	d.DisallowUnknownFields()
	if err := d.Decode(&op); err != nil {
		return op, fmt.Errorf("WINGLESS_STAGE1_CANDIDATE_JSON_INVALID: %w", err)
	}
	var extra any
	if err := d.Decode(&extra); err != io.EOF {
		return op, errors.New("WINGLESS_STAGE1_CANDIDATE_TRAILING_VALUE")
	}
	return op, nil
}

// PrepareWinglessStage1ExternalPlan turns raw candidate JSON into immutable
// plane-owned application data after rechecking the exact workspace preimage.
func PrepareWinglessStage1ExternalPlan(binding WinglessStage1Binding, raw []byte) (WinglessStage1ExternalPlan, error) {
	var out WinglessStage1ExternalPlan
	if err := validateWinglessStage1BindingContract(binding); err != nil {
		return out, err
	}
	op, err := DecodeWinglessStage1WriteText(raw)
	if err != nil {
		return out, err
	}
	edit, err := BuildWinglessStage1PlaneEdit(binding, op)
	if err != nil {
		return out, err
	}
	out = WinglessStage1ExternalPlan{
		SourceCommit:         binding.SourceCommit,
		WorkOrderID:          binding.WorkOrderID,
		RequestID:            winglessStage1RequestID(binding),
		Attempt:              binding.Attempt,
		Workspace:            binding.Workspace,
		BaselineSHA:          binding.BaselineSHA,
		WorkOrderDigest:      binding.WorkOrderDigest,
		Path:                 edit.Path,
		ExpectedBeforeSHA256: edit.ExpectedBeforeSHA256,
		ExpectedAfterSHA256:  edit.AfterSHA256,
		Content:              edit.Content,
		ApplicationAuthority: WinglessStage1ApplicationAuthority,
		AcceptanceAuthority:  WinglessStage1AcceptanceAuthority,
		TrustCeiling:         WinglessStage1TrustCeiling,
	}
	return out, nil
}

func validateWinglessStage1ExternalPlan(binding WinglessStage1Binding, plan WinglessStage1ExternalPlan) error {
	if err := validateWinglessStage1BindingContract(binding); err != nil {
		return err
	}
	if plan.SourceCommit != binding.SourceCommit || plan.WorkOrderID != binding.WorkOrderID || plan.RequestID != winglessStage1RequestID(binding) || plan.Attempt != binding.Attempt || plan.Workspace != binding.Workspace || plan.BaselineSHA != binding.BaselineSHA || plan.WorkOrderDigest != binding.WorkOrderDigest {
		return errors.New("WINGLESS_STAGE1_PLAN_IDENTITY_MISMATCH")
	}
	if plan.Path != binding.ProductionPath || plan.ExpectedBeforeSHA256 != binding.BeforeSHA256 {
		return errors.New("WINGLESS_STAGE1_PLAN_PREIMAGE_MISMATCH")
	}
	if plan.Content == "" || len(plan.Content) > winglessStage1MaxCandidateJSONBytes || !utf8.ValidString(plan.Content) || strings.ContainsRune(plan.Content, '\x00') {
		return errors.New("WINGLESS_STAGE1_PLAN_CONTENT_INVALID")
	}
	if plan.ExpectedAfterSHA256 != winglessStage1SHA256([]byte(plan.Content)) || plan.ExpectedAfterSHA256 == plan.ExpectedBeforeSHA256 {
		return errors.New("WINGLESS_STAGE1_PLAN_POSTIMAGE_MISMATCH")
	}
	if plan.ApplicationAuthority != WinglessStage1ApplicationAuthority || plan.AcceptanceAuthority != WinglessStage1AcceptanceAuthority || plan.TrustCeiling != WinglessStage1TrustCeiling {
		return errors.New("WINGLESS_STAGE1_PLAN_AUTHORITY_MISMATCH")
	}
	return nil
}

// ApplyWinglessStage1ExternalPlan is the single narrow plane-owned write used by
// the isolated R2 proof. It requires an existing regular production file, exact
// current preimage, exact plan identity, and byte-for-byte post-write verification.
// It performs no test execution, retry, acceptance, promotion, queue mutation,
// backend invocation, process launch, or live action.
func ApplyWinglessStage1ExternalPlan(binding WinglessStage1Binding, plan WinglessStage1ExternalPlan) error {
	if err := validateWinglessStage1ExternalPlan(binding, plan); err != nil {
		return err
	}
	target, err := winglessStage1BoundTarget(binding.Workspace, binding.ProductionPath)
	if err != nil {
		return err
	}
	info, err := os.Lstat(target)
	if err != nil || !info.Mode().IsRegular() {
		return errors.New("WINGLESS_STAGE1_APPLY_TARGET_INVALID")
	}
	before, err := os.ReadFile(target)
	if err != nil {
		return fmt.Errorf("WINGLESS_STAGE1_APPLY_READ_FAILED: %w", err)
	}
	if winglessStage1SHA256(before) != plan.ExpectedBeforeSHA256 {
		return errors.New("WINGLESS_STAGE1_CURRENT_PREIMAGE_MISMATCH")
	}

	rollback := func(cause error) error {
		if rb := os.WriteFile(target, before, info.Mode().Perm()); rb != nil {
			return fmt.Errorf("%v; WINGLESS_STAGE1_ROLLBACK_FAILED: %w", cause, rb)
		}
		return cause
	}
	if err := os.WriteFile(target, []byte(plan.Content), info.Mode().Perm()); err != nil {
		return rollback(fmt.Errorf("WINGLESS_STAGE1_APPLY_WRITE_FAILED: %w", err))
	}
	after, err := os.ReadFile(target)
	if err != nil {
		return rollback(fmt.Errorf("WINGLESS_STAGE1_APPLY_VERIFY_READ_FAILED: %w", err))
	}
	if winglessStage1SHA256(after) != plan.ExpectedAfterSHA256 || string(after) != plan.Content {
		return rollback(errors.New("WINGLESS_STAGE1_APPLY_POSTIMAGE_MISMATCH"))
	}
	return nil
}

// VerifyWinglessStage1ExternalApplication proves only the observed postimage.
// The status mirrors the sealed Wingless contract and acceptance remains external_required.
func VerifyWinglessStage1ExternalApplication(binding WinglessStage1Binding, plan WinglessStage1ExternalPlan, observed []byte) (WinglessStage1PostimageEvidence, error) {
	var out WinglessStage1PostimageEvidence
	if err := validateWinglessStage1ExternalPlan(binding, plan); err != nil {
		return out, err
	}
	if !utf8.Valid(observed) || bytes.IndexByte(observed, 0) >= 0 {
		return out, errors.New("WINGLESS_STAGE1_OBSERVED_POSTIMAGE_INVALID")
	}
	observedSHA := winglessStage1SHA256(observed)
	if observedSHA != plan.ExpectedAfterSHA256 || string(observed) != plan.Content {
		return out, errors.New("WINGLESS_STAGE1_OBSERVED_POSTIMAGE_MISMATCH")
	}
	out = WinglessStage1PostimageEvidence{
		WorkOrderID:          plan.WorkOrderID,
		RequestID:            plan.RequestID,
		Workspace:            plan.Workspace,
		Path:                 plan.Path,
		ExpectedBeforeSHA256: plan.ExpectedBeforeSHA256,
		ExpectedAfterSHA256:  plan.ExpectedAfterSHA256,
		ObservedAfterSHA256:  observedSHA,
		Status:               WinglessStage1PostimageVerified,
		Acceptance:           WinglessStage1AcceptanceAuthority,
		TrustCeiling:         WinglessStage1TrustCeiling,
	}
	return out, nil
}
