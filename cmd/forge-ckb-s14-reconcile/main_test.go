package main

import (
    "bytes"
    "context"
    "errors"
    "strings"
    "testing"
)

func TestRetiredReconciliationRejectsEveryHistoricalInput(t *testing.T) {
    inputs := [][]string{
        nil, {}, {"--help"},
        {"--state", "/tmp/old-ledgers", "--pinned", "/tmp/old-sha-pins.json"},
        {"--state", "\\\\legacy\\state", "--pinned", "X:\\old-pins.json"},
        {"--state", strings.Repeat("x", 16000)},
        {"--pinned", "../../outside.json"},
        {"--token", "synthetic-test-token-not-a-real-secret"},
    }
    for _, args := range inputs {
        for _, token := range []string{"", "synthetic-test-token", "ghs_" + strings.Repeat("q", 40)} {
            var out bytes.Buffer
            err := run(context.Background(), args, &out, token)
            if !errors.Is(err, errRetired) {
                t.Fatalf("legacy reconciliation unexpectedly accessed sources: %v", err)
            }
            if out.Len() != 0 {
                t.Fatal("retired reconciliation emitted misleading evidence")
            }
        }
    }
}

func TestRetiredReconciliationCannotClaimFirstUse(t *testing.T) {
    if !FORGE_CKB_S14_RECONCILE_COMMAND_RETIRED {
        t.Fatal("reconciliation retirement sentinel removed")
    }
    var out bytes.Buffer
    ctx, cancel := context.WithCancel(context.Background())
    cancel()
    err := run(ctx, []string{"--state", "irrelevant"}, &out, "ignored")
    if !errors.Is(err, errRetired) || out.Len() != 0 {
        t.Fatal("retired reconciliation accepted cancellation or emitted authority")
    }
}
