package dreamrsi

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "reflect"
 "strings"
 "testing"
)
func r27OwnerInput(t *testing.T,lane string,signer,auditor byte)([]byte,[]byte){
 t.Helper()
 q:=r24Lane(t,lane,signer,auditor)
 owner:=SingleLaneOwnerBundle{Schema:SingleLaneOwnerSchema,
  Lane:OwnerLaneEvidence{
   Lane:lane,Optimizer:q.Optimizer,Train:q.Train,Validation:q.Validation,
   Heldout:q.Heldout,FrozenHoldout:q.FrozenHoldout,SignedAudit:q.SignedAudit,
  }}
 raw,err:=json.Marshal(owner)
 if err!=nil{t.Fatal(err)}
 sha:=sha256.Sum256(raw)
 pins:=SingleLaneIndependentPins{Schema:SingleLanePinsSchema,
  OwnerBundleSHA256:hex.EncodeToString(sha[:]),
  Lane:IndependentLanePins{
   Lane:lane,FrozenOptimizerHeadSHA256:q.Optimizer.LineageHeadSHA256,
   Train:q.TrainPin,Validation:q.ValidationPin,Heldout:q.HeldoutPin,
   HoldoutSpecSHA256:q.IndependentlyPinnedHoldoutSpecSHA256,
   Audit:q.AuditPins,
  }}
 p,err:=json.Marshal(pins)
 if err!=nil{t.Fatal(err)}
 return raw,p
}
func TestR27PositiveSingleLaneAdvisoryWithoutOtherLane(t *testing.T){
 for _,tc:=range []struct{lane string;signer,auditor byte}{
  {"Wingless",81,82},{"Yggdrasil",91,92},
 } {
  t.Run(tc.lane,func(t *testing.T){
   owner,pins:=r27OwnerInput(t,tc.lane,tc.signer,tc.auditor)
   a,err:=ReviewOwnerSingleLaneEvidence(owner,pins)
   if err!=nil{t.Fatal(err)}
   b,err:=ReviewOwnerSingleLaneEvidence(owner,pins)
   if err!=nil||!reflect.DeepEqual(a,b){t.Fatal("nondeterministic single-lane shadow",err)}
   if a.Schema!=SingleLaneReviewSchema||a.Lane.Lane!=tc.lane||
    a.Lane.AuditedAssignments!=75||len(a.Lane.Comparison.Baselines)!=4||
    a.IndependentRandomizationOperationallyProven||
    a.IndependentFirstUseAndSourceBirthProven||a.ScientificImprovementEstablished||
    a.ScientificAccepted||a.OptimizerDispatchAuthorized||a.NewOriginalsExecuted!=0{
    t.Fatal("single-lane shadow lost four baselines or elevated authority")
   }
  })
 }
}
func TestR27MissingOtherLaneNeverBlocksValidEvidence(t *testing.T){
 owner,pins:=r27OwnerInput(t,"Yggdrasil",101,102)
 review,err:=ReviewOwnerSingleLaneEvidence(owner,pins)
 if err!=nil||review.Lane.Lane!="Yggdrasil"{t.Fatal("Wingless missing blocked independent Yggdrasil shadow:",err)}
}
func TestR27SingleLaneUntrustedInputsFailClosed(t *testing.T){
 owner,pins:=r27OwnerInput(t,"Wingless",111,112)
 checks:=[]struct{name string;modify func([]byte,[]byte)([]byte,[]byte)}{
  {"no owner",func(_,p []byte)([]byte,[]byte){return nil,p}},
  {"no external trust pins",func(o,_ []byte)([]byte,[]byte){return o,nil}},
  {"trailing evidence",func(o,p []byte)([]byte,[]byte){return append(append([]byte{},o...),'{'),p}},
  {"noncanonical source",func(o,p []byte)([]byte,[]byte){return append([]byte(" "),o...),p}},
  {"untrusted trust pin",func(o,p []byte)([]byte,[]byte){return o,append([]byte{},p[:len(p)-3]...)}},
  {"changed signer record",func(o,p []byte)([]byte,[]byte){
   var x SingleLaneOwnerBundle
   json.Unmarshal(o,&x)
   x.Lane.Heldout.History.Decisions[0].Outcome="SUPPORTED"
   out,_:=json.Marshal(x)
   return out,p
  }},
  {"wrong lane",func(o,p []byte)([]byte,[]byte){
   var x SingleLaneOwnerBundle
   json.Unmarshal(o,&x)
   x.Lane.Lane="Yggdrasil"
   out,_:=json.Marshal(x)
   return out,p
  }},
  {"signed audit missing",func(o,p []byte)([]byte,[]byte){
   var x SingleLaneOwnerBundle
   json.Unmarshal(o,&x)
   x.Lane.SignedAudit.SignatureHex=""
   out,_:=json.Marshal(x)
   return out,p
  }},
  {"wrong frozen spec",func(o,p []byte)([]byte,[]byte){
   var x SingleLaneIndependentPins
   json.Unmarshal(p,&x)
   x.Lane.HoldoutSpecSHA256=strings.Repeat("f",64)
   out,_:=json.Marshal(x)
   return o,out
  }},
 }
 for _,tc:=range checks{
  t.Run(tc.name,func(t *testing.T){
   o,p:=tc.modify(owner,pins)
   out,err:=ReviewOwnerSingleLaneEvidence(o,p)
   if err==nil||!reflect.DeepEqual(out,SingleLaneReview{}){
    t.Fatalf("bad independent research input accepted: %v %+v",err,out)
   }
  })
 }
}
func TestR27IndependentAuditCannotUseOwnerSigner(t *testing.T){
 q:=r24Lane(t,"Wingless",121,122)
 q.AuditPins.IndependentAuditorKeyHex=q.HeldoutPin.IndependentEd25519PublicKeyHex
 got,err:=AssessProspectiveLane(q)
 if err==nil||!reflect.DeepEqual(got,ProspectiveLaneReview{}){
  t.Fatal("owner signer impersonated separately pinned auditor")
 }
}
