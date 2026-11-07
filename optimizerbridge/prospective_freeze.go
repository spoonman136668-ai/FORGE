package optimizerbridge

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
)

var ErrProspectiveFreeze=errors.New("FORGE_DREAM_PARETO_PROSPECTIVE_FREEZE_INCOMPLETE")
type ProspectiveFreeze struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 SourceCommitSHA string `json:"source_commit_sha"`
 DreamPolicySHA256 string `json:"dream_policy_sha256"`
 FrozenControlSHA256 string `json:"frozen_control_sha256"`
 ParetoPoolSHA256 string `json:"pareto_pool_sha256"`
 EligibilityAndExclusionSHA256 string `json:"eligibility_and_exclusion_sha256"`
 OutcomeMetricSHA256 string `json:"outcome_metric_sha256"`
 RandomizationProtocolSHA256 string `json:"randomization_protocol_sha256"`
 ComputeBudget int64 `json:"compute_budget"`
 ExperimentCount int `json:"experiment_count"`
 HoldoutSealed bool `json:"holdout_sealed"`
}
type ProspectiveRecord struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 PreregisteredSHA256 string `json:"preregistered_sha256"`
 Status string `json:"status"`
 OriginalsExecuted int `json:"originals_executed"`
 ScientificImprovementEstablished bool `json:"scientific_improvement_established"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
}
func FreezeProspective(plan PriorityPlan,p ProspectiveFreeze)(ProspectiveRecord,error){
 if plan.Schema!="forge.optimizer.priority-plan.v1"||
  plan.Phase!="DREAM_PARETO_FROZEN_CONTROL_PROSPECTIVE_PREREGISTRATION"||
  !plan.FrozenControlsRequired||!plan.ProspectiveRandomizationRequired||
  !plan.IndependentOutcomeReviewRequired||plan.ExperimentDispatchAuthorized||
  p.Schema!="forge.optimizer.prospective-freeze.v1"||
  !checkLane(p.Lane)||p.Lane!=plan.Lane||
  p.DreamPolicySHA256!=plan.DreamPolicySHA256||
  !digestOK(p.SourceCommitSHA,40)||!digestOK(p.FrozenControlSHA256,64)||
  !digestOK(p.ParetoPoolSHA256,64)||!digestOK(p.EligibilityAndExclusionSHA256,64)||
  !digestOK(p.OutcomeMetricSHA256,64)||!digestOK(p.RandomizationProtocolSHA256,64)||
  p.ComputeBudget<=0||p.ExperimentCount<2||p.ExperimentCount>20||!p.HoldoutSealed {
  return ProspectiveRecord{},ErrProspectiveFreeze
 }
 b,err:=json.Marshal(p)
 if err!=nil{return ProspectiveRecord{},ErrProspectiveFreeze}
 h:=sha256.Sum256(append([]byte("FORGE-DREAM-PARETO-PREREG-V1\x00"),b...))
 return ProspectiveRecord{Schema:"forge.optimizer.prospective-record.v1",Lane:p.Lane,
  PreregisteredSHA256:hex.EncodeToString(h[:]),
  Status:"FROZEN_PROSPECTIVE_PLAN_NOT_EXECUTED"},nil
}
