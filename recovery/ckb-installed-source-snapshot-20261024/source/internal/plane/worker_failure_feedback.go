package plane

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"unicode/utf8"
)

const (
	workerRetryFeedbackMaxBytes           = 96 << 10
	workerRetryAcceptanceMaxBytes         = 24 << 10
	workerRetryAcceptanceResultMaxBytes   = 8 << 10
	workerRetryDiagnosticMaxBytes         = 32 << 10
	workerRetryDiagnosticStderrMaxBytes   = 16 << 10
	workerRetryExitMaxBytes               = 8 << 10
	workerRetryStderrMaxBytes             = 16 << 10
	workerRetryFeedbackParseMaxBytes      = 128 << 10
	workerRetryMultiFocusedMaxBytes       = 8 << 10
	workerRetryMultiFocusedStderrMaxBytes = 2 << 10
	workerRetryMultiGoMaxBytes            = 16 << 10
	workerRetryMultiGoStderrMaxBytes      = 4 << 10
	workerRetryGoSummaryMaxBytes          = 16 << 10
	workerRetryGoScanMaxBytes             = 64 << 20
	workerRetryGoPerTestOutputMaxBytes    = 2 << 10
	workerRetryGoTrackedTestsMax          = 512
	workerRetryFeedbackReplacementText    = "\uFFFD"
)

var focusedGoEvidenceName = regexp.MustCompile(`\bgo-focused-[0-9]+\.jsonl\b`)

type retryFeedbackSection struct {
	name  string
	dir   string
	file  string
	text  string
	limit int
	tail  bool
}

// previousAttemptFeedback returns bounded diagnostic evidence from the immediately
// preceding attempt. The returned text is prompt data only: it is explicitly
// untrusted and cannot authorize execution, acceptance, promotion, or policy
// changes. Only fixed evidence filenames, plus a strictly validated focused-Go
// filename explicitly referenced by the plane-owned acceptance record, are
// eligible. Arbitrary paths, stdout, source, workspace files, candidate diffs,
// and changed-file inventories are excluded.
func previousAttemptFeedback(root, id string, attempt int) string {
	if attempt <= 1 || !safeID.MatchString(id) {
		return ""
	}
	previousDir := filepath.Join(root, "evidence", id, strconv.Itoa(attempt-1))
	if err := bridgeContained(root, previousDir); err != nil {
		return ""
	}

	sections := []retryFeedbackSection{
		{name: "PREVIOUS ACCEPTANCE RESULT", file: "acceptance_result.json", limit: workerRetryAcceptanceResultMaxBytes},
	}
	sections = append(sections, previousAcceptanceDiagnosticSections(root, previousDir)...)
	sections = append(sections,
		retryFeedbackSection{name: "PREVIOUS ACCEPTANCE CHECKS", file: "acceptance_checks.json", limit: workerRetryAcceptanceMaxBytes},
		retryFeedbackSection{name: "PREVIOUS WORKER EXIT", file: "worker_exit.json", limit: workerRetryExitMaxBytes},
		retryFeedbackSection{name: "PREVIOUS WORKER STDERR", file: "worker_stderr.log", limit: workerRetryStderrMaxBytes, tail: true},
	)

	// An administrative controller shutdown can insert a clean WORKER_CANCELLED
	// attempt between a deterministic acceptance failure and its repair retry.
	// Carry exactly one earlier plane-owned acceptance diagnostic hop forward so
	// the repair worker does not lose the concrete failing gate. This remains
	// bounded to fixed evidence filenames; stdout, candidate diffs, workspaces and
	// changed-file inventories remain excluded.
	if carryDir := cancelledAttemptCarryDir(root, id, attempt, previousDir); carryDir != "" {
		sections = append(sections, retryFeedbackSection{
			name:  "PRE-CANCELLATION ACCEPTANCE RESULT",
			dir:   carryDir,
			file:  "acceptance_result.json",
			limit: workerRetryAcceptanceResultMaxBytes,
		})
		carrySections := previousAcceptanceDiagnosticSections(root, carryDir)
		for i := range carrySections {
			carrySections[i].dir = carryDir
			carrySections[i].name = "PRE-CANCELLATION " + carrySections[i].name
		}
		sections = append(sections, carrySections...)
		sections = append(sections, retryFeedbackSection{
			name:  "PRE-CANCELLATION ACCEPTANCE CHECKS",
			dir:   carryDir,
			file:  "acceptance_checks.json",
			limit: workerRetryAcceptanceMaxBytes,
		})
	}

	var out strings.Builder
	out.WriteString("<<<UNTRUSTED_PREVIOUS_ATTEMPT_DIAGNOSTICS>>>\n")
	wrote := false
	for _, section := range sections {
		text := section.text
		truncated := false
		ok := text != ""
		if !ok {
			dir := section.dir
			if dir == "" {
				dir = previousDir
			}
			text, truncated, ok = readRetryFeedbackFile(root, dir, section.file, section.limit, section.tail)
		}
		if !ok {
			continue
		}
		wrote = true
		fmt.Fprintf(&out, "[%s — untrusted diagnostic data", section.name)
		if truncated {
			out.WriteString(", truncated")
		}
		out.WriteString("]\n")
		out.WriteString(text)
		if !strings.HasSuffix(text, "\n") {
			out.WriteByte('\n')
		}
	}
	if !wrote {
		return ""
	}
	out.WriteString("<<<END_UNTRUSTED_PREVIOUS_ATTEMPT_DIAGNOSTICS>>>\n")
	return truncateRetryFeedbackUTF8(out.String(), workerRetryFeedbackMaxBytes, false)
}

