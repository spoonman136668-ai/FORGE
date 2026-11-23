package infogain

// A source-bound development finding becomes a falsifiable, non-executing
// proposal. This code only processes caller-supplied observations; FORGE never
// fetches another project or claims external evidence custody or first-use.
import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "reflect"
)

const HybridFindingSchema = "forge.infogain.hybrid-observation-dev.v1"
const HybridProposalSchema = "forge.infogain.hybrid-observation-proposal-dev.v1"

type HybridFinding struct {
 Schema string `json:"schema"`
 OriginalSourceSHA string `json:"original_source_sha"`
 ReserveSourceSHA string `json:"reserve_source_sha"`
 OriginalRunID uint64 `json:"original_run_id"`
 ReserveRunID uint64 `json:"reserve_run_id"`
 CallerEvidenceSHA256 string `json:"caller_evidence_sha256"`
 MatchedWorlds int `json:"matched_worlds"`
 SignFlipWorlds int `json:"signflip_worlds"`
 UpdatesPerWorld int `json:"updates_per_world"`
 OriginalPostSwitchUpdates int `json:"original_post_switch_updates"`
 ReservePreSwitchUpdates int `json:"reserve_pre_switch_updates"`
 ReservePostSwitchUpdates int `json:"reserve_post_switch_updates"`
 ReserveDetectorSelected int `json:"reserve_detector_selected"`
 ReserveForcedUpdates int `json:"reserve_forced_updates"`
 SignFlipForcedUpdates int `json:"signflip_forced_updates"`
 SignFlipPostSwitchNonforcedSelected int `json:"signflip_post_switch_nonforced_selected"`
 RandomPostSwitchUpdates int `json:"random_post_switch_updates"`
 PeriodicPostSwitchUpdates int `json:"periodic_post_switch_updates"`
 SameObservationsAndCheckpoints bool `json:"same_observations_and_checkpoints"`
 ScientificTrainingRun bool `json:"scientific_training_run"`
}

