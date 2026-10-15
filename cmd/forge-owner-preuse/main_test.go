package main

import(
 "bytes"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/originalclaim"
)
func fixture(t *testing.T)(string,[]string,originalclaim.Claim){
 t.Helper()
 root:=t.TempDir()
 digest:=func(v string)string{h:=sha256.Sum256([]byte("R32_TEST_ONLY_"+v));return hex.EncodeToString(h[:])}
 claim:=originalclaim.Claim{
  Schema:originalclaim.Schema,Lane:"Wingless",ExperimentID:"FUTURE_01",
  SourceCommitSHA:strings.Repeat("a",40),
  FrozenSHA256:digest("frozen"),IntentSHA256:digest("intent"),
  OriginalRunID:"future_01",OwnerEpoch:17,WorkerID:"test_worker",
  FirstUseConsumed:true,
 }
 owner:=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{21},ed25519.SeedSize))
 witness:=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{31},ed25519.SeedSize))
 event:=originalclaim.Predecision{
  Schema:originalclaim.PredecisionSchema,Lane:claim.Lane,
  ExperimentID:claim.ExperimentID,FrozenSHA256:claim.FrozenSHA256,
  IntentSHA256:claim.IntentSHA256,SourceCommitSHA:claim.SourceCommitSHA,
  OriginalRunID:claim.OriginalRunID,OwnerEpoch:claim.OwnerEpoch,
  WorkerID:claim.WorkerID,PolicySHA256:digest("policy"),
  CandidateSetSHA256:digest("candidates"),SelectedCandidateSHA256:digest("selected"),
  BaselinePolicySHA256:[4]string{digest("b1"),digest("b2"),digest("b3"),digest("b4")},
  LoggedActionProbabilityBP:2500,RandomizationProofSHA256:digest("random"),
  DecisionSequence:1,BeforeOutcomeDeclared:true,
 }
 raw,_:=json.Marshal(event)
 msg:=append([]byte(originalclaim.PredecisionDomain),raw...)
 signed:=originalclaim.SignedPredecision{
  Event:event,OwnerSignatureHex:hex.EncodeToString(ed25519.Sign(owner,msg)),
  WitnessSignatureHex:hex.EncodeToString(ed25519.Sign(witness,msg)),
 }
 eventHash,_:=originalclaim.PredecisionHash(event)
 pins:=originalclaim.PinnedTrust{
  OwnerPublicKeyHex:hex.EncodeToString(owner.Public().(ed25519.PublicKey)),
  WitnessPublicKeyHex:hex.EncodeToString(witness.Public().(ed25519.PublicKey)),
  ExpectedPredecisionSHA256:eventHash,ExpectedPolicySHA256:event.PolicySHA256,
  ExpectedBaselinePolicySHA256:event.BaselinePolicySHA256,
 }
 write:=func(name string,v any)string{
  path:=filepath.Join(root,name)
  b,err:=json.Marshal(v)
  if err!=nil{t.Fatal(err)}
  if err:=os.WriteFile(path,append(b,'\n'),0600);err!=nil{t.Fatal(err)}
  return path
 }
 c:=write("claim.json",claim)
 s:=write("signed.json",signed)
 p:=write("pins.json",pins)
 journal:=filepath.Join(root,"journal")
 if err:=os.Mkdir(journal,0700);err!=nil{t.Fatal(err)}
 args:=[]string{"--claim",c,"--signed-predecision",s,"--independent-pins",p,
  "--journal-dir",journal,"--expected-lane","Wingless",
  "--expected-experiment","FUTURE_01","--expected-source-commit",strings.Repeat("a",40)}
 return root,args,claim
}
func TestR32ValidSyntheticRecordIsAlwaysNonAuthorizing(t *testing.T){
 _,args,claim:=fixture(t)
 var out bytes.Buffer
 got,err:=run(args,&out)
 if err!=nil{t.Fatal(err)}
 if got.Schema!="forge.original.r32-owner-local-preuse-record.v1"||
  got.ExperimentID!=claim.ExperimentID||got.SourceCommitSHA!=claim.SourceCommitSHA||
  !got.SignedOwnerPredecisionVerified||!got.LocalFirstUseClaimVerified||
  got.IndependentSignerDeploymentVerified||got.ExternalMonotonicFirstUseCASVerified||
  got.GenuineRandomizationVerified||got.ScientificExecutionAuthorized||
  got.ScientificImprovementEstablished||got.OriginalsExecuted!=0{
  t.Fatalf("test-only signed proof became independent scientific authority: %+v",got)
 }
 var reread Report
 if err:=json.Unmarshal(out.Bytes(),&reread);err!=nil||reread!=got{t.Fatal("noncanonical report",err)}
 out.Reset()
 if second,err:=run(args,&out);err==nil||out.Len()!=0||second!= (Report{}){
  t.Fatal("duplicate first-use accepted")
 }
}
func TestR32UntrustedSourceAndSignerFailWithoutClaim(t *testing.T){
 for _,tc:=range []struct{
  name string;mutate func([]string)[]string
 }{
  {"missing claim",func(a []string)[]string{a[1]="/does/not/exist";return a}},
  {"wrong parent/source",func(a []string)[]string{a[len(a)-1]=strings.Repeat("b",40);return a}},
  {"wrong lane",func(a []string)[]string{a[9]="Yggdrasil";return a}},
  {"wrong original",func(a []string)[]string{a[11]="FUTURE_02";return a}},
  {"shared pin and claim source",func(a []string)[]string{a[5]=a[1];return a}},
  {"missing journal",func(a []string)[]string{a[7]="/does/not/exist";return a}},
 }{
  t.Run(tc.name,func(t *testing.T){
   _,args,_:=fixture(t)
   args=tc.mutate(args)
   var out bytes.Buffer
   got,err:=run(args,&out)
   if err==nil||out.Len()!=0||got!=(Report{}){
    t.Fatalf("untrusted owner input accepted: %s %v",tc.name,err)
   }
  })
 }
}
func TestR32ForgedWitnessDeniedBeforeLocalFirstUse(t *testing.T){
 root,args,_:=fixture(t)
 signed:=args[3]
 b,err:=os.ReadFile(signed)
 if err!=nil{t.Fatal(err)}
 var v originalclaim.SignedPredecision
 if json.Unmarshal(b,&v)!=nil{t.Fatal("bad fixture")}
 v.WitnessSignatureHex=strings.Repeat("0",128)
 raw,_:=json.Marshal(v)
 if err:=os.WriteFile(signed,append(raw,'\n'),0600);err!=nil{t.Fatal(err)}
 var out bytes.Buffer
 if _,err:=run(args,&out);err==nil{t.Fatal("forged witness accepted")}
 files,err:=os.ReadDir(filepath.Join(root,"journal"))
 if err!=nil||len(files)!=0{t.Fatal("untrusted signer touched first-use journal",err)}
}
func TestR32NoSymlinkOrUnknownFieldOwnerInputs(t *testing.T){
 _,args,_:=fixture(t)
 link:=filepath.Join(t.TempDir(),"claim-link")
 if err:=os.Symlink(args[1],link);err==nil{
  copyArgs:=append([]string(nil),args...)
  copyArgs[1]=link
  if _,err:=run(copyArgs,&bytes.Buffer{});err==nil{t.Fatal("source symlink accepted")}
 }
 for _,path:=range []string{args[1],args[3],args[5]}{
  raw,err:=os.ReadFile(path)
  if err!=nil{t.Fatal(err)}
  changed:=append([]byte{},bytes.TrimSuffix(raw,[]byte("\n"))...)
  changed=append(changed[:len(changed)-1],[]byte(`,"extra":"field"}`)...)
  if err:=os.WriteFile(path,changed,0600);err!=nil{t.Fatal(err)}
  if _,err:=run(args,&bytes.Buffer{});err==nil{t.Fatal("unknown source field accepted")}
  if err:=os.WriteFile(path,raw,0600);err!=nil{t.Fatal(err)}
 }
}
