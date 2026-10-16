// ISO-03: The historical CKB custody inspector is permanently retired.
// Its former ledger-reading implementation remains in Git history only.
// No execution of this command may read local controller state, imported
// ledgers, a private repository, or FORGE scientific evidence.
package main

import (
    "errors"
    "fmt"
    "io"
    "os"
)

const FORGE_CKB_CUSTODY_COMMAND_RETIRED = true

var errRetired = errors.New("FORGE_CKB_CUSTODY_RETIRED_NO_CKB_PLANE_ACCESS")

// Retain the old invocation signature solely for fail-closed regression tests.
// Ignore every caller-supplied flag and path; never open a file or a network
// connection, and never emit a misleading historical custody report.
func run(_ []string, _ io.Writer) error {
    return errRetired
}

func main() {
    fmt.Fprintln(os.Stderr, errRetired)
    os.Exit(1)
}
