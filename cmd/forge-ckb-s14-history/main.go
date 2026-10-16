// This legacy command is permanently retired by FORGE ISO-02.
//
// Historical source and tests remain in Git for provenance. No CLI invocation
// is allowed to read CKB-plane, infer scientific first-use, or grant FORGE
// authority. FORGE must qualify its own evidence and permission natively.
package main

import (
    "context"
    "errors"
    "fmt"
    "io"
    "os"
)

const FORGE_CKB_LEGACY_COMMAND_RETIRED = true

var errRetired = errors.New("FORGE_CKB_S14_HISTORY_RETIRED_NO_CKB_PLANE_CONNECTION")

// Preserve the legacy command's test surface while denying every invocation.
func run(_ context.Context, _ string, _ io.Writer) error {
    return errRetired
}

func main() {
    fmt.Fprintln(os.Stderr, errRetired)
    os.Exit(1)
}
