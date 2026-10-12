package fsareservation

import (
 "errors"
 "os"
 "path/filepath"
 "strings"
 "sync"
 "testing"

 "github.com/spoonman136668-ai/forge/startrecovery"
)
func intent(lane,experiment,cohort string)startrecovery.Intent{
 return startrecovery.Intent{
  Lane:lane,ExperimentID:experiment,FrozenSHA256:strings.Repeat("a",64),
  SourceSHA:strings.Repeat("b",40),CohortSHA256:cohort,
  NonceSHA256:strings.Repeat("d",64),Generation:1,
 }
}
func TestDurableSingleWinnerAcrossConcurrentCallersAndReopen(t *testing.T){
 root:=t.TempDir()
 s,err:=Open(root);if err!=nil{t.Fatal(err)}
 cohort:=strings.Repeat("c",64)
 var wg sync.WaitGroup
 errs:=make(chan error,24)
 for n:=0;n<24;n++{
  wg.Add(1);go func(n int){defer wg.Done()
   lane:="Wingless";if n%2==1{lane="Yggdrasil"}
   errs<-s.Reserve(intent(lane,"candidate",cohort))
  }(n)
 }
 wg.Wait();close(errs)
 winners:=0
 for err:=range errs{if err==nil{winners++}else if !errors.Is(err,ErrConsumed){t.Fatalf("unexpected error: %v",err)}}
 if winners!=1{t.Fatalf("one-shot cohort winners=%d",winners)}
 reopened,err:=Open(root);if err!=nil{t.Fatal(err)}
 if err:=reopened.Reserve(intent("Yggdrasil","another",cohort));!errors.Is(err,ErrConsumed){t.Fatalf("cohort reused after reopen: %v",err)}
 exists,err:=reopened.Inspect(intent("Wingless","candidate",cohort))
 if err!=nil||!exists{t.Fatalf("recovered claim missing: %v",err)}
}
func TestFailClosedOnCorruptClaimsAndUnprovisionedRoot(t *testing.T){
 if _,err:=Open(filepath.Join(t.TempDir(),"absent"));!errors.Is(err,ErrUnprovisioned){t.Fatal(err)}
 root:=t.TempDir();s,err:=Open(root);if err!=nil{t.Fatal(err)}
 i:=intent("Wingless","W001",strings.Repeat("e",64))
 if err:=os.WriteFile(filepath.Join(root,i.CohortSHA256+".json"),[]byte("truncated"),0600);err!=nil{t.Fatal(err)}
 if err:=s.Reserve(i);!errors.Is(err,ErrConsumed){t.Fatalf("corrupt claim replayed: %v",err)}
 claimed,err:=s.Inspect(i);if !claimed||!errors.Is(err,ErrIndeterminate){t.Fatalf("corrupt claim accepted: %v %v",claimed,err)}
 i.ExperimentID="../escape"
 if err:=s.Reserve(i);!errors.Is(err,ErrInvalid){t.Fatalf("invalid identity accepted: %v",err)}
}
