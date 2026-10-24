package plane

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"runtime"
	"strconv"
	"strings"
	"time"
)

const (
	localOperationsSchema       = "ckb-plane.local-operations.v1"
	localExecutionResultSchema  = "ckb-plane.local-execution-result.v1"
	localOperationsConfigPath   = "config/local-operations.json"
	localOperationScriptPrefix  = "operations/"
	localOperationMaxScriptSize = 256 << 10
	localOperationCaptureLimit  = 8 << 10
)

var localArgumentName = regexp.MustCompile(`^[A-Za-z][A-Za-z0-9_]{0,39}$`)
var localUnsafeValue = regexp.MustCompile("[\\x00\\r\\n;&|<>`$(){}\\[\\]\"':\\\\/]")

type LocalOperationRegistry struct {
	Schema     string           `json:"schema"`
	Operations []LocalOperation `json:"operations"`
	byID       map[string]LocalOperation
}

type LocalOperation struct {
	ID             string                   `json:"id"`
	Class          string                   `json:"class"`
	Script         string                   `json:"script"`
	ScriptSHA256   string                   `json:"script_sha256"`
	WorkingRoot    string                   `json:"working_root"`
	WorkingDir     string                   `json:"working_dir"`
	TimeoutSeconds int                      `json:"timeout_seconds"`
	Arguments      []LocalOperationArgument `json:"arguments"`
}

type LocalOperationArgument struct {
	Name      string   `json:"name"`
	Type      string   `json:"type"`
	Required  bool     `json:"required,omitempty"`
	Pattern   string   `json:"pattern,omitempty"`
	Enum      []string `json:"enum,omitempty"`
	Min       *int64   `json:"min,omitempty"`
	Max       *int64   `json:"max,omitempty"`
	MaxLength int      `json:"max_length,omitempty"`
}

type LocalExecutionRequest struct {
	RequestID    string
	OperationID  string
	ScriptSHA256 string
	Parameters   map[string]json.RawMessage
}

type LocalExecutionResult struct {
	Schema                 string    `json:"schema"`
	RequestID              string    `json:"request_id"`
	OperationID            string    `json:"operation_id"`
	Status                 string    `json:"status"`
	ScriptSHA256           string    `json:"script_sha256"`
	ExitCode               int       `json:"exit_code"`
	StartedAt              time.Time `json:"started_at"`
	FinishedAt             time.Time `json:"finished_at"`
	Stdout                 string    `json:"stdout,omitempty"`
	Stderr                 string    `json:"stderr,omitempty"`
	OutputTruncated        bool      `json:"output_truncated"`
	EvidenceManifestSHA256 string    `json:"evidence_manifest_sha256,omitempty"`
}

type localCapture struct {
	buf       bytes.Buffer
	limit     int
	truncated bool
}

func (w *localCapture) Write(b []byte) (int, error) {
	original := len(b)
	if w.limit <= 0 {
		w.truncated = w.truncated || original > 0
		return original, nil
	}
	if len(b) > w.limit {
		b = b[:w.limit]
		w.truncated = true
	}
	_, _ = w.buf.Write(b)
	w.limit -= len(b)
	if original > len(b) {
		w.truncated = true
	}
	return original, nil
}

