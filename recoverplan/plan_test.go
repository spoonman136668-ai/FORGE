package recoverplan
import(
 "strings"
 "testing"
 "github.com/spoonman136668-ai/forge/researchstate"
)
func makeJournal(t *testing.T,executed bool)researchstate.Journal{
 t.Helper();j:=researchstate.New();prev:=researchstate.Phase("")
 phases:=[]researchstate.Phase{researchstate.Proposed,researchstate.Preregistered,researchstate.Qualifying,researchstate.Qualified,researchstate.Authorized}
 if executed{phases=append(phases,researchstate.Executing)}
 for _,next:=range phases{
  h,err:=researchstate.Head(j);if err!=nil{t.Fatal(err)}
  e:=researchstate.Event{Lane:"Wingless",ExperimentID:"original",FrozenSHA256:strings.Repeat("b",64),From:prev,To:next,IrreversibleRisk:next==researchstate.Executing}
  if next==researchstate.Qualified||next==researchstate.Authorized||next==researchstate.Executing{e.EvidenceSHA256=strings.Repeat("c",64)}
  j,err=researchstate.Append(j,e,h);if err!=nil{t.Fatal(err)}
  prev=next
 }
 return j
}
func TestNeverReplayAfterAuthorization(t *testing.T){
 for _,executed:=range []bool{false,true}{
  j:=makeJournal(t,executed)
  o:=Observation{Lane:"Wingless",ExperimentID:"original",Category:Infrastructure,ExactSourceSHA:strings.Repeat("a",40),FrozenSHA256:strings.Repeat("b",64),Budget:3}
  p,err:=Decide(j,o);if err!=nil||p.Action!=Reconcile{t.Fatal(p,err)}
 }
}
func TestBoundedQualificationAndIntegrity(t *testing.T){
 j:=researchstate.New();h,_:=researchstate.Head(j)
 j,err:=researchstate.Append(j,researchstate.Event{Lane:"Yggdrasil",ExperimentID:"original",FrozenSHA256:strings.Repeat("b",64),To:researchstate.Proposed},h)
 if err!=nil{t.Fatal(err)}
 o:=Observation{Lane:"Yggdrasil",ExperimentID:"original",Category:Qualification,ExactSourceSHA:strings.Repeat("a",40),FrozenSHA256:strings.Repeat("b",64),Budget:2,PreviousAttempts:1}
 p,err:=Decide(j,o);if err!=nil||p.Action!=Requalify||p.NextAttempt!=2{t.Fatal(p,err)}
 o.PreviousAttempts=2;p,err=Decide(j,o);if err!=nil||p.Action!=Freeze{t.Fatal(p,err)}
 o.PreviousAttempts=0;o.Category=Integrity
 p,err=Decide(j,o);if err!=nil||p.Action!=Freeze{t.Fatal(p,err)}
 o.ExactSourceSHA="bad";if _,err=Decide(j,o);err==nil{t.Fatal("drift admitted")}
}
