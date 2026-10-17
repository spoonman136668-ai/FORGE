// The pre-isolation CKB-to-FSA cutover audit is permanently retired.
//
// All former evidence-bundle flags and clock arguments are denied before
// any legacy local state, private repository, witness or token can be read.
// FORGE cutover qualification must be redesigned natively and independently.
// Historical implementation remains in immutable Git history only.
package main

import (
    "errors"
    "fmt"
    "io"
    "os"
)

const FORGE_CKB_CUTOVER_AUDIT_COMMAND_RETIRED = true

var errRetired = errors.New("FORGE_CKB_FSA_CUTOVER_AUDIT_RETIRED_NO_PRIVATE_CONTROLLER")

// Keep the public command test signature for explicit fail-closed coverage.
// Inputs are intentionally never inspected. No side effects are permitted.
func run(_ []string, _ io.Writer, _ uint64) error {
    return errRetired
}

func main() {
    fmt.Fprintln(os.Stderr, errRetired)
    os.Exit(1)
}
