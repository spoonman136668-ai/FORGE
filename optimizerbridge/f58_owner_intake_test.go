package optimizerbridge

import (
 "errors"
 "strings"
 "testing"
)

// This test-only verifier cannot be used as genuine external custody.
// It only checks the shape of the integration contract.
type f58TestOnlyVerifier struct {deny bool}
func (v f58TestOnlyVerifier)VerifyProspectiveResearchSelection(ProspectiveSelection)error{
 if v.deny{return ErrStageEvidence}
 return nil
}
func (v f58TestOnlyVerifier)VerifyAcceptedScientificOutcome(IndependentlyAcceptedOutcome)error{
 return ErrStageEvidence
}
func f58TestOnlyTrial(f F58Freeze,i int)ProspectiveSelection{
 codes:=[]string{"a","b","c","d","e","f"}
 src:="7"
 if i==1 {codes=[]string{"1","2","3","4","5","6"};src="8"}
 var p ProspectiveSelection
 p.Lane=f.Lanes[i].Lane
 for _,base:=range f.Lanes[i].Controls{
  p.FrozenBaselinePolicySHA256=append(p.FrozenBaselinePolicySHA256,base.SHA256)
 }
 p.FrozenDreamPolicySHA256=strings.Repeat(codes[0],64)
 p.FrozenParetoPolicySHA256=strings.Repeat(codes[1],64)
 p.PreregistrationSHA256=strings.Repeat(codes[2],64)
 p.ProspectiveSourceSHA=strings.Repeat(src,40)
 p.FirstUseReceiptSHA256=strings.Repeat(codes[3],64)
 p.RandomizationAuditSHA256=strings.Repeat(codes[4],64)
 p.IndependentCausalReviewSHA256=strings.Repeat(codes[5],64)
 return p
}
func TestF58OwnerSelectionDoesNotInferAuthenticityFromHashes(t *testing.T){
 freeze,err:=FreezeF58();if err!=nil{t.Fatal(err)}
 w,y:=f58TestOnlyTrial(freeze,0),f58TestOnlyTrial(freeze,1)
 noTrust,err:=AssessF58OwnerSelections(freeze,[]ProspectiveSelection{w,y},nil)
 if err!=nil||noTrust.TrustVerifiedProspectiveLanes!=0||
  noTrust.ExistingControllerPolicyGateEligible||
  noTrust.ScientificOriginalDispatchAuthorized||
  noTrust.Mode!="TWO_SOURCE_CLAIMS_PRESENT_BUT_INDEPENDENT_TRUST_MISSING"{
  t.Fatalf("source signatures became authority: %+v %v",noTrust,err)
 }
 empty,err:=AssessF58OwnerSelections(freeze,nil,nil)
 if err!=nil||empty.StructurallyRegisteredLanes!=0||empty.ExistingControllerPolicyGateEligible||
  empty.Mode!="BLOCKED_NO_AUTHENTIC_PROSPECTIVE_OWNER_SELECTION"{
  t.Fatalf("false optimizer activation %+v %v",empty,err)
 }
 one,err:=AssessF58OwnerSelections(freeze,[]ProspectiveSelection{w},nil)
 if err!=nil||one.StructurallyRegisteredLanes!=1||
  one.ExistingControllerPolicyGateEligible||one.TrustVerifiedProspectiveLanes!=0{
  t.Fatalf("one lane blocked or improperly promoted %+v %v",one,err)
 }
 if _,err:=AssessF58OwnerSelections(freeze,[]ProspectiveSelection{w,y},f58TestOnlyVerifier{deny:true});!errors.Is(err,ErrStageEvidence){
  t.Fatalf("rejected external auditor accepted %v",err)
 }
 testOnly,err:=AssessF58OwnerSelections(freeze,[]ProspectiveSelection{w,y},f58TestOnlyVerifier{})
 if err!=nil||!testOnly.ExistingControllerPolicyGateEligible||
  testOnly.TrustVerifiedProspectiveLanes!=2||
  testOnly.AutomaticControllerCutoverAuthorized||
  testOnly.ScientificOriginalDispatchAuthorized||
  testOnly.AcceptedRefMutation||testOnly.ThetaWeightUpdatesAuthorized{
  t.Fatalf("verified owner protocol bypassed independent policy gate %+v %v",testOnly,err)
 }
}
func TestF58RejectsInvalidProspectiveSelectionLineageAndReusedReceipts(t *testing.T){
 f,err:=FreezeF58();if err!=nil{t.Fatal(err)}
 for name,change:=range map[string]func(*ProspectiveSelection,*ProspectiveSelection){
  "mutated frozen control":func(w,y *ProspectiveSelection){w.FrozenBaselinePolicySHA256[0]=strings.Repeat("9",64)},
  "missing fourth baseline":func(w,y *ProspectiveSelection){w.FrozenBaselinePolicySHA256=w.FrozenBaselinePolicySHA256[:3]},
  "repeated lane":func(w,y *ProspectiveSelection){y.Lane=w.Lane},
  "missing preregistration":func(w,y *ProspectiveSelection){w.PreregistrationSHA256=""},
  "no randomization audit":func(w,y *ProspectiveSelection){w.RandomizationAuditSHA256=""},
  "repeat first use":func(w,y *ProspectiveSelection){y.FirstUseReceiptSHA256=w.FirstUseReceiptSHA256},
  "reuse audit":func(w,y *ProspectiveSelection){y.RandomizationAuditSHA256=w.RandomizationAuditSHA256},
  "same review as prereg":func(w,y *ProspectiveSelection){w.IndependentCausalReviewSHA256=w.PreregistrationSHA256},
  "unqualified parent source":func(w,y *ProspectiveSelection){w.ProspectiveSourceSHA=F58ParentSource},
  "challenger equals frozen baseline":func(w,y *ProspectiveSelection){w.FrozenDreamPolicySHA256=f.Lanes[0].Controls[0].SHA256},
  "wrong observed owner source":func(w,y *ProspectiveSelection){y.ProspectiveSourceSHA="not_a_sha"},
 }{
  t.Run(name,func(t *testing.T){
   w,y:=f58TestOnlyTrial(f,0),f58TestOnlyTrial(f,1)
   change(&w,&y)
   out,err:=AssessF58OwnerSelections(f,[]ProspectiveSelection{w,y},nil)
   if err==nil||out!=(F58SelectionIntake{}){t.Fatalf("invalid real-world study passed %+v %v",out,err)}
  })
 }
}
