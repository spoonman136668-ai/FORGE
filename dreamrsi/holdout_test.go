package dreamrsi

import (
 "encoding/json"
 "testing"
)
func TestSealedHoldoutSeparateFromOptimizerAndAuthority(t *testing.T){
 train,validation,spec,pin:=frozen(t,"Yggdrasil")
 optimizer,err:=Optimize(train,validation,spec,pin)
 if err!=nil{t.Fatal(err)}
 if !optimizer.QualifiedForProspectiveTest{t.Skip("insufficient fixture support")}
 _,_,held:=signedFixture(t,"Yggdrasil",240,75)
 hold:=HoldoutSpec{
  Schema:HoldoutSpecSchema,Lane:"Yggdrasil",Epoch:1,
  SelectedPolicySHA256:optimizer.SelectedPolicySHA256,
  FrozenOptimizerHeadSHA256:optimizer.LineageHeadSHA256,
  HoldoutHistorySHA256:held.HistorySHA256,
  HoldoutAfterTick:220,MaxHoldoutDecisions:75,
  MinEffectiveSampleSize:4,MinMatchBP:1000,
  FirstUseReceiptSHA256:hash([]byte("external-test-only-sealed-use")),
 }
 bytes,_:=json.Marshal(hold)
 digest:=hash(bytes)
 result,err:=AssessHoldout(optimizer,train,validation,held,hold,digest)
 if err!=nil{t.Fatal(err)}
 if result.Schema!=HoldoutReportSchema||result.ScientificAccepted||
  result.DispatchAuthorized||result.ImprovementEstablished||
  !result.MultipleComparisonsAndCausalAuditRequired||len(result.Baselines)!=4{
  t.Fatalf("holdout prematurely promoted evidence: %+v",result)
 }
 if result.Selected.PolicySHA256!=optimizer.SelectedPolicySHA256{
  t.Fatal("holdout replaced the preselected candidate")
 }
 // Even the strongest observed signal cannot produce authority itself.
 hold.HoldoutAfterTick=250
 if _,err=AssessHoldout(optimizer,train,validation,held,hold,digest);err==nil{
  t.Fatal("modified holdout freeze passed")
 }
 hold.HoldoutAfterTick=220
 forged:=held;forged.Decisions=append([]Decision(nil),held.Decisions...)
 forged.Decisions[0].ChosenCohortSHA256=train.Decisions[0].ChosenCohortSHA256
 if _,err=AssessHoldout(optimizer,train,validation,forged,hold,digest);err==nil{
  t.Fatal("historical cohort reused in sealed holdout")
 }
}
