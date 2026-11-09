package nativediscovery

import (
  "crypto/sha256"
  "testing"
)

// One-use DEV-only tracked Go source delta, never merged into production.
func TestG155ChangedTrackedGoSourceUsesOriginalSuite(t *testing.T) {
  digest := sha256.Sum256([]byte("FORGE-G155-source"))
  control := sha256.Sum256(append([]byte("FORGE-"), []byte("G155-source")...))
  if digest != control {
    t.Fatal("changed source test does not preserve deterministic equality")
  }
}