func LoadLocalOperationRegistry(root string, c Config, file string) (*LocalOperationRegistry, error) {
	if file == "" {
		return nil, nil
	}
	if filepath.ToSlash(file) != localOperationsConfigPath {
		return nil, errors.New("LOCAL_EXEC_CONFIG_PATH_INVALID")
	}
	registryPath, err := localContainedRegular(root, file, 1<<20)
	if err != nil {
		return nil, err
	}
	raw, err := os.ReadFile(registryPath)
	if err != nil {
		return nil, err
	}
	if len(c.Execution.LocalOperationsSHA256) != 64 || strings.Trim(c.Execution.LocalOperationsSHA256, "0123456789abcdef") != "" || digest(raw) != c.Execution.LocalOperationsSHA256 {
		return nil, errors.New("LOCAL_EXEC_REGISTRY_HASH_MISMATCH")
	}
	var registry LocalOperationRegistry
	if err = bridgeDecode(raw, &registry); err != nil {
		return nil, fmt.Errorf("LOCAL_EXEC_CONFIG_INVALID: %w", err)
	}
	if registry.Schema != localOperationsSchema || len(registry.Operations) == 0 || len(registry.Operations) > 64 {
		return nil, errors.New("LOCAL_EXEC_CONFIG_INVALID")
	}
	registry.byID = make(map[string]LocalOperation, len(registry.Operations))
	for _, op := range registry.Operations {
		if err = validateLocalOperation(root, c, op); err != nil {
			return nil, fmt.Errorf("LOCAL_EXEC_OPERATION_INVALID %s: %w", op.ID, err)
		}
		if _, exists := registry.byID[op.ID]; exists {
			return nil, errors.New("LOCAL_EXEC_OPERATION_DUPLICATE")
		}
		registry.byID[op.ID] = op
	}
	return &registry, nil
}

func validateLocalOperation(root string, c Config, op LocalOperation) error {
	if !safeID.MatchString(op.ID) {
		return errors.New("id")
	}
	if op.Class != "diagnostic" && op.Class != "acceptance" {
		return errors.New("class")
	}
	if !safePath(op.Script) || !strings.HasPrefix(filepath.ToSlash(op.Script), localOperationScriptPrefix) || !strings.HasSuffix(strings.ToLower(op.Script), ".ps1") {
		return errors.New("script")
	}
	if len(op.ScriptSHA256) != 64 || strings.Trim(op.ScriptSHA256, "0123456789abcdef") != "" {
		return errors.New("script hash")
	}
	if op.WorkingRoot != "plane" {
		if !strings.HasPrefix(op.WorkingRoot, "repo:") {
			return errors.New("working root")
		}
		repoID := strings.TrimPrefix(op.WorkingRoot, "repo:")
		if !safeID.MatchString(repoID) {
			return errors.New("working root")
		}
		repo, ok := c.Repos[repoID]
		if !ok || repo.LocalPath == "" {
			return errors.New("working repo unavailable")
		}
	}
	if op.WorkingDir == "" {
		op.WorkingDir = "."
	}
	if op.WorkingDir != "." && !safePath(filepath.ToSlash(op.WorkingDir)) {
		return errors.New("working dir")
	}
	if op.TimeoutSeconds < 1 || op.TimeoutSeconds > 300 {
		return errors.New("timeout")
	}
	if len(op.Arguments) > 16 {
		return errors.New("too many arguments")
	}
	seen := map[string]bool{}
	for _, a := range op.Arguments {
		if !localArgumentName.MatchString(a.Name) || seen[a.Name] {
			return errors.New("argument name")
		}
		lower := strings.ToLower(a.Name)
		for _, forbidden := range []string{"token", "secret", "credential", "password", "privatekey", "apikey"} {
			if strings.Contains(lower, forbidden) {
				return errors.New("secret-like argument prohibited")
			}
		}
		for _, forbidden := range []string{"command", "cmd", "script", "scriptpath", "path", "executable", "program", "shell", "powershell", "workingdir", "workdir", "environment", "env", "arguments", "args"} {
			if lower == forbidden {
				return errors.New("capability-shaping argument prohibited")
			}
		}
		seen[a.Name] = true
		switch a.Type {
		case "bool":
			if a.Pattern != "" || len(a.Enum) != 0 || a.Min != nil || a.Max != nil || a.MaxLength != 0 {
				return errors.New("bool argument constraints")
			}
		case "int":
			if a.Pattern != "" || len(a.Enum) != 0 || a.Min == nil || a.Max == nil || *a.Min > *a.Max {
				return errors.New("int argument constraints")
			}
		case "enum":
			if a.Pattern != "" || len(a.Enum) == 0 || len(a.Enum) > 32 || a.Min != nil || a.Max != nil || a.MaxLength != 0 {
				return errors.New("enum argument constraints")
			}
			for _, value := range a.Enum {
				if err := validateLocalString(value, 256, nil); err != nil {
					return errors.New("unsafe enum value")
				}
			}
		case "string":
			if a.Pattern == "" || a.Min != nil || a.Max != nil || len(a.Enum) != 0 || a.MaxLength < 1 || a.MaxLength > 256 {
				return errors.New("string argument constraints")
			}
			if !strings.HasPrefix(a.Pattern, "^") || !strings.HasSuffix(a.Pattern, "$") {
				return errors.New("string pattern must be anchored")
			}
			if _, err := regexp.Compile(a.Pattern); err != nil {
				return errors.New("string pattern")
			}
		default:
			return errors.New("argument type")
		}
	}
	scriptPath, err := localContainedRegular(root, op.Script, localOperationMaxScriptSize)
	if err != nil {
		return err
	}
	raw, err := os.ReadFile(scriptPath)
	if err != nil {
		return err
	}
	if digest(raw) != op.ScriptSHA256 {
		return errors.New("LOCAL_EXEC_SCRIPT_HASH_MISMATCH")
	}
	_, err = localWorkingDirectory(root, c, op)
	return err
}

