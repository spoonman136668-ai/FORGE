package optimizerstages

import (
 "bytes"
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "strings"
 "testing"
)

func f90SyntheticRows(t *testing.T,f FrozenSixPolicyTrial,seed byte,start uint64,n int)[]F90Observation{
 t.Helper()
 private:=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{seed},ed25519.SeedSize))
 public:=private.Public().(ed25519.PublicKey)
 out:=make([]F90Observation,0,n)
 for i:=0;i<n;i++{
  a,err:=PrepareF89Selection(f,f89Raw(start+uint64(i)))
  if err!=nil{t.Fatal(err)}
  witness:=F90Predecision{
   Schema:F90WitnessSchema,Lane:f.Lane,
   FrozenDesignSHA256:F89FreezeDigest(f),AssignmentSHA256:a.AssignmentSHA256,
   OwnerSourceSHA:f.OwnerSourceSHA,PreregistrationSHA256:f.PreregistrationSHA256,
   CandidateSlateSHA256:f.CandidateSlateSHA256,
   OriginalReceiptSHA256:f90Hash([]byte(fmt.Sprintf("synthetic-%s-%d",f.Lane,i))),
   Sequence:uint64(i+1),ClaimedPredecisionUnix:int64(200000+i*10),
  }
  raw,_:=json.Marshal(witness)
  sig:=ed25519.Sign(private,append([]byte(F90SignatureDomain),raw...))
  out=append(out,F90Observation{
   Assignment:a,Witness:F90SignedPredecision{
    Record:witness,SignatureHex:hex.EncodeToString(sig),
   },
   Pin:F90Pin{WitnessPublicKeyHex:hex.EncodeToString(public),
    SignedRecordSHA256:f90Hash(raw)},
   Classification:"SUPPORTED",Score:int64(30+i),ComputeUnits:int64(10+i),
   ClaimedOutcomeUnix:witness.ClaimedPredecisionUnix+5,
  })
 }
 return out
}

func TestF90SourceOnlyRealAuthorityNeverInferred(t *testing.T){
 w,y:=f89Frozen("Wingless"),f89Frozen("Yggdrasil")
 wr:=f90SyntheticRows(t,w,11,0,6)
 yr:=f90SyntheticRows(t,y,12,10,6)
 audit,err:=AuditF90PreparedOutcomes(w,wr,y,yr)
 if err!=nil{t.Fatal(err)}
 if !audit.SourceCryptographyConsistent||len(audit.Lanes)!=2||
  audit.ExactPolicyArmProbabilityNumerator!=1||audit.ExactPolicyArmProbabilityDenominator!=6||
  audit.RealPreOutcomeCustodyIndependentlyProven||
  audit.AuthenticRandomnessIndependentlyProven||
  audit.CompleteOwnerLeaseHistoryVerified||audit.FirstUseOriginalIndependentlyVerified||
  audit.CausalGainScientificallyEstablished||
  audit.DreamParetoActivationAuthorized||audit.ThetaEvolveAcceptedTrainingEnabled||
  audit.ScientificOriginalDispatchAuthorized||audit.AcceptedReferenceMutation{
  t.Fatalf("source-only test forged authority: %+v",audit)
 }
 if !strings.Contains(audit.Status,"NOT_INDEPENDENTLY_WITNESSED"){t.Fatalf("missing stop line %+v",audit)}
 for _,l:=range audit.Lanes{
  if l.SourceOnlyAssignmentCount!=6||l.MissingOutcomes!=0||
   !l.SignedWitnessClaimsConsistent||!l.ReportedTimeSequenceConsistent||
   len(l.Arms)!=6{t.Fatalf("bad source audit %+v",l)}
  for armIndex,a:=range l.Arms{
   if a.Assigned!=1||a.Observed!=1||a.Missing!=0||
    a.ScoreIPS!=fmt.Sprintf("%d",30+armIndex)||
    a.ComputeIPS!=fmt.Sprintf("%d",10+armIndex){
    // Different random draws can select the same arms, so the all-arms
    // fixture here is deliberately based on chosen index rather than row.
    t.Fatalf("unexpected arm diagnostic %+v",a)
   }
  }
 }
}

