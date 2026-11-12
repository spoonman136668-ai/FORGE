package dreamrsi

import (
 "bytes"
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "reflect"
 "strings"
 "testing"
)

func r24SignEnvelope(t *testing.T, env Envelope, seed byte)(Envelope,TrustPin){
 t.Helper()
 key:=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{seed},ed25519.SeedSize))
 raw,err:=json.Marshal(env.History)
 if err!=nil{t.Fatal(err)}
 env.SignatureHex=hex.EncodeToString(ed25519.Sign(key,append([]byte(AttestationDomain),raw...)))
 p:=TrustPin{ExpectedHistorySHA256:hash(raw),
  IndependentEd25519PublicKeyHex:hex.EncodeToString(key.Public().(ed25519.PublicKey))}
 return env,p
}
func r24Lane(t *testing.T,lane string,sourceSeed,auditorSeed byte)ProspectiveLaneInput{
 t.Helper()
 tr,va,spec,specSHA:=frozen(t,lane)
 optimizer,err:=Optimize(tr,va,spec,specSHA)
 if err!=nil{t.Fatal(err)}
 train,_,_:=signedFixture(t,lane,1,90)
 validation,_,_:=signedFixture(t,lane,110,90)
 heldout,_,held:=signedFixture(t,lane,240,75)
 train,tp:=r24SignEnvelope(t,train,sourceSeed)
 validation,vp:=r24SignEnvelope(t,validation,sourceSeed)
 heldout,hp:=r24SignEnvelope(t,heldout,sourceSeed)
 specHold:=HoldoutSpec{
  Schema:HoldoutSpecSchema,Lane:lane,Epoch:1,
  SelectedPolicySHA256:optimizer.SelectedPolicySHA256,
  FrozenOptimizerHeadSHA256:optimizer.LineageHeadSHA256,
  HoldoutHistorySHA256:held.HistorySHA256,HoldoutAfterTick:220,
  MaxHoldoutDecisions:75,MinEffectiveSampleSize:4,MinMatchBP:1000,
  FirstUseReceiptSHA256:hash([]byte("TEST_ONLY_FIRST_USE_"+lane))}
 specJSON,err:=json.Marshal(specHold)
 if err!=nil{t.Fatal(err)}
 audit:=ProspectiveAudit{Schema:ProspectiveAuditSchema,Lane:lane,
  Epoch:1,HoldoutHistorySHA256:held.HistorySHA256,
  SelectedPolicySHA256:optimizer.SelectedPolicySHA256}
 for _,d:=range held.Decisions {
  audit.Entries=append(audit.Entries,ProspectiveAssignment{
   Tick:d.Tick,ReceiptSHA256:d.ReceiptSHA256,ChosenID:d.ChosenID,
   ChosenCohortSHA256:d.ChosenCohortSHA256,
   LoggedProbabilityBP:d.LoggedActionProbabilityBP,
   RandomizationProofSHA256:d.RandomizationProofSHA256,
   AssignmentEventSHA256:hash([]byte("SYNTHETIC_ASSIGNMENT_"+lane+d.ReceiptSHA256)),
  })
 }
 b,err:=json.Marshal(audit)
 if err!=nil{t.Fatal(err)}
 key:=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{auditorSeed},ed25519.SeedSize))
 signed:=SignedProspectiveAudit{Audit:audit,
  SignatureHex:hex.EncodeToString(ed25519.Sign(key,append([]byte(ProspectiveAuditDomain),b...)))}
 return ProspectiveLaneInput{
  Lane:lane,Optimizer:optimizer,Train:train,Validation:validation,Heldout:heldout,
  TrainPin:tp,ValidationPin:vp,HeldoutPin:hp,FrozenHoldout:specHold,
  IndependentlyPinnedHoldoutSpecSHA256:hash(specJSON),
  SignedAudit:signed,
  AuditPins:ProspectiveAuditPins{ExpectedAuditSHA256:hash(b),
   IndependentAuditorKeyHex:hex.EncodeToString(key.Public().(ed25519.PublicKey))},
 }
}

func TestR24SignedAssignmentPredecisionAudit(t *testing.T){
 in:=r24Lane(t,"Wingless",11,12)
 _,err:=VerifyEnvelope(in.Heldout,in.HeldoutPin)
 if err!=nil{t.Fatal(err)}
 verified,_:=VerifyEnvelope(in.Heldout,in.HeldoutPin)
 count,err:=verifyProspectiveAssignmentAudit(in,verified)
 if err!=nil||count!=75{t.Fatalf("valid synthetic claim invalid: %d %v",count,err)}
 in.SignedAudit.Audit.Entries[0].LoggedProbabilityBP++
 if _,err:=verifyProspectiveAssignmentAudit(in,verified);err==nil{
  t.Fatal("tampered probability accepted")
 }
}

