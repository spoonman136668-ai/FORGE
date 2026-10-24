// RSH-04A: read-only original source byte integrity, without scientific authority.
package researchfeed

import (
 "context"
 "crypto/sha1"
 "crypto/sha256"
 "encoding/hex"
 "errors"
 "strconv"
)

const MaxOriginalBytes = 1 << 20
var ErrOriginalBlocked = errors.New("FORGE_RESEARCH_ORIGINAL_SOURCE_INTEGRITY_BLOCKED")

// OriginalPin must come from an independently controlled immutable source,
// never the untrusted proposed index or Mind-Palace advisory context.
type OriginalPin struct {
 Lane, ResearchID, SourceRepo, SourceCommit, SourcePath string
 BlobSHA1, BytesSHA256 string
}

// OriginalBlob must be returned by a separate read-only source adapter. The
// adapter must independently verify commit/tree/path -> Git blob identity.
// Merely returning self-consistent hashes does not authenticate provenance.
type OriginalBlob struct {
 SourceRepo, SourceCommit, SourcePath, BlobSHA1 string
 Bytes []byte
}
type ReadonlyOriginalSource interface {
 ReadOriginalAt(context.Context, string, string, string) (OriginalBlob, error)
}
type OriginalIntegrityObservation struct {
 Schema string `json:"schema"`
 IndexSHA256 string `json:"index_sha256"`
 Lane string `json:"lane"`
 ResearchID string `json:"research_id"`
 SourceRepo string `json:"source_repo"`
 SourceCommit string `json:"source_commit"`
 SourcePath string `json:"source_path"`
 BlobSHA1 string `json:"blob_sha1"`
 BytesSHA256 string `json:"bytes_sha256"`
 OriginalSize int `json:"original_size"`
 AdvisoryOnly bool `json:"advisory_only"`
 BlobIntegrityVerified bool `json:"blob_integrity_verified"`
 OriginalBytesAuthenticated bool `json:"original_bytes_authenticated"`
 ExternalSignerVerified bool `json:"external_signer_verified"`
 OriginalFirstUseCleared bool `json:"original_first_use_cleared"`
 ScientificAccepted bool `json:"scientific_accepted"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
}
func validOriginalPin(p OriginalPin) bool {
 return safeID(p.ResearchID) && repoFor(p.Lane,p.SourceRepo,p.SourcePath) &&
  safePath(p.SourcePath) && hexLower(p.SourceCommit,40) &&
  hexLower(p.BlobSHA1,40) && hexLower(p.BytesSHA256,64)
}
// ObserveOriginalIntegrity checks the entire proposed six-lane index BEFORE
// any external read, then verifies one pinned original. It never copies raw
// source bytes into observations or clears signer/first-use/science gates.
func ObserveOriginalIntegrity(ctx context.Context, rawIndex []byte, pin OriginalPin, source ReadonlyOriginalSource)(OriginalIntegrityObservation,error){
 var zero OriginalIntegrityObservation
 if ctx==nil||ctx.Err()!=nil||source==nil||!validOriginalPin(pin){return zero,ErrOriginalBlocked}
 preview,err:=PreviewCandidates(rawIndex)
 if err!=nil||!preview.AdvisoryOnly||preview.OriginalBytesAuthenticated||
  preview.ScientificAccepted||preview.ExecutionAuthorized{return zero,ErrOriginalBlocked}
 found:=false
 for _,entry:=range preview.Entries {
  if entry.Lane!=pin.Lane||entry.ResearchID!=pin.ResearchID{continue}
  if found||entry.SourceRepo!=pin.SourceRepo||entry.SourceCommit!=pin.SourceCommit||
   entry.SourcePath!=pin.SourcePath||
   (entry.ReportedSHA256!=""&&entry.ReportedSHA256!=pin.BytesSHA256){
   return zero,ErrOriginalBlocked
  }
  found=true
 }
 if !found||ctx.Err()!=nil{return zero,ErrOriginalBlocked}
 orig,err:=source.ReadOriginalAt(ctx,pin.SourceRepo,pin.SourceCommit,pin.SourcePath)
 if err!=nil||ctx.Err()!=nil||len(orig.Bytes)==0||len(orig.Bytes)>MaxOriginalBytes||
  orig.SourceRepo!=pin.SourceRepo||orig.SourceCommit!=pin.SourceCommit||
  orig.SourcePath!=pin.SourcePath||orig.BlobSHA1!=pin.BlobSHA1{return zero,ErrOriginalBlocked}
 framed:=make([]byte,0,len(orig.Bytes)+48)
 framed=append(framed,[]byte("blob "+strconv.Itoa(len(orig.Bytes))+"\x00")...)
 framed=append(framed,orig.Bytes...)
 blob:=sha1.Sum(framed)
 digest:=sha256.Sum256(orig.Bytes)
 if hex.EncodeToString(blob[:])!=pin.BlobSHA1||
  hex.EncodeToString(digest[:])!=pin.BytesSHA256{return zero,ErrOriginalBlocked}
 return OriginalIntegrityObservation{
  Schema:"forge.research-single-source-byte-integrity.v1",IndexSHA256:preview.InputSHA256,
  Lane:pin.Lane,ResearchID:pin.ResearchID,SourceRepo:pin.SourceRepo,
  SourceCommit:pin.SourceCommit,SourcePath:pin.SourcePath,
  BlobSHA1:pin.BlobSHA1,BytesSHA256:pin.BytesSHA256,
  OriginalSize:len(orig.Bytes),AdvisoryOnly:true,BlobIntegrityVerified:true,
 },nil
}
