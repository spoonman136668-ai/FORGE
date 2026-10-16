package optimizerbridge

// F60 connects the pre-existing signature-verified Cloudflare export and
// two independently signed research-assignment claim audits to the frozen
// F58 policy IDs. It is intentionally historical and non-authorizing.
// Authenticated historical observations are not externally accepted new
// challenger policies, real random assignment, or prospective science.
import "errors"

const F60ObservationSchema="forge.optimizer.f60.signed-history-challenger-observation.v1"
var ErrF60=errors.New("FORGE_F60_REAL_SIGNED_OWNER_EVIDENCE_REQUIRED")

type F60LaneObservation struct{
 Lane string `json:"lane"`
 FrozenBaselinePolicySHA256 []string `json:"frozen_baseline_policy_sha256"`
 HistoricalDreamPolicySHA256 string `json:"historical_dream_policy_sha256"`
 HistoricalParetoFreezeSHA256 string `json:"historical_pareto_freeze_sha256"`
 SignedTrainingHistorySHA256 string `json:"signed_training_history_sha256"`
 SignedValidationHistorySHA256 string `json:"signed_validation_history_sha256"`
 SignedAssignmentClaimCount int `json:"signed_assignment_claim_count"`
 DistinctDreamPolicyFromFrozenControls bool `json:"distinct_dream_policy_from_frozen_controls"`
 OwnerApprovedProspectiveChallengers bool `json:"owner_approved_prospective_challengers"`
 ActualPredecisionRandomizationProven bool `json:"actual_predecision_randomization_proven"`
 FirstNewProspectiveSelectionExecuted bool `json:"first_new_prospective_selection_executed"`
 IndependentlyAcceptedResearchOutcome bool `json:"independently_accepted_research_outcome"`
}
type F60ShadowCandidateObservation struct{
 Schema string `json:"schema"`
 FrozenControlRegistrySHA256 string `json:"frozen_control_registry_sha256"`
 OriginalExternalExportManifestSHA256 string `json:"original_external_export_manifest_sha256"`
 PinnedSourceAndSignerClaimConsistent bool `json:"pinned_source_and_signer_claim_consistent"`
 Lanes []F60LaneObservation `json:"lanes"`
 IndependentlyProvenRandomizedResearchSelections int `json:"independently_proven_randomized_research_selections"`
 ProspectivelyQualifiedOwnerPolicies int `json:"prospectively_qualified_owner_policies"`
 AcceptedScientificOriginals int `json:"accepted_scientific_originals"`
 DreamParetoLiveActivationAuthorized bool `json:"dream_pareto_live_activation_authorized"`
 ThetaEvolveWeightUpdatesAuthorized bool `json:"theta_evolve_weight_updates_authorized"`
 ControllerCutoverOrScientificDispatchAuthorized bool `json:"controller_cutover_or_scientific_dispatch_authorized"`
 Status string `json:"status"`
}

