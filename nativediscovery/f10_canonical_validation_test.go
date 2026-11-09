package nativediscovery

import (
 "encoding/json"
 "reflect"
 "sync"
 "testing"
)

// TestF10CanonicalValidationColdAndConcurrent preserves both independent cold
// development and the complete original forged-evidence/authority denial suite.
func TestF10CanonicalValidationColdAndConcurrent(t *testing.T) {
 original, err := F10Development()
 if err != nil { t.Fatal("original F10 development failed:", err) }
 cold, err := F10Development()
 if err != nil || !reflect.DeepEqual(original, cold) {
  t.Fatal("independent cold F10 report changed:", err)
 }
 if err := F10Validate(original); err != nil { t.Fatal("valid F10 rejected:", err) }
 clone := func() F10Review {
  data, err := json.Marshal(original)
  if err != nil { t.Fatal("original F10 marshal:", err) }
  var out F10Review
  if err := json.Unmarshal(data, &out); err != nil { t.Fatal("F10 clone:", err) }
  return out
 }
 forged := clone()
 forged.Arms[0].G1G2[1].SelectedCorrect = 64
 forged.DigestSHA256 = f10Digest(forged)
 if F10Validate(forged) == nil { t.Fatal("self-rehashed forged F10 score accepted") }
 forged = clone()
 forged.ParentF7SHA256 = "self-rehashed-foreign-source"
 forged.DigestSHA256 = f10Digest(forged)
 if F10Validate(forged) == nil { t.Fatal("self-rehashed forged F10 parent accepted") }
 forged = clone()
 forged.ScientificAccepted = true
 forged.DigestSHA256 = f10Digest(forged)
 if F10Validate(forged) == nil { t.Fatal("forged scientific first-use accepted") }
 if err := F10Validate(original); err != nil {
  t.Fatal("valid report rejected after forged input:", err)
 }
 const concurrent = 8
 errors := make(chan error, concurrent)
 var group sync.WaitGroup
 for i := 0; i < concurrent; i++ {
  group.Add(1)
  go func() {
   defer group.Done()
   errors <- F10Validate(original)
  }()
 }
 group.Wait()
 close(errors)
 for err := range errors {
  if err != nil { t.Fatal("read-only canonical F10 validation race:", err) }
 }
 if err := F10Validate(cold); err != nil {
  t.Fatal("independent cold F10 rejected after concurrency:", err)
 }
}
