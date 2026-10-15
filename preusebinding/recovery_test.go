package preusebinding
import "testing"
func TestR37RecoveryNeverGrantsDispatchOrRetry(t *testing.T){
 s,p:=fixture();c,err:=Verify(s,p);if err!=nil{t.Fatal(err)}
 e:=RecoveryEvidence{
  OriginalKeySHA256:c.OriginalKeySHA256,DecisionSHA256:c.FrozenPredecisionSHA256,
  OwnerEpoch:c.OwnerEpoch,Sequence:c.ClaimedSequence,
  DatabaseClaimPresent:true,ClaimIdentityMatches:true,IndependentlyWitnessedClaim:true,
 }
 for _,tc:=range []struct{started,terminal,match bool;want string}{
  {false,false,false,"CONSUMED_UNCERTAIN_NO_RETRY"},
  {true,false,false,"CONSUMED_INTERRUPTED_NO_RETRY"},
  {true,true,true,"CONSUMED_TERMINAL_NEEDS_SCIENTIFIC_REVIEW"},
 }{
  x:=e;x.WorkerStartedReceiptPresent=tc.started;x.WorkerTerminalReceiptPresent=tc.terminal;x.StartedAndTerminalIdentityMatch=tc.match
  got,err:=Reconcile(c,x)
  if err!=nil||got.Status!=tc.want||!got.FirstUseConsumed||!got.ExternalFirstUseVerified||
   got.CanRetry||got.CanDispatch||got.ScientificAccepted{t.Fatalf("unsafe original recovery: %+v %v",got,err)}
 }
}
func TestR37ForgedOrMissingExternalEvidenceFailClosed(t *testing.T){
 s,p:=fixture();c,err:=Verify(s,p);if err!=nil{t.Fatal(err)}
 e:=RecoveryEvidence{OriginalKeySHA256:c.OriginalKeySHA256,DecisionSHA256:c.FrozenPredecisionSHA256,
  OwnerEpoch:c.OwnerEpoch,Sequence:c.ClaimedSequence,DatabaseClaimPresent:true,
  ClaimIdentityMatches:true,IndependentlyWitnessedClaim:true}
 for _,tc:=range []struct{name string;mutate func(*RecoveryEvidence)}{
  {"no_claim",func(x *RecoveryEvidence){x.DatabaseClaimPresent=false}},
  {"no_external_witness",func(x *RecoveryEvidence){x.IndependentlyWitnessedClaim=false}},
  {"wrong_identity",func(x *RecoveryEvidence){x.ClaimIdentityMatches=false}},
  {"wrong_decision",func(x *RecoveryEvidence){x.DecisionSHA256="f"+x.DecisionSHA256[1:]}},
  {"wrong_epoch",func(x *RecoveryEvidence){x.OwnerEpoch++}},
  {"wrong_sequence",func(x *RecoveryEvidence){x.Sequence++}},
  {"terminal_without_start",func(x *RecoveryEvidence){x.WorkerTerminalReceiptPresent=true}},
 }{
  t.Run(tc.name,func(t *testing.T){x:=e;tc.mutate(&x);got,err:=Reconcile(c,x);if err==nil||got!=(RecoveryReport{}){t.Fatal("accepted untrusted recovery evidence",got,err)}})
 }
}
