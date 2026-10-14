package classification

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"

 "github.com/spoonman136668-ai/forge/evoportfolio"
 "github.com/spoonman136668-ai/forge/researchstate"
)

// LaneReadinessInput binds independent classification to one frozen candidate
// portfolio. Inputs must arrive from existing qualified authority/custody.
// No synthetic fixture or CI conclusion can supply a trusted Expected key.
type LaneReadinessInput struct {
 Journal researchstate.Journal
 Attestation Attestation
 Expected Expected
 Portfolio evoportfolio.Frozen
 PortfolioSHA256 string
 PolicyHistory evoportfolio.PolicyFreeze
 PolicyHistorySHA256 string
}

type LaneReadiness struct {
 Lane string `json:"lane"`
 ParentExperimentID string `json:"parent_experiment_id"`
 ParentClassificationSHA256 string `json:"parent_classification_sha256"`
 ParentOutcome string `json:"parent_outcome"`
 Eligible bool `json:"eligible"`
 Reason string `json:"reason"`
 SelectedTrainingPolicy string `json:"selected_training_policy,omitempty"`
 PortfolioDecisionSHA256 string `json:"portfolio_decision_sha256,omitempty"`
 NextCandidateID string `json:"next_candidate_id,omitempty"`
 NextCandidateSourceSHA string `json:"next_candidate_source_sha,omitempty"`
 ScreenComputeSpent int64 `json:"screen_compute_spent,omitempty"`
 SealedComputeReserved int64 `json:"sealed_compute_reserved,omitempty"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 ScientificAccepted bool `json:"scientific_accepted"`
}

type DualReadiness struct {
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Wingless LaneReadiness `json:"wingless"`
 Yggdrasil LaneReadiness `json:"yggdrasil"`
 PlanSHA256 string `json:"plan_sha256"`
 NewScientificOriginalsExecuted int `json:"new_scientific_originals_executed"`
 FirstUseClaimsCreated int `json:"first_use_claims_created"`
 ScientificExecutionAuthorized bool `json:"scientific_execution_authorized"`
 AcceptedRefMutation bool `json:"accepted_ref_mutation"`
}

var ErrReadiness = errors.New("FORGE_DUAL_SUCCESSOR_READINESS_BLOCKED")

func planLane(in LaneReadinessInput,expectedLane string)(LaneReadiness,error){
 var empty LaneReadiness
 if in.Expected.Lane!=expectedLane||in.Attestation.Statement.Lane!=expectedLane||
  in.Portfolio.Lane!=expectedLane||in.PolicyHistory.Lane!=expectedLane{
  return empty,ErrReadiness
 }
 assessment,err:=AssessSuccessor(in.Journal,in.Attestation,in.Expected)
 if err!=nil{return empty,ErrReadiness}
 result:=LaneReadiness{Lane:expectedLane,ParentExperimentID:assessment.ParentExperimentID,
  ParentClassificationSHA256:assessment.ParentClassificationSHA256,
  ParentOutcome:in.Attestation.Statement.Outcome,Eligible:assessment.Eligible,Reason:assessment.Reason}
 // Even invalid/inconclusive parents preserve exact portfolio source identity.
 // INVALID is ineligible; INCONCLUSIVE can propose a new diagnostic, never dispatch.
 selected,err:=evoportfolio.PlanAfterReplay(in.PolicyHistory,in.PolicyHistorySHA256,
  in.Portfolio,in.PortfolioSHA256)
 if err!=nil||selected.DispatchAuthorized||selected.Portfolio.DispatchAuthorized||
  selected.Next.DispatchAuthorized||selected.Portfolio.ScientificAccepted||
  selected.Policy.AcceptedRefMutation||selected.Policy.DispatchAuthorized{return empty,ErrReadiness}
 if !assessment.Eligible{return result,nil}
 if selected.Next.Exhausted||selected.Next.NextID==""{
  result.Eligible=false
  result.Reason="PORTFOLIO_EXHAUSTED_REQUIRES_NEW_FROZEN_CANDIDATES"
  return result,nil
 }
 found:=false
 for _,c:=range in.Portfolio.Candidates{
  if c.ID!=selected.Next.NextID{continue}
  if found{return empty,ErrReadiness}
  found=true
  result.NextCandidateID=c.ID
  result.NextCandidateSourceSHA=c.SourceSHA
  result.SealedComputeReserved=c.SealedCompute
 }
 if !found{return empty,ErrReadiness}
 result.SelectedTrainingPolicy=selected.Policy.SelectedPolicy
 result.PortfolioDecisionSHA256=selected.Portfolio.DecisionSHA256
 decision,err:=evoportfolio.Select(in.Portfolio,in.PortfolioSHA256)
 if err!=nil||decision.DispatchAuthorized||decision.ScientificAccepted||
  decision.AcceptedRefMutation{return empty,ErrReadiness}
 result.ScreenComputeSpent=decision.ScreenComputeSpent
 return result,nil
}

// PlanDualReadiness is a pure, deterministic adapter over the EXISTING
// signed-classification gate and portfolio replay. It has no worker, transport,
// scheduler, authority or first-use mutation.
func PlanDualReadiness(w,y LaneReadinessInput)(DualReadiness,error){
 var empty DualReadiness
 sourceSeen:=map[string]bool{}
 parentSeen:=map[string]bool{}
 for _,input:=range []LaneReadinessInput{w,y}{
  key:=input.Expected.Lane+":"+input.Expected.ExperimentID
  if parentSeen[key]{return empty,ErrReadiness}
  parentSeen[key]=true
  for _,c:=range input.Portfolio.Candidates{
   if sourceSeen[c.SourceSHA]{return empty,ErrReadiness}
   sourceSeen[c.SourceSHA]=true
  }
 }
 wingless,err:=planLane(w,"Wingless")
 if err!=nil{return empty,err}
 yggdrasil,err:=planLane(y,"Yggdrasil")
 if err!=nil{return empty,err}
 if wingless.Eligible&&yggdrasil.Eligible&&
  wingless.NextCandidateSourceSHA==yggdrasil.NextCandidateSourceSHA{return empty,ErrReadiness}
 result:=DualReadiness{Schema:"forge.dual-successor-readiness.v1",
  Mode:"INDEPENDENT_SIGNED_PARENT_AND_TRAIN_ONLY_PORTFOLIO_PROPOSALS_NOT_DISPATCH",
  Wingless:wingless,Yggdrasil:yggdrasil}
 bytes,err:=json.Marshal(result)
 if err!=nil{return empty,ErrReadiness}
 digest:=sha256.Sum256(bytes)
 result.PlanSHA256=hex.EncodeToString(digest[:])
 return result,nil
}
