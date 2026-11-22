package nativediscovery

import (
 "encoding/json"
 "reflect"
 "testing"
)

func TestF4TrainingOnlyArchiveHasExactF3LineageAndNoAuthority(t *testing.T){
 first,err:=F4Development()
 if err!=nil{t.Fatal(err)}
 repeat,err:=F4Development()
 if err!=nil{t.Fatal(err)}
 if !reflect.DeepEqual(first,repeat){t.Fatal("F4 training archive is not deterministic")}
 generated,err:=F3Generate()
 if err!=nil{t.Fatal(err)}
 if first.Schema!=F4Schema||
  first.ParentGeneratedSourceSHA256!=generated.SourceSHA256||
  first.NativeGeneratorFrozenSHA256!=generated.GeneratorFrozenSHA256||
  first.SyntheticTrainingHistorySHA256!=generated.TrainingHistorySHA256||
  first.TrainingSeeds!=[2]uint32{17,31}||len(first.Candidates)!=3||
  !first.DevelopmentOnly||first.EvaluatedHeldout||first.SealedFirstUse||
  first.ScientificAccepted||first.GeneralRSIProven||first.OwnerActivation||
  first.DispatchAuthorized||first.AgentCalls!=0||first.PaidAPICalls!=0{
  t.Fatalf("archive lineage, train-only budget or authority drift: %+v",first)
 }
 byID:=map[string]F3SourceCandidate{}
 for _,c:=range generated.Candidates{byID[c.ID]=c}
 signatures:=map[string]string{}
 duplicates:=0
 var selected *F4ArchivedCandidate
 previous:=""
 for i:=range first.Candidates {
  row:=&first.Candidates[i]
  source,ok:=byID[row.CandidateID]
  if !ok||row.CandidateID<=previous||row.GeneratedType!=source.GeneratedType||
   row.StructuralSourceSHA256!=source.StructuralSourceSHA256{
   t.Fatalf("source identity or stable archive order corrupted: %+v",row)
  }
  previous=row.CandidateID
  signature,novelty,err:=f4Behavior(row.CandidateID)
  if err!=nil{t.Fatal(err)}
  if signature!=row.TrainingBehaviorSHA256||novelty!=row.DisagreementBits||
   novelty<0||novelty>32{t.Fatalf("behavioral signature mismatch %+v",row)}
  if prior,exists:=signatures[signature];exists{
   if row.DuplicateBehaviorOf!=prior{t.Fatalf("duplicate behavior not archived: %+v",row)}
   duplicates++
  }else{
   if row.DuplicateBehaviorOf!=""{t.Fatalf("novel behavior wrongly suppressed: %+v",row)}
   signatures[signature]=row.CandidateID
  }
  var totalGap float64
  for j,seed:=range [2]uint32{17,31}{
   trial:=row.TrainingTrials[j]
   if trial.Seed!=seed||trial.CandidateID!=row.CandidateID||
    trial.TrainExperiences!=48||trial.NewWorldProbes!=6||
    trial.InterferenceExperiences!=16||trial.ScoredDecisions!=64||
    trial.NativeColdBasePct!=trial.NativeBaseAfterPct{
    t.Fatalf("TRAIN evidence or retention budget mismatch %+v",trial)
   }
   strongest:=trial.TabularChangedPct
   if trial.FactorizedChangedPct>strongest{strongest=trial.FactorizedChangedPct}
   if trial.ExistingF2NativeChangedPct>strongest{strongest=trial.ExistingF2NativeChangedPct}
   totalGap+=(trial.NativeChangedPct-strongest)/2
  }
  if row.MeanGainOverStrongestPP!=totalGap{t.Fatalf("strongest comparator gap changed: %+v",row)}
  classification:="TRAIN_TIED_STRONGEST"
  if totalGap>0{classification="TRAIN_AHEAD_UNVERIFIED"}
  if totalGap<0{classification="TRAIN_BELOW_STRONGEST"}
  if row.TrainingClassification!=classification{t.Fatal("misclassified negative or tie")}
  if row.DuplicateBehaviorOf==""&&row.DisagreementBits>0{
   if selected==nil||row.DisagreementBits>selected.DisagreementBits||
    (row.DisagreementBits==selected.DisagreementBits&&
     row.MeanGainOverStrongestPP>selected.MeanGainOverStrongestPP){
    selected=row
   }
  }
 }
 if duplicates!=first.DuplicateBehaviorCount{t.Fatal("duplicate count mismatch")}
 if selected==nil&&first.NextProbeCandidateID!=""{t.Fatal("invented novelty suggestion")}
 if selected!=nil&&selected.CandidateID!=first.NextProbeCandidateID{
  t.Fatal("train-only novelty selection changed")
 }
 if err:=F4ValidatePreview(first);err!=nil{t.Fatal("original preview failed readback",err)}
 raw,err:=json.Marshal(first);if err!=nil{t.Fatal(err)}
 t.Logf("FORGE_EUREKA_F4_TRAINING_PREVIEW=%s",raw)
}

func TestF4TrainingArchiveRejectsAlteredRecordsAndPromotionClaims(t *testing.T){
 original,err:=F4Development();if err!=nil{t.Fatal(err)}
 clone:=func()F4Preview{
  raw,err:=json.Marshal(original);if err!=nil{t.Fatal(err)}
  var result F4Preview
  if err:=json.Unmarshal(raw,&result);err!=nil{t.Fatal(err)}
  return result
 }
 changes:=[]struct{name string;change func(*F4Preview)}{
  {"heldout seed",func(r *F4Preview){r.TrainingSeeds[1]=59}},
  {"heldout consumed",func(r *F4Preview){r.EvaluatedHeldout=true}},
  {"scientific acceptance",func(r *F4Preview){r.ScientificAccepted=true}},
  {"owner activation",func(r *F4Preview){r.OwnerActivation=true}},
  {"dispatch",func(r *F4Preview){r.DispatchAuthorized=true}},
  {"paid agent",func(r *F4Preview){r.PaidAPICalls=1;r.AgentCalls=1}},
  {"parent source drift",func(r *F4Preview){r.ParentGeneratedSourceSHA256="stale"}},
  {"structural source drift",func(r *F4Preview){r.Candidates[0].StructuralSourceSHA256="stale"}},
  {"behavior tamper",func(r *F4Preview){r.Candidates[0].TrainingBehaviorSHA256="stale"}},
  {"metric rewrite",func(r *F4Preview){r.Candidates[0].MeanGainOverStrongestPP+=1}},
  {"trial seed rewrite",func(r *F4Preview){r.Candidates[0].TrainingTrials[0].Seed=83}},
  {"trial omission",func(r *F4Preview){r.Candidates=r.Candidates[1:]}},
  {"duplicate identity",func(r *F4Preview){r.Candidates[1].CandidateID=r.Candidates[0].CandidateID}},
  {"fake winner",func(r *F4Preview){r.NextProbeCandidateID="forged"}},
 }
 for _,tc:=range changes{t.Run(tc.name,func(t *testing.T){
  modified:=clone();tc.change(&modified)
  if err:=F4ValidatePreview(modified);err==nil{t.Fatal("tampered training archive accepted")}
 })}
 if _,_,err:=f4Behavior("arbitrary");err==nil{t.Fatal("unknown executable source identity accepted")}
}
