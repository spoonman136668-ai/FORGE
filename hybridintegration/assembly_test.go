package hybridintegration

import (
 "bytes"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/hybridcustody"
 "github.com/spoonman136668-ai/forge/hybridresearch"
 "github.com/spoonman136668-ai/forge/hybridrunnerpreview"
 "github.com/spoonman136668-ai/forge/researchstate"
 "github.com/spoonman136668-ai/forge/researchstatepreview"
)
func sum(b []byte)string{
 x:=sha256.Sum256(b)
 return hex.EncodeToString(x[:])
}
func envelope(repo,sha string,run uint64)[]byte{
 row:=map[string]any{
  "id":run,"run_attempt":uint64(1),"name":"Engineering only verified",
  "head_sha":sha,"head_branch":"engineering/frozen","status":"completed",
  "conclusion":"success","created_at":"2026-11-07T00:00:00Z",
  "html_url":"https://github.com/"+repo+"/actions/runs/5303",
  "repository":map[string]string{"full_name":repo},
  "head_repository":map[string]string{"full_name":repo},
 }
 b,_:=json.Marshal(map[string]any{
  "total_count":uint64(1),"workflow_runs":[]any{row},
 })
 return b
}
func fixture(t *testing.T)Input{
 t.Helper()
 sourceSHA:=strings.Repeat("a",40)
 proto:=[]byte("{\"frozen\":true,\"scope\":\"engineering-only\"}")
 artifact:=[]byte("{\"training\":\"NOT_RUN\"}")
 pSHA:=sum(proto)
 pubSeed:=sha256.Sum256([]byte("synthetic-test-only-not-a-trust-anchor"))
 private:=ed25519.NewKeyFromSeed(pubSeed[:])
 repo:=hybridcustody.Project
 protocolPath:="experiments/g7_s24_frozen_good_views.json"
 expected:=hybridcustody.Expected{
  SourceSHA:sourceSHA,PullRequest:39,ProtocolPath:protocolPath,
  TrustedPublicKey:private.Public().(ed25519.PublicKey),
 }
 att:=hybridcustody.Statement{
  Schema:hybridcustody.StatementSchema,Repository:repo,
  PullRequest:39,PullRequestURL:"https://github.com/"+repo+"/pull/39",
  SourceSHA:sourceSHA,ProtocolPath:protocolPath,ProtocolSHA256:pSHA,
  EvidenceKind:"ENGINEERING_RECEIPT",ArtifactName:"engineering_receipt.json",
  ArtifactSHA256:sum(artifact),WorkflowRunID:5303,WorkflowAttempt:1,
 }
 statement,_:=json.Marshal(att)
 signature:=ed25519.Sign(private,append([]byte(hybridcustody.SignatureDomain),statement...))
 snapshot,_:=json.Marshal(hybridresearch.Snapshot{
  Schema:hybridresearch.SnapshotSchema,Repository:repo,
  Candidates:[]hybridresearch.Candidate{{
   ExperimentID:"G7-S24",PullRequest:39,HeadSHA:sourceSHA,
   ProtocolSHA256:pSHA,PullRequestURL:"https://github.com/"+repo+"/pull/39",
   Stage:"ENGINEERING_CANDIDATE",
  }},
 })
 j:=researchstate.New()
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  head,err:=researchstate.Head(j);if err!=nil{t.Fatal(err)}
  j,err=researchstate.Append(j,researchstate.Event{
   Lane:lane,ExperimentID:"existing",FrozenSHA256:strings.Repeat("d",64),
   To:researchstate.Proposed,
  },head)
  if err!=nil{t.Fatal(err)}
 }
 originalHead,err:=researchstate.Head(j);if err!=nil{t.Fatal(err)}
 preview,err:=researchstatepreview.Build(j,originalHead,nil)
 if err!=nil{t.Fatal(err)}
 for _,step:=range []struct{from,to researchstatepreview.Phase}{
  {"",researchstatepreview.Observed},
  {researchstatepreview.Observed,researchstatepreview.ProtocolFrozen},
  {researchstatepreview.ProtocolFrozen,researchstatepreview.EngineeringChecked},
 }{
  preview,err=researchstatepreview.Advance(j,originalHead,preview,researchstatepreview.Event{
   Lane:"Hybrid",ExperimentID:"G7-S24",ProtocolSHA256:pSHA,
   From:step.from,To:step.to,
  })
  if err!=nil{t.Fatal(err)}
 }
 return Input{
  WinglessWorkflowRaw:envelope("spoonman136668-ai/Wingless",sourceSHA,5303),
  YggdrasilWorkflowRaw:envelope("spoonman136668-ai/Yggdrasil",sourceSHA,5303),
  HybridWorkflowRaw:envelope(repo,sourceSHA,5303),
  CandidateSnapshotRaw:snapshot,SelectedExperimentID:"G7-S24",
  ProtocolRaw:proto,ArtifactRaw:artifact,StatementRaw:statement,
  Signature:signature,Expected:expected,
  LegacyJournal:j,ExpectedLegacyHeadSHA256:originalHead,
  HybridShadowEvents:preview.Hybrid,
  RunnerRequest:hybridrunnerpreview.Request{
   Repository:repo,SourceSHA:sourceSHA,ProtocolSHA256:pSHA,
   PullRequest:39,PullRequestURL:"https://github.com/"+repo+"/pull/39",
   OriginalID:"S24-TEST-0001",RunnerName:hybridrunnerpreview.RunnerName,
   RunnerLabel:hybridrunnerpreview.RunnerLabel,
   RequestedVRAMMiB:3072,RequestedWallSeconds:420,
   RequestedConcurrentGPUJobs:1,
  },
  Host:hybridrunnerpreview.HostObservation{
   Repository:repo,RunnerName:hybridrunnerpreview.RunnerName,
   RunnerLabel:hybridrunnerpreview.RunnerLabel,
   ObservedAtUnix:1800000000,Online:true,Idle:true,
   TotalVRAMMiB:12288,FreeVRAMMiB:10000,
   ReservedForOtherProjectsMiB:4096,
  },
  NowUnix:1800000030,
  ClaimedHybridFirstUseLedgerHeadSHA256:strings.Repeat("e",64),
 }
}
func TestCoherentInactiveIntegrationDoesNotLaunchOrPromote(t *testing.T){
 in:=fixture(t)
 before,_:=json.Marshal(in.LegacyJournal)
 result,err:=Assemble(in)
 if err!=nil{t.Fatal(err)}
 if err:=Validate(result);err!=nil{t.Fatal(err)}
 if result.Handoff.ReviewStatus!="REVIEW_ONLY"||
  result.ExecutionAuthorized||result.ResearchDispatched||
  result.ScientificAccepted||result.IndependentGitHubSourceAuthenticated||
  result.IndependentHybridFirstUseAuthenticated||
  !result.Handoff.RequiresIndependentSourceAndFirstUseWitness{
  t.Fatal("inactive integration claimed authority",result)
 }
 again,err:=Assemble(in)
 if err!=nil||again.Handoff.HandoffSHA256!=result.Handoff.HandoffSHA256{
  t.Fatal("non-deterministic inactive integration",err)
 }
 after,_:=json.Marshal(in.LegacyJournal)
 if !bytes.Equal(before,after){t.Fatal("altered old scientific journal")}
}
func TestInactiveIntegrationFailsClosedOnProvenanceAndEvidenceDrift(t *testing.T){
 in:=fixture(t)
 tests:=[]struct{name string;mutate func(*Input)}{
  {"wrong attestation signature",func(x *Input){x.Signature=append([]byte(nil),x.Signature...);x.Signature[0]^=0xff}},
  {"changed protocol bytes",func(x *Input){x.ProtocolRaw=[]byte("changed")}},
  {"changed artifact bytes",func(x *Input){x.ArtifactRaw=[]byte("changed")}},
  {"wrong source pin",func(x *Input){x.RunnerRequest.SourceSHA=strings.Repeat("f",40)}},
  {"wrong protocol pin",func(x *Input){x.RunnerRequest.ProtocolSHA256=strings.Repeat("f",64)}},
  {"wrong PR",func(x *Input){x.RunnerRequest.PullRequest=40;x.RunnerRequest.PullRequestURL="https://github.com/"+hybridcustody.Project+"/pull/40"}},
  {"wrong experiment",func(x *Input){x.SelectedExperimentID="G7-S25"}},
  {"wrong signed issuer",func(x *Input){x.Expected.TrustedPublicKey=ed25519.PublicKey(strings.Repeat("z",32))}},
  {"wrong workflow run",func(x *Input){x.HybridWorkflowRaw=bytes.Replace(x.HybridWorkflowRaw,[]byte("5303"),[]byte("5304"),1)}},
  {"failed workflow",func(x *Input){x.HybridWorkflowRaw=bytes.Replace(x.HybridWorkflowRaw,[]byte(`"conclusion":"success"`),[]byte(`"conclusion":"failure"`),1)}},
  {"wrong candidate source",func(x *Input){x.CandidateSnapshotRaw=bytes.Replace(x.CandidateSnapshotRaw,[]byte(strings.Repeat("a",40)),[]byte(strings.Repeat("f",40)),1)}},
  {"missing shadow",func(x *Input){x.HybridShadowEvents=nil}},
  {"modified shadow",func(x *Input){
    x.HybridShadowEvents=append([]researchstatepreview.Event(nil),x.HybridShadowEvents...)
    x.HybridShadowEvents[0].ProtocolSHA256=strings.Repeat("f",64)
  }},
  {"wrong original legacy anchor",func(x *Input){x.ExpectedLegacyHeadSHA256=strings.Repeat("f",64)}},
  {"missing original first-use claim",func(x *Input){x.ClaimedHybridFirstUseLedgerHeadSHA256=""}},
 }
 for _,tc:=range tests{
  t.Run(tc.name,func(t *testing.T){
   c:=in
   tc.mutate(&c)
   if _,err:=Assemble(c);err==nil{t.Fatal("unsafe assembly accepted",tc.name)}
  })
 }
}
func TestBusyAndPreviouslyAttemptedResearchRemainBlocked(t *testing.T){
 in:=fixture(t)
 in.Host.ActiveForeignGPUJobs=1
 out,err:=Assemble(in)
 if err!=nil||out.Handoff.ReviewStatus!="BLOCKED"||
  out.Handoff.ReviewReason!="HOST_BUSY_OR_OTHER_RESEARCH_ACTIVE"||
  out.ExecutionAuthorized||out.ResearchDispatched{
  t.Fatal("foreign research blocked planning incorrectly",out,err)
 }
 in=fixture(t)
 in.Attempts=[]hybridrunnerpreview.Attempt{{
  OriginalID:in.RunnerRequest.OriginalID,
  SourceSHA:in.RunnerRequest.SourceSHA,Status:"START_RISK",
 }}
 out,err=Assemble(in)
 if err!=nil||out.Handoff.ReviewStatus!="BLOCKED"||
  out.Handoff.ReviewReason!="PRIOR_OR_INDETERMINATE_ORIGINAL_NO_REPLAY"||
  out.ExecutionAuthorized||out.ResearchDispatched{
  t.Fatal("first-use replay risk bypass",out,err)
 }
}
func TestRejectAnyAuthorityEscalationInFinalOutput(t *testing.T){
 in:=fixture(t)
 out,err:=Assemble(in);if err!=nil{t.Fatal(err)}
 for _,fn:=range []func(*Result){
  func(r *Result){r.ExecutionAuthorized=true},
  func(r *Result){r.ResearchDispatched=true},
  func(r *Result){r.ScientificAccepted=true},
  func(r *Result){r.IndependentGitHubSourceAuthenticated=true},
  func(r *Result){r.IndependentHybridFirstUseAuthenticated=true},
  func(r *Result){r.Handoff.ExecutionAuthorized=true},
  func(r *Result){r.Handoff.HandoffSHA256=strings.Repeat("f",64)},
 }{
  candidate:=out;fn(&candidate)
  if err:=Validate(candidate);err==nil{t.Fatal("unsafe final result accepted",candidate)}
 }
}
