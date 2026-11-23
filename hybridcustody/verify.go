// Package hybridcustody checks detached, bounded Hybrid engineering artifact
// attestations. Caller-provided signer keys and source pins must be qualified
// independently; this library does not authenticate GitHub, dispatch, or science.
package hybridcustody

import (
 "bytes"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "strconv"
 "strings"
)

const (
 Project = "spoonman136668-ai/TTT-Hybrid-Lab"
 StatementSchema = "forge.hybrid.engineering-attestation.v1"
 ReportSchema = "forge.hybrid.engineering-consistency.v1"
 SignatureDomain = "FORGE-HYBRID-ENGINEERING-ATTESTATION-V1\n"
 MaxProtocolBytes = 256 << 10
 MaxArtifactBytes = 2 << 20
 MaxStatementBytes = 8 << 10
)
var ErrUnverified = errors.New("FORGE_HYBRID_EVIDENCE_UNVERIFIED")

type Statement struct {
 Schema string `json:"schema"`
 Repository string `json:"repository"`
 PullRequest uint64 `json:"pull_request"`
 PullRequestURL string `json:"pull_request_url"`
 SourceSHA string `json:"source_sha"`
 ProtocolPath string `json:"protocol_path"`
 ProtocolSHA256 string `json:"protocol_sha256"`
 EvidenceKind string `json:"evidence_kind"`
 ArtifactName string `json:"artifact_name"`
 ArtifactSHA256 string `json:"artifact_sha256"`
 WorkflowRunID uint64 `json:"workflow_run_id"`
 WorkflowAttempt uint64 `json:"workflow_attempt"`
}
type Expected struct {
 // These are trusted *caller* requirements, not derived from the statement.
 // A live caller must obtain them from a separately qualified source witness.
 SourceSHA string
 PullRequest uint64
 ProtocolPath string
 TrustedPublicKey ed25519.PublicKey
}
type Report struct {
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Repository string `json:"repository"`
 SourceSHA string `json:"source_sha"`
 PullRequest uint64 `json:"pull_request"`
 ProtocolPath string `json:"protocol_path"`
 ProtocolSHA256 string `json:"protocol_sha256"`
 EvidenceKind string `json:"evidence_kind"`
 ArtifactSHA256 string `json:"artifact_sha256"`
 WorkflowRunID uint64 `json:"workflow_run_id"`
 WorkflowAttempt uint64 `json:"workflow_attempt"`
 AttestationSHA256 string `json:"attestation_sha256"`
 PublicKeySHA256 string `json:"public_key_sha256"`
 SignatureVerified bool `json:"signature_verified"`
 PayloadDigestsMatch bool `json:"payload_digests_match"`
 GitHubSourceAuthenticated bool `json:"github_source_authenticated"`
 FirstUseAuthenticated bool `json:"first_use_authenticated"`
 ExecutionAuthorized bool `json:"execution_authorized"`
 ScientificAccepted bool `json:"scientific_accepted"`
}
func digest(b []byte) string{
 h:=sha256.Sum256(b)
 return hex.EncodeToString(h[:])
}
func hexString(s string,expected int) bool{
 if len(s)!=expected{return false}
 for _,c:=range s{
  if !((c>='0'&&c<='9')||(c>='a'&&c<='f')){return false}
 }
 return true
}
func safePath(p string)bool{
 if len(p)<24||len(p)>160||!strings.HasPrefix(p,"experiments/g7_s")||
  !strings.HasSuffix(p,".json")||strings.Contains(p,"..")||
  strings.ContainsAny(p,"\\\r\n\t ") {return false}
 for _,c:=range p{
  if !((c>='a'&&c<='z')||(c>='0'&&c<='9')||
   c=='_'||c=='-'||c=='.'||c=='/') {return false}
 }
 return true
}
func safeName(n string)bool{
 if len(n)<1||len(n)>128||strings.Contains(n,".."){return false}
 for _,c:=range n{
  if !((c>='a'&&c<='z')||(c>='0'&&c<='9')||
   c=='_'||c=='-'||c=='.'){return false}
 }
 return true
}
// decodeStrict requires canonical bytes and rejects duplicate/case-folded
// keys, unknown fields, coercions, formatting ambiguity, and appended values.
// Statement signatures bind these exact bytes, not untrusted parsed text.
func decodeStrict(raw []byte)(Statement,error){
 var s Statement
 if len(raw)==0||len(raw)>MaxStatementBytes{return s,ErrUnverified}
 dec:=json.NewDecoder(bytes.NewReader(raw))
 dec.DisallowUnknownFields()
 if err:=dec.Decode(&s);err!=nil{return Statement{},ErrUnverified}
 var extra any
 if err:=dec.Decode(&extra);!errors.Is(err,io.EOF){return Statement{},ErrUnverified}
 canonical,err:=json.Marshal(s)
 if err!=nil||!bytes.Equal(canonical,raw){return Statement{},ErrUnverified}
 return s,nil
}
func validStatement(s Statement,expected Expected)bool{
 if s.Schema!=StatementSchema||s.Repository!=Project||
  s.PullRequest==0||s.PullRequest>99999999||s.PullRequest!=expected.PullRequest||
  s.PullRequestURL!="https://github.com/"+Project+"/pull/"+strconv.FormatUint(s.PullRequest,10)||
  !hexString(s.SourceSHA,40)||s.SourceSHA!=expected.SourceSHA||
  !safePath(s.ProtocolPath)||s.ProtocolPath!=expected.ProtocolPath||
  !hexString(s.ProtocolSHA256,64)||!hexString(s.ArtifactSHA256,64)||
  !safeName(s.ArtifactName){return false}
 switch s.EvidenceKind{
 case "FROZEN_PROTOCOL":
  return s.WorkflowRunID==0&&s.WorkflowAttempt==0&&
   s.ArtifactName=="protocol"&&s.ArtifactSHA256==s.ProtocolSHA256
 case "ENGINEERING_RECEIPT":
  return s.WorkflowRunID>0&&s.WorkflowAttempt>0&&
   s.WorkflowAttempt<=9999&&s.ArtifactName!="protocol"
 default:return false
 }
}
// Verify checks detached Ed25519 evidence and the exact supplied payloads
// against an independently supplied source/issuer pin. It DOES NOT authenticate
// the GitHub origin, scientific first-use, runner authority, or scientific PASS.
// Signature validity alone must never authorize an experiment.
func Verify(protocolRaw,artifactRaw,statementRaw,signature []byte,expected Expected)(Report,error){
 var zero Report
 if len(protocolRaw)==0||len(protocolRaw)>MaxProtocolBytes||
  len(artifactRaw)==0||len(artifactRaw)>MaxArtifactBytes||
  len(signature)!=ed25519.SignatureSize||len(expected.TrustedPublicKey)!=ed25519.PublicKeySize||
  !hexString(expected.SourceSHA,40)||expected.PullRequest==0||
  !safePath(expected.ProtocolPath){return zero,ErrUnverified}
 statement,err:=decodeStrict(statementRaw)
 if err!=nil||!validStatement(statement,expected){return zero,ErrUnverified}
 if !ed25519.Verify(expected.TrustedPublicKey,
  append([]byte(SignatureDomain),statementRaw...),signature){return zero,ErrUnverified}
 if digest(protocolRaw)!=statement.ProtocolSHA256||
  digest(artifactRaw)!=statement.ArtifactSHA256{return zero,ErrUnverified}
 if statement.EvidenceKind=="FROZEN_PROTOCOL"&&!bytes.Equal(protocolRaw,artifactRaw){
  return zero,ErrUnverified
 }
 return Report{
  Schema:ReportSchema,Mode:"SIGNED_CONSISTENCY_ONLY_NO_SCIENTIFIC_OR_EXECUTION_AUTHORITY",
  Repository:Project,SourceSHA:statement.SourceSHA,
  PullRequest:statement.PullRequest,ProtocolPath:statement.ProtocolPath,
  ProtocolSHA256:statement.ProtocolSHA256,EvidenceKind:statement.EvidenceKind,
  ArtifactSHA256:statement.ArtifactSHA256,WorkflowRunID:statement.WorkflowRunID,
  WorkflowAttempt:statement.WorkflowAttempt,AttestationSHA256:digest(statementRaw),
  PublicKeySHA256:digest(expected.TrustedPublicKey),
  SignatureVerified:true,PayloadDigestsMatch:true,
 },nil
}
