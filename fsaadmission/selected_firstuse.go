package fsaadmission

// Source-only verification for authentic, independently attested first-use
// *readiness*. It cannot sign, reserve, dispatch, open a worker, or authorize
// scientific first-use. Only real FSA archive recovery may call the private
// verification path with an authenticated head.
import(
 "bytes"
 "context"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "fmt"

 "github.com/spoonman136668-ai/forge/eligibility"
 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsatrust"
 "github.com/spoonman136668-ai/forge/privatearchive"
)

const(
 selectedSchema="forge.science.selected-firstuse.v2"
 bornSchema="forge.science.independent-source-birth.v2"
 familySchema="forge.science.complete-family-ledger.v1"
 selectedDomain="FORGE-SCIENCE-SELECTED-FROZEN-V2\n"
 bornDomain="FORGE-SCIENCE-INDEPENDENT-BIRTH-V2\n"
 familyDomain="FORGE-SCIENCE-FAMILY-LEDGER-V1\n"
 SelectedPreflightOnly="FSA_SIGNED_SELECTION_PREFLIGHT_ONLY_NO_START_OR_DISPATCH"
)
type Selected struct{
 Schema string `json:"schema"`
 Frozen eligibility.Frozen `json:"frozen"`
 HypothesisSHA256 string `json:"hypothesis_sha256"`
 FullyTrainedControlSHA256 string `json:"fully_trained_control_sha256"`
 EqualTrainingProofSHA256 string `json:"equal_training_proof_sha256"`
 MaxNativeCPUms uint64 `json:"max_native_cpu_ms"`
 MaxNativePeakRSSBytes uint64 `json:"max_native_peak_rss_bytes"`
 MaxWallSeconds uint64 `json:"max_wall_seconds"`
 CustodyEpoch uint64 `json:"custody_epoch"`
 FrozenSequence uint64 `json:"frozen_sequence"`
}
type SourceBirth struct{
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 CandidateID string `json:"candidate_id"`
 SourceSHA string `json:"source_sha"`
 CohortSHA256 string `json:"cohort_sha256"`
 IndependentFamilySHA256 [2]string `json:"independent_family_sha256"`
 CustodyEpoch uint64 `json:"custody_epoch"`
 FrozenSelectionSHA256 string `json:"frozen_selection_sha256"`
 BirthSequence uint64 `json:"birth_sequence"`
 NeverPreviouslyConsumed bool `json:"never_previously_consumed"`
}
// Third-party signer attests COMPLETE all-lane active/consumed family
// inventories at the exact currently authenticated FSA archive high-water.
// No candidate-supplied flag or unsigned stale inventory can satisfy this.
type FamilySnapshot struct{
 Schema string `json:"schema"`
 ArchiveID string `json:"archive_id"`
 CustodyEpoch uint64 `json:"custody_epoch"`
 Sequence uint64 `json:"sequence"`
 HeadSHA256 string `json:"head_sha256"`
 LedgerGeneration uint64 `json:"ledger_generation"`
 CompleteAllLanes bool `json:"complete_all_lanes"`
 FrozenSelectionSHA256 string `json:"frozen_selection_sha256"`
 SourceBirthSHA256 string `json:"source_birth_sha256"`
 FrozenSequence uint64 `json:"frozen_sequence"`
 BirthSequence uint64 `json:"birth_sequence"`
 ActiveFamilySHA256 []string `json:"active_family_sha256"`
 ConsumedFamilySHA256 []string `json:"consumed_family_sha256"`
}
type SignedSelection struct{
 Selection Selected `json:"selection"`
 SignatureHex string `json:"signature_hex"`
}
type SignedBirth struct{
 Birth SourceBirth `json:"birth"`
 SignatureHex string `json:"signature_hex"`
}
type SignedFamilySnapshot struct{
 Snapshot FamilySnapshot `json:"snapshot"`
 SignatureHex string `json:"signature_hex"`
}
type IndependentPins struct{
 FrozenSigner ed25519.PublicKey
 SourceBirthSigner ed25519.PublicKey
 FamilyLedgerSigner ed25519.PublicKey
}
func hex64(s string)bool{
 if len(s)!=64{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func sameFrozen(a,b eligibility.Frozen)bool{
 if a.Schema!=b.Schema||a.Lane!=b.Lane||a.CandidateID!=b.CandidateID||
 a.SourceSHA!=b.SourceSHA||a.PreregSHA256!=b.PreregSHA256||
 a.CohortSHA256!=b.CohortSHA256||a.ProtocolSHA256!=b.ProtocolSHA256||
 a.BudgetUnits!=b.BudgetUnits||len(a.SeedIDs)!=len(b.SeedIDs){return false}
 for i:=range a.SeedIDs{if a.SeedIDs[i]!=b.SeedIDs[i]{return false}}
 return true
}
func signedDigest(domain string,body any)([]byte,string,error){
 raw,err:=json.Marshal(body)
 if err!=nil{return nil,"",err}
 data:=append([]byte(domain),raw...)
 hash:=sha256.Sum256(data)
 return data,hex.EncodeToString(hash[:]),nil
}
func signatureValid(pub ed25519.PublicKey,signatureHex string,message []byte)bool{
 signature,err:=hex.DecodeString(signatureHex)
 return err==nil&&len(signature)==ed25519.SignatureSize&&ed25519.Verify(pub,message,signature)
}
func completeFamilyInventory(snapshot FamilySnapshot,first,second string)bool{
 if snapshot.ActiveFamilySHA256==nil||snapshot.ConsumedFamilySHA256==nil||
 len(snapshot.ActiveFamilySHA256)>1000||len(snapshot.ConsumedFamilySHA256)>1000{return false}
 seen:=make(map[string]bool,len(snapshot.ActiveFamilySHA256)+len(snapshot.ConsumedFamilySHA256))
 for _,items:=range [][]string{snapshot.ActiveFamilySHA256,snapshot.ConsumedFamilySHA256}{
  previous:=""
  for _,id:=range items{
   if !hex64(id)||seen[id]||(previous!=""&&id<=previous)||id==first||id==second{return false}
   seen[id]=true;previous=id
  }
 }
 return true
}
// verifySelected is deliberately unexported: a caller cannot supply its own
// fake FSA head and invoke a public source-only positive preflight. Only
// AssessSelectedArchived can pass an independently recovered archive head.
func verifySelected(s SignedSelection,b SignedBirth,f SignedFamilySnapshot,
 pins IndependentPins,expected eligibility.Frozen,
 head fsahead.Anchor,ledgerGeneration uint64)(string,error){
 fail:=func(reason string)(string,error){return "",fmt.Errorf("%w: signed first-use: %s",ErrBlocked,reason)}
 if len(pins.FrozenSigner)!=ed25519.PublicKeySize||
 len(pins.SourceBirthSigner)!=ed25519.PublicKeySize||
 len(pins.FamilyLedgerSigner)!=ed25519.PublicKeySize||
 bytes.Equal(pins.FrozenSigner,pins.SourceBirthSigner)||
 bytes.Equal(pins.FrozenSigner,pins.FamilyLedgerSigner)||
 bytes.Equal(pins.SourceBirthSigner,pins.FamilyLedgerSigner){return fail("distinct independent signer pins required")}
 x,y,z:=s.Selection,b.Birth,f.Snapshot
 if x.Schema!=selectedSchema||y.Schema!=bornSchema||z.Schema!=familySchema||
 !sameFrozen(x.Frozen,expected)||x.Frozen.Schema!=eligibility.Schema{
  return fail("frozen identity mismatch")
 }
 if !hex64(x.HypothesisSHA256)||!hex64(x.FullyTrainedControlSHA256)||
 !hex64(x.EqualTrainingProofSHA256)||
 x.HypothesisSHA256==x.FullyTrainedControlSHA256||
 x.MaxNativeCPUms==0||x.MaxNativeCPUms>86400000||
 x.MaxNativePeakRSSBytes<1048576||x.MaxNativePeakRSSBytes>17179869184||
 x.MaxWallSeconds==0||x.MaxWallSeconds>86400||x.CustodyEpoch==0||
 x.FrozenSequence==0{return fail("frozen hypothesis/control or native resource limits")}
 if head.AuthorityEpoch==0||head.Sequence==0||!hex64(head.ArchiveID)||
 !hex64(head.HeadSHA256)||ledgerGeneration==0||
 x.CustodyEpoch!=head.AuthorityEpoch||y.CustodyEpoch!=head.AuthorityEpoch||
 z.CustodyEpoch!=head.AuthorityEpoch{
  return fail("unanchored common custody epoch")
 }
 if y.Lane!=expected.Lane||y.CandidateID!=expected.CandidateID||
 y.SourceSHA!=expected.SourceSHA||y.CohortSHA256!=expected.CohortSHA256||
 !hex64(y.IndependentFamilySHA256[0])||!hex64(y.IndependentFamilySHA256[1])||
 y.IndependentFamilySHA256[0]==y.IndependentFamilySHA256[1]||
 y.IndependentFamilySHA256[0]==expected.CohortSHA256||
 y.IndependentFamilySHA256[1]==expected.CohortSHA256||
 !y.NeverPreviouslyConsumed||y.BirthSequence<=x.FrozenSequence||
 y.BirthSequence>head.Sequence{return fail("missing postfreeze unfamiliar source birth")}
 sm,sh,err:=signedDigest(selectedDomain,x)
 if err!=nil||!signatureValid(pins.FrozenSigner,s.SignatureHex,sm){return fail("unsigned frozen selection")}
 if y.FrozenSelectionSHA256!=sh{return fail("birth not bound to frozen selection digest")}
 bm,bh,err:=signedDigest(bornDomain,y)
 if err!=nil||!signatureValid(pins.SourceBirthSigner,b.SignatureHex,bm){return fail("unsigned independent postfreeze birth")}
 if z.ArchiveID!=head.ArchiveID||z.HeadSHA256!=head.HeadSHA256||
 z.Sequence!=head.Sequence||z.LedgerGeneration!=ledgerGeneration||
 z.FrozenSelectionSHA256!=sh||z.SourceBirthSHA256!=bh||
 z.FrozenSequence!=x.FrozenSequence||z.BirthSequence!=y.BirthSequence||
 !z.CompleteAllLanes||!completeFamilyInventory(z,y.IndependentFamilySHA256[0],y.IndependentFamilySHA256[1]){
  return fail("stale, partial, replayed or consumed source-family ledger")
 }
 fm,_,err:=signedDigest(familyDomain,z)
 if err!=nil||!signatureValid(pins.FamilyLedgerSigner,f.SignatureHex,fm){
  return fail("unsigned independently witnessed full source-family inventory")
 }
 return SelectedPreflightOnly,nil
}
// The actual positive readiness verdict is reachable ONLY after independently
// authenticated, twice-recovered FSA archive and global cohort checks.
// This API is read-only and never issues start receipts or dispatch permission.
func AssessSelectedArchived(ctx context.Context,backend fsatrust.Authority,
 archive *privatearchive.Store,identity fsatrust.Identity,evidence Evidence,
 signed SignedSelection,birth SignedBirth,family SignedFamilySnapshot,
 pins IndependentPins)(string,error){
 decision,head,err:=assessArchivedAnchor(ctx,backend,archive,identity,evidence)
 if err!=nil||decision!=PreflightOnly{return "",fmt.Errorf("%w: authentic FSA archive required: %v",ErrBlocked,err)}
 return verifySelected(signed,birth,family,pins,evidence.Frozen,head,evidence.ExperimentGeneration)
}
