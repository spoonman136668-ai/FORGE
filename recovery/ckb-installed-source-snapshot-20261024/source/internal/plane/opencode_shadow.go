package plane

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

const (
	openCodeShadowSchema        = "ckb-plane.opencode-shadow-result.v1"
	openCodeShadowContextLimit  = 64 << 10
	openCodeShadowTimeoutMaxSec = 120
	openCodeShadowMaxConcurrent = 4
)

type openCodeShadowResult struct {
	Schema                     string `json:"schema"`
	RequestID                  string `json:"request_id"`
	WorkOrderID                string `json:"work_order_id"`
	Attempt                    int    `json:"attempt"`
	Status                     string `json:"status"`
	Reason                     string `json:"reason,omitempty"`
	Model                      string `json:"model,omitempty"`
	SidecarSHA256              string `json:"sidecar_sha256,omitempty"`
	SidecarConfigSHA256        string `json:"sidecar_config_sha256,omitempty"`
	OpenCodeSHA256             string `json:"opencode_sha256,omitempty"`
	PacketSHA256               string `json:"packet_sha256,omitempty"`
	StdoutSHA256               string `json:"stdout_sha256,omitempty"`
	StderrSHA256               string `json:"stderr_sha256,omitempty"`
	ResultBindingSHA256        string `json:"result_binding_sha256,omitempty"`
	ProviderErrorName          string `json:"provider_error_name,omitempty"`
	ProviderErrorCategory      string `json:"provider_error_category,omitempty"`
	ProviderErrorStatus        int    `json:"provider_error_status,omitempty"`
	ProviderErrorRetryable     *bool  `json:"provider_error_retryable,omitempty"`
	MetadataSent               bool   `json:"metadata_sent"`
	RawProviderOutputPersisted bool   `json:"raw_provider_output_persisted"`
	SourceWorkspaceSupplied    bool   `json:"source_workspace_supplied"`
	QueueAuthorityGranted      bool   `json:"queue_authority_granted"`
	AcceptanceAuthorityGranted bool  `json:"acceptance_authority_granted"`
	PromotionAuthorityGranted  bool   `json:"promotion_authority_granted"`
	AdvisoryRequiredForWork    bool   `json:"advisory_required_for_work"`
	StartedAt                  string `json:"started_at"`
	FinishedAt                 string `json:"finished_at"`
}

type openCodeShadowCLIResult struct {
	Invocation OpenCodeAdvisoryInvocation `json:"invocation"`
	Stdout     string                     `json:"stdout"`
	Stderr     string                     `json:"stderr"`
	Error      string                     `json:"error,omitempty"`
}

func openCodeShadowCapacity(max int) int {
	if max < 1 || max > openCodeShadowMaxConcurrent {
		return 1
	}
	return max
}

func openCodeShadowRequestID(id string, attempt int, model string) string {
	binding := openCodeBytesSHA256([]byte(id + "\n" + strconv.Itoa(attempt) + "\n" + model))
	return "shadow_" + binding[:32]
}

func openCodeShadowResultPath(root, id string, attempt int, requestID string) string {
	return filepath.Join(root, "evidence", "opencode-shadow", id, strconv.Itoa(attempt), requestID+".json")
}

