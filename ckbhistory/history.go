// Package ckbhistory independently inspects ORIGINAL S14 GitHub Actions
// attempts and issuer artifacts in the existing CKB-plane repository.
// It performs only authenticated GET requests and never dispatches workflows,
// retries first-use, modifies CKB, or grants FORGE scientific authority.
package ckbhistory

import (
 "bytes"
 "context"
 "crypto/sha256"
 "crypto/tls"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "net/http"
 "sort"
 "strings"
 "time"
)
const Schema="forge.ckb.s14-github-history.v1"
const FixedBase="https://api.github.com/repos/spoonman136668-ai/ckb-plane"
const OriginalPath=".github/workflows/r216-s14-synthetic-execute.yml"
const ArtifactName="ckb-s14-genesis-intent"
const maxJSON=1048576
const runsPath="/actions/workflows/r216-s14-synthetic-execute.yml/runs?per_page=100"
const artifactsPath="/actions/artifacts?name=ckb-s14-genesis-intent&per_page=100"
var ErrBlocked=errors.New("FORGE_CKB_S14_GITHUB_FIRST_USE_INDETERMINATE_NO_RETRY")

type Client struct{
 endpoint string
 token string
 httpClient *http.Client
}
type run struct {
 ID int64 `json:"id"`
 Path string `json:"path"`
 Event string `json:"event"`
 HeadBranch string `json:"head_branch"`
 HeadSHA string `json:"head_sha"`
 RunAttempt int `json:"run_attempt"`
 Status string `json:"status"`
 Conclusion *string `json:"conclusion"`
}
type artifact struct{
 ID int64 `json:"id"`
 Name string `json:"name"`
 Digest string `json:"digest"`
 Expired bool `json:"expired"`
 WorkflowRun struct{ID int64 `json:"id"`} `json:"workflow_run"`
}
type runsResponse struct{
 TotalCount int `json:"total_count"`
 WorkflowRuns []run `json:"workflow_runs"`
}
type artifactsResponse struct{
 TotalCount int `json:"total_count"`
 Artifacts []artifact `json:"artifacts"`
}
type Report struct{
 Schema string `json:"schema"`
 Repository string `json:"repository"`
 OriginalWorkflow string `json:"original_workflow"`
 OriginalRunIDs []int64 `json:"original_run_ids"`
 OriginalAttemptCount int `json:"original_attempt_count"`
 IntentArtifactIDs []int64 `json:"intent_artifact_ids"`
 IntentArtifactCount int `json:"intent_artifact_count"`
 Classification string `json:"classification"`
 FirstUseReplayAuthorized bool `json:"first_use_replay_authorized"`
 ScientificExecutionActivated bool `json:"scientific_execution_activated"`
 EvidenceSHA256 string `json:"evidence_sha256"`
}
func validHash(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func New(token string)(*Client,error){
 if len(token)<21||len(token)>4096||strings.TrimSpace(token)!=token||
  strings.ContainsAny(token,"\r\n\x00"){return nil,ErrBlocked}
 transport:=&http.Transport{TLSClientConfig:&tls.Config{MinVersion:tls.VersionTLS12},
  DisableCompression:true,TLSHandshakeTimeout:5*time.Second}
 return &Client{endpoint:FixedBase,token:token,httpClient:&http.Client{
  Timeout:20*time.Second,Transport:transport,
  CheckRedirect:func(*http.Request,[]*http.Request)error{return ErrBlocked},
 }},nil
}
// hasDuplicateKeys rejects ambiguity anywhere in externally sourced JSON.
// Unknown harmless GitHub API fields may exist, but duplicate keys do not.
func hasDuplicateKeys(raw []byte)bool{
 d:=json.NewDecoder(bytes.NewReader(raw));d.UseNumber()
 var scan func()error
 scan=func()error{
  tok,err:=d.Token();if err!=nil{return err}
  delim,ok:=tok.(json.Delim)
  if !ok{return nil}
  if delim!='{'&&delim!='['{return ErrBlocked}
  known:=map[string]bool{}
  for d.More(){
   if delim=='{'{
    key,err:=d.Token();if err!=nil{return err}
    s,ok:=key.(string)
    if !ok||known[s]{return ErrBlocked}
    known[s]=true
   }
   if err:=scan();err!=nil{return err}
  }
  end,err:=d.Token()
  if err!=nil{return err}
  if delim=='{'&&end!=json.Delim('}')||delim=='['&&end!=json.Delim(']'){return ErrBlocked}
  return nil
 }
 if err:=scan();err!=nil{return true}
 _,err:=d.Token()
 return !errors.Is(err,io.EOF)
}
func (c *Client)get(ctx context.Context,path string,destination any)error{
 if c==nil||ctx==nil||ctx.Err()!=nil||c.httpClient==nil||
  len(c.token)<21||c.endpoint==""||(path!=runsPath&&path!=artifactsPath){return ErrBlocked}
 request,err:=http.NewRequestWithContext(ctx,http.MethodGet,c.endpoint+path,nil)
 if err!=nil{return ErrBlocked}
 request.Header.Set("Authorization","Bearer "+c.token)
 request.Header.Set("Accept","application/vnd.github+json")
 request.Header.Set("X-GitHub-Api-Version","2022-11-28")
 request.Header.Set("User-Agent","forge-ckb-s14-read-only-firstuse-audit")
 resp,err:=c.httpClient.Do(request)
 if err!=nil{return ErrBlocked}
 defer resp.Body.Close()
 if resp.StatusCode!=http.StatusOK{return ErrBlocked}
 data,err:=io.ReadAll(io.LimitReader(resp.Body,maxJSON+1))
 if err!=nil||len(data)==0||len(data)>maxJSON||hasDuplicateKeys(data){return ErrBlocked}
 if err=json.Unmarshal(data,destination);err!=nil{return ErrBlocked}
 return nil
}
func uniquePositive(ids []int64)bool{
 seen:=map[int64]bool{}
 for _,id:=range ids{if id<=0||seen[id]{return false};seen[id]=true}
 return true
}
func classification(runCount,artifactCount int)string{
 if runCount>1||artifactCount>1{return "MULTIPLE_ORIGINAL_OR_ISSUER_ATTEMPTS_QUARANTINE_NO_REPLAY"}
 if runCount==1{return "ORIGINAL_ATTEMPT_RECORDED_NO_REPLAY"}
 if artifactCount==1{return "ISSUER_INTENT_ARCHIVED_ORIGINAL_UNKNOWN_NO_REPLAY"}
 return "NO_GITHUB_RECORD_IS_NOT_FIRST_USE_CLEARANCE"
}
// InspectS14 reports complete first-page histories only. An empty workflow
// listing cannot prove local private original-first-use was never consumed.
func(c *Client)InspectS14(ctx context.Context)(Report,error){
 var runs runsResponse
 if err:=c.get(ctx,runsPath,&runs);err!=nil{return Report{},ErrBlocked}
 if runs.TotalCount<0||runs.TotalCount>100||len(runs.WorkflowRuns)!=runs.TotalCount{
  return Report{},ErrBlocked
 }
 ids:=[]int64{}
 for _,r:=range runs.WorkflowRuns{
  if r.ID<=0||r.Path!=OriginalPath||r.Event!="workflow_dispatch"||
   r.HeadBranch!="main"||!validHash(r.HeadSHA,40)||r.RunAttempt!=1||
   (r.Status!="queued"&&r.Status!="in_progress"&&r.Status!="completed")||
   (r.Status=="completed"&&r.Conclusion==nil)||
   (r.Status!="completed"&&r.Conclusion!=nil){return Report{},ErrBlocked}
  ids=append(ids,r.ID)
 }
 if !uniquePositive(ids){return Report{},ErrBlocked}
 var artifacts artifactsResponse
 if err:=c.get(ctx,artifactsPath,&artifacts);err!=nil{return Report{},ErrBlocked}
 if artifacts.TotalCount<0||artifacts.TotalCount>100||
  len(artifacts.Artifacts)!=artifacts.TotalCount{return Report{},ErrBlocked}
 artifactIDs:=[]int64{}
 for _,a:=range artifacts.Artifacts{
  if a.ID<=0||a.WorkflowRun.ID<=0||a.Expired||a.Name!=ArtifactName||
   !strings.HasPrefix(a.Digest,"sha256:")||
   !validHash(strings.TrimPrefix(a.Digest,"sha256:"),64){
   return Report{},ErrBlocked
  }
  artifactIDs=append(artifactIDs,a.ID)
 }
 if !uniquePositive(artifactIDs){return Report{},ErrBlocked}
 sort.Slice(ids,func(i,j int)bool{return ids[i]<ids[j]})
 sort.Slice(artifactIDs,func(i,j int)bool{return artifactIDs[i]<artifactIDs[j]})
 result:=Report{Schema:Schema,Repository:"spoonman136668-ai/ckb-plane",
  OriginalWorkflow:OriginalPath,OriginalRunIDs:ids,
  OriginalAttemptCount:len(ids),IntentArtifactIDs:artifactIDs,
  IntentArtifactCount:len(artifactIDs),
  Classification:classification(len(ids),len(artifactIDs)),
  FirstUseReplayAuthorized:false,ScientificExecutionActivated:false}
 raw,err:=json.Marshal(result);if err!=nil{return Report{},ErrBlocked}
 h:=sha256.Sum256(append([]byte("FORGE-CKB-S14-HISTORY-V1\n"),raw...))
 result.EvidenceSHA256=hex.EncodeToString(h[:])
 return result,nil
}
