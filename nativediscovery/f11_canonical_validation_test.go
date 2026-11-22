package nativediscovery

import (
 "encoding/json"
 "reflect"
 "sync"
 "testing"
)

func TestF11CanonicalValidationColdAndConcurrent(t *testing.T) {
 original, err := F11Development()
 if err != nil { t.Fatal(err) }
 cold, err := F11Development()
 if err != nil || !reflect.DeepEqual(original, cold) { t.Fatal("original cold F11 evidence changed") }
 if err := F11Validate(original); err != nil { t.Fatal("valid F11 evidence rejected", err) }
 raw, err := json.Marshal(original)
 if err != nil { t.Fatal(err) }
 var forged F11Report
 if err := json.Unmarshal(raw, &forged); err != nil { t.Fatal(err) }
 forged.Arms[0].Rounds[1].PosteriorCorrect++
 forged.DigestSHA256 = f11Digest(forged)
 if F11Validate(forged) == nil { t.Fatal("forged self-hashed causal evidence accepted") }
 if err := F11Validate(original); err != nil { t.Fatal("valid evidence rejected after forged input",err) }
 const concurrent = 8
 var group sync.WaitGroup
 errors := make(chan error, concurrent)
 for i := 0; i < concurrent; i++ {
  group.Add(1)
  go func(){ defer group.Done(); errors <- F11Validate(original) }()
 }
 group.Wait()
 close(errors)
 for err := range errors { if err != nil { t.Fatal("concurrent canonical read failed",err) } }
 if err := F11Validate(cold); err != nil { t.Fatal("cold original F11 evidence no longer accepted",err) }
}
