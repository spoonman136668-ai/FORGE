package main

import (
    "bytes"
    "errors"
    "strings"
    "testing"
)

func TestRetiredCutoverCLIAlwaysDeniesWithoutOutput(t *testing.T) {
    hostile := [][]string{
        nil,
        {},
        {"--bundle", "/private/old_controller_state/custody.json"},
        {"--bundle=/private/old_controller_state/custody.json"},
        {"--bundle", "../private/legacy.json"},
        {"--help"},
        {"--bundle", "/tmp/injected.json", "--enable-science", "--release-original"},
        {"--first-use", "true", "--forged-witness", strings.Repeat("a", 64)},
    }
    for _, args := range hostile {
        for _, now := range []uint64{0, 1, 1000, ^uint64(0)} {
            var out bytes.Buffer
            err := run(args, &out, now)
            if !errors.Is(err, errRetired) {
                t.Fatalf("historical cutover command was revived: args=%q now=%d err=%v", args, now, err)
            }
            if out.Len() != 0 {
                t.Fatalf("retired command emitted a fabricated audit: args=%q output=%q", args, out.String())
            }
        }
    }
}

func TestRetiredCutoverNoTokenOrBundleDependentBehavior(t *testing.T) {
    for _, token := range []string{"", "synthetic-not-real", "ghs_" + strings.Repeat("x", 40)} {
        t.Setenv("GH_TOKEN", token)
        var out bytes.Buffer
        if err := run([]string{"--bundle", "/some/possibly/real/private/location"}, &out, 999); !errors.Is(err, errRetired) {
            t.Fatalf("credential must not affect unconditional block: %v", err)
        }
        if out.Len() != 0 {
            t.Fatal("retired cutover CLI wrote an observation")
        }
    }
}

func TestRetiredCutoverSentinelAndStableDenial(t *testing.T) {
    if !FORGE_CKB_CUTOVER_AUDIT_COMMAND_RETIRED {
        t.Fatal("cutover command retirement was removed")
    }
    if got := errRetired.Error(); got != "FORGE_CKB_FSA_CUTOVER_AUDIT_RETIRED_NO_PRIVATE_CONTROLLER" {
        t.Fatalf("unexpected retired command result: %q", got)
    }
}
