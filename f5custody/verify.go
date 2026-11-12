// Package f5custody is a read-only F5 seed-custody verifier using the
// existing FORGE eligibility ledger and a separately pinned custodian key.
// It never issues science authorization, an original grant, or a start token.
package f5custody

import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "slices"
 "strings"

 "github.com/spoonman136668-ai/forge/eligibility"
)

const Schema="forge.f5.signed-all-lane-seed-custody.v1"
var ErrBlocked=errors.New("F5_FIRST_USE_AUTHENTICATED_CUSTODY_NOT_QUALIFIED")

// Attestation is an externally maintained and independently signed COMPLETE
// all-lane seed index. A mere GitHub Actions success or repository scan cannot
// produce it. The signer must be independent of the F5 worker and candidate.
type Attestation struct {
 Schema string `json:"schema"`
 Scope string `json:"scope"`
 Coverage string `json:"coverage"`
 Revision uint64 `json:"revision"`
 Ledger eligibility.LedgerSnapshot `json:"ledger"`
 ConsumedSeedIDs []string `json:"consumed_seed_ids"`
 ActiveSeedIDs []string `json:"active_seed_ids"`
 UncertainSeedIDs []string `json:"uncertain_seed_ids"`
 LaneHighWater map[string]uint64 `json:"lane_high_water"`
}
type Signed struct {
 Attestation Attestation `json:"attestation"`
 SignatureHex string `json:"signature_hex"`
}
type Pins struct {
 // Separately authenticated out-of-band; NEVER taken from Signed.
 CustodianPublicKeyHex string
 MinRevision uint64
 ExpectedLedgerGeneration uint64
 LedgerSHA256 string
 // Independently pinned lane source high-water floors, never taken from
 // the candidate or the purported signed snapshot itself.
 WinglessMinHighWater uint64
 YggdrasilMinHighWater uint64
}
type Report struct {
 Schema string `json:"schema"`
 Disposition string `json:"disposition"`
 AuthenticatedSnapshot bool `json:"authenticated_snapshot"`
 CompleteAllLaneSeedIndex bool `json:"complete_all_lane_seed_index"`
 IndividualCandidateSeedsAbsentFromUse bool `json:"individual_candidate_seeds_absent_from_use"`
 SourceFrozen bool `json:"source_frozen"`
 OriginalStartAuthorized bool `json:"original_start_authorized"`
 FirstUseClaims int `json:"first_use_claims"`
 Reason string `json:"reason"`
}
func deny(reason string)(Report,error){
 return Report{Schema:"forge.f5.custody-preflight-report.v1",Disposition:"BLOCKED",
  Reason:reason},ErrBlocked
}
func canonicalUniqueSeedIDs(ids []string) bool {
 if ids==nil{return false}
 if !slices.IsSorted(ids){return false}
 for i,id:=range ids {
  if len(id)<3 || len(id)>128{return false}
  if i>0 && ids[i-1]==id{return false}
  found:=false
  for _,p:=range []string{"Wingless:","Yggdrasil:"}{
   if len(id)>len(p)&&id[:len(p)]==p{found=true;break}
  }
  if !found{return false}
 }
 return true
}

func validCandidate(candidate eligibility.Frozen) bool {
 if candidate.Schema!=eligibility.Schema ||
  candidate.Lane!="Yggdrasil" ||
  !strings.HasPrefix(candidate.CandidateID,"Y-FORGE-F5-") ||
  len(candidate.SourceSHA)!=40 ||
  len(candidate.PreregSHA256)!=64 ||
  len(candidate.CohortSHA256)!=64 ||
  len(candidate.ProtocolSHA256)!=64 ||
  candidate.BudgetUnits!=10 ||
  len(candidate.SeedIDs)<1 || len(candidate.SeedIDs)>128 {
  return false
 }
 for _,sum:=range []string{candidate.SourceSHA,candidate.PreregSHA256,
  candidate.CohortSHA256,candidate.ProtocolSHA256}{
  if _,err:=hex.DecodeString(sum);err!=nil{return false}
 }
 ids:=candidate.SeedIDs
 if !slices.IsSorted(ids){return false}
 for i,id:=range ids {
  if !strings.HasPrefix(id,"Yggdrasil:") ||
   len(id)<=len("Yggdrasil:") ||
   (i>0&&ids[i-1]==id){return false}
  for _,c:=range strings.TrimPrefix(id,"Yggdrasil:"){
   if c<'0'||c>'9'{return false}
  }
 }
 return true
}

