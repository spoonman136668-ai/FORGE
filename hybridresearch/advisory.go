// Package hybridresearch validates offline TTT-Hybrid-Lab experiment metadata.
// It does not dispatch work, read a repository, authenticate scientific evidence,
// or change the two-lane FORGE lifecycle.
package hybridresearch

import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "sort"
 "strconv"
 "strings"
)

const (
 SnapshotSchema = "forge.hybrid.candidate-snapshot.v1"
 ReportSchema = "forge.hybrid.candidate-advisory.v1"
 Project = "spoonman136668-ai/TTT-Hybrid-Lab"
 MaximumBytes = 128 << 10
 MaximumCandidates = 64
)
var ErrUnverified = errors.New("FORGE_HYBRID_CANDIDATE_SOURCE_UNVERIFIED")

// Candidate records an external proposal *identity*, never a training request.
// SHA strings are syntactic claims until a separate authorized source witness
// verifies the actual source and protocol bytes.
type Candidate struct {
 ExperimentID string `json:"experiment_id"`
 PullRequest uint64 `json:"pull_request"`
 HeadSHA string `json:"head_sha"`
 ProtocolSHA256 string `json:"protocol_sha256"`
 PullRequestURL string `json:"pull_request_url"`
 Stage string `json:"stage"`
}
type Snapshot struct {
 Schema string `json:"schema"`
 Repository string `json:"repository"`
 Candidates []Candidate `json:"candidates"`
}
type Observed struct {
 Candidate
 Classification string `json:"classification"`
 SourceAuthenticated bool `json:"source_authenticated"`
 OriginalFirstUseAuthenticated bool `json:"original_first_use_authenticated"`
 ScientificAccepted bool `json:"scientific_accepted"`
}
type Report struct {
 Schema string `json:"schema"`
 Repository string `json:"repository"`
 SnapshotSHA256 string `json:"snapshot_sha256"`
 Mode string `json:"mode"`
 Candidates []Observed `json:"candidates"`
 ExecutionAuthorized bool `json:"execution_authorized"`
 TrainingExecuted bool `json:"training_executed"`
 OriginalFirstUseAuthenticated bool `json:"original_first_use_authenticated"`
 ScientificAccepted bool `json:"scientific_accepted"`
}
func validHex(s string, n int) bool {
 if len(s)!=n {return false}
 for _,c:=range s {
  if !((c>='0'&&c<='9')||(c>='a'&&c<='f')) {return false}
 }
 return true
}
func validExperimentID(s string) bool {
 if len(s)<1||len(s)>96 {return false}
 for _,c:=range s {
  if !((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'||c=='-') {return false}
 }
 return true
}
func valid(c Candidate) bool {
 if !validExperimentID(c.ExperimentID)||c.PullRequest==0||c.PullRequest>99999999||
  !validHex(c.HeadSHA,40)||!validHex(c.ProtocolSHA256,64) {return false}
 if c.PullRequestURL!="https://github.com/"+Project+"/pull/"+strconv.FormatUint(c.PullRequest,10) {return false}
 return c.Stage=="PROTOCOL_DESIGN"||c.Stage=="ENGINEERING_CANDIDATE"
}
// noDuplicateKeys rejects duplicate JSON keys, including case-folded nested
// keys. json.Decoder.DisallowUnknownFields alone does not prevent ambiguity.
func noDuplicateKeys(raw []byte) bool {
 dec:=json.NewDecoder(bytes.NewReader(raw))
 var scan func(int)bool
 scan=func(depth int)bool {
  if depth>32 {return false}
  token,err:=dec.Token()
  if err!=nil {return false}
  open,ok:=token.(json.Delim)
  if !ok {return true}
  if open!='{'&&open!='[' {return false}
  used:=make(map[string]bool)
  for dec.More() {
   if open=='{' {
    keyToken,err:=dec.Token()
    if err!=nil {return false}
    key,ok:=keyToken.(string)
    if !ok||len(key)==0||len(key)>128 {return false}
    folded:=strings.ToLower(key)
    if used[folded] {return false}
    used[folded]=true
   }
   if !scan(depth+1) {return false}
  }
  closeToken,err:=dec.Token()
  if err!=nil {return false}
  close,ok:=closeToken.(json.Delim)
  if !ok {return false}
  return (open=='{'&&close=='}')||(open=='['&&close==']')
 }
 if !scan(0) {return false}
 var rest any
 return errors.Is(dec.Decode(&rest),io.EOF)
}
// Inspect is deterministic, read-only and unconditionally non-authorizing.
// Input may be generated from authorized source metadata, but it is not
// itself independent custody or first-use evidence.
func Inspect(raw []byte) (Report,error) {
 var zero Report
 if len(raw)==0||len(raw)>MaximumBytes||!noDuplicateKeys(raw) {return zero,ErrUnverified}
 dec:=json.NewDecoder(bytes.NewReader(raw))
 dec.DisallowUnknownFields()
 var s Snapshot
 if err:=dec.Decode(&s);err!=nil {return zero,ErrUnverified}
 var extra any
 if err:=dec.Decode(&extra);!errors.Is(err,io.EOF) {return zero,ErrUnverified}
 if s.Schema!=SnapshotSchema||s.Repository!=Project||
  len(s.Candidates)==0||len(s.Candidates)>MaximumCandidates {return zero,ErrUnverified}
 seenID,seenPR:=make(map[string]bool),make(map[uint64]bool)
 observed:=make([]Observed,0,len(s.Candidates))
 for _,c:=range s.Candidates {
  if !valid(c)||seenID[c.ExperimentID]||seenPR[c.PullRequest] {return zero,ErrUnverified}
  seenID[c.ExperimentID]=true
  seenPR[c.PullRequest]=true
  observed=append(observed,Observed{
   Candidate:c,Classification:"UNVERIFIED_NOT_SCIENTIFIC_EVIDENCE",
  })
 }
 sort.Slice(observed,func(i,j int)bool {
  if observed[i].ExperimentID!=observed[j].ExperimentID {return observed[i].ExperimentID<observed[j].ExperimentID}
  return observed[i].PullRequest<observed[j].PullRequest
 })
 sum:=sha256.Sum256(raw)
 return Report{
  Schema:ReportSchema,Repository:Project,SnapshotSHA256:hex.EncodeToString(sum[:]),
  Mode:"READ_ONLY_SOURCE_CLAIMS_NOT_DISPATCH_ELIGIBILITY",
  Candidates:observed,
 },nil
}
// VerifyOutput ensures downstream consumers cannot silently upgrade a
// metadata-only report into scientific or execution authority.
func VerifyOutput(report Report) error {
 if report.Schema!=ReportSchema||report.Repository!=Project||
  report.Mode!="READ_ONLY_SOURCE_CLAIMS_NOT_DISPATCH_ELIGIBILITY"||
  !validHex(report.SnapshotSHA256,64)||report.ExecutionAuthorized||
  report.TrainingExecuted||report.OriginalFirstUseAuthenticated||
  report.ScientificAccepted||len(report.Candidates)==0||
  len(report.Candidates)>MaximumCandidates {return ErrUnverified}
 seenID,seenPR:=make(map[string]bool),make(map[uint64]bool)
 previous:=""
 for _,o:=range report.Candidates{
  if !valid(o.Candidate)||seenID[o.ExperimentID]||seenPR[o.PullRequest]||
   (previous!=""&&o.ExperimentID<=previous)||
   o.Classification!="UNVERIFIED_NOT_SCIENTIFIC_EVIDENCE"||
   o.SourceAuthenticated||o.OriginalFirstUseAuthenticated||o.ScientificAccepted {
   return fmt.Errorf("%w: authority or identity drift",ErrUnverified)
  }
  previous=o.ExperimentID
  seenID[o.ExperimentID]=true
  seenPR[o.PullRequest]=true
 }
 return nil
}