func (p *Engine) RunLocalOperation(ctx context.Context, req LocalExecutionRequest) (LocalExecutionResult, error) {
	started := time.Now().UTC()
	result := LocalExecutionResult{
		Schema:       localExecutionResultSchema,
		RequestID:    req.RequestID,
		OperationID:  req.OperationID,
		Status:       "refused",
		ScriptSHA256: req.ScriptSHA256,
		ExitCode:     -1,
		StartedAt:    started,
		FinishedAt:   started,
	}
	if !safeID.MatchString(req.RequestID) || !safeID.MatchString(req.OperationID) {
		return result, errors.New("LOCAL_EXEC_REQUEST_INVALID")
	}

	evidenceDir, err := p.beginLocalExecutionEvidence(req, started)
	if err != nil {
		return result, err
	}
	finish := func(runErr error, stdout, stderr *localCapture) (LocalExecutionResult, error) {
		result.FinishedAt = time.Now().UTC()
		if stdout != nil {
			result.Stdout = stdout.buf.String()
			result.OutputTruncated = result.OutputTruncated || stdout.truncated
		}
		if stderr != nil {
			result.Stderr = stderr.buf.String()
			result.OutputTruncated = result.OutputTruncated || stderr.truncated
		}
		if runErr == nil {
			result.Status = "succeeded"
			result.ExitCode = 0
		} else if result.Status != "refused" {
			result.Status = "failed"
		}
		manifestHash, evidenceErr := sealLocalExecutionEvidence(evidenceDir, result, runErr)
		if evidenceErr != nil {
			return result, fmt.Errorf("LOCAL_EXEC_EVIDENCE_WRITE_FAILED: %w", evidenceErr)
		}
		result.EvidenceManifestSHA256 = manifestHash
		return result, runErr
	}

	if p.localOperations == nil {
		return finish(errors.New("LOCAL_EXEC_DISABLED"), nil, nil)
	}
	op, ok := p.localOperations.byID[req.OperationID]
	if !ok {
		return finish(errors.New("LOCAL_EXEC_OPERATION_NOT_REGISTERED"), nil, nil)
	}
	if req.ScriptSHA256 != op.ScriptSHA256 {
		return finish(errors.New("LOCAL_EXEC_SCRIPT_HASH_MISMATCH"), nil, nil)
	}
	scriptPath, err := localContainedRegular(p.Root, op.Script, localOperationMaxScriptSize)
	if err != nil {
		return finish(err, nil, nil)
	}
	raw, err := os.ReadFile(scriptPath)
	if err != nil {
		return finish(err, nil, nil)
	}
	if digest(raw) != op.ScriptSHA256 {
		return finish(errors.New("LOCAL_EXEC_SCRIPT_HASH_MISMATCH"), nil, nil)
	}
	args, err := buildLocalOperationArgs(op, req.Parameters)
	if err != nil {
		return finish(err, nil, nil)
	}
	workDir, err := localWorkingDirectory(p.Root, p.Config, op)
	if err != nil {
		return finish(err, nil, nil)
	}
	program := p.Config.Tools.Powershell
	if err = validateLocalPowerShell(program); err != nil {
		return finish(err, nil, nil)
	}
	timeoutCtx, cancel := context.WithTimeout(ctx, time.Duration(op.TimeoutSeconds)*time.Second)
	defer cancel()

	stdout := &localCapture{limit: localOperationCaptureLimit}
	stderr := &localCapture{limit: localOperationCaptureLimit}
	processArgs := []string{"-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", scriptPath}
	processArgs = append(processArgs, args...)
	result.Status = "running"
	err = p.runner.Run(timeoutCtx, ProcessSpec{
		Program: program,
		Args:    processArgs,
		Dir:     workDir,
		Env:     append(minimalEnv(), "CKB_PLANE_LOCAL_EXEC=1"),
	}, stdout, stderr)
	result.ExitCode = exitCode(err)
	if errors.Is(timeoutCtx.Err(), context.DeadlineExceeded) {
		err = errors.New("LOCAL_EXEC_TIMEOUT")
	}
	return finish(err, stdout, stderr)
}

