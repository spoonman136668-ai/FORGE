package nrm1j

// This is a POST-IMPLEMENTATION falsification test. It must never be represented
// as a prospectively frozen independent science trial.
import (
 "testing"
 nrm1e "github.com/spoonman136668-ai/forge/research/nr-m1e"
)

func TestReadoutIsProvablyQueryBlindAtTwoSlots(t *testing.T) {
 // Exhaustive action/reward pair roles with four distinct valid public queries.
 // With at most two events, an action either has one reward (normalizing its
 // sole weight cancels context), or it is the ONLY observed action. Hence
 // no choice can depend on the present public context. This is a negative.
 queries:=[]nrm1e.NativePublicGrid{
  {X:0,Y:0,GoalX:0,GoalY:0,Direction:0,FrontBlocked:false},
  {X:64,Y:64,GoalX:64,GoalY:64,Direction:3,FrontBlocked:true},
  {X:1,Y:62,GoalX:63,GoalY:2,Direction:1,FrontBlocked:true},
  {X:30,Y:30,GoalX:29,GoalY:31,Direction:2,FrontBlocked:false},
 }
 rewards:=[]float64{-1,0,1}
 cases:=0
 for a:=0;a<3;a++ {for b:=0;b<3;b++ {
  for _,ra:=range rewards {for _,rb:=range rewards {
   e1:=sampleEvent(t,a,ra)
   e2:=sampleEvent(t,b,rb)
   // Change the recorded predecessor state for the second event so
   // similarity weights genuinely vary across public decision queries.
   second:=nrm1e.NativePublicGrid{
    X:63,Y:2,GoalX:1,GoalY:62,Direction:0,FrontBlocked:true,
   }
   after:=second;after.X=62
   var err error
   e2,err=nrm1e.ConvertObservedPublic(second,b,nrm1e.NativePublicConsequence{
    After:after,Reward:rb,
   })
   if err!=nil {t.Fatal(err)}
   baseline,err:=Recommend([]nrm1e.Event{e1,e2},queries[0])
   if err!=nil {t.Fatal(err)}
   for _,query:=range queries[1:] {
    got,err:=Recommend([]nrm1e.Event{e1,e2},query)
    if err!=nil {t.Fatal(err)}
    if got.Action!=baseline.Action || got.HasEvidence!=baseline.HasEvidence {
     t.Fatalf("counterexample to 2-slot query-blindness: a=%d b=%d ra=%v rb=%v q=%+v got=%+v baseline=%+v",a,b,ra,rb,query,got,baseline)
    }
   }
   cases++
  }}
 }}
 if cases!=81 {t.Fatalf("incomplete action-reward pair census: %d",cases)}
}

func TestScreenDisagreementDoesNotDemonstrateContextActionDependence(t *testing.T) {
 input:=fixture(t,true)
 first,err:=Screen(input);if err!=nil {t.Fatal(err)}
 input.NextPublicGrid=nrm1e.NativePublicGrid{
  X:64,Y:64,GoalX:0,GoalY:0,Direction:3,FrontBlocked:true,
 }
 second,err:=Screen(input);if err!=nil {t.Fatal(err)}
 for name,pair:=range map[string][2]Recommendation{
  "candidate":{first.Candidate,second.Candidate},
  "fifo":{first.FIFO,second.FIFO},
  "reservoir":{first.Reservoir,second.Reservoir},
 } {
  if pair[0].Action!=pair[1].Action || pair[0].HasEvidence!=pair[1].HasEvidence {
   t.Fatalf("%s action improperly depended on current context: %+v",name,pair)
  }
 }
 // This regression demonstrates no basis for source-world promotion.
 if !first.SourceFreeOnly || !second.SourceFreeOnly {t.Fatal("not source free")}
}
