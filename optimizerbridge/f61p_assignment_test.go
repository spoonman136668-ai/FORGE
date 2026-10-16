package optimizerbridge

import (
 "bytes"
 "encoding/binary"
 "encoding/hex"
 "errors"
 "io"
 "reflect"
 "strings"
 "testing"
)

func f61FixedNomination(t *testing.T,f F58Freeze,lane int)F59PolicyNomination{
 t.Helper()
 n:=f59TestNomination(f,lane) // test-only pseudo-digests are NEVER owner evidence
 return n
}
func f61TestPublic() (string,string,string) {
 return strings.Repeat("3",64),strings.Repeat("4",64),strings.Repeat("5",64)
}
func f61DrawReader(draw uint64)io.Reader{
 var b [8]byte
 binary.BigEndian.PutUint64(b[:],draw)
 return bytes.NewReader(b[:])
}
func TestF61PUnbiasedArmMappingAndNonAuthorizingRecord(t *testing.T){
 f,err:=FreezeF58();if err!=nil{t.Fatal(err)}
 slate,family,budget:=f61TestPublic()
 for lane:=0;lane<2;lane++{
  n:=f61FixedNomination(t,f,lane)
  for arm:=0;arm<6;arm++{
   a,err:=PrepareF61OwnerSelection(f,n,slate,family,budget,f61DrawReader(uint64(arm)))
   if err!=nil{t.Fatal(err)}
   if a.ChoiceIndex!=arm||a.ChosenArm!=a.SixPolicyArms[arm]||
    a.LoggedPropensityNumerator!=1||a.LoggedPropensityDenominator!=6||
    len(a.SixPolicyArms)!=6||a.ExternalRandomnessAndTimeAudited||
    a.ExternallyWitnessedPredecisionRegistration||
    a.AtomicFirstUseClaimConsumed||a.GenuineScientificOriginalAuthorized||
    a.PolicyAcceptedOrPromoted{
    t.Fatalf("unearned first use or biased arm: %+v",a)
   }
   if err:=ValidateF61Prepared(f,n,a);err!=nil{t.Fatal(err)}
   a2,err:=PrepareF61OwnerSelection(f,n,slate,family,budget,f61DrawReader(uint64(arm)))
   if err!=nil||!reflect.DeepEqual(a,a2){t.Fatal("nonce-bound trial not reproducible")}
  }
 }
}
func TestF61PMaxUintRejectionAvoidsModuloBias(t *testing.T){
 var payload bytes.Buffer
 for i:=uint64(0);i<4;i++{
  var b [8]byte
  binary.BigEndian.PutUint64(b[:],(^uint64(0))-i)
  payload.Write(b[:])
 }
 payload.Write(make([]byte,8))
 selected,draw,err:=f61Draw(&payload)
 if err!=nil||selected!=0||draw!="0000000000000000"{t.Fatalf("rejection sampling failed %d %q %v",selected,draw,err)}
 for i:=0;i<4;i++{
  var b [8]byte
  binary.BigEndian.PutUint64(b[:],(^uint64(0))-uint64(i))
  if _,_,err:=f61Draw(bytes.NewReader(b[:]));!errors.Is(err,ErrF61Pilot){
   t.Fatal("accepted reserved uint64 entropy tail")
  }
 }
 if _,_,err:=f61Draw(nil);!errors.Is(err,ErrF61Pilot){t.Fatal("nil entropy accepted")}
 if _,_,err:=f61Draw(bytes.NewReader([]byte{1,2}));!errors.Is(err,ErrF61Pilot){t.Fatal("short entropy accepted")}
}
func TestF61PAdversarialMutationCannotBecomeOwnerApproval(t *testing.T){
 f,err:=FreezeF58();if err!=nil{t.Fatal(err)}
 n:=f61FixedNomination(t,f,0)
 slate,family,budget:=f61TestPublic()
 base,err:=PrepareF61OwnerSelection(f,n,slate,family,budget,f61DrawReader(2))
 if err!=nil{t.Fatal(err)}
 mutations:=map[string]func(*F61PilotAssignment){
  "false_owner_witness":func(a *F61PilotAssignment){a.ExternallyWitnessedPredecisionRegistration=true},
  "fake_randomness_attestation":func(a *F61PilotAssignment){a.ExternalRandomnessAndTimeAudited=true},
  "false_science_permit":func(a *F61PilotAssignment){a.GenuineScientificOriginalAuthorized=true},
  "pretend_first_use":func(a *F61PilotAssignment){a.AtomicFirstUseClaimConsumed=true},
  "promote_policy":func(a *F61PilotAssignment){a.PolicyAcceptedOrPromoted=true},
  "remove_frozen_control":func(a *F61PilotAssignment){a.SixPolicyArms=a.SixPolicyArms[1:]},
  "replace_control":func(a *F61PilotAssignment){a.SixPolicyArms[0].PolicySHA256=strings.Repeat("8",64)},
  "source_swap":func(a *F61PilotAssignment){a.OwnerSourceSHA=strings.Repeat("f",40)},
  "changed_decision_slate":func(a *F61PilotAssignment){a.PublicCandidateSlateSHA256=strings.Repeat("6",64)},
  "budget_replay":func(a *F61PilotAssignment){a.BudgetCommitmentSHA256=a.PublicCandidateSlateSHA256},
  "biased_rounding":func(a *F61PilotAssignment){a.LoggedPropensityNumerator=1667;a.LoggedPropensityDenominator=10000},
  "wrong_arm":func(a *F61PilotAssignment){a.ChoiceIndex=3},
  "wrong_chosen_id":func(a *F61PilotAssignment){a.ChosenArm.PolicySHA256=strings.Repeat("f",64)},
  "corrupt_draw":func(a *F61PilotAssignment){a.RandomDrawHex=hex.EncodeToString(bytes.Repeat([]byte{255},8))},
  "nonrandom_draw":func(a *F61PilotAssignment){a.RandomDrawHex="0000000000000005"},
  "tamper_receipt":func(a *F61PilotAssignment){a.AssignmentSHA256=strings.Repeat("f",64)},
 }
 for name,change:=range mutations{
  t.Run(name,func(t *testing.T){
   a:=base
   a.SixPolicyArms=append([]F61PilotArm(nil),base.SixPolicyArms...)
   change(&a)
   if err:=ValidateF61Prepared(f,n,a);!errors.Is(err,ErrF61Pilot){
    t.Fatalf("altered science identity accepted %v",err)
   }
  })
 }
 if _,err:=PrepareF61OwnerSelection(f,n,slate,family,budget,nil);!errors.Is(err,ErrF61Pilot){
  t.Fatal("unrecorded randomness accepted")
 }
 badNom:=n
 badNom.DreamPolicySHA256=f.Lanes[0].Controls[0].SHA256
 if _,err:=PrepareF61OwnerSelection(f,badNom,slate,family,budget,f61DrawReader(0));!errors.Is(err,ErrF61Pilot){
  t.Fatal("frozen control reintroduced as challenger")
 }
}