func buildLocalOperationArgs(op LocalOperation, parameters map[string]json.RawMessage) ([]string, error) {
	if parameters == nil {
		parameters = map[string]json.RawMessage{}
	}
	known := make(map[string]LocalOperationArgument, len(op.Arguments))
	for _, a := range op.Arguments {
		known[a.Name] = a
	}
	for name := range parameters {
		if _, ok := known[name]; !ok {
			return nil, errors.New("LOCAL_EXEC_ARGUMENT_UNKNOWN")
		}
	}
	var out []string
	for _, a := range op.Arguments {
		raw, present := parameters[a.Name]
		if !present {
			if a.Required {
				return nil, errors.New("LOCAL_EXEC_ARGUMENT_REQUIRED")
			}
			continue
		}
		switch a.Type {
		case "bool":
			var value bool
			if err := json.Unmarshal(raw, &value); err != nil {
				return nil, errors.New("LOCAL_EXEC_ARGUMENT_TYPE")
			}
			out = append(out, fmt.Sprintf("-%s:$%t", a.Name, value))
		case "int":
			var value int64
			if err := json.Unmarshal(raw, &value); err != nil {
				return nil, errors.New("LOCAL_EXEC_ARGUMENT_TYPE")
			}
			if value < *a.Min || value > *a.Max {
				return nil, errors.New("LOCAL_EXEC_ARGUMENT_RANGE")
			}
			out = append(out, "-"+a.Name, strconv.FormatInt(value, 10))
		case "enum":
			var value string
			if err := json.Unmarshal(raw, &value); err != nil {
				return nil, errors.New("LOCAL_EXEC_ARGUMENT_TYPE")
			}
			found := false
			for _, allowed := range a.Enum {
				if value == allowed {
					found = true
					break
				}
			}
			if !found {
				return nil, errors.New("LOCAL_EXEC_ARGUMENT_ENUM")
			}
			out = append(out, "-"+a.Name, value)
		case "string":
			var value string
			if err := json.Unmarshal(raw, &value); err != nil {
				return nil, errors.New("LOCAL_EXEC_ARGUMENT_TYPE")
			}
			pattern, _ := regexp.Compile(a.Pattern)
			if err := validateLocalString(value, a.MaxLength, pattern); err != nil {
				return nil, err
			}
			out = append(out, "-"+a.Name, value)
		default:
			return nil, errors.New("LOCAL_EXEC_ARGUMENT_TYPE")
		}
	}
	return out, nil
}

