package researchstate

import (
 "strings"
 "testing"
)
func TestRecoveryNeverReplaysAuthorizedOrQuarantined(t *testing.T){
 j:=New();id:="s14";pin:=strings.Repeat("c",64);evidence:=strings.Repeat("d",64)
 steps:=[]struct{from,to Phase;risk bool}{
  {"",Proposed,false},{Proposed,Preregistered,false},
  {Preregistered,Qualifying,false},{Qualifying,Qualified,false},
  {Qualified,Authorized,false},{Authorized,Quarantined,true},
 }
 for _,s:=range steps{
  evt:=Event{Lane:"Wingless",ExperimentID:id,FrozenSHA256:pin,From:s.from,To:s.to,IrreversibleRisk:s.risk}
  if s.to==Qualified||s.to==Authorized||s.to==Quarantined{evt.EvidenceSHA256=evidence}
  j=add(t,j,evt)
  got,err:=ClassifyRecovery(j,"Wingless",id)
  if err!=nil{t.Fatal(err)}
  if s.to==Authorized||s.to==Quarantined{
   if got!=RecoverReconcileFirstUse{t.Fatalf("%s incorrectly recovered as %s",s.to,got)}
  }else if got!=RecoverReversible{t.Fatalf("%s incorrectly recovered as %s",s.to,got)}
 }
}
func TestRecoveryNeverInfersMissingEvidence(t *testing.T){
 j:=New();got,err:=ClassifyRecovery(j,"Yggdrasil","unknown")
 if err!=nil||got!=RecoverBlocked{t.Fatal(got,err)}
}
