package main

import (
    "bytes"
    "errors"
    "strings"
    "testing"
)

func TestRetiredCustodyRejectsEveryFormerInputWithoutOutput(t *testing.T) {
    inputs := [][]string{
        nil,
        {},
        {"--help"},
        {"--state", "/tmp/legacy-controller-state"},
        {"--pinned", "/tmp/synthetic-pins.json", "--state", "/tmp/synthetic-state"},
        {"--state", "\\\\legacy\\state", "--pinned", "X:\\external-pins.json"},
        {"--token", "synthetic-test-token-not-a-credential"},
        {"--state", strings.Repeat("a", 8000)},
    }
    for _, args := range inputs {
        t.Run(strings.Join(args, "_"), func(t *testing.T) {
            var out bytes.Buffer
            err := run(args, &out)
            if !errors.Is(err, errRetired) {
                t.Fatalf("retired CKB custody must deny all invocations: %v", err)
            }
            if out.Len() != 0 {
                t.Fatal("retired custody emitted a misleading ledger report")
            }
        })
    }
}

func TestLegacyCustodyCannotReportScientificAuthority(t *testing.T) {
    var out bytes.Buffer
    err := run([]string{"--state", "irrelevant"}, &out)
    if err == nil || !FORGE_CKB_CUSTODY_COMMAND_RETIRED {
        t.Fatal("retired command unexpectedly enabled")
    }
    if out.Len() != 0 {
        t.Fatal("retired command emitted evidence or permission")
    }
}
