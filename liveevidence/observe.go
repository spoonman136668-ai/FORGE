// Package liveevidence reads exact public GitHub TRAIN experiment metadata.
// It never grants scientific first-use, independent custody, or execution.
package liveevidence
import (
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "net/http"
 "strconv"
 "strings"
 "time"
)
const Schema="forge.f57.pinned-github-train-metadata.v1"
var ErrBlocked=errors.New("FORGE_F57_EXTERNAL_TRAIN_METADATA_DRIFT_OR_UNAVAILABLE")
const maxResponse int64=2<<20
type pin struct {Lane,Repo,Source,ArtifactName,ArchiveDigest string;RunID,ArtifactID int64}
var frozen=[4]pin{
 {"Wingless","spoonman136668-ai/Wingless","11eec04d174489c99d037f5990e893390c39d5b8","W-F54-new-transition-learning-TRAIN-not-original","sha256:88579b1a7f07dd7acedaf6a47ba6205b3cff74cc077800244497f74a2ce42a87",38818822125,12011653051},
 {"Wingless","spoonman136668-ai/Wingless","d1be885e5d3bbef8f5828a3d195cb3354f755881","W-F54-active-calibration-new-TRAIN-not-F3-original","sha256:d3a984c4b2cbbc34a79e623bdabc7a2f5ed0498390b862765fc419e2279707d0",38819060318,12012406590},
 {"Yggdrasil","spoonman136668-ai/Yggdrasil","9fb99e9c23d5eddad411e31078c8ea40d3c873af","Y-F54-one-TRAIN-only-global-memory-and-evidence","sha256:21162c1e706336ed3772cc9693558d52fb3763a4a59c6b89d45b517ec76b839a",38819086470,12011953258},
 {"Yggdrasil","spoonman136668-ai/Yggdrasil","4ae4066bfbdb7ee5fe1f85abe840cf61f280269d","Y-F54B-new-cohort-corrected-witness-TRAIN-not-F3","sha256:17c84623f3c61226aca71fb9ce85c9379544751ab905c1d186662de2092ede69",38820489117,12013360275},
}
type Observation struct {
 Lane string `json:"lane"`
 Repository string `json:"repository"`
 SourceSHA string `json:"source_sha"`
 RunID int64 `json:"run_id"`
 ArtifactID int64 `json:"artifact_id"`
 ArtifactName string `json:"artifact_name"`
 ArchiveDigest string `json:"github_archive_digest"`
 RunMetadataSHA256 string `json:"run_metadata_sha256"`
 ArtifactListSHA256 string `json:"artifact_list_sha256"`
 RunCreatedAt string `json:"run_created_at"`
 Disposition string `json:"disposition"`
}
type Report struct {
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Records [4]Observation `json:"records"`
 PinnedGithubRunMetadataObserved bool `json:"pinned_github_run_metadata_observed"`
 PinnedGithubArtifactMetadataObserved bool `json:"pinned_github_artifact_metadata_observed"`
 ArchiveContentsAuthenticated bool `json:"archive_contents_authenticated"`
 OriginalStartTerminalSignaturesAuthenticated bool `json:"original_start_terminal_signatures_authenticated"`
 IndependentOwnerHighWaterVerified bool `json:"independent_owner_highwater_verified"`
 DistributedFirstUseCASVerified bool `json:"distributed_first_use_cas_verified"`
 NewProtectedOriginalsExecuted bool `json:"new_protected_originals_executed"`
 UnattendedSuccessorProven bool `json:"unattended_successor_proven"`
 ScientificAcceptanceAuthorized bool `json:"scientific_acceptance_authorized"`
 ResearchDispatchAuthorized bool `json:"research_dispatch_authorized"`
 OwnerCutoverAuthorized bool `json:"owner_cutover_authorized"`
}
type runPayload struct {
 ID int64 `json:"id"`
 HeadSHA string `json:"head_sha"`
 RunAttempt int `json:"run_attempt"`
 Status string `json:"status"`
 Conclusion string `json:"conclusion"`
 CreatedAt string `json:"created_at"`
 Repository struct{FullName string `json:"full_name"`} `json:"repository"`
}
type artifactList struct {
 TotalCount int `json:"total_count"`
 Artifacts []struct{
  ID int64 `json:"id"`
  Name string `json:"name"`
  Expired bool `json:"expired"`
  Digest string `json:"digest"`
  WorkflowRun *struct{ID int64 `json:"id"`} `json:"workflow_run"`
 } `json:"artifacts"`
}
func sum(raw []byte)string{h:=sha256.Sum256(raw);return hex.EncodeToString(h[:])}
func read(ctx context.Context,c *http.Client,url,token string)([]byte,error){
 if ctx==nil||ctx.Err()!=nil||c==nil||!strings.HasPrefix(url,"https://api.github.com/repos/spoonman136668-ai/"){return nil,ErrBlocked}
 req,err:=http.NewRequestWithContext(ctx,"GET",url,nil)
 if err!=nil{return nil,ErrBlocked}
 req.Header.Set("Accept","application/vnd.github+json")
 req.Header.Set("User-Agent","FORGE-F57-read-only")
 req.Header.Set("X-GitHub-Api-Version","2022-11-28")
 if token!=""{req.Header.Set("Authorization","Bearer "+token)}
 resp,err:=c.Do(req)
 if err!=nil{return nil,ErrBlocked}
 defer resp.Body.Close()
 if resp.StatusCode!=200||resp.Request==nil||resp.Request.URL.String()!=url{return nil,ErrBlocked}
 b,err:=io.ReadAll(io.LimitReader(resp.Body,maxResponse+1))
 if err!=nil||len(b)==0||int64(len(b))>maxResponse{return nil,ErrBlocked}
 return b,nil
}
func decode(b []byte,target any)error{
 d:=json.NewDecoder(strings.NewReader(string(b)))
 if d.Decode(target)!=nil{return ErrBlocked}
 var tail any
 if d.Decode(&tail)!=io.EOF{return ErrBlocked}
 return nil
}
// Observe checks LIVE public GitHub run/artifact metadata under frozen pins.
// Signed receipt provenance and scientific acceptance are NOT established.
func Observe(ctx context.Context,c *http.Client,token string)(Report,error){
 var zero Report
 if ctx==nil||ctx.Err()!=nil||c==nil{return zero,ErrBlocked}
 out:=Report{Schema:Schema,Mode:"READ_ONLY_GITHUB_TRAIN_METADATA_NOT_PROTECTED_SCIENCE"}
 seenRuns:=map[int64]bool{};seenArtifacts:=map[int64]bool{}
 lastCreated:=map[string]time.Time{}
 for i,p:=range frozen{
  if seenRuns[p.RunID]||seenArtifacts[p.ArtifactID]{return zero,ErrBlocked}
  seenRuns[p.RunID]=true;seenArtifacts[p.ArtifactID]=true
  base:="https://api.github.com/repos/"+p.Repo+"/actions/runs/"+strconv.FormatInt(p.RunID,10)
  raw,err:=read(ctx,c,base,token)
  if err!=nil{return zero,fmt.Errorf("%w: %s run",ErrBlocked,p.Lane)}
  var run runPayload
  if decode(raw,&run)!=nil||run.ID!=p.RunID||run.HeadSHA!=p.Source||
   run.RunAttempt!=1||run.Status!="completed"||run.Conclusion!="success"||
   run.Repository.FullName!=p.Repo{return zero,ErrBlocked}
  created,err:=time.Parse(time.RFC3339,run.CreatedAt)
  if err!=nil||created.IsZero(){return zero,ErrBlocked}
  if prev,ok:=lastCreated[p.Lane];ok&&!created.After(prev){return zero,ErrBlocked}
  lastCreated[p.Lane]=created
  artifacts,err:=read(ctx,c,base+"/artifacts?per_page=100",token)
  if err!=nil{return zero,fmt.Errorf("%w: %s artifacts",ErrBlocked,p.Lane)}
  var a artifactList
  if decode(artifacts,&a)!=nil||a.TotalCount<1||a.TotalCount>100||
   len(a.Artifacts)!=a.TotalCount{return zero,ErrBlocked}
  matches:=0
  for _,entry:=range a.Artifacts{
   if entry.ID!=p.ArtifactID{continue}
   if entry.Name!=p.ArtifactName||entry.Expired||entry.Digest!=p.ArchiveDigest{return zero,ErrBlocked}
   if entry.WorkflowRun!=nil&&entry.WorkflowRun.ID!=p.RunID{return zero,ErrBlocked}
   matches++
  }
  if matches!=1{return zero,ErrBlocked}
  out.Records[i]=Observation{Lane:p.Lane,Repository:p.Repo,SourceSHA:p.Source,
   RunID:p.RunID,ArtifactID:p.ArtifactID,ArtifactName:p.ArtifactName,
   ArchiveDigest:p.ArchiveDigest,RunMetadataSHA256:sum(raw),
   ArtifactListSHA256:sum(artifacts),RunCreatedAt:run.CreatedAt,
   Disposition:"HISTORICAL_TRAIN_ONLY_NO_F3_FIRST_USE_AUTHORITY"}
 }
 if ctx.Err()!=nil{return zero,ErrBlocked}
 out.PinnedGithubRunMetadataObserved=true
 out.PinnedGithubArtifactMetadataObserved=true
 return out,nil
}
