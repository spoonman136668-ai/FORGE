// Package hostedgrant verifies independently issued, source-pinned FSA
// scientific work grants before a GitHub-hosted compute worker sees them.
// No issuer, protected state, trigger, runner or scientific execution here.
package hostedgrant

import (
 "bytes"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "strconv"

 "github.com/spoonman136668-ai/forge/dreamrsi/fsagate"
)
const (
 GrantSchema="forge.fsa.hosted-work-authorization.v1"
 Domain="FORGE-FSA-HOSTED-WORK-AUTHORIZATION-V1\n"
 ReviewSchema="forge.fsa.hosted-work-review.v1"
 ExpectedRepository="spoonman136668-ai/FORGE"
 ExpectedWorkflow=".github/workflows/forge-fsa-original.yml"
)
var ErrDenied=errors.New("FORGE_HOSTED_ORIGINAL_DENIED_NO_INDEPENDENT_FSA_GRANT")
type Grant struct {
 Schema string
 Repository string
 Workflow string
 RunID string
 Attempt int
 SourceSHA string
 TreeSHA string
 Lane string
 Generation uint64
 ExperimentID string
 CandidateID string
 CohortSHA256 string
 PreregSHA256 string
 ScopeSHA256 string
 ArchiveID string
 AuthorityEpoch uint64
 FirstUsePlanSHA256 string
 FirstUseProofSHA256 string
 StartedRecordSHA256 string
 CommittedSequence uint64
 CommittedHeadSHA256 string
 MaxComputeUnits int
 ScienceRunID uint64
 AuthorizingFSA bool
}
type Envelope struct {
 Grant Grant
 SignatureHex string
}
type Context struct {
 Repository string
 Workflow string
 RunID string
 Attempt int
 SourceSHA string
 TreeSHA string
 Lane string
}
type Pin struct {
 GrantSHA256 string
 GrantKeyHex string
 IndependentFSAHeadKeyHex string
}
type Review struct{
 Schema string
 Mode string
 GrantSHA256 string
 FirstUseProofSHA256 string
 SourceSHA string
 Lane string
 CohortSHA256 string
 FirstUseObserved bool
 IndependentPhysicalCustodyVerified bool
 LiveFSAOperational bool
 ScienceExecuted bool
 AcceptedScience bool
 ProtectedReplayLockAcquired bool
}
func hexValid(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func runValid(s string)bool{
 if len(s)<1||len(s)>20||s[0]=='0'{return false}
 for _,c:=range s{if c<'0'||c>'9'{return false}}
 i,err:=strconv.ParseUint(s,10,64);return err==nil&&i>0
}
func sha(v any)(string,error){
 b,err:=json.Marshal(v);if err!=nil||len(b)>16384{return "",ErrDenied}
 h:=sha256.Sum256(b)
 return hex.EncodeToString(h[:]),nil
}
func ParseEnvelope(data []byte)(Envelope,error){
 var empty Envelope
 if len(data)==0||len(data)>16384{return empty,ErrDenied}
 dec:=json.NewDecoder(bytes.NewReader(data));dec.DisallowUnknownFields()
 var e Envelope
 if dec.Decode(&e)!=nil{return empty,ErrDenied}
 var trail any
 if dec.Decode(&trail)!=io.EOF{return empty,ErrDenied}
 return e,nil
}
func validName(v string)bool{
 if len(v)<1||len(v)>96{return false}
 for _,c:=range v{if !(c>='a'&&c<='z'||c>='A'&&c<='Z'||c>='0'&&c<='9'||c=='_'||c=='-'){return false}}
 return true
}
// ReviewGrant provides only a cryptographically verified handoff summary,
// NEVER launch permission. The actual FSA must also independently validate
// external high-water/physical evidence at execution and consume its
// protected, cohort-scoped dispatch capability exactly once.
func ReviewGrant(e Envelope,pin Pin,ctx Context,
 scope fsagate.Scope,firstuse fsagate.FirstUseProof)(Review,error){
 var empty Review
 g:=e.Grant
 if !hexValid(pin.GrantSHA256,64)||
  !hexValid(pin.GrantKeyHex,64)||
  !hexValid(pin.IndependentFSAHeadKeyHex,64)||
  pin.GrantKeyHex==pin.IndependentFSAHeadKeyHex||
  !hexValid(e.SignatureHex,128)||
  g.Schema!=GrantSchema||!g.AuthorizingFSA||
  g.Repository!=ExpectedRepository||g.Workflow!=ExpectedWorkflow||
  g.Repository!=ctx.Repository||g.Workflow!=ctx.Workflow||
  !runValid(g.RunID)||g.RunID!=ctx.RunID||ctx.Attempt!=1||g.Attempt!=1||
  !hexValid(g.SourceSHA,40)||g.SourceSHA!=ctx.SourceSHA||
  g.SourceSHA!=scope.SourceCommitSHA||
  !hexValid(g.TreeSHA,40)||g.TreeSHA!=ctx.TreeSHA||
  g.Lane!=ctx.Lane||g.Lane!=scope.Lane||
  (g.Lane!="Wingless"&&g.Lane!="Yggdrasil")||
  g.Generation!=scope.Generation||g.ExperimentID!=scope.ExperimentID||
  g.CohortSHA256!=scope.CandidateCohortSHA256||
  g.PreregSHA256!=scope.PreregSHA256||
  g.ArchiveID==""||!hexValid(g.ArchiveID,64)||
  g.AuthorityEpoch!=scope.AuthorityEpoch||
  g.MaxComputeUnits!=scope.MaxComputeUnits||
  g.MaxComputeUnits<1||g.MaxComputeUnits>1000000||
  !validName(g.ExperimentID)||!validName(g.CandidateID)||
  !hexValid(g.CohortSHA256,64)||!hexValid(g.PreregSHA256,64)||
  !hexValid(g.ScopeSHA256,64)||!hexValid(g.FirstUsePlanSHA256,64)||
  !hexValid(g.FirstUseProofSHA256,64)||
  !hexValid(g.StartedRecordSHA256,64)||
  !hexValid(g.CommittedHeadSHA256,64)||g.ScienceRunID==0{
  return empty,ErrDenied
 }
 scopeSHA,err:=sha(scope)
 if err!=nil||scopeSHA!=g.ScopeSHA256{return empty,ErrDenied}
 proofSHA,err:=sha(firstuse)
 if err!=nil||proofSHA!=g.FirstUseProofSHA256||
  firstuse.Schema!=fsagate.FirstUseProofSchema||
  firstuse.Mode!="EXTERNAL_FSA_FIRST_USE_OBSERVED_NO_DISPATCH"||
  !firstuse.FSAFirstUseCommitted||!firstuse.FirstUseConsumed||
  firstuse.ScientificAccepted||firstuse.DispatchAuthorized||
  firstuse.AcceptedRefMutation||firstuse.PhysicalIndependenceDemonstrated||
  firstuse.PlanSHA256!=g.FirstUsePlanSHA256||
  firstuse.Lane!=g.Lane||firstuse.CandidateID!=g.CandidateID||
  firstuse.CohortSHA256!=g.CohortSHA256||
  firstuse.StartedRecordSHA256!=g.StartedRecordSHA256||
  firstuse.ObservedTrustedSequence!=g.CommittedSequence||
  firstuse.ObservedTrustedHeadSHA256!=g.CommittedHeadSHA256{
   return empty,ErrDenied
 }
 grantSHA,err:=sha(g)
 if err!=nil||grantSHA!=pin.GrantSHA256{return empty,ErrDenied}
 grantRaw,_:=json.Marshal(g)
 sig,_:=hex.DecodeString(e.SignatureHex)
 pub,_:=hex.DecodeString(pin.GrantKeyHex)
 if !ed25519.Verify(ed25519.PublicKey(pub),
  append([]byte(Domain),grantRaw...),sig){return empty,ErrDenied}
 // This does NOT attest that source code, external FSA, host, key custody
 // and sealed data belong to independent physically trusted parties.
 // Nor does a signed envelope prevent concurrent attempts without
 // a protected FSA state transition on the original cohort.
 return Review{Schema:ReviewSchema,
  Mode:"CRYPTOGRAPHIC_REVIEW_ONLY_NO_EXECUTION",
  GrantSHA256:grantSHA,FirstUseProofSHA256:proofSHA,
  SourceSHA:g.SourceSHA,Lane:g.Lane,CohortSHA256:g.CohortSHA256,
  FirstUseObserved:true},nil
}
