package classification

import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/evoportfolio"
 "github.com/spoonman136668-ai/forge/researchstate"
)

func syntheticReadiness(t *testing.T,lane,outcome string)LaneReadinessInput{
 t.Helper()
 seed:=sha256.Sum256([]byte("R5 SYNTHETIC TEST SIGNER "+lane))
 signer:=ed25519.NewKeyFromSeed(seed[:])
 letter:="a";original:="b";exp:="W_TEST_PARENT_R5"
 if lane=="Yggdrasil"{letter="1";original="2";exp="Y_TEST_PARENT_R5"}
 expected:=Expected{Lane:lane,ExperimentID:exp,FrozenSHA256:strings.Repeat(letter,64),
  OriginalEvidenceSHA256:strings.Repeat(original,64),ReviewerID:"synthetic_independent_reviewer",
  TrustedKey:signer.Public().(ed25519.PublicKey)}
 a:=Attestation{Statement:Statement{Schema:Schema,Lane:lane,ExperimentID:exp,
  FrozenSHA256:expected.FrozenSHA256,OriginalEvidenceSHA256:expected.OriginalEvidenceSHA256,
  ReviewerID:expected.ReviewerID,Outcome:outcome}}
 b,_:=json.Marshal(a.Statement)
 a.SignatureHex=hex.EncodeToString(ed25519.Sign(signer,append([]byte(domain),b...)))
 h,err:=Verify(a,expected);if err!=nil{t.Fatal(err)}
 journal:=researchstate.New()
 last:=researchstate.Phase("")
 for _,phase:=range []researchstate.Phase{researchstate.Proposed,researchstate.Preregistered,
  researchstate.Qualifying,researchstate.Qualified,researchstate.Authorized,
  researchstate.Executing,researchstate.EvidenceSealed,researchstate.Classified}{
  head,_:=researchstate.Head(journal)
  event:=researchstate.Event{Lane:lane,ExperimentID:exp,
   FrozenSHA256:expected.FrozenSHA256,From:last,To:phase,
   IrreversibleRisk:phase==researchstate.Executing}
  if phase==researchstate.Qualified||phase==researchstate.Authorized||
    phase==researchstate.Executing||phase==researchstate.EvidenceSealed{
    event.EvidenceSHA256=expected.OriginalEvidenceSHA256
  }
  if phase==researchstate.Classified{event.EvidenceSHA256=h}
  journal,err=researchstate.Append(journal,event,head)
  if err!=nil{t.Fatal(err)}
  last=phase
 }
 sources:=[]string{"a","b","c","d"}; screens:=[]string{"e","f","0","9"}
 if lane=="Yggdrasil"{sources=[]string{"1","2","3","4"};screens=[]string{"5","6","7","8"}}
 candidates:=[]evoportfolio.Candidate{}
 for i:=0;i<4;i++{
  family:="a";if i>=2{family="b"}
  class:="SUPPORTED";if i==3{class="INVALID"}else if i==2{class="NEGATIVE"}
  candidates=append(candidates,evoportfolio.Candidate{ID:[]string{"alpha","beta","gamma","invalid"}[i],
   Family:family,SourceSHA:strings.Repeat(sources[i],40),ScreenSHA:strings.Repeat(screens[i],64),
   HistoricalClass:class,Score:int64(9-i),ScreenCompute:2,SealedCompute:2})
 }
 portfolio:=evoportfolio.Frozen{Schema:evoportfolio.Schema,Lane:lane,Epoch:1,
  HistoricalSourceSHA:strings.Repeat(letter,64),MaxScreenCompute:8,MaxSealedCompute:8,
  MaxFinalists:3,MaxPerFamily:2,MaxScreensPerFamily:2,Candidates:candidates}
 history:=evoportfolio.PolicyFreeze{Schema:evoportfolio.PolicyReplaySchema,Lane:lane,TrainingThrough:2}
 names:=[]string{"e1a","e1b","e2a","e2b","e3a","e3b"}
 for i,name:=range names{
  family:="a";compute:=uint64(9);class:="NEGATIVE"
  if i%2==1{family="b";compute=1;class="SUPPORTED"}
  if i==4{class="SUPPORTED"};if i==5{class="NEGATIVE"}
  history.Candidates=append(history.Candidates,evoportfolio.Observation{ID:name,
   Family:family,SourceSHA:strings.Repeat(sources[i%4],40),Class:class,Compute:compute,
   Epoch:uint64(i/2+1)})
 }
 return LaneReadinessInput{Journal:journal,Attestation:a,Expected:expected,
  Portfolio:portfolio,PortfolioSHA256:evoportfolio.Digest(portfolio),
  PolicyHistory:history,PolicyHistorySHA256:evoportfolio.ReplayPolicyDigest(history)}
}
func TestDualReadinessSuccessAndNoFSAExpansion(t *testing.T){
 w:=syntheticReadiness(t,"Wingless","NEGATIVE")
 y:=syntheticReadiness(t,"Yggdrasil","INCONCLUSIVE")
 result,err:=PlanDualReadiness(w,y);if err!=nil{t.Fatal(err)}
 if result.Schema!="forge.dual-successor-readiness.v1"||
  !result.Wingless.Eligible||!result.Yggdrasil.Eligible||
  result.Wingless.NextCandidateID!="alpha"||result.Yggdrasil.NextCandidateID!="alpha"||
  result.Wingless.SelectedTrainingPolicy!="diverse-efficiency"||
  result.Yggdrasil.SelectedTrainingPolicy!="diverse-efficiency"||
  len(result.PlanSHA256)!=64||result.ScientificExecutionAuthorized||
  result.Wingless.DispatchAuthorized||result.Yggdrasil.DispatchAuthorized||
  result.NewScientificOriginalsExecuted!=0||result.FirstUseClaimsCreated!=0||
  result.AcceptedRefMutation{t.Fatalf("R5 authority escaped: %+v",result)}
 again,err:=PlanDualReadiness(w,y);if err!=nil||again.PlanSHA256!=result.PlanSHA256{t.Fatal("R5 nondeterministic")}
 // Only holdout results change: training-selected policy MUST remain fixed.
 y.PolicyHistory.Candidates[4].Class="NEGATIVE"
 y.PolicyHistory.Candidates[5].Class="SUPPORTED"
 y.PolicyHistorySHA256=evoportfolio.ReplayPolicyDigest(y.PolicyHistory)
 holdout,err:=PlanDualReadiness(w,y)
 if err!=nil||holdout.Yggdrasil.SelectedTrainingPolicy!=result.Yggdrasil.SelectedTrainingPolicy{
  t.Fatal("holdout leaked into train-only policy")
 }
}
func TestDualReadinessInvalidParentIsolated(t *testing.T){
 w:=syntheticReadiness(t,"Wingless","INVALID")
 y:=syntheticReadiness(t,"Yggdrasil","NEGATIVE")
 result,err:=PlanDualReadiness(w,y);if err!=nil{t.Fatal(err)}
 if result.Wingless.Eligible||result.Wingless.NextCandidateID!=""||
  result.Wingless.Reason!="INVALID_REQUIRES_INDEPENDENT_PROVENANCE_REVIEW"||
  !result.Yggdrasil.Eligible||result.Yggdrasil.NextCandidateID==""{t.Fatalf("lane isolation lost: %+v",result)}
}
func TestDualReadinessRejectsTamperAndReusedSources(t *testing.T){
 w:=syntheticReadiness(t,"Wingless","NEGATIVE")
 y:=syntheticReadiness(t,"Yggdrasil","NEGATIVE")
 tampered:=w
 tampered.Attestation.SignatureHex=strings.Repeat("0",128)
 if _,err:=PlanDualReadiness(tampered,y);err==nil{t.Fatal("tampered independent review accepted")}
 altered:=y
 altered.PortfolioSHA256=strings.Repeat("0",64)
 if _,err:=PlanDualReadiness(w,altered);err==nil{t.Fatal("changed portfolio accepted")}
 altered=y
 altered.Portfolio.Candidates[0].SourceSHA=w.Portfolio.Candidates[0].SourceSHA
 altered.PortfolioSHA256=evoportfolio.Digest(altered.Portfolio)
 if _,err:=PlanDualReadiness(w,altered);err==nil{t.Fatal("cross-lane source reused")}
 altered=y
 altered.Expected.TrustedKey=w.Expected.TrustedKey
 if _,err:=PlanDualReadiness(w,altered);err==nil{t.Fatal("wrong reviewer key accepted")}
 altered=y
 altered.PolicyHistory.Candidates[0].Class="POSITIVE"
 altered.PolicyHistorySHA256=evoportfolio.ReplayPolicyDigest(altered.PolicyHistory)
 if _,err:=PlanDualReadiness(w,altered);err==nil{t.Fatal("unrecognized history outcome admitted")}
 altered=y
 altered.Journal=researchstate.New()
 if _,err:=PlanDualReadiness(w,altered);err==nil{t.Fatal("missing classified parent admitted")}
}