func TestF90MissingOutcomeSuppressesAllIPSEstimates(t *testing.T){
 w,y:=f89Frozen("Wingless"),f89Frozen("Yggdrasil")
 wr:=f90SyntheticRows(t,w,11,0,6)
 yr:=f90SyntheticRows(t,y,12,10,6)
 yr[3].Classification="MISSING";yr[3].Score=0;yr[3].ComputeUnits=0
 got,err:=AuditF90PreparedOutcomes(w,wr,y,yr)
 if err!=nil{t.Fatal(err)}
 if got.Lanes[1].MissingOutcomes!=1{t.Fatalf("missing outcome erased %+v",got.Lanes[1])}
 for _,a:=range got.Lanes[1].Arms{
  if a.ScoreIPS!=""||a.ComputeIPS!=""{t.Fatalf("partial IPS from missing outcome %+v",a)}
 }
 if got.DreamParetoActivationAuthorized||got.ThetaEvolveAcceptedTrainingEnabled{
  t.Fatalf("missing outcome authorized science %+v",got)
 }
}

func TestF90CryptographyAndFirstUseClaimsFailClosed(t *testing.T){
 f:=f89Frozen("Wingless")
 baseline:=f90SyntheticRows(t,f,11,0,6)
 cases:=map[string]func([]F90Observation){
  "bad witness signature":func(p []F90Observation){p[2].Witness.SignatureHex=strings.Repeat("f",128)},
  "untrusted public key":func(p []F90Observation){p[2].Pin.WitnessPublicKeyHex=strings.Repeat("1",64)},
  "altered independent pin":func(p []F90Observation){p[2].Pin.SignedRecordSHA256=strings.Repeat("2",64)},
  "altered owner sequence":func(p []F90Observation){p[2].Witness.Record.Sequence=2},
  "changed owner source":func(p []F90Observation){p[2].Witness.Record.OwnerSourceSHA=strings.Repeat("e",40)},
  "substituted original":func(p []F90Observation){p[2].Witness.Record.OriginalReceiptSHA256=strings.Repeat("a",64)},
  "owner switched key":func(p []F90Observation){p[2]=f90SyntheticRows(t,f,15,2,1)[0]},
  "bad future timestamp":func(p []F90Observation){p[2].ClaimedOutcomeUnix=p[2].Witness.Record.ClaimedPredecisionUnix},
  "forged firstuse authority":func(p []F90Observation){p[2].Assignment.OwnerFirstUseAuthenticated=true},
  "forged scientific policy gain":func(p []F90Observation){p[2].Assignment.CausalGainEstablished=true},
  "missing without zero budget":func(p []F90Observation){p[2].Classification="MISSING"},
  "bad class":func(p []F90Observation){p[2].Classification="PROMOTED"},
  "bad compute":func(p []F90Observation){p[2].ComputeUnits=0},
  "tampered arm":func(p []F90Observation){p[2].Assignment.ArmIndex=0},
  "reused assignment":func(p []F90Observation){p[2]=p[1]},
 }
 for name,mutate:=range cases{
  t.Run(name,func(t *testing.T){
   rows:=append([]F90Observation(nil),baseline...)
   mutate(rows)
   if _,err:=f90AuditLane(f,rows);!errors.Is(err,ErrF90){
    t.Fatalf("malformed signed study qualified: %v",err)
   }
  })
 }
}
func TestF90TwoLaneSourceAndSignerIsolation(t *testing.T){
 w,y:=f89Frozen("Wingless"),f89Frozen("Yggdrasil")
 wr:=f90SyntheticRows(t,w,11,0,6)
 yr:=f90SyntheticRows(t,y,12,10,6)
 if _,err:=AuditF90PreparedOutcomes(w,wr,y,yr);err!=nil{t.Fatal(err)}
 reusedKey:=f90SyntheticRows(t,y,11,10,6)
 if _,err:=AuditF90PreparedOutcomes(w,wr,y,reusedKey);!errors.Is(err,ErrF90){
  t.Fatalf("same signer across both lanes accepted: %v",err)
 }
 reusedDraw:=f90SyntheticRows(t,y,12,0,6)
 if _,err:=AuditF90PreparedOutcomes(w,wr,y,reusedDraw);!errors.Is(err,ErrF90){
  t.Fatalf("reused cross-lane assignment raw draw accepted: %v",err)
 }
 if _,err:=AuditF90PreparedOutcomes(w,nil,y,yr);!errors.Is(err,ErrF90){t.Fatal("empty lane accepted")}
}
