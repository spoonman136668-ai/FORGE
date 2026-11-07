// Package hybridrunnerpreview checks proposed Hybrid GPU work against
// resource and no-replay constraints without dispatching or reserving work.
// Caller-supplied host/history records are untrusted advisory inputs.
package hybridrunnerpreview

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "strconv"
)

const (
 Schema = "forge.hybrid.disabled-runner-preview.v1"
 Project = "spoonman136668-ai/TTT-Hybrid-Lab"
 RunnerName = "TTT-HYBRID-GPU-WIN"
 RunnerLabel = "ttt-hybrid-gpu-isolated"
 MaxHostObservationAgeSeconds uint64 = 60
 MaxRequestedVRAMMiB uint64 = 4096
 MaxWallSeconds uint64 = 480
 MinimumOtherProjectReserveMiB uint64 = 2048
 MinimumGPUSafetyMarginMiB uint64 = 1024
 MaxHistory = 128
)
var ErrBlocked = errors.New("FORGE_HYBRID_RUNNER_PREVIEW_UNVERIFIED")

type Request struct {
 Repository string `json:"repository"`
 SourceSHA string `json:"source_sha"`
 ProtocolSHA256 string `json:"protocol_sha256"`
 PullRequest uint64 `json:"pull_request"`
 PullRequestURL string `json:"pull_request_url"`
 OriginalID string `json:"original_id"`
 RunnerName string `json:"runner_name"`
 RunnerLabel string `json:"runner_label"`
 RequestedVRAMMiB uint64 `json:"requested_vram_mib"`
 RequestedWallSeconds uint64 `json:"requested_wall_seconds"`
 RequestedConcurrentGPUJobs uint64 `json:"requested_concurrent_gpu_jobs"`
}
type HostObservation struct {
 Repository string `json:"repository"`
 RunnerName string `json:"runner_name"`
 RunnerLabel string `json:"runner_label"`
 ObservedAtUnix uint64 `json:"observed_at_unix"`
 Online bool `json:"online"`
 Idle bool `json:"idle"`
 ActiveForeignGPUJobs uint64 `json:"active_foreign_gpu_jobs"`
 ActiveHybridGPUJobs uint64 `json:"active_hybrid_gpu_jobs"`
 TotalVRAMMiB uint64 `json:"total_vram_mib"`
 FreeVRAMMiB uint64 `json:"free_vram_mib"`
 ReservedForOtherProjectsMiB uint64 `json:"reserved_for_other_projects_mib"`
}
type Attempt struct {
 OriginalID string `json:"original_id"`
 SourceSHA string `json:"source_sha"`
 Status string `json:"status"`
}
type Result struct {
 Schema string `json:"schema"`
 Repository string `json:"repository"`
 RequestSHA256 string `json:"request_sha256"`
 Status string `json:"status"`
 Reason string `json:"reason"`
 TargetRunner string `json:"target_runner"`
 ReviewedAttemptCount int `json:"reviewed_attempt_count"`
 SourceAuthenticated bool `json:"source_authenticated"`
 HostAuthenticated bool `json:"host_authenticated"`
 NoPriorAttemptIndependentlyWitnessed bool `json:"no_prior_attempt_independently_witnessed"`
 GPUReserved bool `json:"gpu_reserved"`
 ExecutionAuthorized bool `json:"execution_authorized"`
 ResearchDispatched bool `json:"research_dispatched"`
}
func isLowerHex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{
  if !((c>='0'&&c<='9')||(c>='a'&&c<='f')){return false}
 }
 return true
}
func validID(s string)bool{
 if len(s)==0||len(s)>80{return false}
 for _,c:=range s{
  if !((c>='a'&&c<='z')||(c>='A'&&c<='Z')||
   (c>='0'&&c<='9')||c=='-'||c=='_'){return false}
 }
 return true
}
func validRequest(r Request)bool{
 return r.Repository==Project&&isLowerHex(r.SourceSHA,40)&&
  isLowerHex(r.ProtocolSHA256,64)&&r.PullRequest>0&&r.PullRequest<100000000&&
  r.PullRequestURL=="https://github.com/"+Project+"/pull/"+strconv.FormatUint(r.PullRequest,10)&&
  validID(r.OriginalID)&&r.RunnerName==RunnerName&&r.RunnerLabel==RunnerLabel&&
  r.RequestedVRAMMiB>=1024&&r.RequestedVRAMMiB<=MaxRequestedVRAMMiB&&
  r.RequestedWallSeconds>=1&&r.RequestedWallSeconds<=MaxWallSeconds&&
  r.RequestedConcurrentGPUJobs==1
}
func validHistory(history []Attempt)bool{
 if len(history)>MaxHistory{return false}
 seen:=make(map[string]bool)
 for _,a:=range history{
  if !validID(a.OriginalID)||!isLowerHex(a.SourceSHA,40)||seen[a.OriginalID]{
   return false
  }
  seen[a.OriginalID]=true
  switch a.Status{
  case "RECORDED", "START_RISK", "CONSUMED", "TERMINAL", "QUARANTINED":
  default:return false
  }
 }
 return true
}
func newResult(r Request,history []Attempt)Result{
 payload,_:=json.Marshal(r)
 hash:=sha256.Sum256(append([]byte("FORGE-HYBRID-RUNNER-PREVIEW-V1\n"),payload...))
 return Result{
  Schema:Schema,Repository:Project,RequestSHA256:hex.EncodeToString(hash[:]),
  Status:"BLOCKED",Reason:"UNQUALIFIED_INPUT",
  TargetRunner:RunnerName,ReviewedAttemptCount:len(history),
 }
}
// Evaluate returns a non-executing review for a prospective research request.
// Even a REVIEW_ONLY result cannot reserve resources, call GitHub, start a
// worker, certify original non-consumption or grant scientific first-use.
// Repeated OriginalIDs fail closed regardless of their recorded outcome.
func Evaluate(r Request,host HostObservation,history []Attempt,nowUnix uint64)(Result,error){
 var zero Result
 if !validRequest(r)||!validHistory(history)||nowUnix==0{return zero,ErrBlocked}
 out:=newResult(r,history)
 for _,a:=range history{
  if a.OriginalID==r.OriginalID{
   out.Reason="PRIOR_OR_INDETERMINATE_ORIGINAL_NO_REPLAY"
   return out,nil
  }
 }
 if host.Repository!=Project||host.RunnerName!=RunnerName||
  host.RunnerLabel!=RunnerLabel||host.ObservedAtUnix==0||
  nowUnix<host.ObservedAtUnix||
  nowUnix-host.ObservedAtUnix>MaxHostObservationAgeSeconds{
  out.Reason="HOST_IDENTITY_OR_FRESHNESS_UNVERIFIED"
  return out,nil
 }
 if !host.Online||!host.Idle||host.ActiveForeignGPUJobs>0||
  host.ActiveHybridGPUJobs>0{
  out.Reason="HOST_BUSY_OR_OTHER_RESEARCH_ACTIVE"
  return out,nil
 }
 if host.ReservedForOtherProjectsMiB<MinimumOtherProjectReserveMiB||
  host.TotalVRAMMiB<host.ReservedForOtherProjectsMiB||
  host.FreeVRAMMiB>host.TotalVRAMMiB{
  out.Reason="OTHER_RESEARCH_RESOURCE_RESERVE_UNVERIFIED"
  return out,nil
 }
 // Subtraction avoids integer overflow and treats reservation as unavailable
 // even when the reported instantaneous free VRAM looks sufficient.
 // Conservatively subtract all of the claimed foreign-project reserve
 // from both physical capacity AND currently free VRAM. A planning
 // observation cannot double-spend another research lane's allocation.
 // The bounded request and margin make the addition overflow-safe.
 needed:=r.RequestedVRAMMiB+MinimumGPUSafetyMarginMiB
 if host.TotalVRAMMiB-host.ReservedForOtherProjectsMiB<needed||
  host.FreeVRAMMiB<host.ReservedForOtherProjectsMiB||
  host.FreeVRAMMiB-host.ReservedForOtherProjectsMiB<needed{
  out.Reason="INSUFFICIENT_UNRESERVED_GPU_MEMORY"
  return out,nil
 }
 out.Status="REVIEW_ONLY"
 out.Reason="RESOURCE_CLAIMS_APPEAR_WITHIN_BUDGET_NOT_AUTHORIZATION"
 return out,nil
}
func validReason(status,reason string)bool{
 switch status{
 case "REVIEW_ONLY":
  return reason=="RESOURCE_CLAIMS_APPEAR_WITHIN_BUDGET_NOT_AUTHORIZATION"
 case "BLOCKED":
  switch reason{
  case "PRIOR_OR_INDETERMINATE_ORIGINAL_NO_REPLAY",
   "HOST_IDENTITY_OR_FRESHNESS_UNVERIFIED",
   "HOST_BUSY_OR_OTHER_RESEARCH_ACTIVE",
   "OTHER_RESEARCH_RESOURCE_RESERVE_UNVERIFIED",
   "INSUFFICIENT_UNRESERVED_GPU_MEMORY":
   return true
  }
 }
 return false
}
// AssertNonAuthorizing rejects forged statuses/reasons, negative or oversized
// attempt counts, and every claim of dispatch or independent custody.
func AssertNonAuthorizing(r Result)error{
 if r.Schema!=Schema||r.Repository!=Project||r.TargetRunner!=RunnerName||
  !isLowerHex(r.RequestSHA256,64)||r.GPUReserved||
  r.ExecutionAuthorized||r.ResearchDispatched||r.SourceAuthenticated||
  r.HostAuthenticated||r.NoPriorAttemptIndependentlyWitnessed||
  r.ReviewedAttemptCount<0||r.ReviewedAttemptCount>MaxHistory||
  !validReason(r.Status,r.Reason){return ErrBlocked}
 return nil
}
