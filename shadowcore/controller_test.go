package shadowcore
import(
 "strings"
 "testing"
 "github.com/spoonman136668-ai/forge/researchstate"
 "github.com/spoonman136668-ai/forge/recoverplan"
)
func TestIntegratedExistingLanesAndNoFakeScience(t *testing.T){
 j:=researchstate.New()
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  head,err:=researchstate.Head(j);if err!=nil{t.Fatal(err)}
  j,err=researchstate.Append(j,researchstate.Event{Lane:lane,ExperimentID:"existing_original",FrozenSHA256:strings.Repeat("a",64),To:researchstate.Proposed},head)
  if err!=nil{t.Fatal(err)}
 }
 s,err:=Observe(j);if err!=nil{t.Fatal(err)}
 if s.Mode!="INACTIVE_SHADOW_NO_AUTHORITY"||len(s.Wingless)!=1||len(s.Yggdrasil)!=1||s.UnattendedScientificCycles!=0{t.Fatal(s)}
 if s.Wingless[0].OriginalReplayPermitted||s.Yggdrasil[0].OriginalReplayPermitted{t.Fatal("shadow replay authorized")}
 plan,err:=AssessRecovery(j,recoverplan.Observation{Lane:"Wingless",ExperimentID:"existing_original",Category:recoverplan.Qualification,ExactSourceSHA:strings.Repeat("b",40),FrozenSHA256:strings.Repeat("a",64),Budget:2})
 if err!=nil||plan.Action!=recoverplan.Requalify{t.Fatal(plan,err)}
 j.Entries[0].RecordSHA256=strings.Repeat("0",64)
 if _,err:=Observe(j);err==nil{t.Fatal("corrupt source journal accepted")}
}
