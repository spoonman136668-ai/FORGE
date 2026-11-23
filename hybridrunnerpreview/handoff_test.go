package hybridrunnerpreview

import (
 "strings"
 "testing"
)
func refs(r Request)CustodyReferences{
 return CustodyReferences{
  Repository:Project,SourceSHA:r.SourceSHA,
  ProtocolSHA256:r.ProtocolSHA256,
  SignedAttestationSHA256:strings.Repeat("c",64),
  ArtifactSHA256:strings.Repeat("d",64),
  ClaimedSignerKeySHA256:strings.Repeat("e",64),
  ClaimedOriginalLedgerHeadSHA256:strings.Repeat("f",64),
 }
}
func TestDisabledHandoffBindsRequestAndUntrustedEvidenceRefs(t *testing.T){
 r,h:=request(),host()
 review,err:=Evaluate(r,h,nil,1800000030)
 if err!=nil{t.Fatal(err)}
 out,err:=BuildDisabledHandoff(r,review,refs(r))
 if err!=nil||VerifyDisabledHandoff(out)!=nil||
  out.Mode!=HandoffMode||out.HandoffSHA256==""||
  !out.RequiresIndependentSourceAndFirstUseWitness||
  out.ExecutionAuthorized||out.FirstUseAuthenticated||
  out.SourceAuthenticated||out.GPUReserved{t.Fatal("handoff accidentally authoritative",out,err)}
 same,err:=BuildDisabledHandoff(r,review,refs(r))
 if err!=nil||out.HandoffSHA256!=same.HandoffSHA256{t.Fatal("replay nondeterministic",err)}
}
func TestDisabledHandoffRejectsDriftAndClaims(t *testing.T){
 r,h:=request(),host()
 review,err:=Evaluate(r,h,nil,1800000030)
 if err!=nil{t.Fatal(err)}
 good:=refs(r)
 for _,tc:=range []struct{name string;change func(*Request,*Result,*CustodyReferences)}{
  {"different request",func(r *Request,_ *Result,_ *CustodyReferences){r.OriginalID="SECOND"}},
  {"source mismatch",func(_ *Request,_ *Result,c *CustodyReferences){c.SourceSHA=strings.Repeat("0",40)}},
  {"protocol mismatch",func(_ *Request,_ *Result,c *CustodyReferences){c.ProtocolSHA256=strings.Repeat("0",64)}},
  {"foreign project",func(_ *Request,_ *Result,c *CustodyReferences){c.Repository="other/hybrid"}},
  {"missing attestation",func(_ *Request,_ *Result,c *CustodyReferences){c.SignedAttestationSHA256=""}},
  {"invalid signer",func(_ *Request,_ *Result,c *CustodyReferences){c.ClaimedSignerKeySHA256="bad"}},
  {"missing ledger claim",func(_ *Request,_ *Result,c *CustodyReferences){c.ClaimedOriginalLedgerHeadSHA256=""}},
  {"forged execution",func(_ *Request,v *Result,_ *CustodyReferences){v.ExecutionAuthorized=true}},
  {"forged science",func(_ *Request,v *Result,_ *CustodyReferences){v.SourceAuthenticated=true}},
  {"forged blocked reason",func(_ *Request,v *Result,_ *CustodyReferences){v.Status="BLOCKED";v.Reason="AUTHORIZED"}},
 }{
  t.Run(tc.name,func(t *testing.T){
   a,b,c:=r,review,good
   tc.change(&a,&b,&c)
   if _,err:=BuildDisabledHandoff(a,b,c);err==nil{t.Fatal("mismatched handoff accepted",tc.name)}
  })
 }
 out,err:=BuildDisabledHandoff(r,review,good)
 if err!=nil{t.Fatal(err)}
 for _,modify:=range []func(*Handoff){
  func(h *Handoff){h.ExecutionAuthorized=true},
  func(h *Handoff){h.FirstUseAuthenticated=true},
  func(h *Handoff){h.SourceAuthenticated=true},
  func(h *Handoff){h.GPUReserved=true},
  func(h *Handoff){h.RequiresIndependentSourceAndFirstUseWitness=false},
  func(h *Handoff){h.HandoffSHA256=strings.Repeat("0",64)},
  func(h *Handoff){h.ReviewReason="READY_TO_DISPATCH"},
 }{
  candidate:=out;modify(&candidate)
  if err:=VerifyDisabledHandoff(candidate);err==nil{t.Fatal("unsafe handoff accepted",candidate)}
 }
}
func TestBlockedAndIndeterminateOriginalDoesNotBecomeExecutableHandoff(t *testing.T){
 r,h:=request(),host()
 prior:=[]Attempt{{OriginalID:r.OriginalID,SourceSHA:r.SourceSHA,Status:"START_RISK"}}
 blocked,err:=Evaluate(r,h,prior,1800000030)
 if err!=nil||blocked.Status!="BLOCKED"{t.Fatal("failed to protect ambiguous first use",err)}
 handoff,err:=BuildDisabledHandoff(r,blocked,refs(r))
 if err!=nil||handoff.ReviewStatus!="BLOCKED"||
  handoff.ExecutionAuthorized||handoff.FirstUseAuthenticated||
  VerifyDisabledHandoff(handoff)!=nil{t.Fatal("indeterminate original regained authority",handoff,err)}
}