// Inspect requires an EXTERNALLY PINNED signer, generation, high-water
// revision and ledger digest; it checks individual seed collisions across
// all lanes in addition to existing eligibility.VerifyLedger checks.
// Success is only a read-only preflight, never an execution permit.
func Inspect(s Signed,p Pins,candidate eligibility.Frozen)(Report,error){
 if !validCandidate(candidate){
  return deny("INVALID_FROZEN_F5_SEED_OR_SOURCE_IDENTITY")
 }
 if p.MinRevision==0||p.ExpectedLedgerGeneration==0||
  p.WinglessMinHighWater==0||p.YggdrasilMinHighWater==0||
  len(p.CustodianPublicKeyHex)!=ed25519.PublicKeySize*2||
  len(p.LedgerSHA256)!=64{
  return deny("MISSING_INDEPENDENT_AUTHORITY_PINS")
 }
 key,err:=hex.DecodeString(p.CustodianPublicKeyHex)
 if err!=nil||len(key)!=ed25519.PublicKeySize{return deny("INVALID_INDEPENDENT_KEY")}
 sig,err:=hex.DecodeString(s.SignatureHex)
 if err!=nil||len(sig)!=ed25519.SignatureSize{return deny("MISSING_SIGNED_CUSTODY")}
 raw,err:=json.Marshal(s.Attestation)
 if err!=nil||!ed25519.Verify(ed25519.PublicKey(key),append([]byte("FORGE-F5-ALL-LANE-SEED-CUSTODY-V1\n"),raw...),sig){
  return deny("UNAUTHENTICATED_SIGNER_OR_RECORD")
 }
 a:=s.Attestation
 if a.Schema!=Schema||a.Scope!="ALL_LANES"||
  a.Coverage!="GENESIS_TO_HIGH_WATER_INCLUDING_UNCERTAIN"||
  a.Revision<p.MinRevision||a.Ledger.Generation!=p.ExpectedLedgerGeneration||
  len(a.LaneHighWater)!=2||
  a.LaneHighWater["Wingless"]<p.WinglessMinHighWater||
  a.LaneHighWater["Yggdrasil"]<p.YggdrasilMinHighWater{
  return deny("INCOMPLETE_ALL_LANE_OR_STALE_WITNESS")
 }
 for _,list:=range [][]string{a.ConsumedSeedIDs,a.ActiveSeedIDs,a.UncertainSeedIDs}{
  if !canonicalUniqueSeedIDs(list){return deny("MISSING_OR_MALFORMED_SEED_INDEX")}
 }
 used:=map[string]bool{}
 for _,list:=range [][]string{a.ConsumedSeedIDs,a.ActiveSeedIDs,a.UncertainSeedIDs}{
  for _,id:=range list{
   if used[id]{return deny("AMBIGUOUS_SEED_CUSTODY")}
   used[id]=true
  }
 }
 for _,id:=range candidate.SeedIDs {
  if used[id]{return deny("CANDIDATE_SEED_CONSUMED_ACTIVE_OR_UNCERTAIN")}
 }
 if err=eligibility.VerifyLedger(candidate,a.Ledger,p.LedgerSHA256,
  p.ExpectedLedgerGeneration,true);err!=nil{
  return deny("LEDGER_COHORT_OR_PRIOR_START_COLLISION")
 }
 // Even a genuine verified all-lane seed ledger is not F5 original
 // authorization. F5 prospective protocol has NO frozen scientific
 // source, cohort allocation, or issued once-only start grant yet.
 return Report{Schema:"forge.f5.custody-preflight-report.v1",
  Disposition:"AUDIT_ONLY_SOURCE_AND_ORIGINAL_AUTHORITY_STILL_BLOCKED",
  AuthenticatedSnapshot:true,CompleteAllLaneSeedIndex:true,
  IndividualCandidateSeedsAbsentFromUse:true,
  SourceFrozen:false,OriginalStartAuthorized:false,
  FirstUseClaims:0,Reason:fmt.Sprintf(
   "revision %d structurally checked; science not authorized",a.Revision)},nil
}

// Digest only helps reproduce an authenticated ledger; it cannot provide
// an external pin or substitute for the custodian signature.
func Digest(s eligibility.LedgerSnapshot)(string,error){
 raw,err:=json.Marshal(s);if err!=nil{return "",err}
 h:=sha256.Sum256(append([]byte("FORGE-ELIGIBILITY-LEDGER-SNAPSHOT-V1\n"),raw...))
 return hex.EncodeToString(h[:]),nil
}