type HybridFindingProposal struct {
 Schema string `json:"schema"`
 InputSHA256 string `json:"input_sha256"`
 CallerEvidenceSHA256 string `json:"caller_evidence_sha256"`
 Diagnostic string `json:"diagnostic"`
 ProposedExperiment string `json:"proposed_experiment"`
 MechanisticQuestion string `json:"mechanistic_question"`
 ProposedIntervention string `json:"proposed_intervention"`
 Controls []string `json:"matched_controls"`
 UpdatesPerWorld int `json:"matched_update_budget_per_world"`
 PostSwitchDifferenceVersusRandom int `json:"post_switch_update_count_vs_random"`
 PrimaryEndpoint string `json:"primary_endpoint"`
 ScientificThresholdFrozen bool `json:"scientific_threshold_frozen"`
 NewOriginalSourceAuthenticated bool `json:"new_original_source_authenticated"`
 OriginalEvidenceIndependentlyAuthenticated bool `json:"original_evidence_independently_authenticated"`
 ResearchExecuted bool `json:"research_executed"`
 ScientificAccepted bool `json:"scientific_accepted"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 DevelopmentOnly bool `json:"development_only"`
 ReceiptSHA256 string `json:"receipt_sha256"`
}

func findingDigest(domain string, value any)string{
 raw,_:=json.Marshal(value)
 sum:=sha256.Sum256(append([]byte(domain),raw...))
 return hex.EncodeToString(sum[:])
}

// SuggestHybridFinding proposes a *future* calibrated change-detection
// falsifier only where matched development evidence shows budget recovery
// without a nonforced detector hit in the changing-world cohort.
func SuggestHybridFinding(f HybridFinding)(HybridFindingProposal,error){
 var zero HybridFindingProposal
 budget:=int64(f.MatchedWorlds)*int64(f.UpdatesPerWorld)
 if f.Schema!=HybridFindingSchema||
  !validHex(f.OriginalSourceSHA,40)||!validHex(f.ReserveSourceSHA,40)||
  f.OriginalSourceSHA==f.ReserveSourceSHA||
  !validHex(f.CallerEvidenceSHA256,64)||
  f.OriginalRunID==0||f.ReserveRunID==0||
  f.OriginalRunID==f.ReserveRunID||
  f.MatchedWorlds<2||f.MatchedWorlds>256||
  f.SignFlipWorlds<1||f.SignFlipWorlds>f.MatchedWorlds||
  f.UpdatesPerWorld<1||f.UpdatesPerWorld>128||
  budget>32768||!f.SameObservationsAndCheckpoints||
  f.ScientificTrainingRun{return zero,ErrFrozen}
 counts:=[]int{f.OriginalPostSwitchUpdates,f.ReservePreSwitchUpdates,
  f.ReservePostSwitchUpdates,f.ReserveDetectorSelected,
  f.ReserveForcedUpdates,f.SignFlipForcedUpdates,
  f.SignFlipPostSwitchNonforcedSelected,
  f.RandomPostSwitchUpdates,f.PeriodicPostSwitchUpdates}
 for _,x:=range counts{if x<0||int64(x)>budget{return zero,ErrFrozen}}
 if int64(f.ReservePreSwitchUpdates)+int64(f.ReservePostSwitchUpdates)!=budget||
  int64(f.ReserveDetectorSelected)+int64(f.ReserveForcedUpdates)!=budget||
  f.SignFlipForcedUpdates>f.ReserveForcedUpdates||
  f.SignFlipForcedUpdates>f.SignFlipWorlds*f.UpdatesPerWorld||
  f.SignFlipPostSwitchNonforcedSelected>f.ReservePostSwitchUpdates||
  f.SignFlipPostSwitchNonforcedSelected>f.ReserveDetectorSelected{
  return zero,ErrFrozen
 }
 out:=HybridFindingProposal{
  Schema:HybridProposalSchema,
  InputSHA256:findingDigest("FORGE-HYBRID-DEV-FINDING-V1\n",f),
  CallerEvidenceSHA256:f.CallerEvidenceSHA256,
  Diagnostic:"DEVELOPMENT_OBSERVATION_ONLY",
  Controls:[]string{"conventional_ttt_same_information_actions_compute",
   "random_gate_same_update_budget","periodic_gate_same_update_budget",
   "surprise_gate_same_update_budget","quarter_reserve_only_ablation"},
  UpdatesPerWorld:f.UpdatesPerWorld,
  PostSwitchDifferenceVersusRandom:f.ReservePostSwitchUpdates-f.RandomPostSwitchUpdates,
  PrimaryEndpoint:"post_switch_nonforced_detection_and_subsequent_adaptation_error",
  DevelopmentOnly:true,
 }
 if f.OriginalPostSwitchUpdates==0&&f.ReservePostSwitchUpdates>0&&
  f.SignFlipForcedUpdates>0&&f.SignFlipPostSwitchNonforcedSelected==0{
  out.Diagnostic="RESERVE_WORKS_CHANGE_DETECTOR_NOT_DEMONSTRATED"
  out.ProposedExperiment="freeze_calibrated_contradiction_trigger_vs_matched_controls"
  out.MechanisticQuestion="Does a train-only calibrated contradiction trigger detect unfamiliar sign flips better than a matched random gate?"
  out.ProposedIntervention="freeze_threshold_on_training_only_observations_then_test_novel_switches_without_oracle_cues"
 }else{
  out.Diagnostic="NO_TRIGGER_SPECIFIC_PROPOSAL_FROM_THESE_OBSERVATIONS"
 }
 out.ReceiptSHA256=findingDigest("FORGE-HYBRID-DEV-PROPOSAL-V1\n",out)
 return out,nil
}

// Replay exactly from the supplied bounded finding; receipt equality never
// upgrades untrusted input to independent source or scientific authority.
func VerifyHybridFindingProposal(f HybridFinding,p HybridFindingProposal)error{
 expected,err:=SuggestHybridFinding(f)
 if err!=nil||!reflect.DeepEqual(expected,p){return ErrFrozen}
 return nil
}