func cancelledAttemptCarryDir(root, id string, attempt int, previousDir string) string {
	if attempt <= 2 {
		return ""
	}

	exitText, truncated, ok := readRetryFeedbackFile(root, previousDir, "worker_exit.json", workerRetryExitMaxBytes, false)
	if !ok || truncated {
		return ""
	}
	var exit struct {
		FailureClass  string `json:"failure_class"`
		FailureReason string `json:"failure_reason"`
	}
	if json.Unmarshal([]byte(exitText), &exit) != nil {
		return ""
	}
	if exit.FailureClass != "WORKER_CANCELLED" && !strings.HasPrefix(exit.FailureReason, "WORKER_CANCELLED") {
		return ""
	}

	resultText, truncated, ok := readRetryFeedbackFile(root, previousDir, "acceptance_result.json", workerRetryAcceptanceResultMaxBytes, false)
	if !ok || truncated {
		return ""
	}
	var result struct {
		AcceptanceRan bool `json:"acceptance_ran"`
	}
	if json.Unmarshal([]byte(resultText), &result) != nil || result.AcceptanceRan {
		return ""
	}

	checksText, truncated, ok := readRetryFeedbackFile(root, previousDir, "acceptance_checks.json", workerRetryFeedbackParseMaxBytes, false)
	if !ok || truncated {
		return ""
	}
	var checks []struct {
		Pass bool `json:"pass"`
	}
	if json.Unmarshal([]byte(checksText), &checks) != nil {
		return ""
	}
	for _, check := range checks {
		if !check.Pass {
			return ""
		}
	}

	carryDir := filepath.Join(root, "evidence", id, strconv.Itoa(attempt-2))
	if err := bridgeContained(root, carryDir); err != nil {
		return ""
	}
	if !hasRetryFeedbackDiagnosticFailure(root, carryDir) {
		return ""
	}
	return carryDir
}

func hasRetryFeedbackDiagnosticFailure(root, dir string) bool {
	text, truncated, ok := readRetryFeedbackFile(root, dir, "acceptance_checks.json", workerRetryFeedbackParseMaxBytes, false)
	if !ok || truncated {
		return false
	}
	var checks []struct {
		Name string `json:"name"`
		Pass bool   `json:"pass"`
	}
	if json.Unmarshal([]byte(text), &checks) != nil {
		return false
	}
	for _, check := range checks {
		if check.Pass {
			continue
		}
		switch check.Name {
		case "GO_TEST_FAILED", "GO_TEST_ASSERTION_FAILED", "GO_TEST_TIMEOUT", "GO_TEST_INFRASTRUCTURE_FAILED", "GO_CACHE_ACCESS_FAILED", "FOCUSED_TEST_FAILED", "POWERSHELL_ACCEPTANCE_FAILED", "PLAYWRIGHT_FAILED":
			return true
		}
	}
	return false
}