func validateLocalString(value string, max int, pattern *regexp.Regexp) error {
	if value == "" || len(value) > max || strings.HasPrefix(value, "-") || localUnsafeValue.MatchString(value) {
		return errors.New("LOCAL_EXEC_ARGUMENT_UNSAFE")
	}
	if pattern != nil && !pattern.MatchString(value) {
		return errors.New("LOCAL_EXEC_ARGUMENT_PATTERN")
	}
	return nil
}

func validateLocalPowerShell(program string) error {
	if !filepath.IsAbs(program) || !strings.EqualFold(filepath.Ext(program), ".exe") {
		return errors.New("LOCAL_EXEC_POWERSHELL_INVALID")
	}
	info, err := os.Lstat(program)
	if err != nil || !info.Mode().IsRegular() || info.Mode()&os.ModeSymlink != 0 {
		return errors.New("LOCAL_EXEC_POWERSHELL_INVALID")
	}
	return nil
}

func localWorkingDirectory(root string, c Config, op LocalOperation) (string, error) {
	base := root
	if op.WorkingRoot != "plane" {
		repoID := strings.TrimPrefix(op.WorkingRoot, "repo:")
		repo, ok := c.Repos[repoID]
		if !ok || repo.LocalPath == "" {
			return "", errors.New("LOCAL_EXEC_WORKING_ROOT_INVALID")
		}
		base = repo.LocalPath
		if !filepath.IsAbs(base) {
			base = filepath.Join(root, base)
		}
	}
	base, err := filepath.Abs(base)
	if err != nil {
		return "", err
	}
	base, err = filepath.EvalSymlinks(base)
	if err != nil {
		return "", err
	}
	rel := op.WorkingDir
	if rel == "" {
		rel = "."
	}
	target := filepath.Join(base, filepath.FromSlash(rel))
	target, err = filepath.Abs(target)
	if err != nil {
		return "", err
	}
	if !localPathWithin(base, target) {
		return "", errors.New("LOCAL_EXEC_WORKING_DIR_OUTSIDE_ROOT")
	}
	resolved, err := filepath.EvalSymlinks(target)
	if err != nil {
		return "", err
	}
	if !sameLocalPath(target, resolved) || !localPathWithin(base, resolved) {
		return "", errors.New("LOCAL_EXEC_WORKING_DIR_ALIAS_REJECTED")
	}
	info, err := os.Stat(resolved)
	if err != nil || !info.IsDir() {
		return "", errors.New("LOCAL_EXEC_WORKING_DIR_INVALID")
	}
	return resolved, nil
}

func localContainedRegular(root, rel string, maxSize int64) (string, error) {
	if !safePath(filepath.ToSlash(rel)) {
		return "", errors.New("LOCAL_EXEC_PATH_INVALID")
	}
	base, err := filepath.Abs(root)
	if err != nil {
		return "", err
	}
	base, err = filepath.EvalSymlinks(base)
	if err != nil {
		return "", err
	}
	target := filepath.Join(base, filepath.FromSlash(rel))
	target, err = filepath.Abs(target)
	if err != nil {
		return "", err
	}
	if !localPathWithin(base, target) {
		return "", errors.New("LOCAL_EXEC_PATH_OUTSIDE_PLANE")
	}
	resolved, err := filepath.EvalSymlinks(target)
	if err != nil {
		return "", err
	}
	if !sameLocalPath(target, resolved) || !localPathWithin(base, resolved) {
		return "", errors.New("LOCAL_EXEC_PATH_ALIAS_REJECTED")
	}
	info, err := os.Lstat(resolved)
	if err != nil || !info.Mode().IsRegular() || info.Mode()&os.ModeSymlink != 0 {
		return "", errors.New("LOCAL_EXEC_FILE_INVALID")
	}
	if maxSize > 0 && info.Size() > maxSize {
		return "", errors.New("LOCAL_EXEC_FILE_TOO_LARGE")
	}
	return resolved, nil
}

