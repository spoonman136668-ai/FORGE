package shadowcore

import (
 "strings"
 "testing"
 "github.com/spoonman136668-ai/forge/researchstate"
)
func addCycle(t *testing.T,j researchstate.Journal,lane,id string,from,to researchstate.Phase)researchstate.Journal{
 t.Helper();h,err:=researchstate.Head(j);if err!=nil{t.Fatal(err)}
 ev:=researchstate.Event{Lane:lane,ExperimentID:id,FrozenSHA256:strings.Repeat("a",64),From:from,To:to,IrreversibleRisk:to==researchstate.Executing}
 if to==researchstate.Qualified||to==researchstate.Authorized||to==researchstate.Executing||to==researchstate.EvidenceSealed||to==researchstate.Classified||to==researchstate.SuccessorReady{ev.EvidenceSHA256=strings.Repeat("b",64)}
 out,err:=researchstate.Append(j,ev,h);if err!=nil{t.Fatal(err)}
 return out
}
func TestCycleTraceRequiresExactAncestry(t *testing.T){
 j:=researchstate.New()
 phases:=[]researchstate.Phase{researchstate.Proposed,researchstate.Preregistered,researchstate.Qualifying,researchstate.Qualified,researchstate.Authorized,researchstate.Executing,researchstate.EvidenceSealed,researchstate.Classified,researchstate.SuccessorReady}
 from:=researchstate.Phase("")
 for _,next:=range phases{j=addCycle(t,j,"Wingless","old",from,next);from=next}
 // Both existing programs must be present to qualify the shared observer.
 j=addCycle(t,j,"Yggdrasil","other","",researchstate.Proposed)
 parent:=j
 c:=j;from=""
 for _,next:=range phases[:4]{c=addCycle(t,c,"Wingless","new",researchstate.Phase(from),next);from=next}
 ph,_:=researchstate.Head(parent);ch,_:=researchstate.Head(c)
 good:=CycleTrace{Lane:"Wingless",ParentExperimentID:"old",ChildExperimentID:"new",ParentHeadSHA256:ph,ChildHeadSHA256:ch,OriginalStartReceiptSHA256:strings.Repeat("c",64),TerminalReceiptSHA256:strings.Repeat("d",64),RawEvidenceSHA256:strings.Repeat("e",64),IndependentClassificationSHA256:strings.Repeat("f",64),SuccessorQualificationSHA256:strings.Repeat("1",64),OwnerEpoch:1,IndependentlyAuthenticated:true}
 if err:=VerifyCycleTrace(parent,c,good);err!=nil{t.Fatal(err)}
 good.IndependentlyAuthenticated=false
 if err:=VerifyCycleTrace(parent,c,good);err==nil{t.Fatal("unverified witness accepted")}
 good.IndependentlyAuthenticated=true;good.ChildExperimentID="old"
 if err:=VerifyCycleTrace(parent,c,good);err==nil{t.Fatal("original reused as child")}
}