// previewF60Review refuses any attempt to cast signature consistency or
// historical scores as the independent prospective owner gate. Source tests
// may exercise this helper but MUST NOT publish test claims as real science.
func previewF60Review(f F58Freeze,pins []LanePins,verified ExportReview)(F60ShadowCandidateObservation,error){
 var empty F60ShadowCandidateObservation
 frozen,err:=ReadinessF58(f)
 if err!=nil{return empty,ErrF60}
 if len(pins)!=2||verified.Schema!="forge.optimizer.cloud-export-review.v1"||
  verified.Mode!="EXTERNAL_EXPORT_AND_SIGNED_ASSIGNMENT_CLAIMS_SHADOW_ONLY"||
  !verified.SourceDigestAndCustodySignatureVerified||
  !f59Hex(verified.ManifestSHA256,64)||
  len(verified.Shadow.Lanes)!=2||len(verified.SelectionAudits)!=2||
  verified.Shadow.ScientificAccepted||verified.Shadow.DispatchAuthorized||
  verified.Shadow.ScientificImprovementEstablished||
  verified.Shadow.ScienceOriginalsExecuted!=0||verified.Shadow.FirstUseConsumed{
  return empty,ErrF60
 }
 out:=F60ShadowCandidateObservation{
  Schema:F60ObservationSchema,
  FrozenControlRegistrySHA256:frozen.FrozenControlRegistrySHA256,
  OriginalExternalExportManifestSHA256:verified.ManifestSHA256,
  PinnedSourceAndSignerClaimConsistent:true,
  Status:"REAL_SIGNED_HISTORICAL_SHADOW_NOT_INDEPENDENT_PROSPECTIVE_OWNER_CUSTODY",
 }
 for i,lane:=range verified.Shadow.Lanes{
  expected:=f.Lanes[i]
  audit:=verified.SelectionAudits[i]
  pin:=pins[i]
  if lane.Lane!=expected.Lane||pin.Lane!=expected.Lane||audit.Lane!=expected.Lane||
   !audit.SignedClaimsConsistent||audit.EntriesCrossChecked<1||
   audit.ActualRandomizationIndependentlyDemonstrated||
   audit.ProspectiveScienceAuthorized||audit.ScientificImprovementEstablished||
   !f59Hex(lane.DreamPolicySHA256,64)||!f59Hex(pin.ParetoPolicySHA256,64)||
   !f59Hex(pin.DreamTrainSHA256,64)||!f59Hex(pin.DreamValidationSHA256,64)||
   pin.DreamTrainSHA256==pin.DreamValidationSHA256||
   lane.DreamTrainingSHA256!=pin.DreamTrainSHA256||
   lane.DreamValidationSHA256!=pin.DreamValidationSHA256||
   lane.CapabilityModes["dream_rsi"]!="SIGNED_HISTORICAL_REPLAY_NOT_PROSPECTIVE_GAIN"||
   lane.CapabilityModes["shinka_pareto"]!="HISTORICAL_DIVERSITY_ADVISORY"||
   !lane.DreamProspectiveComparisonEligible {
   return empty,ErrF60
  }
  item:=F60LaneObservation{
   Lane:lane.Lane,HistoricalDreamPolicySHA256:lane.DreamPolicySHA256,
   HistoricalParetoFreezeSHA256:pin.ParetoPolicySHA256,
   SignedTrainingHistorySHA256:pin.DreamTrainSHA256,
   SignedValidationHistorySHA256:pin.DreamValidationSHA256,
   SignedAssignmentClaimCount:audit.EntriesCrossChecked,
  }
  distinct:=true
  for _,base:=range expected.Controls{
   item.FrozenBaselinePolicySHA256=append(item.FrozenBaselinePolicySHA256,base.SHA256)
   if lane.DreamPolicySHA256==base.SHA256{distinct=false}
  }
  item.DistinctDreamPolicyFromFrozenControls=distinct
  out.Lanes=append(out.Lanes,item)
 }
 if out.Lanes[0].HistoricalDreamPolicySHA256==out.Lanes[1].HistoricalDreamPolicySHA256||
  out.Lanes[0].HistoricalParetoFreezeSHA256==out.Lanes[1].HistoricalParetoFreezeSHA256||
  out.Lanes[0].SignedTrainingHistorySHA256==out.Lanes[1].SignedTrainingHistorySHA256||
  out.Lanes[0].SignedValidationHistorySHA256==out.Lanes[1].SignedValidationHistorySHA256{
  return empty,ErrF60
 }
 return out,nil
}

// ObserveF60FromSignedExport is the single real-input entrypoint. Every
// signature and original export object must verify under existing *separately
// provided* trust pins before any shadow nominee can be observed.
func ObserveF60FromSignedExport(f F58Freeze,signed SignedExport,trust ExternalTrust,
 raw [2][]byte,pins []LanePins,audits [2]SignedSelectionAudit,auditPins [2]SelectionAuditPin,
)(F60ShadowCandidateObservation,error){
 var empty F60ShadowCandidateObservation
 verified,err:=EvaluatePinnedExportWithAudits(signed,trust,raw,pins,audits,auditPins)
 if err!=nil{return empty,ErrF60}
 out,err:=previewF60Review(f,pins,verified)
 if err!=nil{return empty,ErrF60}
 return out,nil
}
