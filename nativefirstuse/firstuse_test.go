package nativefirstuse

import (
 "errors"
 "strings"
 "testing"
)

type fakeCustody struct{ blockPre,blockClaim bool }
func (f fakeCustody) VerifyExternalPredecision(Receipt)error{
 if f.blockPre{return errors.New("no independent predecision")}
 return nil
}
func (f fakeCustody) VerifyDurableFirstUse(Receipt)error{
 if f.blockClaim{return errors.New("no durable one-use")}
 return nil
}
func sample(lane string,tag string)Receipt{
 h:=func(n int)string{return strings.Repeat(tag,n)}
 return Receipt{
  Lane:lane,SourceSHA:h(40),FrozenDecisionSHA256:h(64),
  OwnerEpoch:4,FirstUseSequence:17,GlobalClaimSHA256:strings.Repeat("a",64),
  FirstUseLedgerHeadSHA256:strings.Repeat("b",64),
  CloudflareClaimSHA256:strings.Repeat("c",64),
  PublicSlateSHA256:strings.Repeat("d",64),
  BudgetSHA256:strings.Repeat("e",64),
  PolicySHA256:strings.Repeat("f",64),
  PolicyArmNumerator:1,PolicyArmDenominator:6,
  WitnessIdentitySHA256:strings.Repeat("1",64),
 }
}
func TestNativeSourceOnlyPermitNeverIssued(t *testing.T){
 w:=sample("Wingless","2");y:=sample("Yggdrasil","3")
 y.GlobalClaimSHA256=strings.Repeat("4",64)
 y.CloudflareClaimSHA256=strings.Repeat("5",64)
 y.FirstUseLedgerHeadSHA256=strings.Repeat("6",64)
 y.WitnessIdentitySHA256=strings.Repeat("7",64)
 y.PolicySHA256=strings.Repeat("8",64)
 out,err:=ReviewNativePair(w,y,fakeCustody{})
 if err!=nil{t.Fatal(err)}
 for _,r:=range out {
  if !r.ExternalAdmissionEvidenceVerified||!r.SeparateOperationalApprovalRequired||
   r.AuthorizedOriginalStart||r.AuthorizedControllerCutover||
   r.AcceptedScientificOutcome||r.ExactPolicyProbabilityNumerator!=1||
   r.ExactPolicyProbabilityDenominator!=6{t.Fatalf("unsafe source fixture %+v",r)}
 }
}
func TestNativeFailClosedMissingAuthAndReplay(t *testing.T){
 w:=sample("Wingless","2")
 for _,c:=range []Custody{nil,fakeCustody{blockPre:true},fakeCustody{blockClaim:true}}{
  if _,err:=ReviewNativeFirstUse(w,c);!errors.Is(err,ErrUnverified){t.Fatalf("accepted fake custody: %v",err)}
 }
 y:=sample("Yggdrasil","3")
 y.SourceSHA=strings.Repeat("4",40)
 y.PolicySHA256=strings.Repeat("8",64)
 if _,err:=ReviewNativePair(w,y,fakeCustody{});!errors.Is(err,ErrUnverified){
  t.Fatal("accepted shared first-use identity")
 }
 w.PolicyArmDenominator=10000
 if _,err:=ReviewNativeFirstUse(w,fakeCustody{});!errors.Is(err,ErrUnverified){
  t.Fatal("accepted rounded propensity")
 }
}
