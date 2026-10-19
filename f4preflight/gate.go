// Package f4preflight is a narrow read-only adapter to FORGE's existing
// eligibility ledger. It cannot mint an independently authenticated snapshot,
// verify remote custody, assert per-seed non-reuse or authorize science.
package f4preflight

import (
 "encoding/json"
 "errors"
 "strconv"

 "github.com/spoonman136668-ai/forge/eligibility"
)

var ErrBlocked=errors.New("F4_FIRSTUSE_NOT_AUTHENTICATED_OR_SOURCE_UNFROZEN")
const ProposalStatus="PROPOSED_NOT_FROZEN_NO_SCIENTIFIC_AUTHORITY"
const TargetID="Y-FORGE-F4-SENSOR-SET-REALLOCATION-01"

// Proposal is intentionally narrow. Unknown fields in the prospective
// protocol are left to the separate frozen F4 protocol tests.
type Proposal struct {
 Status string `json:"status"`
 PlannedOriginalID string `json:"planned_original_id"`
 SourceRequirements struct {
  ImplementationSourceSHA string `json:"implementation_source_sha"`
 } `json:"source_requirements"`
 ProposedCohorts struct {
  DevelopmentSeeds []int `json:"development_seeds"`
  SealedCandidateSeeds []int `json:"sealed_candidate_seeds"`
  SeedFirstUseStatus string `json:"seed_first_use_status"`
 } `json:"proposed_cohorts"`
}

// Report is a descriptive preflight, never an admission/dispatch token.
type Report struct {
 Schema string `json:"schema"`
 Status string `json:"status"`
 LedgerSnapshotVerified bool `json:"ledger_snapshot_verified"`
 FrozenSourceVerified bool `json:"frozen_source_verified"`
 IndividualSeedFirstUseVerified bool `json:"individual_seed_first_use_verified"`
 ScientificDispatchAuthorized bool `json:"scientific_dispatch_authorized"`
 FirstUseClaimsCreated int `json:"first_use_claims_created"`
 Reason string `json:"reason"`
}

func base(reason string)Report{
 return Report{Schema:"forge.f4.firstuse.readonly-preflight.v1",
  Status:"BLOCKED",Reason:reason}
}

func LoadProtocol(raw []byte)(Proposal,error){
 var p Proposal
 if err:=json.Unmarshal(raw,&p);err!=nil{return p,ErrBlocked}
 if p.Status!=ProposalStatus||p.PlannedOriginalID!=TargetID||
  p.SourceRequirements.ImplementationSourceSHA!="UNRESOLVED_REQUIRED_BEFORE_FREEZE"||
  p.ProposedCohorts.SeedFirstUseStatus!="UNVERIFIED_MUST_INDEPENDENTLY_PROVE_UNUSED_BEFORE_CLAIM"{
  return p,ErrBlocked
 }
 dev,sealed:=p.ProposedCohorts.DevelopmentSeeds,p.ProposedCohorts.SealedCandidateSeeds
 if len(dev)!=8||len(sealed)!=16{return p,ErrBlocked}
 used:=map[int]bool{}
 for _,id:=range append(append([]int{},dev...),sealed...) {
  if id<=0||used[id] {return p,ErrBlocked}
  used[id]=true
 }
 return p,nil
}

// ExamineLedger tests supplied bytes against an OUTSIDE, independently
// authenticated SHA256 pin and generation. Digest matching alone cannot
// authenticate the purported external authority, and a cohort-hash ledger
// cannot prove that individual seed IDs are unique across different cohorts.
func ExamineLedger(
 snapshotBytes []byte,pin string,generation uint64,complete bool,
 candidate eligibility.Frozen,
)(Report,error){
 if len(snapshotBytes)==0||pin==""||generation==0||!complete{
  return base("MISSING_COMPLETE_EXTERNALLY_PINNED_ALL_LANE_LEDGER"),ErrBlocked
 }
 if len(snapshotBytes)>1<<20 {
  return base("LEDGER_TOO_LARGE"),ErrBlocked
 }
 // Do not derive pin from the ledger supplied by the candidate worker.
 var snapshot eligibility.LedgerSnapshot
 if err:=json.Unmarshal(snapshotBytes,&snapshot);err!=nil{
  return base("LEDGER_JSON_INVALID"),ErrBlocked
 }
 if err:=eligibility.VerifyLedger(candidate,snapshot,pin,generation,complete);err!=nil{
  return base("LEDGER_IDENTITY_COLLISION_OR_START_NOT_RECONCILED"),ErrBlocked
 }
 return Report{Schema:"forge.f4.firstuse.readonly-preflight.v1",
  Status:"COHORT_HASH_PRECHECK_ONLY_SEED_AND_SOURCE_FIDELITY_PENDING",
  LedgerSnapshotVerified:true,Reason:"Ledger hash and cohort collision check passed structurally, but external pin provenance, individual seed-index coverage and source freeze remain separately unverified."},nil
}

func fmtSeed(seed int) string{return "Yggdrasil:"+strconv.Itoa(seed)}

// ReportCurrent remains blocked even after a structurally valid snapshot,
// because prospective F4 source SHA and per-seed first-use are not qualified.
func ReportCurrent(protocol []byte,snapshotBytes []byte,pin string,generation uint64,
 complete bool,candidate eligibility.Frozen)(Report,error){
 proposal,err:=LoadProtocol(protocol)
 if err!=nil{
  return base("F4_PROPOSAL_IDENTITY_OR_SOURCE_GATE_INVALID"),ErrBlocked
 }
 if candidate.Lane!="Yggdrasil"||candidate.CandidateID!=proposal.PlannedOriginalID||
  len(candidate.SeedIDs)!=len(proposal.ProposedCohorts.SealedCandidateSeeds){
  return base("F4_FROZEN_COHORT_CONTRACT_MISSING_OR_DRIFT"),ErrBlocked
 }
 for i,seed:=range proposal.ProposedCohorts.SealedCandidateSeeds {
  if candidate.SeedIDs[i]!=fmtSeed(seed) {
   return base("F4_FROZEN_COHORT_CONTRACT_MISSING_OR_DRIFT"),ErrBlocked
  }
 }
 assessment,err:=ExamineLedger(snapshotBytes,pin,generation,complete,candidate)
 if err!=nil{return assessment,err}
 assessment.Status="BLOCKED_F4_SOURCE_NOT_FROZEN_INDIVIDUAL_SEED_PROOF_MISSING"
 assessment.Reason="Only structural cohort-hash verification is established; independently prove ledger origin, seed-level completeness, and frozen source before any first use."
 return assessment,ErrBlocked
}

