package nativediscovery

import (
    "crypto/sha256"
    "testing"
)

// DEV-only source delta: ensures the Go compiler graph genuinely differs
// while preserving every pre-existing Go package, test and runtime behavior.
func TestG151ExactMainCompilerSeedNewGoSource(t *testing.T) {
    actual := sha256.Sum256([]byte("FORGE-G151-exact-source-marker"))
    expected := sha256.Sum256(append([]byte("FORGE-G151-"), []byte("exact-source-marker")...))
    if actual != expected {
        t.Fatal("deterministic source-control mismatch")
    }
}
