package optimizerstages

import (
 "errors"
 "fmt"
 "math"
 "strings"
 "testing"
)

func f93PlanFixture(t *testing.T)(FrozenSixPolicyTrial,FrozenSixPolicyTrial,F93MatchedPlan){
 t.Helper()
 w,y:=f89Frozen("Wingless"),f89Frozen("Yggdrasil")
 p,err:=PlanF93MatchedBlocks(w,y,strings.Repeat("1",64),
  strings.Repeat("2",64),strings.Repeat("3",64),strings.Repeat("4",64),
  10,F93MaxBlocksPerLane)
 if err!=nil{t.Fatal(err)}
 return w,y,p
}
func f93SyntheticBlocks(f FrozenSixPolicyTrial,p F93MatchedPlan,n int)[]F93MatchedBlock{
 names,policies:=f89Arms(f)
 out:=make([]F93MatchedBlock,0,n)
 for i:=0;i<n;i++{
  b:=F93MatchedBlock{
   Lane:f.Lane,BlockProtocolSHA256:p.PlanSHA256,
   BlockCaseSHA256:f93Hash("F93-SYNTHETIC-CASE",fmt.Sprintf("%s-case-%d",f.Lane,i)),
   ClaimedPositionDrawSHA256:f93Hash("F93-SYNTHETIC-DRAW",fmt.Sprintf("%s-draw-%d",f.Lane,i)),
  }
  for j:=0;j<6;j++{
   score:=int64(20)
   if j==4{score=40}
   if j==5{score=30}
   b.Cells[j]=F93Cell{
    ArmIndex:j,ArmName:names[j],PolicySHA256:policies[j],
    RandomizedPosition:(j+i)%6, // cyclic SOURCE-ONLY fixture, not real randomization
    PredecisionReceiptSHA256:f93Hash("F93-SYNTHETIC-RECEIPT",
      fmt.Sprintf("%s-block-%d-arm-%d",f.Lane,i,j)),
    OutcomeArtifactSHA256:f93Hash("F93-SYNTHETIC-OUTCOME",
      fmt.Sprintf("%s-block-%d-arm-%d",f.Lane,i,j)),
    Classification:"SUPPORTED",Score:score,ComputeUnits:int64(10+j),
   }
  }
  out=append(out,b)
 }
 return out
}
func TestF93FewerBlocksThanF91ButNoRealPowerClaim(t *testing.T){
 w,y,_:=f93PlanFixture(t)
 cases:=[]struct{target,minimum int;feasible bool}{
  {5,4615,false},{10,1154,true},{20,289,true},
 }
 for _,tc:=range cases{
  t.Run(fmt.Sprintf("target_%d",tc.target),func(t *testing.T){
   p,err:=PlanF93MatchedBlocks(w,y,strings.Repeat("1",64),
    strings.Repeat("2",64),strings.Repeat("3",64),strings.Repeat("4",64),
    tc.target,F93MaxBlocksPerLane)
   if err!=nil{t.Fatal(err)}
   if p.StrictMinimumIndependentBlocks!=tc.minimum||
    p.MathematicallyResolvesTargetWithinPlan!=tc.feasible||
    p.PlannedOriginalsPerLane!=6*F93MaxBlocksPerLane||
    p.SixArmOriginalsPerBlock!=6||
    p.ConditionalOneSidedOffsetAtPlanMaximum<6.4||
    p.ConditionalOneSidedOffsetAtPlanMaximum>6.6{
    t.Fatalf("bad matched-block precision math %+v",p)
   }
   if f93ConditionalRadius(tc.minimum)>=float64(tc.target)||
    f93ConditionalRadius(tc.minimum-1)<float64(tc.target){
    t.Fatalf("strict min not minimal for %d",tc.target)
   }
   if err:=ValidateF93MatchedPlan(w,y,p);err!=nil{t.Fatal(err)}
   if p.GenuineIndependentMatchedTasksVerified||
    p.UniformOrderRandomizationVerified||p.NoInterferenceIndependentlyVerified||
    p.TruePreOutcomeWitnessAndFirstUseVerified||
    p.AuthenticAcceptedProspectiveImprovement||
    p.DreamParetoPromotionAuthorized||p.ThetaEvolveTrainingEnabled||
    p.ScientificOriginalDispatchAuthorized||p.CloudflareMutationAuthorized{
    t.Fatalf("fake scientific authorization %+v",p)
   }
  })
 }
}
func TestF93SyntheticPositiveDoesNotEstablishPolicyGain(t *testing.T){
 w,y,p:=f93PlanFixture(t)
 result,err:=AuditF93MatchedSource(w,y,p,f93SyntheticBlocks(w,p,6),f93SyntheticBlocks(y,p,6))
 if err!=nil{t.Fatal(err)}
 if result.Status!="SYNTACTIC_MATCHED_BLOCKS_ONLY_NOT_INDEPENDENT_PROSPECTIVE_SCIENCE"||
  !result.MatchedBlockSourceClaimsWellFormed||result.PrespecifiedComparisons!=16||
  result.IndependentBlocksExternallyAuthenticated||
  result.PreOutcomeAssignmentsExternallyWitnessed||
  result.AuthenticOriginalFirstUseVerified||
  result.CompleteUnselectedPopulationVerified||
  result.AcceptedScientificCausalGain||
  result.DreamParetoPromotionAuthorized||
  result.ThetaEvolveAcceptedTrainingEnabled||
  result.ScienceDispatchAuthorized||result.AcceptedRefMutation{
  t.Fatalf("untrusted synthetic study promoted %+v",result)
 }
 for _,lane:=range result.Lanes{
  if lane.BlocksReviewed!=6||lane.MissingOutcomeCells!=0||
   !lane.SixCellsPerCompleteBlock||len(lane.ConditionalComparisons)!=8{
   t.Fatalf("lost matched block %+v",lane)
  }
  for idx,contrast:=range lane.ConditionalComparisons{
   wanted:="20"
   if idx>=4{wanted="10"}
   if contrast.ExactMeanMatchedScoreDifference!=wanted||
    contrast.ConditionalLowerAboveZero||
    !contrast.PositiveDiagnosticPointDifference||
    contrast.ConditionalOneSidedLowerScore>=0{
    t.Fatalf("diagnostic turned into proof %+v",contrast)
   }
  }
 }
}
func TestF93MissingOriginalOrIncompleteBlockBlocksComparisons(t *testing.T){
 w,y,p:=f93PlanFixture(t)
 wb,yb:=f93SyntheticBlocks(w,p,4),f93SyntheticBlocks(y,p,4)
 wb[2].Cells[4].Classification="MISSING"
 wb[2].Cells[4].Score=0;wb[2].Cells[4].ComputeUnits=0
 wb[2].Cells[4].OutcomeArtifactSHA256=""
 got,err:=AuditF93MatchedSource(w,y,p,wb,yb)
 if err!=nil{t.Fatal(err)}
 if got.Lanes[0].MissingOutcomeCells!=1||
  len(got.Lanes[0].ConditionalComparisons)!=0||
  len(got.Lanes[1].ConditionalComparisons)!=8||
  got.DreamParetoPromotionAuthorized||got.ThetaEvolveAcceptedTrainingEnabled{
  t.Fatalf("missing treated as positive data %+v",got)
 }
 wb[2].Cells[4].Score=50
 if _,err:=AuditF93MatchedSource(w,y,p,wb,yb);!errors.Is(err,ErrF93){
  t.Fatalf("missing with value admitted: %v",err)
 }
}
func TestF93TamperedBlocksFailClosed(t *testing.T){
 w,y,p:=f93PlanFixture(t)
 mutations:=map[string]func([]F93MatchedBlock){
  "duplicate arm":func(b []F93MatchedBlock){b[0].Cells[1].ArmIndex=b[0].Cells[0].ArmIndex},
  "duplicate position":func(b []F93MatchedBlock){b[0].Cells[1].RandomizedPosition=b[0].Cells[0].RandomizedPosition},
  "wrong policy":func(b []F93MatchedBlock){b[0].Cells[1].PolicySHA256=b[0].Cells[0].PolicySHA256},
  "falsified case":func(b []F93MatchedBlock){b[0].BlockCaseSHA256="garbage"},
  "wrong prereg protocol":func(b []F93MatchedBlock){b[0].BlockProtocolSHA256=strings.Repeat("f",64)},
  "duplicate block case":func(b []F93MatchedBlock){b[1].BlockCaseSHA256=b[0].BlockCaseSHA256},
  "duplicate order digest":func(b []F93MatchedBlock){b[1].ClaimedPositionDrawSHA256=b[0].ClaimedPositionDrawSHA256},
  "reused firstuse receipt":func(b []F93MatchedBlock){b[1].Cells[0].PredecisionReceiptSHA256=b[0].Cells[0].PredecisionReceiptSHA256},
  "reused outcome":func(b []F93MatchedBlock){b[1].Cells[0].OutcomeArtifactSHA256=b[0].Cells[0].OutcomeArtifactSHA256},
  "invalid score":func(b []F93MatchedBlock){b[0].Cells[0].Score=101},
  "zero compute":func(b []F93MatchedBlock){b[0].Cells[0].ComputeUnits=0},
  "forgotten classification":func(b []F93MatchedBlock){b[0].Cells[0].Classification=""},
 }
 for name,mutate:=range mutations{
  t.Run(name,func(t *testing.T){
   wb,yb:=f93SyntheticBlocks(w,p,2),f93SyntheticBlocks(y,p,2)
   mutate(wb)
   if _,err:=AuditF93MatchedSource(w,y,p,wb,yb);!errors.Is(err,ErrF93){
    t.Fatalf("malformed non-independent cells admitted %s: %v",name,err)
   }
  })
 }
}
func TestF93NoPosthocPlanRehashOrCrossLaneReuse(t *testing.T){
 w,y,p:=f93PlanFixture(t)
 edits:=map[string]func(*F93MatchedPlan){
  "alpha":func(a *F93MatchedPlan){a.MathematicallyResolvesTargetWithinPlan=false},
  "max":func(a *F93MatchedPlan){a.PlannedMaximumBlocksPerLane=200},
  "protocol":func(a *F93MatchedPlan){a.PositionRandomizationProtocolSHA256=strings.Repeat("e",64)},
  "false gain":func(a *F93MatchedPlan){a.AuthenticAcceptedProspectiveImprovement=true},
  "false original":func(a *F93MatchedPlan){a.ScientificOriginalDispatchAuthorized=true},
  "false theta":func(a *F93MatchedPlan){a.ThetaEvolveTrainingEnabled=true},
  "false cloudflare":func(a *F93MatchedPlan){a.CloudflareMutationAuthorized=true},
 }
 for name,edit:=range edits{
  t.Run(name,func(t *testing.T){
   q:=p;edit(&q)
   q.PlanSHA256=f93PlanHash(q)
   if err:=ValidateF93MatchedPlan(w,y,q);!errors.Is(err,ErrF93){
    t.Fatalf("rehash of changed plan admitted %v",err)
   }
  })
 }
 changed:=y;changed.Epoch=2
 if err:=ValidateF93MatchedPlan(w,changed,p);!errors.Is(err,ErrF93){
  t.Fatal("source freeze drift admitted")
 }
 wb,yb:=f93SyntheticBlocks(w,p,1),f93SyntheticBlocks(y,p,1)
 yb[0].BlockCaseSHA256=wb[0].BlockCaseSHA256
 if _,err:=AuditF93MatchedSource(w,y,p,wb,yb);!errors.Is(err,ErrF93){
  t.Fatal("cross-lane reused matched task admitted")
 }
}
func TestF93NoImpliedPrecisionFromTinyBlocks(t *testing.T){
 w,y,_:=f93PlanFixture(t)
 p,err:=PlanF93MatchedBlocks(w,y,strings.Repeat("1",64),
  strings.Repeat("2",64),strings.Repeat("3",64),strings.Repeat("4",64),10,6)
 if err!=nil{t.Fatal(err)}
 if p.MathematicallyResolvesTargetWithinPlan||p.ConditionalOneSidedOffsetAtPlanMaximum<100||
  math.IsNaN(p.ConditionalOneSidedOffsetAtPlanMaximum){t.Fatalf("false precision %+v",p)}
}
