package originalclaim

import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "os"
 "path/filepath"
 "reflect"
 "strings"
 "sync"
 "testing"
)

func r30Signed(c Claim)(SignedPredecision,PinnedTrust){
 digest:=func(v string)string{
  h:=sha256.Sum256([]byte("R30_SYNTHETIC_NOT_SCIENTIFIC_"+v))
  return hex.EncodeToString(h[:])
 }
 ownerKey:=ed25519.NewKeyFromSeed(bytesRepeat(31,ed25519.SeedSize))
 witnessKey:=ed25519.NewKeyFromSeed(bytesRepeat(37,ed25519.SeedSize))
 event:=Predecision{
  Schema:PredecisionSchema,
  Lane:c.Lane,ExperimentID:c.ExperimentID,
  FrozenSHA256:c.FrozenSHA256,IntentSHA256:c.IntentSHA256,
  SourceCommitSHA:c.SourceCommitSHA,OriginalRunID:c.OriginalRunID,
  OwnerEpoch:c.OwnerEpoch,WorkerID:c.WorkerID,
  PolicySHA256:digest("selected-policy"),
  CandidateSetSHA256:digest("candidate-set"),
  SelectedCandidateSHA256:digest("specific-candidate"),
  BaselinePolicySHA256:[4]string{
   digest("baseline-a"),digest("baseline-b"),digest("baseline-c"),digest("baseline-d"),
  },
  LoggedActionProbabilityBP:5000,
  RandomizationProofSHA256:digest("synthetic-randomized-proof"),
  DecisionSequence:19,BeforeOutcomeDeclared:true,
 }
 raw,_:=json.Marshal(event)
 message:=append([]byte(PredecisionDomain),raw...)
 hash,_:=PredecisionHash(event)
 signed:=SignedPredecision{Event:event,
  OwnerSignatureHex:hex.EncodeToString(ed25519.Sign(ownerKey,message)),
  WitnessSignatureHex:hex.EncodeToString(ed25519.Sign(witnessKey,message))}
 pins:=PinnedTrust{
  OwnerPublicKeyHex:hex.EncodeToString(ownerKey.Public().(ed25519.PublicKey)),
  WitnessPublicKeyHex:hex.EncodeToString(witnessKey.Public().(ed25519.PublicKey)),
  ExpectedPredecisionSHA256:hash,ExpectedPolicySHA256:event.PolicySHA256,
  ExpectedBaselinePolicySHA256:event.BaselinePolicySHA256,
 }
 return signed,pins
}
func bytesRepeat(v byte,n int)[]byte{
 b:=make([]byte,n)
 for i:=range b{b[i]=v}
 return b
}
func TestR30SignedPredecisionFollowedByExactlyOneDurableFirstUse(t *testing.T){
 root:=t.TempDir()
 c:=fixture()
 signed,pins:=r30Signed(c)
 if err:=ConsumeWithPredecision(root,c,signed,pins);err!=nil{t.Fatal(err)}
 got,assessment,err:=ReadPredecision(root,c,pins)
 if err!=nil{t.Fatal(err)}
 if !reflect.DeepEqual(got,signed)||
  !assessment.ClaimVerified||!assessment.PredecisionSigned||
  assessment.ActualPreOutcomeTimingIndependentlyVerified||
  assessment.IndependentExternalFirstUseVerified||
  assessment.ScientificExecutionAuthorized||assessment.ScientificImprovementEstablished{
  t.Fatalf("owner cryptographic record inflated into science authority: %+v",assessment)
 }
 if err:=ConsumeWithPredecision(root,c,signed,pins);err==nil{
  t.Fatal("duplicate original was redispatched")
 }
}
func TestR30ConcurrentOwnerPredecisionsHaveOnlyOneWinner(t *testing.T){
 root:=t.TempDir()
 c:=fixture()
 signed,pins:=r30Signed(c)
 var wait sync.WaitGroup
 successes:=make(chan bool,32)
 for i:=0;i<32;i++{
  wait.Add(1)
  go func(){defer wait.Done();successes<-ConsumeWithPredecision(root,c,signed,pins)==nil}()
 }
 wait.Wait()
 close(successes)
 count:=0
 for v:=range successes{if v{count++}}
 if count!=1{t.Fatalf("cross-worker duplicate first-use=%d",count)}
 if _,_,err:=ReadPredecision(root,c,pins);err!=nil{t.Fatal(err)}
}
func TestR30UntrustedOwnerSourceDoesNotTouchOriginalClaim(t *testing.T){
 base:=fixture()
 for _,tc:=range []struct{
  name string
  edit func(*SignedPredecision,*PinnedTrust,*Claim)
 }{
  {"signature_not_signed",func(s *SignedPredecision,p *PinnedTrust,c *Claim){s.OwnerSignatureHex=strings.Repeat("0",128)}},
  {"witness_not_signed",func(s *SignedPredecision,p *PinnedTrust,c *Claim){s.WitnessSignatureHex=strings.Repeat("0",128)}},
  {"owner_key_unpinned",func(s *SignedPredecision,p *PinnedTrust,c *Claim){p.OwnerPublicKeyHex=""}},
  {"owner_and_witness_same_key",func(s *SignedPredecision,p *PinnedTrust,c *Claim){p.WitnessPublicKeyHex=p.OwnerPublicKeyHex}},
  {"wrong_event_pin",func(s *SignedPredecision,p *PinnedTrust,c *Claim){p.ExpectedPredecisionSHA256=strings.Repeat("f",64)}},
  {"wrong_frozen_policy",func(s *SignedPredecision,p *PinnedTrust,c *Claim){p.ExpectedPolicySHA256=strings.Repeat("f",64)}},
  {"late_declared",func(s *SignedPredecision,p *PinnedTrust,c *Claim){s.Event.BeforeOutcomeDeclared=false}},
  {"zero_probability",func(s *SignedPredecision,p *PinnedTrust,c *Claim){s.Event.LoggedActionProbabilityBP=0}},
  {"probability_over_1",func(s *SignedPredecision,p *PinnedTrust,c *Claim){s.Event.LoggedActionProbabilityBP=10001}},
  {"source_commit_drift",func(s *SignedPredecision,p *PinnedTrust,c *Claim){s.Event.SourceCommitSHA=strings.Repeat("f",40)}},
  {"epoch_drift",func(s *SignedPredecision,p *PinnedTrust,c *Claim){s.Event.OwnerEpoch++}},
  {"worker_drift",func(s *SignedPredecision,p *PinnedTrust,c *Claim){s.Event.WorkerID="other-worker"}},
  {"candidate_hash_reused",func(s *SignedPredecision,p *PinnedTrust,c *Claim){s.Event.SelectedCandidateSHA256=s.Event.CandidateSetSHA256}},
  {"same_baseline_twice",func(s *SignedPredecision,p *PinnedTrust,c *Claim){s.Event.BaselinePolicySHA256[1]=s.Event.BaselinePolicySHA256[0]}},
  {"baseline_identity_drift",func(s *SignedPredecision,p *PinnedTrust,c *Claim){p.ExpectedBaselinePolicySHA256[2]=strings.Repeat("d",64)}},
  {"no_randomization_proof",func(s *SignedPredecision,p *PinnedTrust,c *Claim){s.Event.RandomizationProofSHA256=""}},
  {"claim_not_consumed",func(s *SignedPredecision,p *PinnedTrust,c *Claim){c.FirstUseConsumed=false}},
  {"decision_seq_zero",func(s *SignedPredecision,p *PinnedTrust,c *Claim){s.Event.DecisionSequence=0}},
 } {
  t.Run(tc.name,func(t *testing.T){
   root:=t.TempDir()
   c:=base
   signed,pins:=r30Signed(c)
   tc.edit(&signed,&pins,&c)
   if err:=ConsumeWithPredecision(root,c,signed,pins);err==nil{t.Fatal("untrusted first-use admitted")}
   files,err:=os.ReadDir(root)
   if err!=nil||len(files)!=0{t.Fatalf("untrusted claim persisted files=%d %v",len(files),err)}
  })
 }
}
func TestR30InterruptedAfterPredecisionNeverAllowsAutomaticRetry(t *testing.T){
 root:=t.TempDir()
 c:=fixture()
 signed,pins:=r30Signed(c)
 b,err:=signedCanonical(signed)
 if err!=nil{t.Fatal(err)}
 if err=os.WriteFile(predecisionPath(root,c),b,0600);err!=nil{t.Fatal(err)}
 if err=ConsumeWithPredecision(root,c,signed,pins);err==nil{
  t.Fatal("uncertain predecision automatically retried")
 }
 if _,err=os.Stat(path(root,c));!os.IsNotExist(err){
  t.Fatal("interrupted predecision falsely recorded a completed local claim")
 }
 if _,_,err:=ReadPredecision(root,c,pins);err==nil{
  t.Fatal("unconsumed original appeared verified")
 }
}
func TestR30TamperedPredecisionReadbackFailsClosed(t *testing.T){
 root:=t.TempDir()
 c:=fixture()
 signed,pins:=r30Signed(c)
 if err:=ConsumeWithPredecision(root,c,signed,pins);err!=nil{t.Fatal(err)}
 if err:=os.WriteFile(predecisionPath(root,c),[]byte("{}\n"),0600);err!=nil{t.Fatal(err)}
 if _,_,err:=ReadPredecision(root,c,pins);err==nil{t.Fatal("tampered predecision trusted")}
 if err:=ConsumeWithPredecision(root,c,signed,pins);err==nil{
  t.Fatal("tampered first-use replayed")
 }
}
func TestR30DoesNotCreateUnownedRootsOrTreatRelativeFilesystemAsAuthority(t *testing.T){
 c:=fixture()
 signed,pins:=r30Signed(c)
 if err:=ConsumeWithPredecision(filepath.Join(t.TempDir(),"missing"),c,signed,pins);err==nil{
  t.Fatal("unbound source directory accepted")
 }
 if err:=ConsumeWithPredecision(".",c,signed,pins);err==nil{
  t.Fatal("relative cwd treated as independent custody")
 }
}