func previousAcceptanceDiagnosticSections(root, previousDir string) []retryFeedbackSection {
	text, truncated, ok := readRetryFeedbackFile(root, previousDir, "acceptance_checks.json", workerRetryFeedbackParseMaxBytes, false)
	if !ok || truncated {
		return nil
	}
	var checks []struct {
		Name   string `json:"name"`
		Pass   bool   `json:"pass"`
		Detail string `json:"detail"`
	}
	if err := json.Unmarshal([]byte(text), &checks); err != nil {
		return nil
	}

	var focused []string
	seenFocused := map[string]bool{}
	goAll := false
	var fallback []retryFeedbackSection

	for _, check := range checks {
		if check.Pass {
			continue
		}
		switch check.Name {
		case "GO_TEST_FAILED", "GO_TEST_ASSERTION_FAILED", "GO_TEST_TIMEOUT", "GO_TEST_INFRASTRUCTURE_FAILED", "GO_CACHE_ACCESS_FAILED":
			goAll = true
		case "FOCUSED_TEST_FAILED":
			name := focusedGoEvidenceName.FindString(check.Detail)
			if name != "" && !seenFocused[name] {
				seenFocused[name] = true
				focused = append(focused, name)
			}
		case "POWERSHELL_ACCEPTANCE_FAILED":
			if len(fallback) == 0 {
				fallback = []retryFeedbackSection{
					{name: "PREVIOUS POWERSHELL ACCEPTANCE STDOUT", file: "powershell.stdout.log", limit: workerRetryDiagnosticMaxBytes, tail: true},
					{name: "PREVIOUS POWERSHELL ACCEPTANCE STDERR", file: "powershell.stderr.log", limit: workerRetryDiagnosticStderrMaxBytes, tail: true},
				}
			}
		case "PLAYWRIGHT_FAILED":
			if len(fallback) == 0 {
				fallback = []retryFeedbackSection{
					{name: "PREVIOUS BROWSER RESULT", file: "browser_result.json", limit: workerRetryDiagnosticMaxBytes},
					{name: "PREVIOUS BROWSER STDERR", file: "browser_stderr.log", limit: workerRetryDiagnosticStderrMaxBytes, tail: true},
				}
			}
		}
	}

	goFailures := len(focused)
	if goAll {
		goFailures++
	}
	if goFailures == 0 {
		return fallback
	}

	sections := make([]retryFeedbackSection, 0, len(focused)*2+3)
	if goFailures == 1 && len(focused) == 1 {
		name := focused[0]
		return []retryFeedbackSection{
			{name: "PREVIOUS FOCUSED GO TEST OUTPUT " + name, file: name, limit: workerRetryDiagnosticMaxBytes, tail: true},
			{name: "PREVIOUS FOCUSED GO TEST STDERR " + name, file: name + ".stderr.log", limit: workerRetryDiagnosticStderrMaxBytes, tail: true},
		}
	}

	if goAll {
		if summary := goFailedTestsSummary(root, previousDir); summary != "" {
			sections = append(sections, retryFeedbackSection{
				name: "PREVIOUS GO FAILED TEST SUMMARY",
				text: summary,
			})
		}
	}

	if goFailures == 1 {
		sections = append(sections,
			retryFeedbackSection{name: "PREVIOUS GO TEST OUTPUT", file: "go-all.jsonl", limit: workerRetryDiagnosticMaxBytes, tail: true},
			retryFeedbackSection{name: "PREVIOUS GO TEST STDERR", file: "go-all.jsonl.stderr.log", limit: workerRetryDiagnosticStderrMaxBytes, tail: true},
		)
		return sections
	}

	for _, name := range focused {
		sections = append(sections,
			retryFeedbackSection{name: "PREVIOUS FOCUSED GO TEST OUTPUT " + name, file: name, limit: workerRetryMultiFocusedMaxBytes, tail: true},
			retryFeedbackSection{name: "PREVIOUS FOCUSED GO TEST STDERR " + name, file: name + ".stderr.log", limit: workerRetryMultiFocusedStderrMaxBytes, tail: true},
		)
	}
	if goAll {
		sections = append(sections,
			retryFeedbackSection{name: "PREVIOUS GO TEST OUTPUT", file: "go-all.jsonl", limit: workerRetryMultiGoMaxBytes, tail: true},
			retryFeedbackSection{name: "PREVIOUS GO TEST STDERR", file: "go-all.jsonl.stderr.log", limit: workerRetryMultiGoStderrMaxBytes, tail: true},
		)
	}
	return sections
}

