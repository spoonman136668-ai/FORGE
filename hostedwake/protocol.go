// Package hostedwake separates pre-run wake eligibility from the later,
// run-ID-bound FSA execution grant. No FSA signer, lock, dispatch or runner.
package hostedwake

import (
 "bytes"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "strconv"

 "github.com/spoonman136668-ai/forge/hostedgrant"
)
const (
 IntentSchema="forge.fsa.hosted-prewake.v1"
 ClaimSchema="forge.fsa.hosted-run-claim.v1"
 LeaseSchema="forge.fsa.hosted-run-bound-lease.v1"
 ResultSchema="forge.fsa.hosted-wake-observation.v1"
 IntentDomain="FORGE-FSA-HOSTED-PREWAKE-V1\n"
 LeaseDomain="FORGE-FSA-HOSTED-LEASE-V1\n"
 IntentMode="PREWAKE_ONLY_NO_SCIENTIFIC_AUTHORITY"
 LeaseMode="EXTERNAL_FSA_DISPATCH_CONSUMPTION_CLAIM"
)
var ErrDenied=errors.New("FORGE_HOSTED_WAKE_NO_INDEPENDENT_FSA")
type Intent struct{
 Schema string
 Mode string
 Repository string
 Workflow string
 SourceSHA string
 TreeSHA string
 Lane string
 Generation uint64
 ExperimentID string
 CohortSHA256 string
 PreregSHA256 string
 ScopeSHA256 string
 CorrelationSHA256 string
 FSAArchiveID string
 FSAEpoch uint64
 SourceWitnessSHA256 string
 MaxComputeUnits int
 // RunID intentionally ABSENT. GitHub assigns it only after the wake.
}
type SignedIntent struct{Intent Intent;SignatureHex string}
type Pin struct{
 IntentSHA256 string
 IntentKeyHex string
 LeaseKeyHex string
 FSAHeadKeyHex string
}
type Context struct{
 Repository string
 Workflow string
 SourceSHA string
 TreeSHA string
 Lane string
 RunID string
 Attempt int
}
type Claim struct{
 Schema string
 PrewakeSHA256 string
 Repository string
 Workflow string
 SourceSHA string
 TreeSHA string
 Lane string
 RunID string
 Attempt int
 CorrelationSHA256 string
}
type Lease struct{
 Schema string
 Mode string
 PrewakeSHA256 string
 ClaimSHA256 string
 RunID string
 Attempt int
 Lane string
 CohortSHA256 string
 GrantSHA256 string
 FSAArchiveID string
 FSAEpoch uint64
 ConsumedDispatchSequence uint64
 ConsumedDispatchHeadSHA256 string
 DispatchLockWitnessSHA256 string
 ConsumedDispatchLease bool
}
type SignedLease struct{Lease Lease;SignatureHex string}
type Observation struct {
 Schema string
 Mode string
 PrewakeSHA256 string
 ClaimSHA256 string
 RunID string
 Lane string
 ScientificOriginalStarted bool
 DispatchAuthorized bool
 ProtectedDispatchConsumptionIndependentlyAudited bool
 GitHubOIDCIndependentlyVerified bool
 FSAOperational bool
 AcceptedRefMutation bool
}
func lowerHex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f')){return false}}
 return true
}
func validID(s string)bool{
 if len(s)<1||len(s)>96{return false}
 for _,c:=range s{if !(c>='a'&&c<='z'||c>='A'&&c<='Z'||c>='0'&&c<='9'||c=='-'||c=='_'){return false}}
 return true
}
func runID(s string)bool{
 if len(s)<1||len(s)>20||s[0]=='0'{return false}
 for _,c:=range s{if c<'0'||c>'9'{return false}}
 n,e:=strconv.ParseUint(s,10,64);return e==nil&&n>0
}
func sha(v any)(string,error){
 b,e:=json.Marshal(v);if e!=nil||len(b)>16384{return "",ErrDenied}
 h:=sha256.Sum256(b);return hex.EncodeToString(h[:]),nil
}
func verify(data any,sigHex,pinnedSHA,pubHex,domain string)error{
 if !lowerHex(sigHex,128)||!lowerHex(pinnedSHA,64)||!lowerHex(pubHex,64){return ErrDenied}
 raw,e:=json.Marshal(data);if e!=nil||len(raw)>16384{return ErrDenied}
 sum:=sha256.Sum256(raw)
 if hex.EncodeToString(sum[:])!=pinnedSHA{return ErrDenied}
 sig,_:=hex.DecodeString(sigHex)
 key,_:=hex.DecodeString(pubHex)
 if !ed25519.Verify(key,append([]byte(domain),raw...),sig){return ErrDenied}
 return nil
}
func ValidPins(pin Pin)bool{
 return lowerHex(pin.IntentSHA256,64)&&lowerHex(pin.IntentKeyHex,64)&&
  lowerHex(pin.LeaseKeyHex,64)&&lowerHex(pin.FSAHeadKeyHex,64)&&
  pin.IntentKeyHex!=pin.LeaseKeyHex&&pin.IntentKeyHex!=pin.FSAHeadKeyHex&&
  pin.LeaseKeyHex!=pin.FSAHeadKeyHex
}
func ParseIntent(raw []byte)(SignedIntent,error){
 var zero SignedIntent
 if len(raw)==0||len(raw)>16384{return zero,ErrDenied}
 d:=json.NewDecoder(bytes.NewReader(raw));d.DisallowUnknownFields()
 var s SignedIntent
 if d.Decode(&s)!=nil{return zero,ErrDenied}
 var extra any
 if d.Decode(&extra)!=io.EOF{return zero,ErrDenied}
 return s,nil
}
func ParseLease(raw []byte)(SignedLease,error){
 var zero SignedLease
 if len(raw)==0||len(raw)>16384{return zero,ErrDenied}
 d:=json.NewDecoder(bytes.NewReader(raw));d.DisallowUnknownFields()
 var s SignedLease
 if d.Decode(&s)!=nil{return zero,ErrDenied}
 var extra any
 if d.Decode(&extra)!=io.EOF{return zero,ErrDenied}
 return s,nil
}
// ObserveWake binds an independently pinned PRE-run FSA intent to the
// GitHub-assigned POST-wake run ID, without self-authorizing any science.
func ObserveWake(s SignedIntent,pin Pin,ctx Context)(Claim,Observation,error){
 var empty Claim
 var none Observation
 g:=s.Intent
 if !ValidPins(pin)||verify(g,s.SignatureHex,pin.IntentSHA256,pin.IntentKeyHex,IntentDomain)!=nil||
  g.Schema!=IntentSchema||g.Mode!=IntentMode||
  g.Repository!=hostedgrant.ExpectedRepository||g.Workflow!=hostedgrant.ExpectedWorkflow||
  g.Repository!=ctx.Repository||g.Workflow!=ctx.Workflow||
  !lowerHex(g.SourceSHA,40)||g.SourceSHA!=ctx.SourceSHA||
  !lowerHex(g.TreeSHA,40)||g.TreeSHA!=ctx.TreeSHA||
  g.Lane!=ctx.Lane||(g.Lane!="Wingless"&&g.Lane!="Yggdrasil")||
  g.Generation==0||g.FSAEpoch==0||!validID(g.ExperimentID)||
  !lowerHex(g.CohortSHA256,64)||!lowerHex(g.PreregSHA256,64)||
  !lowerHex(g.ScopeSHA256,64)||!lowerHex(g.CorrelationSHA256,64)||
  !lowerHex(g.FSAArchiveID,64)||!lowerHex(g.SourceWitnessSHA256,64)||
  g.MaxComputeUnits<1||g.MaxComputeUnits>1000000||
  !runID(ctx.RunID)||ctx.Attempt!=1{
  return empty,none,ErrDenied
 }
 c:=Claim{Schema:ClaimSchema,PrewakeSHA256:pin.IntentSHA256,
  Repository:g.Repository,Workflow:g.Workflow,
  SourceSHA:g.SourceSHA,TreeSHA:g.TreeSHA,
  Lane:g.Lane,RunID:ctx.RunID,Attempt:1,
  CorrelationSHA256:g.CorrelationSHA256}
 claimSHA,e:=sha(c);if e!=nil{return empty,none,ErrDenied}
 return c,Observation{Schema:ResultSchema,Mode:"OBSERVED_RUN_ONLY_NO_FSA_DISPATCH",
  PrewakeSHA256:pin.IntentSHA256,ClaimSHA256:claimSHA,
  RunID:ctx.RunID,Lane:ctx.Lane},nil
}
// VerifyLease checks a separately FSA-signed, run-ID-bound lease claim
// after the wake. A signed *claim* is not an independently audited atomic
// lease consumption, so even a PASS remains non-executable.
func VerifyLease(c Claim,observation Observation,s SignedLease,
 pinnedLeaseSHA string,pin Pin,grantReview hostedgrant.Review)(Observation,error){
 var none Observation
 lease:=s.Lease
 claimSHA,e:=sha(c)
 if e!=nil||!ValidPins(pin)||!lowerHex(pinnedLeaseSHA,64)||
  c.Schema!=ClaimSchema||observation.Schema!=ResultSchema||
  observation.Mode!="OBSERVED_RUN_ONLY_NO_FSA_DISPATCH"||
  observation.PrewakeSHA256!=pin.IntentSHA256||
  observation.ClaimSHA256!=claimSHA||observation.RunID!=c.RunID||
  observation.Lane!=c.Lane||
  observation.ScientificOriginalStarted||observation.DispatchAuthorized||
  observation.ProtectedDispatchConsumptionIndependentlyAudited||
  observation.GitHubOIDCIndependentlyVerified||observation.FSAOperational||
  observation.AcceptedRefMutation||
  lease.Schema!=LeaseSchema||lease.Mode!=LeaseMode||
  lease.PrewakeSHA256!=pin.IntentSHA256||lease.ClaimSHA256!=claimSHA||
  lease.RunID!=c.RunID||!runID(lease.RunID)||lease.Attempt!=1||
  c.Attempt!=1||lease.Lane!=c.Lane||!lowerHex(lease.CohortSHA256,64)||
  !lowerHex(lease.GrantSHA256,64)||
  !lowerHex(lease.FSAArchiveID,64)||lease.FSAEpoch==0||
  lease.ConsumedDispatchSequence==0||
  !lowerHex(lease.ConsumedDispatchHeadSHA256,64)||
  !lowerHex(lease.DispatchLockWitnessSHA256,64)||
  !lease.ConsumedDispatchLease||
  grantReview.Schema!=hostedgrant.ReviewSchema||
  grantReview.Mode!="CRYPTOGRAPHIC_REVIEW_ONLY_NO_EXECUTION"||
  grantReview.GrantSHA256!=lease.GrantSHA256||
  grantReview.SourceSHA!=c.SourceSHA||
  grantReview.Lane!=c.Lane||grantReview.CohortSHA256!=lease.CohortSHA256||
  !grantReview.FirstUseObserved||grantReview.ProtectedReplayLockAcquired||
  grantReview.LiveFSAOperational||grantReview.ScienceExecuted||
  grantReview.AcceptedScience||grantReview.IndependentPhysicalCustodyVerified||
  verify(lease,s.SignatureHex,pinnedLeaseSHA,pin.LeaseKeyHex,LeaseDomain)!=nil{
   return none,ErrDenied
 }
 // The FSA, not this code, must prove it independently committed that
 // dispatch lease to a protected, replay-proof floor BEFORE any execution.
 // This package cannot attest external state and never returns "start".
 return Observation{Schema:ResultSchema,
  Mode:"SIGNED_LEASE_CLAIM_REVIEWED_NO_EXECUTION",
  PrewakeSHA256:pin.IntentSHA256,ClaimSHA256:claimSHA,
  RunID:c.RunID,Lane:c.Lane},nil
}
