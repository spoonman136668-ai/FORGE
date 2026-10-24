package plane

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"
)

const (
	openCodeManualPacketLimit             = openCodeAdvisorMaxContext + (32 << 10)
	openCodeAdvisorySupervisedOutputLimit = 16 << 20
)

type OpenCodeAdvisoryInvocation struct {
	Schema                    string `json:"schema"`
	RequestID                 string `json:"request_id"`
	InvocationID              string `json:"invocation_id"`
	SubjectID                 string `json:"subject_id,omitempty"`
	Attempt                   int    `json:"attempt,omitempty"`
	DataClassification        string `json:"data_classification"`
	InputEvidenceSHA256       string `json:"input_evidence_sha256,omitempty"`
	Model                     string `json:"model"`
	ToolSHA256                string `json:"tool_sha256"`
	PacketBindingSHA256       string `json:"packet_binding_sha256"`
	StdoutSHA256              string `json:"stdout_sha256"`
	StderrSHA256              string `json:"stderr_sha256"`
	ProviderErrorName         string `json:"provider_error_name,omitempty"`
	ProviderErrorCategory     string `json:"provider_error_category,omitempty"`
	ProviderErrorStatus       int    `json:"provider_error_status,omitempty"`
	ProviderErrorRetryable    *bool  `json:"provider_error_retryable,omitempty"`
	ResultBindingSHA256       string `json:"result_binding_sha256"`
	StdoutBytes               int    `json:"stdout_bytes"`
	StderrBytes               int    `json:"stderr_bytes"`
	ProcessOutputLimitBytes   int    `json:"process_output_limit_bytes"`
	EvidencePath              string `json:"evidence_path"`
	WorkspaceRemoved          bool   `json:"workspace_removed"`
	SourceWorkspaceSupplied   bool   `json:"source_workspace_supplied"`
	QueueAuthorityGranted     bool   `json:"queue_authority_granted"`
	AcceptanceAuthorityGranted bool  `json:"acceptance_authority_granted"`
	PromotionAuthorityGranted bool   `json:"promotion_authority_granted"`
	StartedAt                 string `json:"started_at"`
	FinishedAt                string `json:"finished_at"`
	Succeeded                 bool   `json:"succeeded"`
	Failure                   string `json:"failure,omitempty"`
}

type OpenCodeAdvisoryService struct {
	Root   string
	Config Config
	runner ProcessRunner
}

func NewOpenCodeAdvisoryService(root string, config Config) OpenCodeAdvisoryService {
	return OpenCodeAdvisoryService{Root: root, Config: config}
}

func ParseOpenCodeAdvisoryPacket(raw []byte) (OpenCodeAdvisoryPacket, error) {
	var packet OpenCodeAdvisoryPacket
	if len(raw) == 0 || len(raw) > openCodeManualPacketLimit {
		return packet, errors.New("OPENCODE_ADVISORY_PACKET_SIZE_INVALID")
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&packet); err != nil {
		return packet, errors.New("OPENCODE_ADVISORY_PACKET_JSON_INVALID")
	}
	var extra any
	if err := decoder.Decode(&extra); err != io.EOF {
		return packet, errors.New("OPENCODE_ADVISORY_PACKET_JSON_INVALID")
	}
	if err := packet.Validate(); err != nil {
		return packet, err
	}
	return packet, nil
}

func openCodeBytesSHA256(b []byte) string {
	sum := sha256.Sum256(b)
	return hex.EncodeToString(sum[:])
}

