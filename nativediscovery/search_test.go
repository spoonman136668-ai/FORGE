package nativediscovery

import (
 "encoding/json"
 "reflect"
 "testing"

 "github.com/spoonman136668-ai/forge/genenv"
)

func TestNativeDiscoveryF1GeneratedPopulationAndHeldout(t *testing.T){
 result,err:=F1Development()
 if err!=nil{t.Fatal(err)}
 rerun,err:=F1Development()
 if err!=nil||!reflect.DeepEqual(result,rerun){t.Fatal("nondeterministic native F1 generation or evaluation",err)}
 if result.Schema!=F1Schema||result.SourceSHA!=F1SourceSHA||
  result.TrainingSeeds!=[2]int{11,23}||result.HoldoutSeed!=47||
  result.RequiredGainPP!=5||result.MaxInterferenceLossPP!=10||
  result.DevelopmentStatus!="DEV_NO_GO"||len(result.Lanes)!=2||
  result.GenuineSourceGeneration||result.AuthenticScience||result.F94IndependentSourceAudit||
  result.ControllerWrites!=0||result.PaidAPICalls!=0||result.AgentCalls!=0||
  result.ScientificFirstUse||result.ScientificAccepted||result.AcceptedRefMutations!=0{
  t.Fatalf("frozen source-only authority or negative criterion drift %+v",result)
 }
 for _,lane:=range result.Lanes{
  if lane.SyntheticLaneLabel!="Wingless"&&lane.SyntheticLaneLabel!="Yggdrasil"{
   t.Fatal("invalid synthetic lane label")
  }
  if len(lane.GeneratorCandidates)!=3||len(lane.TrainingMetrics)!=6||
   len(lane.HoldoutMetrics)!=3||lane.HeldoutCriterionMet{
   t.Fatalf("population/negative outcome incorrectly promoted %+v",lane)
  }
  known:=map[string]bool{}
  for _,c:=range lane.GeneratorCandidates{
   if known[c.ID]||len(c.Vector)!=3||c.Classification!="UNTESTED_PROPOSAL"||
    c.HistoricalDistance<1||len(c.EnvironmentSHA256)!=64{
    t.Fatalf("duplicate or malformed generated candidate %+v",c)
   }
   known[c.ID]=true
  }
  if !known[lane.SelectedCandidateID]{t.Fatal("selection not from genuine bounded generator")}
  for _,m:=range append(append([]F1Metric{},lane.TrainingMetrics...),lane.HoldoutMetrics...){
   if !known[m.CandidateID]||m.LearnedObservations!=90||m.OriginalF95Relations!=18||
    m.ColdAccuracy!=m.NativeAccuracy||m.NativeAccuracy>100||m.StrongestConventionalAccuracy>100{
    t.Fatalf("matched data / cold retention or candidate custody mismatch %+v",m)
   }
  }
  for _,m:=range lane.HoldoutMetrics{
   if m.Seed!=47||m.NativeAccuracy>m.StrongestConventionalAccuracy{
    t.Fatalf("unearned synthetic improvement or heldout scope drift %+v",m)
   }
  }
 }
 bytes,err:=json.Marshal(result);if err!=nil{t.Fatal(err)}
 t.Logf("FORGE_NATIVE_DISCOVERY_F1=%s",bytes)
}

func TestNativeDiscoveryF1TamperingFailsClosed(t *testing.T){
 frozen,history,pin,histSHA:=f1Generator("Wingless")
 if _,err:=genenv.Generate(frozen,pin,history,histSHA);err!=nil{t.Fatal(err)}
 drift:=frozen
 drift.Requests=append([]genenv.Request(nil),frozen.Requests...)
 drift.Requests[0].Changes=append([]genenv.Change(nil),frozen.Requests[0].Changes...)
 drift.Requests[0].Changes[0].Delta= -1
 if _,err:=genenv.Generate(drift,pin,history,histSHA);err==nil{
  t.Fatal("generator changed after frozen pin without detection")
 }
 history.Records[0].Classification="SUPPORTED"
 if _,err:=genenv.Generate(frozen,pin,history,histSHA);err==nil{
  t.Fatal("negative historical classification rewritten")
 }
 invalid:=genenv.Candidate{ID:"arbitrary",Vector:[]int64{999,2,2},
  Classification:"UNTESTED_PROPOSAL"}
 if _,err:=f1Score(invalid,11);err==nil{t.Fatal("invalid generated mechanism admitted")}
 invalid.Vector=[]int64{2,2}
 if _,err:=f1Score(invalid,11);err==nil{t.Fatal("truncated mechanism admitted")}
 if F1SourceSHA==""{t.Fatal("source pin absent")}
}
