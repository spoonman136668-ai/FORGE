// Package historycoverage inventories public GitHub metadata without executing
// science or mistaking a PR/CI/archive digest for authenticated original custody.
package historycoverage

import (
 "bufio"
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "sort"
 "strings"
)
const Schema="forge.research-history-coverage.v1"
const MaxInputBytes=32<<20
const MaxEntries=15000
var ErrBlocked=errors.New("FORGE_HISTORY_SOURCE_COVERAGE_UNVERIFIED")
type Run struct{
 ID uint64 `json:"id"`
 RunAttempt uint64 `json:"run_attempt"`
 HeadSHA string `json:"head_sha"`
 Status string `json:"status"`
 Conclusion *string `json:"conclusion"`
 Path string `json:"path"`
 Repository struct{FullName string `json:"full_name"`} `json:"repository"`
}
type Artifact struct{
 ID uint64 `json:"id"`
 Name string `json:"name"`
 Expired bool `json:"expired"`
 Digest string `json:"digest"`
 Size uint64 `json:"size_in_bytes"`
 WorkflowRun struct{ID uint64 `json:"id"`;HeadSHA string `json:"head_sha"`} `json:"workflow_run"`
}
type Source struct{
 Lane string
 Runs []byte
 Artifacts []byte
 DeclaredRuns uint64
 DeclaredArtifacts uint64
}
type Original struct{
 Lane string `json:"lane"`
 RunID uint64 `json:"run_id"`
 ArtifactID uint64 `json:"artifact_id"`
 ArtifactName string `json:"artifact_name"`
 HeadSHA string `json:"head_sha"`
 Digest string `json:"digest"`
 Status string `json:"status"`
}
type LaneReport struct{
 Lane string `json:"lane"`
 Repository string `json:"repository"`
 DeclaredRunCount uint64 `json:"declared_run_count"`
 ObservedRunCount int `json:"observed_run_count"`
 DeclaredArtifactCount uint64 `json:"declared_artifact_count"`
 ObservedArtifactCount int `json:"observed_artifact_count"`
 CompleteAccessiblePagination bool `json:"complete_accessible_pagination"`
 OriginalNamedCount int `json:"original_named_count"`
 OriginalExpiredCount int `json:"original_expired_count"`
 OriginalMissingDigestCount int `json:"original_missing_digest_count"`
 OriginalUnverifiedAvailableCount int `json:"original_unverified_available_count"`
 ArtifactOrphanCount int `json:"artifact_orphan_count"`
 ArtifactSourceDriftCount int `json:"artifact_source_drift_count"`
 RunsSHA256 string `json:"runs_sha256"`
 ArtifactsSHA256 string `json:"artifacts_sha256"`
}
type Report struct{
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Wingless LaneReport `json:"wingless"`
 Yggdrasil LaneReport `json:"yggdrasil"`
 OriginalObservations []Original `json:"original_observations"`
 GithubAccessibleSnapshotReconciled bool `json:"github_accessible_snapshot_reconciled"`
 FullHistoricalScientificCoverageVerified bool `json:"full_historical_scientific_coverage_verified"`
 LongTermOriginalBytesRetained bool `json:"long_term_original_bytes_retained"`
 IndependentScientificCustodyQualified bool `json:"independent_scientific_custody_qualified"`
 NewScientificExecution bool `json:"new_scientific_execution"`
 AcceptedRefMutation bool `json:"accepted_ref_mutation"`
}
func sha(b []byte)string{h:=sha256.Sum256(b);return hex.EncodeToString(h[:])}
func validSHA(s string)bool{if len(s)!=40{return false};for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}};return true}
func validDigest(s string)bool{if !strings.HasPrefix(s,"sha256:")||len(s)!=71{return false};for _,c:=range s[7:]{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}};return true}
func parseLines[T any](raw []byte)([]T,error){
 if len(raw)==0||len(raw)>MaxInputBytes{return nil,ErrBlocked}
 scanner:=bufio.NewScanner(bytes.NewReader(raw))
 scanner.Buffer(make([]byte,4096),1<<20)
 out:=[]T{}
 for scanner.Scan(){
  if len(out)>=MaxEntries||len(scanner.Bytes())==0{return nil,ErrBlocked}
  var item T
  d:=json.NewDecoder(bytes.NewReader(scanner.Bytes()))
  if d.Decode(&item)!=nil||d.Decode(new(any))!=io.EOF{return nil,ErrBlocked}
  out=append(out,item)
 }
 if scanner.Err()!=nil||len(out)==0{return nil,ErrBlocked}
 return out,nil
}
func lane(s Source)(LaneReport,[]Original,error){
 var zero LaneReport
 if s.Lane!="Wingless"&&s.Lane!="Yggdrasil"{return zero,nil,ErrBlocked}
 repo:="spoonman136668-ai/"+s.Lane
 runs,err:=parseLines[Run](s.Runs);if err!=nil{return zero,nil,err}
 arts,err:=parseLines[Artifact](s.Artifacts);if err!=nil{return zero,nil,err}
 report:=LaneReport{Lane:s.Lane,Repository:repo,DeclaredRunCount:s.DeclaredRuns,ObservedRunCount:len(runs),DeclaredArtifactCount:s.DeclaredArtifacts,ObservedArtifactCount:len(arts),RunsSHA256:sha(s.Runs),ArtifactsSHA256:sha(s.Artifacts)}
 ids:=map[uint64]Run{}
 for _,r:=range runs{
  if r.ID==0||r.RunAttempt==0||!validSHA(r.HeadSHA)||r.Repository.FullName!=repo||ids[r.ID].ID!=0{return zero,nil,ErrBlocked}
  ids[r.ID]=r
 }
 if s.DeclaredRuns==0||s.DeclaredArtifacts==0||s.DeclaredRuns>MaxEntries||s.DeclaredArtifacts>MaxEntries{return zero,nil,ErrBlocked}
 seen:=map[uint64]bool{}
 results:=[]Original{}
 for _,a:=range arts{
  if a.ID==0||a.WorkflowRun.ID==0||seen[a.ID]||len(a.Name)==0||len(a.Name)>256{return zero,nil,ErrBlocked}
  seen[a.ID]=true
  ref,found:=ids[a.WorkflowRun.ID]
  if !found{report.ArtifactOrphanCount++}
  if !validSHA(a.WorkflowRun.HeadSHA)||found&&a.WorkflowRun.HeadSHA!=ref.HeadSHA{report.ArtifactSourceDriftCount++}
  // Names are only heuristic candidates, not proof that all science originals
  // are discoverable or that any original was accepted.
  if !strings.Contains(strings.ToLower(a.Name),"original"){continue}
  report.OriginalNamedCount++
  status:="AVAILABLE_METADATA_ONLY_RAW_BYTES_UNVERIFIED"
  switch{
  case !found:status="ORPHAN_RUN_UNRESOLVED"
  case a.WorkflowRun.HeadSHA!=ref.HeadSHA:status="SOURCE_IDENTITY_DRIFT"
  case a.Expired:status="EXPIRED_BYTES_UNAVAILABLE_FROM_GITHUB"
  case !validDigest(a.Digest):status="DIGEST_MISSING_OR_MALFORMED"
  case a.Size==0:status="EMPTY_ARCHIVE"
  }
  if a.Expired{report.OriginalExpiredCount++}
  if !validDigest(a.Digest){report.OriginalMissingDigestCount++}
  if status=="AVAILABLE_METADATA_ONLY_RAW_BYTES_UNVERIFIED"{report.OriginalUnverifiedAvailableCount++}
  results=append(results,Original{Lane:s.Lane,RunID:a.WorkflowRun.ID,ArtifactID:a.ID,ArtifactName:a.Name,HeadSHA:a.WorkflowRun.HeadSHA,Digest:a.Digest,Status:status})
 }
 report.CompleteAccessiblePagination=uint64(len(runs))==s.DeclaredRuns&&uint64(len(arts))==s.DeclaredArtifacts&&report.ArtifactOrphanCount==0&&report.ArtifactSourceDriftCount==0
 return report,results,nil
}
// Build is a complete pagination *accounting* test for the API's visible
// window, not a claim about deleted runs, original bytes, prereg or custody.
func Build(a,b Source)(Report,error){
 var zero Report
 if a.Lane!="Wingless"||b.Lane!="Yggdrasil"{return zero,ErrBlocked}
 w,wo,err:=lane(a);if err!=nil{return zero,fmt.Errorf("%w: Wingless: %v",ErrBlocked,err)}
 y,yo,err:=lane(b);if err!=nil{return zero,fmt.Errorf("%w: Yggdrasil: %v",ErrBlocked,err)}
 records:=append(wo,yo...)
 sort.Slice(records,func(i,j int)bool{if records[i].Lane!=records[j].Lane{return records[i].Lane<records[j].Lane};if records[i].RunID!=records[j].RunID{return records[i].RunID<records[j].RunID};return records[i].ArtifactID<records[j].ArtifactID})
 return Report{Schema:Schema,Mode:"GITHUB_ACCESSIBLE_METADATA_AUDIT_NOT_RAW_CUSTODY",Wingless:w,Yggdrasil:y,OriginalObservations:records,
  GithubAccessibleSnapshotReconciled:w.CompleteAccessiblePagination&&y.CompleteAccessiblePagination},nil
}
