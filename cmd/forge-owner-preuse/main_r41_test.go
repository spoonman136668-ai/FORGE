package main

import (
 "bytes"
 "encoding/json"
 "testing"
)

func TestR41NativeCLIEmitsOneCanonicalNonAuthorizingD1Tuple(t *testing.T) {
 _,args,claim:=fixture(t)
 var out bytes.Buffer
 report,err:=run(args,&out)
 if err!=nil{t.Fatal(err)}
 if report.D1ClaimCandidate.ScientificAuthorized||
  report.D1ClaimCandidate.Lane!=claim.Lane||
  report.D1ClaimCandidate.OwnerEpoch!=claim.OwnerEpoch||
  report.D1ClaimCandidate.SourceCommitSHA!=claim.SourceCommitSHA||
  report.D1ClaimCandidate.ClaimedSequence!=1||
  report.D1ClaimCandidate.FrozenPredecisionSHA256==""||
  report.IndependentSignerDeploymentVerified||report.ExternalMonotonicFirstUseCASVerified||
  report.ScientificExecutionAuthorized||report.OriginalsExecuted!=0{
  t.Fatalf("source projection wrongly authorized science: %+v",report)
 }
 var wire map[string]any
 if json.Unmarshal(out.Bytes(),&wire)!=nil{t.Fatal("invalid report")}
 if _,ok:=wire["d1_claim_candidate"];!ok{t.Fatal("signed D1 candidate missing")}
 // The former R32 CLI remains non-reusable even after producing a valid tuple.
 out.Reset()
 if _,err:=run(args,&out);err==nil||out.Len()!=0{
  t.Fatal("duplicate local preuse failed to close")
 }
}