func (p *Engine) launchOpenCodeShadow(parent context.Context, id string, attempt int, order WorkOrder) {
	cfg := p.Config.Advisory.OpenCode.Shadow
	if !cfg.Enabled {
		return
	}
	if p.shadowSlots == nil {
		p.shadowSlots = make(chan struct{}, openCodeShadowCapacity(cfg.MaxConcurrent))
	}
	requestID := openCodeShadowRequestID(id, attempt, cfg.Model)
	started := time.Now().UTC()

	select {
	case p.shadowSlots <- struct{}{}:
		p.shadowWG.Add(1)
		go func() {
			defer p.shadowWG.Done()
			defer func() { <-p.shadowSlots }()
			defer func() {
				if recover() != nil {
					_ = p.writeOpenCodeShadowResult(openCodeShadowResult{
						Schema:                     openCodeShadowSchema,
						RequestID:                  requestID,
						WorkOrderID:                id,
						Attempt:                    attempt,
						Status:                     "failed",
						Reason:                     "SHADOW_PANIC",
						Model:                      cfg.Model,
						RawProviderOutputPersisted: false,
						AdvisoryRequiredForWork:    false,
						StartedAt:                  started.Format(time.RFC3339Nano),
						FinishedAt:                 time.Now().UTC().Format(time.RFC3339Nano),
					})
				}
			}()
			p.runOpenCodeShadow(parent, id, attempt, order, requestID, started)
		}()
	default:
		p.shadowWG.Add(1)
		go func() {
			defer p.shadowWG.Done()
			_ = p.writeOpenCodeShadowResult(openCodeShadowResult{
				Schema:                     openCodeShadowSchema,
				RequestID:                  requestID,
				WorkOrderID:                id,
				Attempt:                    attempt,
				Status:                     "skipped",
				Reason:                     "CAPACITY_BUSY",
				Model:                      cfg.Model,
				RawProviderOutputPersisted: false,
				AdvisoryRequiredForWork:    false,
				StartedAt:                  started.Format(time.RFC3339Nano),
				FinishedAt:                 time.Now().UTC().Format(time.RFC3339Nano),
			})
		}()
	}
}

func (p *Engine) runOpenCodeShadow(parent context.Context, id string, attempt int, order WorkOrder, requestID string, started time.Time) {
	cfg := p.Config.Advisory.OpenCode.Shadow
	result := openCodeShadowResult{
		Schema:                     openCodeShadowSchema,
		RequestID:                  requestID,
		WorkOrderID:                id,
		Attempt:                    attempt,
		Status:                     "failed",
		Model:                      cfg.Model,
		SidecarSHA256:              cfg.SidecarSHA256,
		SidecarConfigSHA256:        cfg.SidecarConfigSHA256,
		OpenCodeSHA256:             cfg.OpenCodeSHA256,
		RawProviderOutputPersisted: false,
		AdvisoryRequiredForWork:    false,
		StartedAt:                  started.Format(time.RFC3339Nano),
	}
	finish := func(status, reason string) {
		result.Status = status
		result.Reason = reason
		result.FinishedAt = time.Now().UTC().Format(time.RFC3339Nano)
		_ = p.writeOpenCodeShadowResult(result)
	}

	if !cfg.AllowWorkOrderMetadata {
		finish("skipped", "DATA_POLICY_NOT_APPROVED")
		return
	}
	if err := validateOpenCodeShadowConfig(cfg); err != nil {
		finish("failed", err.Error())
		return
	}

	key := os.Getenv("OPENROUTER_API_KEY")
	if strings.TrimSpace(key) == "" {
		finish("failed", "OPENROUTER_KEY_UNAVAILABLE")
		return
	}

	contextRaw, err := openCodeShadowMetadata(order)
	if err != nil {
		finish("failed", err.Error())
		return
	}
	packet := OpenCodeAdvisoryPacket{
		Schema:             openCodeAdvisorPacketSchema,
		RequestID:          requestID,
		Attempt:            attempt,
		Purpose:            "Provide a non-authoritative risk and verification review of bounded work-order metadata. Do not call tools or propose authority changes.",
		DataClassification: "operator_approved",
		Context:            string(contextRaw),
	}
	packetRaw, err := json.Marshal(packet)
	if err != nil {
		finish("failed", "SHADOW_PACKET_ENCODE_FAILED")
		return
	}
	result.PacketSHA256 = openCodeBytesSHA256(packetRaw)
	result.MetadataSent = true

	packetPath, cleanup, err := p.writeOpenCodeShadowPacket(requestID, packetRaw)
	if err != nil {
		finish("failed", "SHADOW_PACKET_WRITE_FAILED")
		return
	}
	defer cleanup()

	ctx, cancel := context.WithTimeout(parent, time.Duration(cfg.TimeoutSeconds)*time.Second)
	defer cancel()

	env := append(minimalEnv(), "OPENROUTER_API_KEY="+key)
	spec := ProcessSpec{
		Program: cfg.SidecarExecutable,
		Args:    []string{"advisory", "run", "--config", cfg.SidecarConfig, "--file", packetPath, "--json"},
		Dir:     filepath.Dir(cfg.SidecarExecutable),
		Env:     env,
	}
	var stdout, stderr bytes.Buffer
	runErr := p.shadowRunner.Run(ctx, spec, &stdout, &stderr)
	key = ""

	var payload openCodeShadowCLIResult
	parsed := json.Unmarshal(stdout.Bytes(), &payload) == nil
	if parsed {
		inv := payload.Invocation
		result.StdoutSHA256 = inv.StdoutSHA256
		result.StderrSHA256 = inv.StderrSHA256
		result.ResultBindingSHA256 = inv.ResultBindingSHA256
		result.ProviderErrorName = inv.ProviderErrorName
		result.ProviderErrorCategory = inv.ProviderErrorCategory
		result.ProviderErrorStatus = inv.ProviderErrorStatus
		result.ProviderErrorRetryable = inv.ProviderErrorRetryable
		result.SourceWorkspaceSupplied = inv.SourceWorkspaceSupplied
		result.QueueAuthorityGranted = inv.QueueAuthorityGranted
		result.AcceptanceAuthorityGranted = inv.AcceptanceAuthorityGranted
		result.PromotionAuthorityGranted = inv.PromotionAuthorityGranted
	}

	if errors.Is(ctx.Err(), context.DeadlineExceeded) {
		finish("failed", "SHADOW_TIMEOUT")
		return
	}
	if errors.Is(ctx.Err(), context.Canceled) {
		finish("cancelled", "AUTHORITATIVE_ATTEMPT_FINISHED_OR_CANCELLED")
		return
	}
	if runErr != nil {
		if parsed && result.ProviderErrorCategory != "" {
			finish("failed", "PROVIDER_"+strings.ToUpper(result.ProviderErrorCategory))
		} else {
			finish("failed", "SHADOW_SIDECAR_RUN_FAILED")
		}
		return
	}
	if !parsed {
		finish("failed", "SHADOW_SIDECAR_OUTPUT_INVALID")
		return
	}
	if !payload.Invocation.Succeeded {
		finish("failed", "SHADOW_INVOCATION_NOT_SUCCESSFUL")
		return
	}
	if payload.Invocation.Model != cfg.Model || payload.Invocation.ToolSHA256 != cfg.OpenCodeSHA256 {
		finish("failed", "SHADOW_BINDING_MISMATCH")
		return
	}
	if payload.Invocation.SourceWorkspaceSupplied || payload.Invocation.QueueAuthorityGranted || payload.Invocation.AcceptanceAuthorityGranted || payload.Invocation.PromotionAuthorityGranted {
		finish("failed", "SHADOW_AUTHORITY_BOUNDARY_VIOLATED")
		return
	}
	finish("succeeded", "")
}