func TestR24CandidateOutcomeAndAuthorityFailClosed(t *testing.T){
 pair:=[2]ProspectiveLaneInput{r24Lane(t,"Wingless",21,22),r24Lane(t,"Yggdrasil",31,32)}
 if !pair[0].Optimizer.QualifiedForProspectiveTest||!pair[1].Optimizer.QualifiedForProspectiveTest{
  t.Fatal("future-trial positive fixture is not independently eligible; no vacuous qualification")
 }
 good,err:=AssessProspectivePair(pair)
 if err!=nil{t.Fatal(err)}
 replay,err:=AssessProspectivePair(pair)
 if err!=nil||!reflect.DeepEqual(good,replay){t.Fatal("non-deterministic source-only comparison",err)}
 if len(good.Lanes)!=2||good.ScientificAccepted||good.ScientificImprovementEstablished||
  good.OptimizerDispatchAuthorized||good.IndependentRandomizationOperationallyProven||
  good.IndependentFirstUseAndSourceBirthProven||good.NewOriginalsExecuted!=0{
  t.Fatal("synthetic history was promoted to scientific authority")
 }
 for _,l:=range good.Lanes{
  if l.AuditedAssignments!=75||len(l.Comparison.Baselines)!=4||
   l.FirstUseCustodyVerified||l.ActualRandomizationIndependentlyDemonstrated||
   !l.Comparison.MultipleComparisonsAndCausalAuditRequired{
   t.Fatal("prospective baseline or custody boundary missing")
  }
 }
}
func TestR24ProspectiveDualLaneDenials(t *testing.T){
 build:=func()[2]ProspectiveLaneInput{
  return [2]ProspectiveLaneInput{r24Lane(t,"Wingless",41,42),r24Lane(t,"Yggdrasil",51,52)}
 }
 baseline:=build()
 if _,err:=AssessProspectivePair(baseline);err!=nil{t.Fatal("negative suite must begin from a valid verified baseline:",err)}
 cases:=[]struct{name string;bad func(*[2]ProspectiveLaneInput)}{
  {"missing heldout",func(x *[2]ProspectiveLaneInput){x[0].Heldout=Envelope{}}},
  {"fake accepted",func(x *[2]ProspectiveLaneInput){x[0].Optimizer.ScientificAccepted=true}},
  {"missing assigned audit",func(x *[2]ProspectiveLaneInput){x[1].SignedAudit.SignatureHex=""}},
  {"cross lane auditor key",func(x *[2]ProspectiveLaneInput){
   x[1].AuditPins.IndependentAuditorKeyHex=x[0].AuditPins.IndependentAuditorKeyHex}},
  {"cross lane source key",func(x *[2]ProspectiveLaneInput){
   x[1].TrainPin.IndependentEd25519PublicKeyHex=x[0].TrainPin.IndependentEd25519PublicKeyHex}},
  {"post result cohort reuse",func(x *[2]ProspectiveLaneInput){
   x[1].Heldout.History.Decisions[0].ChosenCohortSHA256=x[0].Heldout.History.Decisions[0].ChosenCohortSHA256}},
  {"false freeze head",func(x *[2]ProspectiveLaneInput){
   x[0].FrozenHoldout.FrozenOptimizerHeadSHA256=strings.Repeat("f",64)}},
  {"tampered outcome",func(x *[2]ProspectiveLaneInput){
   x[1].Heldout.History.Decisions[0].Outcome="SUPPORTED"}},
  {"audit forged",func(x *[2]ProspectiveLaneInput){
   x[0].SignedAudit.Audit.Entries[0].AssignmentEventSHA256=strings.Repeat("a",64)}},
  {"no prospectively eligible optimizer",func(x *[2]ProspectiveLaneInput){
   x[0].Optimizer.QualifiedForProspectiveTest=false}},
 }
 for _,c:=range cases{t.Run(c.name,func(t *testing.T){
  pair:=build()
  c.bad(&pair)
  got,err:=AssessProspectivePair(pair)
  if err==nil||!reflect.DeepEqual(got,ProspectivePairReview{}){
   t.Fatalf("untrusted future trial released partial advisory: %+v / %v",got,err)
  }
 })}
}
