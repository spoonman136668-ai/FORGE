package shadowcore

import (
 "strings"
 "testing"
 "github.com/spoonman136668-ai/forge/researchstate"
)
func appendStep(t *testing.T,j researchstate.Journal,lane,id string,from,to researchstate.Phase)researchstate.Journal{
 t.Helper();head,err:=researchstate.Head(j);if err!=nil{t.Fatal(err)}
 e:=researchstate.Event{Lane:lane,ExperimentID:id,FrozenSHA256:strings.Repeat("a",64),From:from,To:to,IrreversibleRisk:to==researchstate.Executing}
 if to==researchstate.Qualified||to==researchstate.Authorized||to==researchstate.Executing||to==researchstate.EvidenceSealed||to==researchstate.Classified||to==researchstate.SuccessorReady{e.EvidenceSHA256=strings.Repeat("b",64)}
 next,err:=researchstate.Append(j,e,head);if err!=nil{t.Fatal(err)}
 return next
}
func TestTwoExistingLaneSimulatedCyclesWithRestartIntegrity(t *testing.T){
 phases:=[]researchstate.Phase{researchstate.Proposed,researchstate.Preregistered,researchstate.Qualifying,researchstate.Qualified,researchstate.Authorized,researchstate.Executing,researchstate.EvidenceSealed,researchstate.Classified,researchstate.SuccessorReady}
 j:=researchstate.New()
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  previous:=researchstate.Phase("")
  for _,phase:=range phases{
   j=appendStep(t,j,lane,"original",previous,phase)
   previous=phase
  }
  previous=""
  for _,phase:=range phases[:4]{
   j=appendStep(t,j,lane,"successor",researchstate.Phase(previous),phase)
   previous=phase
  }
 }
 report,err:=Rehearsal(j);if err!=nil{t.Fatal(err)}
 if report.CompleteExistingLanes!=2||report.SimulatedSuccessorCycles!=2||report.RealScientificCycles!=0{t.Fatal(report)}
 // Crash-safe logical replay must not classify an in-memory synthetic trace
 // as real progression, nor allow a partial/tampered journal.
 if err:=researchstate.Verify(j);err!=nil{t.Fatal(err)}
 j.Entries[len(j.Entries)-1].EvidenceSHA256=strings.Repeat("f",64)
 if _,err:=Rehearsal(j);err==nil{t.Fatal("tampered resumed journal accepted")}
}
func TestNoFakeAutonomyFromProposedOnly(t *testing.T){
 j:=seeded(t)
 if _,err:=Rehearsal(j);err==nil{t.Fatal("incomplete lifecycle reported complete")}
}
