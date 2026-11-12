package nativediscovery

import (
 "encoding/json"
 "reflect"
 "sync"
 "testing"
)

// TestF12CanonicalValidationColdAndConcurrent keeps the original F12
// oracle-free evidence, self-hash, and owner/first-use denials unchanged.
func TestF12CanonicalValidationColdAndConcurrent(t *testing.T) {
 original, err := F12Development()
 if err != nil { t.Fatal(err) }
 cold, err := F12Development()
 if err != nil || !reflect.DeepEqual(original, cold) {
  t.Fatal("cold F12 canonical development result changed")
 }
 if err := F12Validate(original); err != nil {
  t.Fatal("valid source-bound development evidence rejected:", err)
 }
 raw, err := json.Marshal(original)
 if err != nil { t.Fatal(err) }
 var forged F12Report
 if err := json.Unmarshal(raw, &forged); err != nil { t.Fatal(err) }
 forged.Arms[0].Rounds[0].CausalCorrect++
 forged.DigestSHA256 = f12Digest(forged)
 if F12Validate(forged) == nil {
  t.Fatal("self-hashed altered causal evidence was accepted")
 }
 if err := F12Validate(original); err != nil {
  t.Fatal("forged evidence changed valid reference:", err)
 }
 const concurrent = 8
 var group sync.WaitGroup
 errors := make(chan error, concurrent)
 for i := 0; i < concurrent; i++ {
  group.Add(1)
  go func() {
   defer group.Done()
   errors <- F12Validate(original)
  }()
 }
 group.Wait()
 close(errors)
 for err := range errors {
  if err != nil { t.Fatal("read-only canonical validation race:", err) }
 }
 if err := F12Validate(cold); err != nil {
  t.Fatal("cold original evidence no longer matches reference:", err)
 }
}