func validateOpenCodeShadowConfig(cfg OpenCodeShadowConfig) error {
	if !cfg.Enabled {
		return errors.New("SHADOW_DISABLED")
	}
	if cfg.TimeoutSeconds < 1 || cfg.TimeoutSeconds > openCodeShadowTimeoutMaxSec {
		return errors.New("SHADOW_TIMEOUT_INVALID")
	}
	if cfg.MaxConcurrent < 1 || cfg.MaxConcurrent > openCodeShadowMaxConcurrent {
		return errors.New("SHADOW_CONCURRENCY_INVALID")
	}
	if !strings.HasPrefix(cfg.Model, "openrouter/") || strings.TrimSpace(cfg.Model) != cfg.Model {
		return errors.New("SHADOW_MODEL_INVALID")
	}
	for _, value := range []string{cfg.SidecarSHA256, cfg.SidecarConfigSHA256, cfg.OpenCodeSHA256} {
		if len(value) != 64 || strings.Trim(value, "0123456789abcdef") != "" {
			return errors.New("SHADOW_SHA_INVALID")
		}
	}
	if !filepath.IsAbs(cfg.SidecarExecutable) || !filepath.IsAbs(cfg.SidecarConfig) {
		return errors.New("SHADOW_PATH_INVALID")
	}
	for _, path := range []string{cfg.SidecarExecutable, cfg.SidecarConfig} {
		unsafe, err := openCodePathReparseUnsafe(path)
		if err != nil || unsafe {
			return errors.New("SHADOW_PATH_UNSAFE")
		}
		info, err := os.Lstat(path)
		if err != nil || !info.Mode().IsRegular() {
			return errors.New("SHADOW_PATH_INVALID")
		}
	}
	exeSHA, err := openCodeFileSHA256(cfg.SidecarExecutable)
	if err != nil || exeSHA != cfg.SidecarSHA256 {
		return errors.New("SHADOW_SIDECAR_SHA_MISMATCH")
	}
	configSHA, err := openCodeFileSHA256(cfg.SidecarConfig)
	if err != nil || configSHA != cfg.SidecarConfigSHA256 {
		return errors.New("SHADOW_CONFIG_SHA_MISMATCH")
	}
	sidecarConfig, err := LoadConfig(cfg.SidecarConfig)
	if err != nil {
		return errors.New("SHADOW_CONFIG_INVALID")
	}
	sidecarRoot := filepath.Clean(filepath.Join(filepath.Dir(cfg.SidecarConfig), ".."))
	_, toolSHA, err := validateOpenCodeActivationConfig(sidecarRoot, sidecarConfig)
	if err != nil {
		return errors.New("SHADOW_CONFIG_INVALID")
	}
	if !sidecarConfig.Advisory.OpenCode.ManualOnly || sidecarConfig.Advisory.OpenCode.Model != cfg.Model || toolSHA != cfg.OpenCodeSHA256 {
		return errors.New("SHADOW_BINDING_MISMATCH")
	}
	return nil
}

