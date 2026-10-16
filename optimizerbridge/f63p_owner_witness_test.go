package optimizerbridge

import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "strings"
 "testing"
)
func f63PSourceFixtures(t *testing.T)(F58Freeze,[]F63PResearchIntake){
 t.Helper()
 f,err:=FreezeF58();if err!=nil{t.Fatal(err)}
 out:=make([]F63PResearchIntake,0,2)
 for i:=0;i<2;i++{
  _,n,trials:=f62Fixture(t,i,1)
  trial:=trials[0]
  selectClaim:=f58TestOnlyTrial(f,i)
  selectClaim.FrozenDreamPolicySHA256=n.DreamPolicySHA256
  selectClaim.FrozenParetoPolicySHA256=n.ParetoPolicySHA256
  selectClaim.PreregistrationSHA256=n.OwnerPreregistrationSHA256
  selectClaim.ProspectiveSourceSHA=n.PredecisionOwnerSourceSHA
  selectClaim.FirstUseReceiptSHA256=fmt.Sprintf("%064x",i+20001)
  record:=F63PWitnessRecord{
   Schema:F63PWitnessSchema,Lane:n.Lane,
   AssignmentSHA256:trial.Assignment.AssignmentSHA256,
   OwnerSourceSHA:n.PredecisionOwnerSourceSHA,
   OwnerDecisionSequence:trial.OwnerDecisionSequence,
   FirstUseReceiptSHA256:selectClaim.FirstUseReceiptSHA256,
   OriginalReceiptSHA256:trial.OriginalReceiptSHA256,
   CandidateSlateSHA256:trial.Assignment.PublicCandidateSlateSHA256,
   SourceFamilySHA256:trial.Assignment.PublicSourceFamilySHA256,
   BudgetCommitmentSHA256:trial.Assignment.BudgetCommitmentSHA256,
   FirstUseLedgerHeadSHA256:fmt.Sprintf("%064x",i+21001),
   FirstUseLedgerHighWater:uint64(i+1),
  }
  raw,err:=json.Marshal(record);if err!=nil{t.Fatal(err)}
  seed:=sha256.Sum256([]byte(fmt.Sprintf("TEST_ONLY_NEVER_EXTERNAL_OWNER_%d",i)))
  private:=ed25519.NewKeyFromSeed(seed[:])
  pub:=private.Public().(ed25519.PublicKey)
  signed:=F63PSignedWitness{Record:record,SignatureHex:hex.EncodeToString(
   ed25519.Sign(private,append([]byte(F63PDomain),raw...))),
  )}
  pin:=F63PExternalPin{
   Lane:n.Lane,SignedRecordSHA256:f63PHash(raw),
   WitnessPublicKeyHex:hex.EncodeToString(pub),
   FirstUseLedgerHeadSHA256:record.FirstUseLedgerHeadSHA256,
   MinimumFirstUseLedgerHighWater:uint64(i+1),
  }
  selectClaim.RandomizationAuditSHA256=pin.SignedRecordSHA256
  out=append(out,F63PResearchIntake{
   Nomination:n,OwnerSelection:selectClaim,Trial:trial,
   Witness:signed,ExternalPin:pin,
  })
 }
 return f,out
}
func TestF63PReadOnlySourceSignatureBindingNeverGrantsRealFirstUse(t *testing.T){
 f,items:=f63PSourceFixtures(t)
 report,err:=ObserveF63PExistingOwner(f,items,f58TestOnlyVerifier{})
 if err!=nil{t.Fatal(err)}
 if !report.ExternallyPinnedWitnessSignaturesVerified||
  !report.ExistingOwnerTrustInterfaceAcceptedClaims||
  report.ExactPolicyArmPropensityNumerator!=1||
  report.ExactPolicyArmPropensityDenominator!=6||
  report.IndependentlyProvenPreOutcomeTiming||
  report.IndependentlyVerifiedMonotonicFirstUse||
  report.NewOriginalDispatchAuthorized||report.CausalComparisonAuthorized||
  report.DreamParetoActivationAuthorized||report.ThetaWeightUpdateAuthorized{
  t.Fatalf("test-only signed witness activated science: %+v",report)
 }
}
func TestF63PFailsClosedWithoutIndependentOwnerTrust(t *testing.T){
 f,items:=f63PSourceFixtures(t)
 if _,err:=ObserveF63PExistingOwner(f,items,nil);!errors.Is(err,ErrF63P){
  t.Fatal("missing existing owner trust accepted",err)
 }
 if _,err:=ObserveF63PExistingOwner(f,items,f58TestOnlyVerifier{deny:true});!errors.Is(err,ErrF63P){
  t.Fatal("negative existing owner trust accepted",err)
 }
 if _,err:=ObserveF63PExistingOwner(f,items[:1],f58TestOnlyVerifier{});!errors.Is(err,ErrF63P){
  t.Fatal("one-lane witness accepted",err)
 }
}
func TestF63PRejectsForgeryReplayDriftAndCrossLaneReuse(t *testing.T){
 f,items:=f63PSourceFixtures(t)
 checks:=[]struct{
  name string
  mutate func([]F63PResearchIntake)
 }{
  {"witness signature",func(a []F63PResearchIntake){a[0].Witness.SignatureHex=strings.Repeat("0",128)}},
  {"untrusted witness key",func(a []F63PResearchIntake){a[0].ExternalPin.WitnessPublicKeyHex=a[1].ExternalPin.WitnessPublicKeyHex}},
  {"pin digest mismatch",func(a []F63PResearchIntake){a[0].ExternalPin.SignedRecordSHA256=strings.Repeat("f",64)}},
  {"tampered source",func(a []F63PResearchIntake){a[0].Witness.Record.OwnerSourceSHA=strings.Repeat("f",40)}},
  {"changed first-use receipt",func(a []F63PResearchIntake){a[0].Witness.Record.FirstUseReceiptSHA256=strings.Repeat("f",64)}},
  {"unsupported local timing assertion",func(a []F63PResearchIntake){a[0].Witness.Record.FirstUseLedgerHighWater=0}},
  {"high-water below pinned",func(a []F63PResearchIntake){a[0].ExternalPin.MinimumFirstUseLedgerHighWater=2}},
  {"mismatched ledger head",func(a []F63PResearchIntake){a[0].ExternalPin.FirstUseLedgerHeadSHA256=strings.Repeat("f",64)}},
  {"fake partial transcript",func(a []F63PResearchIntake){a[0].Witness.Record.AssignmentSHA256=strings.Repeat("f",64)}},
  {"duplicate owner witness",func(a []F63PResearchIntake){a[1].ExternalPin.WitnessPublicKeyHex=a[0].ExternalPin.WitnessPublicKeyHex}},
  {"cross-lane first-use",func(a []F63PResearchIntake){a[1].OwnerSelection.FirstUseReceiptSHA256=a[0].OwnerSelection.FirstUseReceiptSHA256}},
  {"cross-lane original",func(a []F63PResearchIntake){a[1].Trial.OriginalReceiptSHA256=a[0].Trial.OriginalReceiptSHA256}},
  {"claimed pre-use approval within preparation",func(a []F63PResearchIntake){a[0].Trial.Assignment.ExternallyWitnessedPredecisionRegistration=true}},
  {"basis point instead of rational",func(a []F63PResearchIntake){a[0].Trial.Assignment.LoggedPropensityDenominator=10000}},
  {"cross-lane publication",func(a []F63PResearchIntake){a[1].Nomination.Lane=a[0].Nomination.Lane}},
 }
 for _,c:=range checks {
  t.Run(c.name,func(t *testing.T){
   a:=append([]F63PResearchIntake(nil),items...)
   c.mutate(a)
   if _,err:=ObserveF63PExistingOwner(f,a,f58TestOnlyVerifier{});err==nil{
    t.Fatal("f63p verifier accepted",c.name)
   }
  })
 }
}