func localPathWithin(root, target string) bool {
	rel, err := filepath.Rel(root, target)
	if err != nil || filepath.IsAbs(rel) {
		return false
	}
	return rel != ".." && !strings.HasPrefix(rel, ".."+string(os.PathSeparator))
}

func sameLocalPath(a, b string) bool {
	a = filepath.Clean(a)
	b = filepath.Clean(b)
	if runtime.GOOS == "windows" {
		return strings.EqualFold(a, b)
	}
	return a == b
}

func (p *Engine) beginLocalExecutionEvidence(req LocalExecutionRequest, started time.Time) (string, error) {
	root := filepath.Join(p.Root, "evidence", "local-exec")
	if err := os.MkdirAll(root, 0700); err != nil {
		return "", err
	}
	dir := filepath.Join(root, req.RequestID)
	if err := os.Mkdir(dir, 0700); err != nil {
		if os.IsExist(err) {
			return "", errors.New("LOCAL_EXEC_EVIDENCE_EXISTS")
		}
		return "", err
	}
	parameters, err := json.Marshal(req.Parameters)
	if err != nil {
		return "", err
	}
	request := map[string]any{
		"schema":                  "ckb-plane.local-execution-request.v1",
		"request_id":              req.RequestID,
		"operation_id":            req.OperationID,
		"requested_script_sha256": req.ScriptSHA256,
		"parameters_sha256":       digest(parameters),
		"started_at":              started,
	}
	if err = writeLocalExclusiveJSON(filepath.Join(dir, "request.json"), request); err != nil {
		return "", err
	}
	return dir, nil
}

func sealLocalExecutionEvidence(dir string, result LocalExecutionResult, runErr error) (string, error) {
	if result.Stdout != "" {
		if err := writeLocalExclusive(filepath.Join(dir, "stdout.txt"), []byte(result.Stdout)); err != nil {
			return "", err
		}
	}
	if result.Stderr != "" {
		if err := writeLocalExclusive(filepath.Join(dir, "stderr.txt"), []byte(result.Stderr)); err != nil {
			return "", err
		}
	}
	record := map[string]any{
		"schema":           result.Schema,
		"request_id":       result.RequestID,
		"operation_id":     result.OperationID,
		"status":           result.Status,
		"script_sha256":    result.ScriptSHA256,
		"exit_code":        result.ExitCode,
		"started_at":       result.StartedAt,
		"finished_at":      result.FinishedAt,
		"output_truncated": result.OutputTruncated,
	}
	if runErr != nil {
		record["error"] = runErr.Error()
	}
	if err := writeLocalExclusiveJSON(filepath.Join(dir, "result.json"), record); err != nil {
		return "", err
	}
	manifest, err := Manifest(dir)
	if err != nil {
		return "", err
	}
	manifestRaw, err := json.MarshalIndent(manifest, "", "  ")
	if err != nil {
		return "", err
	}
	manifestRaw = append(manifestRaw, '\n')
	if err = writeLocalExclusive(filepath.Join(dir, "evidence_manifest.json"), manifestRaw); err != nil {
		return "", err
	}
	if err = VerifyManifest(dir); err != nil {
		return "", err
	}
	return digest(manifestRaw), nil
}

func writeLocalExclusiveJSON(path string, value any) error {
	raw, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return err
	}
	return writeLocalExclusive(path, append(raw, '\n'))
}

func writeLocalExclusive(path string, raw []byte) error {
	f, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {
		return err
	}
	defer f.Close()
	if _, err = f.Write(raw); err != nil {
		return err
	}
	return f.Sync()
}
