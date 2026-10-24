package plane

import (
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
)

func TestWorkerFailureFeedback_GoAssertionAcceptanceCarriesDeterministicFailureEvidenceAliasR1(t *testing.T) {
	root := t.TempDir()
	id := "WORKER_FEEDBACK_ASSERT_ALIAS_R1"
	attempt := 4

	dir := filepath.Join(root, "evidence", id, strconv.Itoa(attempt))
	if err := os.MkdirAll(dir, 0700); err != nil {
		t.Fatal(err)
	}

	files := map[string]string{
		"acceptance_result.json":  `{"state":"REJECTED_RETRYABLE","reason":"GO_TEST_ASSERTION_FAILED","attempt":4}`,
		"acceptance_checks.json":  `[{"name":"GO_TEST_ASSERTION_FAILED","pass":false,"detail":"GO_TEST_ASSERTION_FAILED: Go test failed: process exit 1: exit status 1; see go-all.jsonl and sandbox launch/stderr evidence"}]`,
		"go-all.jsonl":            "{\"Action\":\"output\",\"Output\":\"--- FAIL: TestKCHFullSuiteOnly (0.00s)\\n\"}\n",
		"go-all.jsonl.stderr.log": "assertion stderr marker\n",
	}

	for name, body := range files {
		if err := os.WriteFile(filepath.Join(dir, name), []byte(body), 0600); err != nil {
			t.Fatal(err)
		}
	}

	got := previousAttemptFeedback(root, id, attempt+1)

	for _, want := range []string{
		"GO_TEST_ASSERTION_FAILED",
		"PREVIOUS GO TEST OUTPUT",
		"TestKCHFullSuiteOnly",
		"PREVIOUS GO TEST STDERR",
		"assertion stderr marker",
	} {
		if !strings.Contains(got, want) {
			t.Fatalf("assertion feedback missing %q: %q", want, got)
		}
	}
}
