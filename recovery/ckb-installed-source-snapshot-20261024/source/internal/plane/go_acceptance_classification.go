package plane

import (
	"context"
	"errors"
	"strings"
	"time"
)

const (
	goFocusedTestTimeout       = 60 * time.Second
	goFullTestTimeout          = 180 * time.Second
	goFocusedSupervisorTimeout = 2 * time.Minute
	goFullSupervisorTimeout    = 5 * time.Minute
)

func goAcceptanceSupervisorTimeout(all bool) time.Duration {
	if all {
		return goFullSupervisorTimeout
	}
	return goFocusedSupervisorTimeout
}

func goAcceptanceTimeoutArg(all bool) string {
	if all {
		return "-timeout=180s"
	}
	return "-timeout=60s"
}

func classifyGoAcceptanceExecutionFailure(ctxErr, runErr error, stdout, stderr []byte) string {
	combined := strings.ToLower(string(stdout) + "\n" + string(stderr))
	if runErr != nil {
		combined += "\n" + strings.ToLower(runErr.Error())
	}

	if errors.Is(ctxErr, context.DeadlineExceeded) ||
		strings.Contains(combined, "panic: test timed out after") ||
		strings.Contains(combined, "test timed out after") {
		return "GO_TEST_TIMEOUT"
	}

	cacheMention := strings.Contains(combined, "gocache") ||
		strings.Contains(combined, "gotmpdir") ||
		strings.Contains(combined, "build cache") ||
		strings.Contains(combined, "cache directory")
	cacheAccessFailure := strings.Contains(combined, "access is denied") ||
		strings.Contains(combined, "permission denied") ||
		strings.Contains(combined, "failed to initialize build cache") ||
		strings.Contains(combined, "cannot create") ||
		strings.Contains(combined, "not a directory")
	if cacheMention && cacheAccessFailure {
		return "GO_CACHE_ACCESS_FAILED"
	}

	// Go's -json output proves that the test command launched and reached test
	// execution. Deterministic compile/test failures stay source-repair failures.
	if strings.Contains(combined, "\"action\":\"fail\"") ||
		strings.Contains(combined, "\"action\": \"fail\"") {
		return "GO_TEST_ASSERTION_FAILED"
	}

	// Without positive timeout/cache/test-failure evidence, an execution error
	// is infrastructure. Successful commands that simply yield no matching
	// test pass are handled by the caller as assertion failures.
	if runErr != nil {
		return "GO_TEST_INFRASTRUCTURE_FAILED"
	}
	return "GO_TEST_ASSERTION_FAILED"
}

func goAcceptanceCheckName(pass bool, detail string) string {
	if pass {
		return "GO_TEST_ASSERTION_FAILED"
	}
	for _, code := range []string{
		"GO_TEST_TIMEOUT",
		"GO_CACHE_ACCESS_FAILED",
		"GO_TEST_INFRASTRUCTURE_FAILED",
		"GO_TEST_ASSERTION_FAILED",
	} {
		if strings.HasPrefix(detail, code+":") || detail == code {
			return code
		}
	}
	upper := strings.ToUpper(detail)
	if strings.Contains(upper, "GO_ENVIRONMENT_FAILED") ||
		strings.Contains(upper, "GO_EXECUTABLE_UNAVAILABLE") ||
		strings.Contains(upper, "GO_NATIVE_LAUNCH_FAILED") ||
		strings.Contains(upper, "WINDOWS_TOOLCHAIN_MISMATCH") ||
		strings.Contains(upper, "EVIDENCE_WRITE_FAILED") {
		return "GO_TEST_INFRASTRUCTURE_FAILED"
	}
	return "GO_TEST_ASSERTION_FAILED"
}

func retryPolicyGoInfrastructureFailure(code string) bool {
	code = strings.TrimSpace(code)
	if strings.HasPrefix(code, "RETRY_LIMIT_REACHED:") {
		code = strings.TrimSpace(strings.TrimPrefix(code, "RETRY_LIMIT_REACHED:"))
	}
	switch code {
	case "GO_TEST_TIMEOUT", "GO_TEST_INFRASTRUCTURE_FAILED", "GO_CACHE_ACCESS_FAILED":
		return true
	default:
		return false
	}
}
