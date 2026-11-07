package hybridrunnerpreview

import (
 "strings"
 "testing"
)
func request()Request{
 return Request{
  Repository:Project,SourceSHA:strings.Repeat("a",40),ProtocolSHA256:strings.Repeat("b",64),
  PullRequest:39,PullRequestURL:"https://github.com/"+Project+"/pull/39",
  OriginalID:"S24-GPU-DEV-1",RunnerName:RunnerName,RunnerLabel:RunnerLabel,
  RequestedVRAMMiB:3072,RequestedWallSeconds:420,RequestedConcurrentGPUJobs:1,
 }
}
func host()HostObservation{
 return HostObservation{
  Repository:Project,RunnerName:RunnerName,RunnerLabel:RunnerLabel,
  ObservedAtUnix:1800000000,Online:true,Idle:true,
  TotalVRAMMiB:12288,FreeVRAMMiB:10000,ReservedForOtherProjectsMiB:4096,
 }
}
func TestDisabledPreviewNeverGrantsExecutionEvenOnFavorableObservations(t *testing.T){
 r,h:=request(),host()
 out,err:=Evaluate(r,h,nil,1800000030)
 if err!=nil||out.Status!="REVIEW_ONLY"||out.ResearchDispatched||
  out.ExecutionAuthorized||out.GPUReserved||out.SourceAuthenticated||
  out.HostAuthenticated||out.NoPriorAttemptIndependentlyWitnessed{t.Fatalf("unsafe preview %+v %v",out,err)}
 if err:=AssertNonAuthorizing(out);err!=nil{t.Fatal(err)}
 second,err:=Evaluate(r,h,nil,1800000030)
 if err!=nil||second.RequestSHA256!=out.RequestSHA256{t.Fatal("not deterministic",err)}
}
func TestNoReplayRegardlessOfAttemptOutcome(t *testing.T){
 r,h:=request(),host()
 for _,state:=range []string{"RECORDED","START_RISK","CONSUMED","TERMINAL","QUARANTINED"}{
  prior:=[]Attempt{{OriginalID:r.OriginalID,SourceSHA:r.SourceSHA,Status:state}}
  out,err:=Evaluate(r,h,prior,1800000030)
  if err!=nil||out.Status!="BLOCKED"||
   out.Reason!="PRIOR_OR_INDETERMINATE_ORIGINAL_NO_REPLAY"{t.Fatal(state,out,err)}
  if err:=AssertNonAuthorizing(out);err!=nil{t.Fatal(err)}
 }
 r.OriginalID="S24-GPU-NEW-1"
 out,err:=Evaluate(r,h,[]Attempt{{
  OriginalID:"S24-GPU-DEV-1",SourceSHA:r.SourceSHA,Status:"CONSUMED",
 }},1800000030)
 if err!=nil||out.Status!="REVIEW_ONLY"||out.ExecutionAuthorized{
  t.Fatal("new proposal cannot gain authority",out,err)
 }
}
func TestProtectSharedRunnersAndResourceBudgets(t *testing.T){
 r,h:=request(),host()
 cases:=[]struct{name string;modify func(*HostObservation);reason string}{
  {"active foreign science",func(h *HostObservation){h.ActiveForeignGPUJobs=1},"HOST_BUSY_OR_OTHER_RESEARCH_ACTIVE"},
  {"hybrid currently running",func(h *HostObservation){h.ActiveHybridGPUJobs=1},"HOST_BUSY_OR_OTHER_RESEARCH_ACTIVE"},
  {"offline",func(h *HostObservation){h.Online=false},"HOST_BUSY_OR_OTHER_RESEARCH_ACTIVE"},
  {"busy",func(h *HostObservation){h.Idle=false},"HOST_BUSY_OR_OTHER_RESEARCH_ACTIVE"},
  {"wrong project runner",func(h *HostObservation){h.Repository="spoonman136668-ai/FORGE"},"HOST_IDENTITY_OR_FRESHNESS_UNVERIFIED"},
  {"wrong runner label",func(h *HostObservation){h.RunnerLabel="forge-codex-isolated"},"HOST_IDENTITY_OR_FRESHNESS_UNVERIFIED"},
  {"stale observation",func(h *HostObservation){h.ObservedAtUnix-=100},"HOST_IDENTITY_OR_FRESHNESS_UNVERIFIED"},
  {"unknown free memory",func(h *HostObservation){h.FreeVRAMMiB=0},"INSUFFICIENT_UNRESERVED_GPU_MEMORY"},
  {"insufficient margin",func(h *HostObservation){h.FreeVRAMMiB=r.RequestedVRAMMiB+512},"INSUFFICIENT_UNRESERVED_GPU_MEMORY"},
  {"insufficient reserve",func(h *HostObservation){h.ReservedForOtherProjectsMiB=0},"OTHER_RESEARCH_RESOURCE_RESERVE_UNVERIFIED"},
  {"impossible VRAM report",func(h *HostObservation){h.FreeVRAMMiB=h.TotalVRAMMiB+1},"OTHER_RESEARCH_RESOURCE_RESERVE_UNVERIFIED"},
  {"overflow avoid",func(h *HostObservation){h.ReservedForOtherProjectsMiB=^uint64(0)},"OTHER_RESEARCH_RESOURCE_RESERVE_UNVERIFIED"},
 }
 for _,tc:=range cases{
  t.Run(tc.name,func(t *testing.T){
   candidate:=h;tc.modify(&candidate)
   got,err:=Evaluate(r,candidate,nil,1800000030)
   if err!=nil||got.Status!="BLOCKED"||got.Reason!=tc.reason{t.Fatal(got,err)}
  })
 }
}
func TestInputAndHistoryDriftCannotBecomeEligible(t *testing.T){
 r,h:=request(),host()
 invalid:=[]struct{name string;modify func(*Request)}{
  {"foreign repo",func(r *Request){r.Repository="other/project"}},
  {"foreign url",func(r *Request){r.PullRequestURL="https://github.com/other/project/pull/39"}},
  {"bad source pin",func(r *Request){r.SourceSHA="x"}},
  {"bad protocol",func(r *Request){r.ProtocolSHA256="x"}},
  {"bad original id",func(r *Request){r.OriginalID="../oops"}},
  {"foreign runner",func(r *Request){r.RunnerName="FORGE-CODEX-REMOTE"}},
  {"foreign label",func(r *Request){r.RunnerLabel="forge-codex-isolated"}},
  {"no job",func(r *Request){r.RequestedConcurrentGPUJobs=0}},
  {"two jobs",func(r *Request){r.RequestedConcurrentGPUJobs=2}},
  {"excess budget",func(r *Request){r.RequestedVRAMMiB=8192}},
  {"no wall limit",func(r *Request){r.RequestedWallSeconds=0}},
  {"excess wall",func(r *Request){r.RequestedWallSeconds=10000}},
 }
 for _,tc:=range invalid{
  t.Run(tc.name,func(t *testing.T){
   req:=r;tc.modify(&req)
   if _,err:=Evaluate(req,h,nil,1800000030);err==nil{t.Fatal("unsafe request accepted")}
  })
 }
 for _,history:=range [][]Attempt{
  {{OriginalID:r.OriginalID,SourceSHA:r.SourceSHA,Status:"UNKNOWN"}},
  {{OriginalID:r.OriginalID,SourceSHA:"bad",Status:"START_RISK"}},
  {{OriginalID:r.OriginalID,SourceSHA:r.SourceSHA,Status:"RECORDED"},
   {OriginalID:r.OriginalID,SourceSHA:r.SourceSHA,Status:"CONSUMED"}},
 }{
  if _,err:=Evaluate(r,h,history,1800000030);err==nil{t.Fatal("unsafe history accepted")}
 }
}
func TestCannotUpgradePlanningOutput(t *testing.T){
 r,h:=request(),host()
 out,err:=Evaluate(r,h,nil,1800000030)
 if err!=nil{t.Fatal(err)}
 for _,mutate:=range []func(*Result){
  func(x *Result){x.ExecutionAuthorized=true},
  func(x *Result){x.ResearchDispatched=true},
  func(x *Result){x.GPUReserved=true},
  func(x *Result){x.SourceAuthenticated=true},
  func(x *Result){x.HostAuthenticated=true},
  func(x *Result){x.NoPriorAttemptIndependentlyWitnessed=true},
  func(x *Result){x.Status="EXECUTING"},
  func(x *Result){x.Reason="READY_TO_DISPATCH"},
 }{
  x:=out;mutate(&x)
  if err:=AssertNonAuthorizing(x);err==nil{t.Fatal("authority forgery accepted",x)}
 }
}
