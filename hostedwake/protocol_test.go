package hostedwake

import (
 "bytes"
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "errors"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/hostedgrant"
)
type fixture struct{
 wake SignedIntent
 pin Pin
 ctx Context
 claim Claim
 observation Observation
 grantReview hostedgrant.Review
 lease SignedLease
 leaseSHA string
 intentKey ed25519.PrivateKey
 leaseKey ed25519.PrivateKey
}
func key(marker byte)ed25519.PrivateKey{
 return ed25519.NewKeyFromSeed(bytes.Repeat([]byte{marker},32))
}
func pub(private ed25519.PrivateKey)string{
 return hex.EncodeToString(private.Public().(ed25519.PublicKey))
}
func sign(private ed25519.PrivateKey,domain string,v any)string{
 raw,_:=json.Marshal(v)
 return hex.EncodeToString(ed25519.Sign(private,append([]byte(domain),raw...)))
}
func fixtureFor(t *testing.T,lane string)fixture{
 t.Helper()
 intentKey,leaseKey,headKey:=key(17),key(18),key(19)
 ctx:=Context{Repository:hostedgrant.ExpectedRepository,
  Workflow:hostedgrant.ExpectedWorkflow,
  SourceSHA:strings.Repeat("a",40),
  TreeSHA:strings.Repeat("b",40),
  Lane:lane,RunID:"38155009101",Attempt:1}
 in:=Intent{
  Schema:IntentSchema,Mode:IntentMode,
  Repository:ctx.Repository,Workflow:ctx.Workflow,
  SourceSHA:ctx.SourceSHA,TreeSHA:ctx.TreeSHA,
  Lane:lane,Generation:21,ExperimentID:"EXPERIMENT_21",
  CohortSHA256:strings.Repeat("c",64),
  PreregSHA256:strings.Repeat("d",64),
  ScopeSHA256:strings.Repeat("e",64),
  CorrelationSHA256:strings.Repeat("f",64),
  FSAArchiveID:strings.Repeat("1",64),
  FSAEpoch:8,SourceWitnessSHA256:strings.Repeat("2",64),
  MaxComputeUnits:320}
 wakeSHA,_:=sha(in)
 pin:=Pin{IntentSHA256:wakeSHA,IntentKeyHex:pub(intentKey),
  LeaseKeyHex:pub(leaseKey),FSAHeadKeyHex:pub(headKey)}
 wake:=SignedIntent{Intent:in,SignatureHex:sign(intentKey,IntentDomain,in)}
 claim,obs,err:=ObserveWake(wake,pin,ctx)
 if err!=nil{t.Fatal(err)}
 grant:=hostedgrant.Review{Schema:hostedgrant.ReviewSchema,
  Mode:"CRYPTOGRAPHIC_REVIEW_ONLY_NO_EXECUTION",
  GrantSHA256:strings.Repeat("3",64),
  SourceSHA:ctx.SourceSHA,Lane:lane,CohortSHA256:in.CohortSHA256,
  FirstUseObserved:true}
 cs,_:=sha(claim)
 lease:=Lease{
  Schema:LeaseSchema,Mode:LeaseMode,
  PrewakeSHA256:wakeSHA,ClaimSHA256:cs,RunID:ctx.RunID,
  Attempt:1,Lane:lane,CohortSHA256:in.CohortSHA256,
  GrantSHA256:grant.GrantSHA256,
  FSAArchiveID:in.FSAArchiveID,FSAEpoch:in.FSAEpoch,
  ConsumedDispatchSequence:87,
  ConsumedDispatchHeadSHA256:strings.Repeat("4",64),
  DispatchLockWitnessSHA256:strings.Repeat("5",64),
  ConsumedDispatchLease:true}
 leaseSHA,_:=sha(lease)
 return fixture{wake:wake,pin:pin,ctx:ctx,claim:claim,
  observation:obs,grantReview:grant,
  lease:SignedLease{Lease:lease,SignatureHex:sign(leaseKey,LeaseDomain,lease)},
  leaseSHA:leaseSHA,intentKey:intentKey,leaseKey:leaseKey}
}
func (f *fixture)resignIntent(){
 f.wake.SignatureHex=sign(f.intentKey,IntentDomain,f.wake.Intent)
 f.pin.IntentSHA256,_=sha(f.wake.Intent)
}
func (f *fixture)resignLease(){
 f.lease.SignatureHex=sign(f.leaseKey,LeaseDomain,f.lease.Lease)
 f.leaseSHA,_=sha(f.lease.Lease)
}
func TestWakeBeforeRunIDCanLaterBindRealGitHubContext(t *testing.T){
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  f:=fixtureFor(t,lane)
  before,_:=json.Marshal(f.wake.Intent)
  if bytes.Contains(before,[]byte("RunID")){t.Fatal("prewake requires unavailable GitHub run ID")}
  c,o,err:=ObserveWake(f.wake,f.pin,f.ctx)
  if err!=nil||c.RunID!=f.ctx.RunID||o.RunID!=f.ctx.RunID||
   o.DispatchAuthorized||o.ScientificOriginalStarted||
   o.FSAOperational||o.GitHubOIDCIndependentlyVerified{
   t.Fatalf("untrusted wake self-authorized: %v %+v",err,o)
  }
  reviewed,err:=VerifyLease(c,o,f.lease,f.leaseSHA,f.pin,f.grantReview)
  if err!=nil||reviewed.Mode!="SIGNED_LEASE_CLAIM_REVIEWED_NO_EXECUTION"||
   reviewed.DispatchAuthorized||reviewed.ScientificOriginalStarted||
   reviewed.ProtectedDispatchConsumptionIndependentlyAudited||
   reviewed.FSAOperational||reviewed.GitHubOIDCIndependentlyVerified{
   t.Fatalf("signed lease claim falsely allowed execution: %v %+v",err,reviewed)
  }
 }
}
func TestWakeIdentityReplayAndForeignSourceRefused(t *testing.T){
 alters:=[]func(*fixture){
  func(f *fixture){f.ctx.Attempt=2},
  func(f *fixture){f.ctx.RunID="0"},
  func(f *fixture){f.ctx.RunID="01"},
  func(f *fixture){f.ctx.Repository="attacker/FORGE"},
  func(f *fixture){f.ctx.Workflow=".github/workflows/foreign.yml"},
  func(f *fixture){f.ctx.TreeSHA=strings.Repeat("0",40)},
  func(f *fixture){f.ctx.SourceSHA=strings.Repeat("0",40)},
  func(f *fixture){f.ctx.Lane="Yggdrasil"},
  func(f *fixture){f.wake.Intent.MaxComputeUnits=1000001;f.resignIntent()},
  func(f *fixture){f.wake.Intent.Generation=0;f.resignIntent()},
  func(f *fixture){f.wake.Intent.CorrelationSHA256="";f.resignIntent()},
  func(f *fixture){f.wake.Intent.FSAArchiveID="";f.resignIntent()},
  func(f *fixture){f.wake.Intent.SourceWitnessSHA256="";f.resignIntent()},
  func(f *fixture){f.wake.Intent.Mode="FSA_DISPATCH";f.resignIntent()},
  func(f *fixture){f.pin.IntentKeyHex=f.pin.LeaseKeyHex},
  func(f *fixture){f.pin.LeaseKeyHex=f.pin.FSAHeadKeyHex},
  func(f *fixture){f.wake.SignatureHex=strings.Repeat("0",128)},
 }
 for i,alter:=range alters{
  f:=fixtureFor(t,"Wingless");alter(&f)
  if _,_,err:=ObserveWake(f.wake,f.pin,f.ctx);!errors.Is(err,ErrDenied){
   t.Fatalf("alter %d admitted untrusted wake",i)
  }
 }
}
func TestDifferentHostedRunsProduceDisjointClaims(t *testing.T){
 f:=fixtureFor(t,"Wingless")
 second:=f.ctx;second.RunID="38155009102"
 a,_,err:=ObserveWake(f.wake,f.pin,f.ctx);if err!=nil{t.Fatal(err)}
 b,_,err:=ObserveWake(f.wake,f.pin,second);if err!=nil{t.Fatal(err)}
 ah,_:=sha(a);bh,_:=sha(b)
 if ah==bh{t.Fatal("distinct run IDs have identical claim hashes")}
 // A stolen lease for one hosted run cannot authorize the other.
 otherObservation:=f.observation
 otherObservation.RunID=second.RunID
 otherObservation.ClaimSHA256=bh
 if _,err=VerifyLease(b,otherObservation,f.lease,f.leaseSHA,f.pin,f.grantReview);err==nil{
  t.Fatal("lease replay across different real GitHub run IDs")
 }
}
func TestSignedLeaseCannotPromoteUndemonstratedFSAConsumption(t *testing.T){
 alters:=[]func(*fixture){
  func(f *fixture){f.lease.Lease.ConsumedDispatchLease=false;f.resignLease()},
  func(f *fixture){f.lease.Lease.ClaimSHA256=strings.Repeat("0",64);f.resignLease()},
  func(f *fixture){f.lease.Lease.GrantSHA256=strings.Repeat("0",64);f.resignLease()},
  func(f *fixture){f.lease.Lease.RunID="38155009102";f.resignLease()},
  func(f *fixture){f.lease.Lease.Attempt=2;f.resignLease()},
  func(f *fixture){f.lease.Lease.Lane="Yggdrasil";f.resignLease()},
  func(f *fixture){f.lease.Lease.ConsumedDispatchSequence=0;f.resignLease()},
  func(f *fixture){f.lease.Lease.DispatchLockWitnessSHA256="";f.resignLease()},
  func(f *fixture){f.grantReview.FirstUseObserved=false},
  func(f *fixture){f.grantReview.LiveFSAOperational=true},
  func(f *fixture){f.grantReview.ProtectedReplayLockAcquired=true},
  func(f *fixture){f.observation.GitHubOIDCIndependentlyVerified=true},
  func(f *fixture){f.observation.ScientificOriginalStarted=true},
  func(f *fixture){f.pin.LeaseKeyHex=f.pin.IntentKeyHex},
  func(f *fixture){f.lease.SignatureHex=strings.Repeat("0",128)},
 }
 for i,alter:=range alters{
  f:=fixtureFor(t,"Wingless");alter(&f)
  if _,err:=VerifyLease(f.claim,f.observation,f.lease,f.leaseSHA,f.pin,f.grantReview);!errors.Is(err,ErrDenied){
   t.Fatalf("alter %d admitted untrusted lease",i)
  }
 }
}
func TestMalformedExternallySignedInputs(t *testing.T){
 for _,bad:=range [][]byte{nil,[]byte("{"),[]byte("{}{}"),[]byte("[]"),
  []byte(`{"Intent":{"Undocumented":"value"}}`)}{
  if _,err:=ParseIntent(bad);err==nil{t.Fatal("invalid FSA intent parsed")}
  if _,err:=ParseLease(bad);err==nil{t.Fatal("invalid FSA lease parsed")}
 }
 f:=fixtureFor(t,"Wingless")
 b,_:=json.Marshal(f.wake)
 if out,err:=ParseIntent(b);err!=nil||out.SignatureHex!=f.wake.SignatureHex{
  t.Fatal("legitimate prewake envelope parser drift")
 }
 b,_=json.Marshal(f.lease)
 if out,err:=ParseLease(b);err!=nil||out.SignatureHex!=f.lease.SignatureHex{
  t.Fatal("legitimate lease envelope parser drift")
 }
}
