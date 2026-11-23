package startrecovery
import (
 "errors"
 "strings"
 "testing"
 "github.com/spoonman136668-ai/forge/researchlog"
)
func TestReconcilePrimary(t *testing.T){
 h:=func(n int)string{return strings.Repeat("a",n)}
 base:=researchlog.Event{Lane:"Wingless",Generation:1,ExperimentID:"exp_01",SourceCommitSHA:h(40),PreregSHA256:h(64),CohortSHA256:strings.Repeat("b",64),WitnessSHA256:strings.Repeat("c",64)}
 j:=researchlog.New()
 appendEvent:=func(kind researchlog.Kind,run uint64,outcome string){
  e:=base;e.Kind=kind;e.RunID=run;e.Outcome=outcome
  if kind==researchlog.Hypothesis{e.PreregSHA256="";e.CohortSHA256="";e.WitnessSHA256=""}
  if kind==researchlog.Preregister{e.WitnessSHA256=""}
  if kind==researchlog.PrimaryTerminal {e.OriginalEvidenceSHA256=strings.Repeat("d",64)}
  next,err:=researchlog.Append(j,e);if err!=nil{t.Fatal(err)};j=next
 }
 pin:=func()TrustedHead{return TrustedHead{Sequence:uint64(len(j.Entries)),SHA256:j.Entries[len(j.Entries)-1].RecordSHA256,IndependentlyAuthenticated:true}}
 appendEvent(researchlog.Hypothesis,0,"")
 appendEvent(researchlog.Preregister,0,"")
 appendEvent(researchlog.SourceQualified,0,"")
 if d,e:=Inspect(j,pin(),"Wingless","exp_01");e!=nil||d!=NoPriorStart{t.Fatalf("prestart: %v %v",d,e)}
 oversized:=pin();oversized.Sequence=uint64(1)<<32+uint64(len(j.Entries))
 if _,e:=Inspect(j,oversized,"Wingless","exp_01");!errors.Is(e,ErrBlocked){t.Fatal("overflowed sequence accepted")}
 stale:=pin()
 appendEvent(researchlog.PrimaryStarted,42,"")
 if d,e:=Inspect(j,pin(),"Wingless","exp_01");e!=nil||d!=Started{t.Fatalf("started: %v %v",d,e)}
 if _,e:=Inspect(j,stale,"Wingless","exp_01");!errors.Is(e,ErrBlocked){t.Fatal("stale head accepted")}
 incomplete:=pin();incomplete.IndependentlyAuthenticated=false
 if _,e:=Inspect(j,incomplete,"Wingless","exp_01");!errors.Is(e,ErrBlocked){t.Fatal("unauthenticated head accepted")}
 if _,e:=Inspect(j,pin(),"Yggdrasil","exp_01");!errors.Is(e,ErrBlocked){t.Fatal("wrong lane accepted")}
 appendEvent(researchlog.PrimaryTerminal,42,"NEGATIVE")
 if d,e:=Inspect(j,pin(),"Wingless","exp_01");e!=nil||d!=Terminal{t.Fatalf("terminal: %v %v",d,e)}
 fork:=pin();fork.SHA256=strings.Repeat("f",64)
 if _,e:=Inspect(j,fork,"Wingless","exp_01");!errors.Is(e,ErrBlocked){t.Fatal("fork accepted")}
}
