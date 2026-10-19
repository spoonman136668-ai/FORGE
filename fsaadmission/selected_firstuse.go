package fsaadmission

// Source-frozen scientific selection verification within the existing FSA
// preflight. No controller, scheduler, worker, issuer, signer, or scientific
// start capability is added here. In particular, this cannot grant F139's
// development-only worker permission to execute scientific first-use.
import (
 "bytes"
 "context"
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "fmt"

 "github.com/spoonman136668-ai/forge/eligibility"
 "github.com/spoonman136668-ai/forge/fsatrust"
 "github.com/spoonman136668-ai/forge/privatearchive"
)

const (
 selectedSchema="forge.science.selected-firstuse.v1"
 bornSchema="forge.science.independent-source-birth.v1"
 selectedDomain="FORGE-SCIENCE-SELECTED-FROZEN-V1\n"
 bornDomain="FORGE-SCIENCE-INDEPENDENT-BIRTH-V1\n"
 SelectedPreflightOnly="FSA_SIGNED_SELECTION_PREFLIGHT_ONLY_NO_START_OR_DISPATCH"
)

// The strongest equally trained control and total native resource caps must
// be frozen before any independent source first-use. The FSA Frozen identifies
// the candidate, exact source, preregistration, cohort, protocol, and seeds.
type Selected struct {
 Schema string `json:"schema"`
 Frozen eligibility.Frozen `json:"frozen"`
 HypothesisSHA256 string `json:"hypothesis_sha256"`
 FullyTrainedControlSHA256 string `json:"fully_trained_control_sha256"`
 EqualTrainingProofSHA256 string `json:"equal_training_proof_sha256"`
 MaxNativeCPUms uint64 `json:"max_native_cpu_ms"`
 MaxNativePeakRSSBytes uint64 `json:"max_native_peak_rss_bytes"`
 MaxWallSeconds uint64 `json:"max_wall_seconds"`
 FrozenSequence uint64 `json:"frozen_sequence"`
}

type SourceBirth struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 CandidateID string `json:"candidate_id"`
 SourceSHA string `json:"source_sha"`
 CohortSHA256 string `json:"cohort_sha256"`
 IndependentFamilySHA256 [2]string `json:"independent_family_sha256"`
 BirthSequence uint64 `json:"birth_sequence"`
 NeverPreviouslyConsumed bool `json:"never_previously_consumed"`
}

type SignedSelection struct {
 Selection Selected `json:"selection"`
 SignatureHex string `json:"signature_hex"`
}
type SignedBirth struct {
 Birth SourceBirth `json:"birth"`
 SignatureHex string `json:"signature_hex"`
}

type IndependentPins struct {
 FrozenSigner ed25519.PublicKey
 SourceBirthSigner ed25519.PublicKey
}

// VerifySelected is intentionally a non-executing, negative-only source
// verification. Pins must come from separate independently provisioned FSA
// custody; accepting them from the candidate would be self-certification.
func VerifySelected(s SignedSelection,b SignedBirth,p IndependentPins,expected eligibility.Frozen)(string,error){
 fail:=func(reason string)(string,error){return "",fmt.Errorf("%w: signed first-use: %s",ErrBlocked,reason)}
 if len(p.FrozenSigner)!=ed25519.PublicKeySize||len(p.SourceBirthSigner)!=ed25519.PublicKeySize||
  bytes.Equal(p.FrozenSigner,p.SourceBirthSigner){return fail("independent signer pins")}
 x,y:=s.Selection,b.Birth
 if x.Schema!=selectedSchema||y.Schema!=bornSchema||
  x.Frozen.Schema!=eligibility.Schema||!sameFrozen(x.Frozen,expected) {
  return fail("frozen identity")
 }
 if !hex64(x.HypothesisSHA256)||!hex64(x.FullyTrainedControlSHA256)||
  !hex64(x.EqualTrainingProofSHA256)||
  x.HypothesisSHA256==x.FullyTrainedControlSHA256||
  x.MaxNativeCPUms==0||x.MaxNativeCPUms>86400000||
  x.MaxNativePeakRSSBytes<1048576||x.MaxNativePeakRSSBytes>17179869184||
  x.MaxWallSeconds==0||x.MaxWallSeconds>86400||
  x.FrozenSequence==0{return fail("unqualified frozen controls or complete resource bounds")}
 if y.Lane!=expected.Lane||y.CandidateID!=expected.CandidateID||
  y.SourceSHA!=expected.SourceSHA||y.CohortSHA256!=expected.CohortSHA256||
  !hex64(y.IndependentFamilySHA256[0])||!hex64(y.IndependentFamilySHA256[1])||
  y.IndependentFamilySHA256[0]==y.IndependentFamilySHA256[1]||
  y.IndependentFamilySHA256[0]==expected.CohortSHA256||
  y.IndependentFamilySHA256[1]==expected.CohortSHA256||
  y.BirthSequence<=x.FrozenSequence||!y.NeverPreviouslyConsumed{
  return fail("missing independently born unfamiliar first-use sources")
 }
 sx,err:=hex.DecodeString(s.SignatureHex);if err!=nil||len(sx)!=ed25519.SignatureSize{return fail("freeze signature encoding")}
 sy,err:=hex.DecodeString(b.SignatureHex);if err!=nil||len(sy)!=ed25519.SignatureSize{return fail("birth signature encoding")}
 xm,err:=json.Marshal(x);if err!=nil{return fail("freeze canonical encoding")}
 ym,err:=json.Marshal(y);if err!=nil{return fail("birth canonical encoding")}
 if !ed25519.Verify(p.FrozenSigner,append([]byte(selectedDomain),xm...),sx)||
    !ed25519.Verify(p.SourceBirthSigner,append([]byte(bornDomain),ym...),sy){
  return fail("independent cryptographic attestations")
 }
 return SelectedPreflightOnly,nil
}


func sameFrozen(a,b eligibility.Frozen)bool{
 if a.Schema!=b.Schema||a.Lane!=b.Lane||a.CandidateID!=b.CandidateID||
 a.SourceSHA!=b.SourceSHA||a.PreregSHA256!=b.PreregSHA256||
 a.CohortSHA256!=b.CohortSHA256||a.ProtocolSHA256!=b.ProtocolSHA256||
 a.BudgetUnits!=b.BudgetUnits||len(a.SeedIDs)!=len(b.SeedIDs){return false}
 for i:=range a.SeedIDs{if a.SeedIDs[i]!=b.SeedIDs[i]{return false}}
 return true
}

func hex64(s string)bool{
 if len(s)!=64{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}

// AssessSelectedArchived ties selected signed origins to existing source,
// all-lane ledger, independently witnessed start history, and twice-checked
// archive recovery. It cannot reserve a cohort, issue an original start,
// authorize GitHub Actions, or move accepted scientific refs. No unsigned or
// synthetic fixture is a substitute for the real independent FSA service.
func AssessSelectedArchived(ctx context.Context,backend fsatrust.Authority,
 archive *privatearchive.Store,identity fsatrust.Identity,evidence Evidence,
 signed SignedSelection,birth SignedBirth,pins IndependentPins)(string,error){
 verdict,err:=AssessArchived(ctx,backend,archive,identity,evidence)
 if err!=nil||verdict!=PreflightOnly{return "",fmt.Errorf("%w: real authenticated FSA archive required: %v",ErrBlocked,err)}
 return VerifySelected(signed,birth,pins,evidence.Frozen)
}