func openCodeFileSHA256(path string) (string, error) {
	f, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer f.Close()
	h := sha256.New()
	if _, err = io.Copy(h, f); err != nil {
		return "", err
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}

func validateOpenCodeActivationConfig(root string, config Config) (string, string, error) {
	cfg := config.Advisory.OpenCode
	if !cfg.Enabled {
		return "", "", errors.New("OPENCODE_ADVISORY_NOT_ENABLED")
	}
	if !cfg.ManualOnly {
		return "", "", errors.New("OPENCODE_ADVISORY_MANUAL_ONLY_REQUIRED")
	}
	if !strings.HasPrefix(cfg.Model, "openrouter/") || strings.TrimSpace(cfg.Model) != cfg.Model || strings.ContainsAny(cfg.Model, "\r\n\x00") {
		return "", "", errors.New("OPENCODE_ADVISORY_MODEL_INVALID")
	}
	if cfg.APIKeyEnv != "OPENROUTER_API_KEY" {
		return "", "", errors.New("OPENCODE_ADVISORY_KEY_ENV_INVALID")
	}
	if cfg.TimeoutSeconds < 1 || cfg.TimeoutSeconds > 300 {
		return "", "", errors.New("OPENCODE_ADVISORY_TIMEOUT_INVALID")
	}
	if len(cfg.ExecutableSHA256) != 64 || strings.Trim(cfg.ExecutableSHA256, "0123456789abcdef") != "" {
		return "", "", errors.New("OPENCODE_ADVISORY_EXECUTABLE_SHA_INVALID")
	}
	absRoot, err := filepath.Abs(root)
	if err != nil {
		return "", "", err
	}
	if err = validateOpenCodePrivatePath(absRoot, false); err != nil {
		return "", "", fmt.Errorf("OPENCODE_ADVISORY_ROOT_UNSAFE: %w", err)
	}
	tool := config.Tools.OpenCode
	if tool == "" || !filepath.IsAbs(tool) {
		return "", "", errors.New("OPENCODE_ADVISORY_TOOL_INVALID")
	}
	if err = validateOpenCodePrivatePath(filepath.Dir(tool), false); err != nil {
		return "", "", fmt.Errorf("OPENCODE_ADVISORY_TOOL_PATH_UNSAFE: %w", err)
	}
	unsafe, err := openCodePathReparseUnsafe(tool)
	if err != nil {
		return "", "", fmt.Errorf("OPENCODE_ADVISORY_TOOL_UNAVAILABLE: %w", err)
	}
	if unsafe {
		return "", "", errors.New("OPENCODE_ADVISORY_TOOL_REPARSE_UNSAFE")
	}
	info, err := os.Lstat(tool)
	if err != nil || !info.Mode().IsRegular() {
		return "", "", errors.New("OPENCODE_ADVISORY_TOOL_INVALID")
	}
	toolSHA, err := openCodeFileSHA256(tool)
	if err != nil {
		return "", "", err
	}
	if toolSHA != cfg.ExecutableSHA256 {
		return "", "", errors.New("OPENCODE_ADVISORY_TOOL_SHA_MISMATCH")
	}
	return absRoot, toolSHA, nil
}

func ensureOpenCodePrivateDir(root string, parts ...string) (string, error) {
	current := filepath.Clean(root)
	if err := validateOpenCodePrivatePath(current, false); err != nil {
		return "", err
	}
	for _, part := range parts {
		if !safeID.MatchString(part) {
			return "", errors.New("OPENCODE_ADVISORY_PRIVATE_PATH_INVALID")
		}
		current = filepath.Join(current, part)
		_, err := os.Lstat(current)
		if os.IsNotExist(err) {
			if err = os.Mkdir(current, 0700); err != nil {
				return "", err
			}
		} else if err != nil {
			return "", err
		}
		if err = validateOpenCodePrivatePath(current, false); err != nil {
			return "", err
		}
	}
	return current, nil
}

func sanitizeOpenCodeFailure(err error, credential string) string {
	if err == nil {
		return ""
	}
	message := err.Error()
	if credential != "" {
		message = strings.ReplaceAll(message, credential, "[REDACTED]")
	}
	if len(message) > 4096 {
		message = message[:4096]
	}
	return message
}

type openCodeProviderErrorEvent struct {
	Type  string `json:"type"`
	Error struct {
		Name string `json:"name"`
		Data struct {
			StatusCode  int   `json:"statusCode"`
			IsRetryable *bool `json:"isRetryable"`
		} `json:"data"`
	} `json:"error"`
}

func openCodeProviderErrorClassification(output []byte) (name, category string, status int, retryable *bool) {
	for _, line := range strings.Split(strings.ReplaceAll(string(output), "\r\n", "\n"), "\n") {
		if strings.TrimSpace(line) == "" {
			continue
		}
		var event openCodeProviderErrorEvent
		if err := json.Unmarshal([]byte(line), &event); err != nil || event.Type != "error" {
			continue
		}
		name = event.Error.Name
		status = event.Error.Data.StatusCode
		retryable = event.Error.Data.IsRetryable
		switch status {
		case 401, 403:
			category = "authentication_or_authorization"
		case 404:
			category = "provider_not_found"
		case 408:
			category = "provider_timeout"
		case 429:
			category = "rate_limited"
		default:
			if status >= 500 {
				category = "provider_server"
			} else {
				category = "provider_error"
			}
		}
		return name, category, status, retryable
	}
	return "", "", 0, nil
}

func (s OpenCodeAdvisoryService) Run(ctx context.Context, packet OpenCodeAdvisoryPacket, out, stderr io.Writer) (OpenCodeAdvisoryInvocation, error) {
	var invocation OpenCodeAdvisoryInvocation
	if out == nil || stderr == nil {
		return invocation, errors.New("OPENCODE_ADVISORY_OUTPUT_INVALID")
	}
	if err := packet.Validate(); err != nil {
		return invocation, err
	}
	root, toolSHA, err := validateOpenCodeActivationConfig(s.Root, s.Config)
	if err != nil {
		return invocation, err
	}
	claimsDir, err := ensureOpenCodePrivateDir(root, "state", "opencode-advisory", "claims")
	if err != nil {
		return invocation, err
	}
	workspaceBase, err := ensureOpenCodePrivateDir(root, "workspaces", "opencode-advisory")
	if err != nil {
		return invocation, err
	}
	invocationID := randomID()
	evidenceDir, err := ensureOpenCodePrivateDir(root, "evidence", "opencode-advisory", packet.RequestID, invocationID)
	if err != nil {
		return invocation, err
	}
	requestDir, err := os.MkdirTemp(workspaceBase, "request-")
	if err != nil {
		return invocation, err
	}
	if err = validateOpenCodePrivatePath(requestDir, true); err != nil {
		_ = os.RemoveAll(requestDir)
		return invocation, err
	}

	started := time.Now().UTC()
	cfg := s.Config.Advisory.OpenCode
	processOutputLimit := 0
	if s.runner == nil {
		processOutputLimit = openCodeAdvisorySupervisedOutputLimit
	}
	invocation = OpenCodeAdvisoryInvocation{
		Schema:                     "ckb-plane.opencode-advisory-invocation.v1",
		RequestID:                  packet.RequestID,
		InvocationID:               invocationID,
		SubjectID:                  packet.SubjectID,
		Attempt:                    packet.Attempt,
		DataClassification:         packet.DataClassification,
		InputEvidenceSHA256:        packet.EvidenceSHA256,
		Model:                      cfg.Model,
		ToolSHA256:                 toolSHA,
		PacketBindingSHA256:        openCodePacketBinding(packet, s.Config.Tools.OpenCode, cfg.Model),
		ProcessOutputLimitBytes:    processOutputLimit,
		EvidencePath:               evidenceDir,
		SourceWorkspaceSupplied:    false,
		QueueAuthorityGranted:      false,
		AcceptanceAuthorityGranted: false,
		PromotionAuthorityGranted:  false,
		StartedAt:                  started.Format(time.RFC3339Nano),
	}

	runCtx, cancel := context.WithTimeout(ctx, time.Duration(cfg.TimeoutSeconds)*time.Second)
	defer cancel()

	var stdoutBuffer, stderrBuffer bytes.Buffer
	runner := s.runner
	if runner == nil {
		runner = SupervisedRunner{}
	}
	advisor := OpenCodeAdvisor{
		Config: OpenCodeAdvisorConfig{
			Enabled:   true,
			Tool:      s.Config.Tools.OpenCode,
			Model:     cfg.Model,
			APIKeyEnv: cfg.APIKeyEnv,
		},
		Runner: runner,
		Replay: NewOpenCodeReplayFence(claimsDir),
	}
	runErr := advisor.Run(runCtx, requestDir, packet, &stdoutBuffer, &stderrBuffer)

	credential, _ := os.LookupEnv(cfg.APIKeyEnv)
	credentialLeak := credential != "" && (strings.Contains(stdoutBuffer.String(), credential) || strings.Contains(stderrBuffer.String(), credential))
	if credentialLeak {
		runErr = errors.New("OPENCODE_ADVISORY_CREDENTIAL_LEAK_DETECTED")
	}

	cleanupErr := os.RemoveAll(requestDir)
	if cleanupErr == nil {
		_, statErr := os.Lstat(requestDir)
		if !os.IsNotExist(statErr) {
			cleanupErr = errors.New("OPENCODE_ADVISORY_WORKSPACE_CLEANUP_FAILED")
		}
	}
	invocation.WorkspaceRemoved = cleanupErr == nil
	invocation.StdoutBytes = stdoutBuffer.Len()
	invocation.StderrBytes = stderrBuffer.Len()
	invocation.StdoutSHA256 = openCodeBytesSHA256(stdoutBuffer.Bytes())
	invocation.StderrSHA256 = openCodeBytesSHA256(stderrBuffer.Bytes())
	if runErr != nil {
		invocation.ProviderErrorName, invocation.ProviderErrorCategory, invocation.ProviderErrorStatus, invocation.ProviderErrorRetryable = openCodeProviderErrorClassification(stdoutBuffer.Bytes())
		if invocation.ProviderErrorName == "" {
			invocation.ProviderErrorName, invocation.ProviderErrorCategory, invocation.ProviderErrorStatus, invocation.ProviderErrorRetryable = openCodeProviderErrorClassification(stderrBuffer.Bytes())
		}
	}
	invocation.FinishedAt = time.Now().UTC().Format(time.RFC3339Nano)
	invocation.Succeeded = runErr == nil && cleanupErr == nil && !credentialLeak
	if runErr != nil {
		invocation.Failure = sanitizeOpenCodeFailure(runErr, credential)
	} else if cleanupErr != nil {
		invocation.Failure = sanitizeOpenCodeFailure(cleanupErr, credential)
	}
	resultMaterial := strings.Join([]string{
		invocation.PacketBindingSHA256,
		invocation.ToolSHA256,
		invocation.Model,
		invocation.StdoutSHA256,
		invocation.StderrSHA256,
		fmt.Sprintf("%t", invocation.Succeeded),
		invocation.Failure,
	}, "\x00")
	invocation.ResultBindingSHA256 = openCodeBytesSHA256([]byte(resultMaterial))

	evidenceJSON, marshalErr := json.MarshalIndent(invocation, "", "  ")
	if marshalErr != nil {
		return invocation, marshalErr
	}
	if err = durableNew(filepath.Join(evidenceDir, "result.json"), append(evidenceJSON, '\n')); err != nil {
		return invocation, err
	}

	if runErr != nil {
		return invocation, runErr
	}
	if !credentialLeak {
		if _, err = out.Write(stdoutBuffer.Bytes()); err != nil {
			return invocation, err
		}
		if _, err = stderr.Write(stderrBuffer.Bytes()); err != nil {
			return invocation, err
		}
	}
	if cleanupErr != nil {
		return invocation, cleanupErr
	}
	return invocation, nil
}
