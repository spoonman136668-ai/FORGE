// Package f4preflight is a narrow read-only adapter to FORGE's existing
// eligibility ledger. It cannot mint an independently authenticated snapshot,
// verify remote custody, assert per-seed non-reuse or authorize science.
package f4preflight

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "os"

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

// ReportCurrent remains blocked even after a structurally valid snapshot,
// because prospective F4 source SHA and per-seed first-use are not qualified.
func ReportCurrent(protocol []byte,snapshotBytes []byte,pin string,generation uint64,
 complete bool,candidate eligibility.Frozen)(Report,error){
 if _,err:=LoadProtocol(protocol);err!=nil{
  return base("F4_PROPOSAL_IDENTITY_OR_SOURCE_GATE_INVALID"),ErrBlocked
 }
 assessment,err:=ExamineLedger(snapshotBytes,pin,generation,complete,candidate)
 if err!=nil{return assessment,err}
 assessment.Status="BLOCKED_F4_SOURCE_NOT_FROZEN_INDIVIDUAL_SEED_PROOF_MISSING"
 assessment.Reason="Only structural cohort-hash verification is established; independently prove ledger origin, seed-level completeness, and frozen source before any first use."
 return assessment,ErrBlocked
}

// ReadOnlyCLI writes the refusal reason only; it never consumes or mutates a
// ledger or launches a worker. Optional external data must be independently
// pinned; it is never rehashed locally to manufacture a matching 'witness'.
func ReadOnlyCLI(protocolPath,ledgerPath,pin string,generation uint64)Report{
 raw,err:=os.ReadFile(protocolPath)
 if err!=nil{return base("PROTOCOL_UNAVAILABLE")}
 if _,err=LoadProtocol(raw);err!=nil{return base("PROTOCOL_NOT_QUALIFIED")}
 if ledgerPath==""||pin==""||generation==0{return base("AUTHENTICATED_ALL_LANE_LEDGER_NOT_SUPPLIED")}
 ledger,err:=os.ReadFile(ledgerPath)
 if err!=nil{return base("LEDGER_UNAVAILABLE")}
 // Frozen source is not yet specified, so it would be unsafe to invent a
 // candidate Frozen fingerprint to inspect a purported complete ledger.
 _=ledger
 return base("F4_FROZEN_IDENTITY_AND_PINNED_SEED_INDEX_NOT_QUALIFIED")
}

// Verify external marker syntax only, never provenance.
func PinShape(pin string)bool{
 if len(pin)!=64{return false}
 _,err:=hex.DecodeString(pin)
 if err!=nil{return false}
 return pin==fmt.Sprintf("%x",mustDecode(pin))
}
func mustDecode(pin string)[]byte{out,_:=hex.DecodeString(pin);return out}
var _=sha256.Size