func openCodeShadowMetadata(order WorkOrder) ([]byte, error) {
	view := map[string]any{
		"title":             order.Title,
		"instructions":      append([]string(nil), order.Instructions...),
		"allowed_paths":     append([]string(nil), order.Scope.Allowed...),
		"forbidden_paths":   append([]string(nil), order.Scope.Forbidden...),
		"required_paths":    append([]string(nil), order.RequiredPaths...),
		"preserve":          append([]string(nil), order.Preserve...),
		"forbidden":         append([]string(nil), order.Forbidden...),
		"powershell_tests":  append([]string(nil), order.RequiredTests.PowerShellScripts...),
		"focused_go_tests":  append([]string(nil), order.RequiredTests.FocusedGo...),
		"go_packages":       append([]string(nil), order.RequiredTests.Packages...),
	}
	raw, err := json.Marshal(view)
	if err != nil {
		return nil, errors.New("SHADOW_METADATA_ENCODE_FAILED")
	}
	if len(raw) == 0 || len(raw) > openCodeShadowContextLimit {
		return nil, errors.New("SHADOW_METADATA_SIZE_INVALID")
	}
	return raw, nil
}

func (p *Engine) writeOpenCodeShadowPacket(requestID string, raw []byte) (string, func(), error) {
	if !safeID.MatchString(requestID) {
		return "", func() {}, errors.New("SHADOW_REQUEST_ID_INVALID")
	}
	root := filepath.Join(p.Root, "workspaces", "opencode-shadow")
	if err := os.MkdirAll(root, 0700); err != nil {
		return "", func() {}, err
	}
	path := filepath.Join(root, requestID+".json")
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {
		return "", func() {}, err
	}
	_, writeErr := file.Write(raw)
	closeErr := file.Close()
	if writeErr != nil {
		_ = os.Remove(path)
		return "", func() {}, writeErr
	}
	if closeErr != nil {
		_ = os.Remove(path)
		return "", func() {}, closeErr
	}
	return path, func() { _ = os.Remove(path) }, nil
}

func (p *Engine) writeOpenCodeShadowResult(result openCodeShadowResult) error {
	if !safeID.MatchString(result.WorkOrderID) || !safeID.MatchString(result.RequestID) || result.Attempt < 0 || result.Attempt > 1000 {
		return errors.New("SHADOW_RESULT_ID_INVALID")
	}
	path := openCodeShadowResultPath(p.Root, result.WorkOrderID, result.Attempt, result.RequestID)
	if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
		return err
	}
	raw, err := json.MarshalIndent(result, "", "  ")
	if err != nil {
		return err
	}
	raw = append(raw, '\n')
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {
		return err
	}
	defer file.Close()
	if _, err = file.Write(raw); err != nil {
		return err
	}
	return file.Sync()
}
