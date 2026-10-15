package preusebinding
import(
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "reflect"
 "strings"
 "testing"
)
func fixture()(Signed,IndependentPins){
 owner:=ed25519.NewKeyFromSeed(make([]byte,32))
 seed:=make([]byte,32);for i:=range seed{seed[i]=1}
 witness:=ed25519.NewKeyFromSeed(seed)
 h:=func(s string)string{x:=sha256.Sum256([]byte(s));return hex.EncodeToString(x[:])}
 d:=Decision{Lane:"Wingless",OwnerEpoch:4,SourceCommitSHA:strings.Repeat("a",40),
  OriginalKeySHA256:h("original"),FrozenPolicySHA256:h("policy"),
  CandidateSetSHA256:h("candidates"),ChosenCandidateSHA256:h("choice"),
  LoggedProbabilityBP:2500,RandomizationProofSHA256:h("random"),Sequence:8}
 body,_:=json.Marshal(d);message:=append([]byte(Domain),body...)
 digest:=sha256.Sum256(message)
 return Signed{Decision:d,OwnerSignatureHex:hex.EncodeToString(ed25519.Sign(owner,message)),
  WitnessSignatureHex:hex.EncodeToString(ed25519.Sign(witness,message))},
  IndependentPins{OwnerPublicKeyHex:hex.EncodeToString(owner.Public().(ed25519.PublicKey)),
   WitnessPublicKeyHex:hex.EncodeToString(witness.Public().(ed25519.PublicKey)),
   ExactDecisionSHA256:hex.EncodeToString(digest[:])}
}
func TestR36SignedSourceBindsR35CandidateWithoutAuthorizing(t *testing.T){
 s,p:=fixture()
 c,err:=Verify(s,p)
 if err!=nil{t.Fatal(err)}
 if c.ScientificAuthorized||c.ClaimedSequence!=8||c.OwnerEpoch!=4||
  c.Lane!="Wingless"||c.FrozenPredecisionSHA256!=p.ExactDecisionSHA256||
  !validHex(c.ExternalOwnerWitnessPinSHA256,64){t.Fatalf("false authorization or identity drift: %+v",c)}
 again,err:=Verify(s,p)
 if err!=nil||!reflect.DeepEqual(c,again){t.Fatal("nondeterministic")}
}
func TestR36AllUntrustedInputsDeniedWithoutClaims(t *testing.T){
 edits:=[]struct{name string;change func(*Signed,*IndependentPins)}{
  {"owner_signature",func(s *Signed,p *IndependentPins){s.OwnerSignatureHex=strings.Repeat("0",128)}},
  {"witness_signature",func(s *Signed,p *IndependentPins){s.WitnessSignatureHex=strings.Repeat("0",128)}},
  {"same_keys",func(s *Signed,p *IndependentPins){p.WitnessPublicKeyHex=p.OwnerPublicKeyHex}},
  {"false_pin",func(s *Signed,p *IndependentPins){p.ExactDecisionSHA256=strings.Repeat("f",64)}},
  {"source_drift",func(s *Signed,p *IndependentPins){s.Decision.SourceCommitSHA=strings.Repeat("b",40)}},
  {"wrong_lane",func(s *Signed,p *IndependentPins){s.Decision.Lane="FORGE"}},
  {"missing_random",func(s *Signed,p *IndependentPins){s.Decision.RandomizationProofSHA256=""}},
  {"missing_probability",func(s *Signed,p *IndependentPins){s.Decision.LoggedProbabilityBP=0}},
  {"invalid_probability",func(s *Signed,p *IndependentPins){s.Decision.LoggedProbabilityBP=10001}},
  {"reused_sequence_zero",func(s *Signed,p *IndependentPins){s.Decision.Sequence=0}},
  {"revised_policy",func(s *Signed,p *IndependentPins){s.Decision.FrozenPolicySHA256=strings.Repeat("c",64)}},
 }
 for _,tc:=range edits{t.Run(tc.name,func(t *testing.T){
  s,p:=fixture();tc.change(&s,&p)
  c,err:=Verify(s,p)
  if err==nil||c!=(Claim{}){t.Fatalf("invalid signed claim admitted: %v",err)}
 })}
}
