// ISO-04: The legacy two-source S14 reconciliation command is retired.
//
// The original historical implementation remains in Git history for research
// provenance only. This executable cannot inspect local controller paths,
// construct a remote CKB history client, or emit source/first-use claims.
// FORGE must obtain operational evidence using its own scientific authority.
package main

import (
    "context"
    "errors"
    "fmt"
    "io"
    "os"
)

const FORGE_CKB_S14_RECONCILE_COMMAND_RETIRED = true

var errRetired = errors.New("FORGE_CKB_S14_RECONCILIATION_RETIRED_NO_PRIVATE_SOURCE_ACCESS")

// Preserve the old invocation signature for adversarial non-access tests.
// All arguments, tokens and writers are ignored. No I/O occurs in run.
func run(_ context.Context, _ []string, _ io.Writer, _ string) error {
    return errRetired
}

func main() {
    fmt.Fprintln(os.Stderr, errRetired)
    os.Exit(1)
}