func goFailedTestsSummary(root, previousDir string) string {
	path := filepath.Join(previousDir, "go-all.jsonl")
	if err := bridgeContained(root, path); err != nil {
		return ""
	}
	info, err := os.Lstat(path)
	if err != nil || !info.Mode().IsRegular() || info.Mode()&os.ModeSymlink != 0 {
		return ""
	}
	f, err := os.Open(path)
	if err != nil {
		return ""
	}
	defer f.Close()

	type goEvent struct {
		Action  string `json:"Action"`
		Package string `json:"Package"`
		Test    string `json:"Test"`
		Output  string `json:"Output"`
	}
	type testState struct {
		pkg  string
		tail string
	}

	states := map[string]testState{}
	order := make([]string, 0, 8)
	seenFailed := map[string]bool{}
	scanner := bufio.NewScanner(io.LimitReader(f, workerRetryGoScanMaxBytes))
	scanner.Buffer(make([]byte, 4096), 2<<20)

	for scanner.Scan() {
		var event goEvent
		if json.Unmarshal(scanner.Bytes(), &event) != nil {
			continue
		}
		if event.Test != "" && event.Output != "" {
			state, exists := states[event.Test]
			if exists || len(states) < workerRetryGoTrackedTestsMax {
				if event.Package != "" {
					state.pkg = event.Package
				}
				state.tail = truncateRetryFeedbackUTF8(state.tail+event.Output, workerRetryGoPerTestOutputMaxBytes, true)
				states[event.Test] = state
			}
		}
		if event.Action != "fail" || event.Test == "" || seenFailed[event.Test] {
			continue
		}
		seenFailed[event.Test] = true
		order = append(order, event.Test)
		if state, exists := states[event.Test]; exists && state.pkg == "" && event.Package != "" {
			state.pkg = event.Package
			states[event.Test] = state
		} else if !exists && len(states) < workerRetryGoTrackedTestsMax {
			states[event.Test] = testState{pkg: event.Package}
		}
	}

	if len(order) == 0 {
		return ""
	}

	var out strings.Builder
	for _, name := range order {
		state := states[name]
		if state.pkg != "" {
			fmt.Fprintf(&out, "%s %s\n", state.pkg, name)
		} else {
			out.WriteString(name)
			out.WriteByte('\n')
		}
		if detail := strings.TrimSpace(state.tail); detail != "" {
			detail = truncateRetryFeedbackUTF8(detail, workerRetryGoPerTestOutputMaxBytes, true)
			out.WriteString(detail)
			if !strings.HasSuffix(detail, "\n") {
				out.WriteByte('\n')
			}
		}
	}
	return truncateRetryFeedbackUTF8(out.String(), workerRetryGoSummaryMaxBytes, false)
}

func readRetryFeedbackFile(root, dir, name string, limit int, tail bool) (string, bool, bool) {
	if limit <= 0 {
		return "", false, false
	}
	path := filepath.Join(dir, name)
	if err := bridgeContained(root, path); err != nil {
		return "", false, false
	}
	info, err := os.Lstat(path)
	if err != nil || !info.Mode().IsRegular() || info.Mode()&os.ModeSymlink != 0 {
		return "", false, false
	}
	f, err := os.Open(path)
	if err != nil {
		return "", false, false
	}
	defer f.Close()

	truncated := info.Size() > int64(limit)
	if tail && truncated {
		if _, err = f.Seek(-int64(limit), io.SeekEnd); err != nil {
			return "", false, false
		}
	}
	readLimit := int64(limit)
	if !tail && !truncated {
		readLimit = info.Size()
	}
	raw, err := io.ReadAll(io.LimitReader(f, readLimit))
	if err != nil {
		return "", false, false
	}
	valid := bytes.ToValidUTF8(raw, []byte(workerRetryFeedbackReplacementText))
	text := truncateRetryFeedbackUTF8(string(valid), limit, tail)
	return text, truncated || len(valid) > limit, true
}

func truncateRetryFeedbackUTF8(s string, limit int, tail bool) string {
	if limit <= 0 {
		return ""
	}
	b := []byte(s)
	if len(b) <= limit {
		return s
	}
	if tail {
		b = b[len(b)-limit:]
		for len(b) > 0 && !utf8.RuneStart(b[0]) {
			b = b[1:]
		}
		return string(b)
	}
	b = b[:limit]
	for len(b) > 0 && !utf8.Valid(b) {
		b = b[:len(b)-1]
	}
	return string(b)
}
