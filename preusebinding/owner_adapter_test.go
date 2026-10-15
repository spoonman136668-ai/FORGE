package preusebinding

import (
 "bytes"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "math"
 "reflect"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/originalclaim"
)

func r41Fixture()(originalclaim.SignedPredecision,originalclaim.Claim,originalclaim.PinnedTrust){
 h:=func(s string)string{x:=sha256.Sum256([]byte("R41_SYNTHETIC_"+s));return hex.EncodeToString(x[:])}
 c:=originalclaim.Claim{
  Schema:originalclaim.Schema,Lane:"Wingless",ExperimentID:"FUTURE_R41",
  FrozenSHA256:h("frozen"),IntentSHA256:h("intent"),SourceCommitSHA:strings.Repeat("a",40),
  OriginalRunID:"RUN_R41",OwnerEpoch:5,WorkerID:"worker_r41",FirstUseConsumed:true,
 }
 e:=originalclaim.Predecision{
  Schema:originalclaim.PredecisionSchema,Lane:c.Lane,ExperimentID:c.ExperimentID,
  FrozenSHA256:c.FrozenSHA256,IntentSHA256:c.IntentSHA256,SourceCommitSHA:c.SourceCommitSHA,
  OriginalRunID:c.OriginalRunID,OwnerEpoch:c.OwnerEpoch,WorkerID:c.WorkerID,
  PolicySHA256:h("policy"),CandidateSetSHA256:h("candidates"),
  SelectedCandidateSHA256:h("chosen"),BaselinePolicySHA256:[4]string{
   h("baseline_1"),h("baseline_2"),h("baseline_3"),h("baseline_4")},
  LoggedActionProbabilityBP:2500,RandomizationProofSHA256:h("randomization"),
  DecisionSequence:9,BeforeOutcomeDeclared:true,
 }
 a:=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{41},32))
 b:=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{42},32))
 raw,_:=json.Marshal(e)
 message:=append([]byte(originalclaim.PredecisionDomain),raw...)
 digest,_:=originalclaim.PredecisionHash(e)
 s:=originalclaim.SignedPredecision{Event:e,
  OwnerSignatureHex:hex.EncodeToString(ed25519.Sign(a,message)),
  WitnessSignatureHex:hex.EncodeToString(ed25519.Sign(b,message))}
 p:=originalclaim.PinnedTrust{
  OwnerPublicKeyHex:hex.EncodeToString(a.Public().(ed25519.PublicKey)),
  WitnessPublicKeyHex:hex.EncodeToString(b.Public().(ed25519.PublicKey)),
  ExpectedPredecisionSHA256:digest,ExpectedPolicySHA256:e.PolicySHA256,
  ExpectedBaselinePolicySHA256:e.BaselinePolicySHA256}
 return s,c,p
}
func TestR41CanonicalOwnerSignatureMapsToExactR35RowWithoutNewSignature(t *testing.T){
 s,c,p:=r41Fixture()
 got,err:=FromOwnerPredecision(s,c,p)
 if err!=nil{t.Fatal(err)}
 key:=sha256.Sum256([]byte(c.Lane+"\x00"+c.ExperimentID))
 pin:=sha256.Sum256([]byte(p.OwnerPublicKeyHex+"\x00"+p.WitnessPublicKeyHex))
 if got.ScientificAuthorized||got.ClaimedSequence!=s.Event.DecisionSequence||
  got.OriginalKeySHA256!=hex.EncodeToString(key[:])||
  got.ExternalOwnerWitnessPinSHA256!=hex.EncodeToString(pin[:])||
  got.FrozenPredecisionSHA256!=p.ExpectedPredecisionSHA256||
  got.OwnerEpoch!=c.OwnerEpoch||got.SourceCommitSHA!=c.SourceCommitSHA||got.Lane!=c.Lane {
  t.Fatalf("canonical signed source drifted into D1 tuple: %+v",got)
 }
 again,err:=FromOwnerPredecision(s,c,p)
 if err!=nil||!reflect.DeepEqual(again,got){t.Fatal("nondeterministic",err)}
 // Field names exactly match the existing additive R35 D1 claim contract.
 raw,err:=json.Marshal(got)
 if err!=nil{t.Fatal(err)}
 var fields map[string]any
 if json.Unmarshal(raw,&fields)!=nil{t.Fatal("invalid candidate JSON")}
 for _,k:=range []string{"original_key_sha256","lane","owner_epoch",
  "source_commit_sha","frozen_predecision_sha256","external_owner_witness_pin_sha256",
  "claimed_sequence","scientific_authorized"} {
  if _,ok:=fields[k];!ok{t.Fatalf("D1 field missing: %s",k)}
 }
}
func TestR41InvalidOrContradictoryOwnerEvidenceDeniedWithoutCandidate(t *testing.T){
 cases:=[]struct{name string;mutate func(*originalclaim.SignedPredecision,*originalclaim.Claim,*originalclaim.PinnedTrust)}{
  {"bad_owner_signature",func(s *originalclaim.SignedPredecision,c *originalclaim.Claim,p *originalclaim.PinnedTrust){s.OwnerSignatureHex=strings.Repeat("0",128)}},
  {"bad_witness_signature",func(s *originalclaim.SignedPredecision,c *originalclaim.Claim,p *originalclaim.PinnedTrust){s.WitnessSignatureHex=strings.Repeat("0",128)}},
  {"same_owner_witness",func(s *originalclaim.SignedPredecision,c *originalclaim.Claim,p *originalclaim.PinnedTrust){p.WitnessPublicKeyHex=p.OwnerPublicKeyHex}},
  {"unpinned_source",func(s *originalclaim.SignedPredecision,c *originalclaim.Claim,p *originalclaim.PinnedTrust){p.ExpectedPredecisionSHA256=strings.Repeat("f",64)}},
  {"different_lane",func(s *originalclaim.SignedPredecision,c *originalclaim.Claim,p *originalclaim.PinnedTrust){c.Lane="Yggdrasil"}},
  {"different_experiment",func(s *originalclaim.SignedPredecision,c *originalclaim.Claim,p *originalclaim.PinnedTrust){c.ExperimentID="OTHER"}},
  {"different_worker",func(s *originalclaim.SignedPredecision,c *originalclaim.Claim,p *originalclaim.PinnedTrust){c.WorkerID="other"}},
  {"source_drift",func(s *originalclaim.SignedPredecision,c *originalclaim.Claim,p *originalclaim.PinnedTrust){c.SourceCommitSHA=strings.Repeat("b",40)}},
  {"intent_drift",func(s *originalclaim.SignedPredecision,c *originalclaim.Claim,p *originalclaim.PinnedTrust){c.IntentSHA256=strings.Repeat("c",64)}},
  {"control_drift",func(s *originalclaim.SignedPredecision,c *originalclaim.Claim,p *originalclaim.PinnedTrust){p.ExpectedBaselinePolicySHA256[2]=strings.Repeat("d",64)}},
  {"after_outcome",func(s *originalclaim.SignedPredecision,c *originalclaim.Claim,p *originalclaim.PinnedTrust){s.Event.BeforeOutcomeDeclared=false}},
  {"claimed_unconsumed",func(s *originalclaim.SignedPredecision,c *originalclaim.Claim,p *originalclaim.PinnedTrust){c.FirstUseConsumed=false}},
  {"sequence_zero",func(s *originalclaim.SignedPredecision,c *originalclaim.Claim,p *originalclaim.PinnedTrust){s.Event.DecisionSequence=0}},
  {"epoch_overflow",func(s *originalclaim.SignedPredecision,c *originalclaim.Claim,p *originalclaim.PinnedTrust){c.OwnerEpoch=uint64(math.MaxInt64)+1;s.Event.OwnerEpoch=c.OwnerEpoch}},
  {"sequence_overflow",func(s *originalclaim.SignedPredecision,c *originalclaim.Claim,p *originalclaim.PinnedTrust){s.Event.DecisionSequence=uint64(math.MaxInt64)+1}},
 }
 for _,tc:=range cases{
  t.Run(tc.name,func(t *testing.T){
   s,c,p:=r41Fixture()
   tc.mutate(&s,&c,&p)
   got,err:=FromOwnerPredecision(s,c,p)
   if err==nil||got!=(Claim{}){t.Fatalf("untrusted origin admitted: %+v %v",got,err)}
  })
 }
}
