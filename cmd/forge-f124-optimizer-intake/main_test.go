package main

import (
 "os"
 "path/filepath"
 "testing"
)

func fakeLane(lane string)(jLane,iLane){
 b:=45;c12:=39;c14:=48;a:=1;late:=7
 if lane=="Yggdrasil"{b=46;c12=35;c14=47;a=3;late=8}
 controls:=map[string]control{"12":{Paired:c12},"14":{Paired:c14},"16":{Paired:48}}
 strata:=map[string]measured{
 "near_collision":{Pairs:10,Paired:10},
 "wrong_role_alias":{Pairs:10,Paired:10},
 "parallel_multiedge":{Pairs:10,Paired:8},
 "repeated_key":{Pairs:10,Paired:10},
 "late_cross_route":{Pairs:8,Paired:late},
 }
 aStrata:=map[string]measured{
 "near_collision":{Pairs:10,Paired:0},
 "wrong_role_alias":{Pairs:10,Paired:0},
 "parallel_multiedge":{Pairs:10,Paired:0},
 "repeated_key":{Pairs:10,Paired:0},
 "late_cross_route":{Pairs:8,Paired:0},
 }
 return jLane{Lane:lane,Selected:"B",BPaired:b,Controls:controls},
        iLane{Lane:lane,Arms:map[string]armReport{
         "A":{Paired:a,Weight:shasum([]byte("authentic-A-"+lane)),Strata:aStrata},
         "B":{Paired:b,Weight:shasum([]byte("authentic-B-"+lane)),Strata:strata},
        }}
}
func TestSourcePinAndNoInventedScience(t *testing.T){
 if err:=freeze(filepath.Join("..",".."));err!=nil{t.Fatal(err)}
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  j,i:=fakeLane(lane)
  v,err:=runLane(j,i);if err!=nil{t.Fatalf("%s: %v",lane,err)}
  if !v.NegativeVsBaseline||v.StrongestApproxBaseline<=v.HistoricalF124HScore{
   t.Fatalf("%s: learned history relabeled as science",lane)
  }
  if len(v.HistoricalPortfolio.Archive)!=5||len(v.Pareto.Archive)!=5{
   t.Fatalf("%s: missing a failed candidate",lane)
  }
  if len(v.Environment.Candidates)!=2||len(v.Prompt.Candidates)!=2{
   t.Fatalf("%s: generators not connected",lane)
  }
  if v.Environment.NegativeCount!=2||v.Environment.ScientificAccepted||
     v.Environment.DispatchAuthorized||v.Prompt.ScientificAccepted||
     v.Pareto.ScientificAccepted||v.HistoricalPortfolio.ScientificAccepted||
     v.ImplementedCandidatePrograms!=0||v.ProtectedInputs!=0{
   t.Fatalf("%s: untested proposals promoted",lane)
  }
  if v.Theta!="BLOCKED_NO_INDEPENDENTLY_ACCEPTED_NEW_RESULTS"||
     v.PolicySelection!="DREAM_RSI_AND_PARETO_PROSPECTIVE_SELECTION_BLOCKED"{
   t.Fatalf("%s: invented optimizer authority",lane)
  }
 }
}
func TestForgedReportsFailClosed(t *testing.T){
 dir:=t.TempDir()
 invalidJ:=filepath.Join(dir,"j.json")
 invalidI:=filepath.Join(dir,"i.json")
 if err:=os.WriteFile(invalidJ,[]byte("{}"),0600);err!=nil{t.Fatal(err)}
 if err:=os.WriteFile(invalidI,[]byte("{}"),0600);err!=nil{t.Fatal(err)}
 if _,err:=execute(filepath.Join("..",".."),invalidJ,invalidI);err==nil{
  t.Fatal("invented report admitted")
 }
 j1,i1:=fakeLane("Wingless")
 j2,i2:=fakeLane("Yggdrasil")
 j:=jReport{Schema:"forge.research.f124j.public-resource-controls-and-confirmation-preflight.v1",
  ISHA:iSHA,HTrain:"3ce0356ad9c19aeb4557ffe0b138908707c65ab3ce4b6af952adbf9899988254",
  Frozen:true,Lanes:[]jLane{j1,j2}}
 i:=iReport{Schema:"forge.research.f124i.frozen-train-mechanism-resource-audit.v1",
  CandidateSHA:"12da879272212b899c6b942004ff38dc21ffa6bb20e7a81eac21d691746b474d",
  WeightsUnchanged:true,Lanes:[]iLane{i1,i2}}
 if !validReports(j,i){t.Fatal("unit evidence shape rejected")}
 j.Lanes[0].Controls["14"]=control{Paired:44}
 if validReports(j,i){t.Fatal("incorrect baseline allowed learned promotion")}
 j.Lanes[0].Controls["14"]=control{Paired:48}
 i.Lanes[1].Arms["B"]=armReport{Paired:46,Strata:map[string]measured{}}
 if validReports(j,i){t.Fatal("missing adversarial strata accepted")}
}
