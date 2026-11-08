package nativediscovery

import (
    "crypto/sha256"
    "testing"
)

// DEV-only tracked Go source change; all existing test bodies remain untouched.
func TestG153ChangedGoSourceReexecutesOriginalSuite(t *testing.T) {
    actual := sha256.Sum256([]byte("FORGE-G153-exact-source-marker"))
    expected := sha256.Sum256(append([]byte("FORGE-G153-"), []byte("exact-source-marker")...))
    if actual != expected {
        t.Fatal("deterministic source identity mismatch")
    }
}
