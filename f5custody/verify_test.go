package f5custody

import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/eligibility"
)

func fixtures()(Signed,Pins,eligibility.Frozen,ed25519.PrivateKey){
 seed:=sha256.Sum256([]byte("FORGE F5 synthetic unit-only private key never for live custody"))
 priv:=ed25519.NewKeyFromSeed(seed[:])
 pub:=priv.Public().(ed25519.PublicKey)
 frozen:=eligibility.Frozen{
  Schema:eligibility.Schema,Lane:"Yggdrasil",CandidateID:"Y-FORGE-F5-TEST-ONLY",
  SourceSHA:strings.Repeat("a",40),PreregSHA256:strings.Repeat("b",64),
  CohortSHA256:strings.Repeat("c",64),ProtocolSHA256:strings.Repeat("d",64),
  BudgetUnits:10,SeedIDs:[]string{"Yggdrasil:70000","Yggdrasil:70001"},
 }
 a:=Attestation{
  Schema:Schema,Scope:"ALL_LANES",
  Coverage:"GENESIS_TO_HIGH_WATER_INCLUDING_UNCERTAIN",Revision:11,
  Ledger:eligibility.LedgerSnapshot{
   Schema:"forge.eligibility.ledger-snapshot.v1",Scope:"ALL_LANES",
   Generation:9,ConsumedCohorts:[]string{},ActiveCohorts:[]string{},
   Starts:[]eligibility.StartRecord{},
  },
  ConsumedSeedIDs:[]string{"Wingless:100","Yggdrasil:67204"},
  ActiveSeedIDs:[]string{"Wingless:200"},
  UncertainSeedIDs:[]string{"Yggdrasil:67240"},
  LaneHighWater:map[string]uint64{"Wingless":4,"Yggdrasil":8},
 }
 digest,_:=eligibility.LedgerFingerprint(a.Ledger)
 pins:=Pins{
  CustodianPublicKeyHex:hex.EncodeToString(pub),MinRevision:11,
  ExpectedLedgerGeneration:9,LedgerSHA256:digest,
  WinglessMinHighWater:4,YggdrasilMinHighWater:8,
 }
 s:=Signed{Attestation:a}
 sign(&s,priv)
 return s,pins,frozen,priv
}
func sign(s *Signed,priv ed25519.PrivateKey){
 raw,_:=json.Marshal(s.Attestation)
 msg:=append([]byte("FORGE-F5-ALL-LANE-SEED-CUSTODY-V1\n"),raw...)
 s.SignatureHex=hex.EncodeToString(ed25519.Sign(priv,msg))
}
func expectBlocked(t *testing.T,s Signed,p Pins,f eligibility.Frozen){
 t.Helper()
 r,e:=Inspect(s,p,f)
 if !errors.Is(e,ErrBlocked){t.Fatalf("expected fail-closed: %+v %v",r,e)}
 if r.OriginalStartAuthorized||r.FirstUseClaims!=0||r.SourceFrozen{
  t.Fatalf("unsafe authority: %+v",r)
 }
}
func TestSyntheticSignedLedgerAuditsOnlyNeverDispatches(t *testing.T){
 s,p,f,_:=fixtures()
 got,err:=Inspect(s,p,f)
 if err!=nil{t.Fatal(err)}
 if got.Disposition!="AUDIT_ONLY_SOURCE_AND_ORIGINAL_AUTHORITY_STILL_BLOCKED"||
  !got.AuthenticatedSnapshot||!got.CompleteAllLaneSeedIndex||
  !got.IndividualCandidateSeedsAbsentFromUse||
  got.SourceFrozen||got.OriginalStartAuthorized||got.FirstUseClaims!=0{
  t.Fatalf("unsafe report %+v",got)
 }
}
func TestMissingAuthorityPinsReject(t *testing.T){
 s,p,f,_:=fixtures()
 p.CustodianPublicKeyHex=""
 expectBlocked(t,s,p,f)
 s,p,f,_=fixtures();p.MinRevision=0
 expectBlocked(t,s,p,f)
 s,p,f,_=fixtures();p.LedgerSHA256=""
 expectBlocked(t,s,p,f)
}
func TestIndependentlyPinnedLaneHighWaterCannotBeDowngraded(t *testing.T){
 s,p,f,_:=fixtures()
 p.WinglessMinHighWater=0
 expectBlocked(t,s,p,f)
 s,p,f,_=fixtures()
 p.YggdrasilMinHighWater=0
 expectBlocked(t,s,p,f)
 s,p,f,_=fixtures()
 p.WinglessMinHighWater=5
 expectBlocked(t,s,p,f)
 s,p,f,_=fixtures()
 p.YggdrasilMinHighWater=9
 expectBlocked(t,s,p,f)
 // A properly signed but stale report is still insufficient, even
 // when its Ed25519 signature is genuinely valid.
 s,p,f,priv:=fixtures()
 s.Attestation.LaneHighWater["Wingless"]=3
 sign(&s,priv)
 expectBlocked(t,s,p,f)
 s,p,f,priv=fixtures()
 s.Attestation.LaneHighWater["Yggdrasil"]=7
 sign(&s,priv)
 expectBlocked(t,s,p,f)
}

func TestForgedSignatureAndChangedContentReject(t *testing.T){
 s,p,f,_:=fixtures()
 s.Attestation.Revision=12
 expectBlocked(t,s,p,f)
 s,p,f,_=fixtures()
 s.SignatureHex=strings.Repeat("0",128)
 expectBlocked(t,s,p,f)
 s,p,f,_=fixtures()
 p.CustodianPublicKeyHex=strings.Repeat("b",64)
 expectBlocked(t,s,p,f)
}
func TestStaleAndIncompleteAllLaneRecordsReject(t *testing.T){
 s,p,f,priv:=fixtures()
 p.MinRevision=12
 expectBlocked(t,s,p,f)
 s,p,f,priv=fixtures()
 s.Attestation.Coverage="PARTIAL";sign(&s,priv)
 expectBlocked(t,s,p,f)
 s,p,f,priv=fixtures()
 delete(s.Attestation.LaneHighWater,"Wingless");sign(&s,priv)
 expectBlocked(t,s,p,f)
 s,p,f,priv=fixtures()
 s.Attestation.Ledger.Generation=10;sign(&s,priv)
 expectBlocked(t,s,p,f)
}
func TestConsumedActiveAndUncertainSeedCollisionReject(t *testing.T){
 for _,where:=range []string{"consumed","active","uncertain"}{
  t.Run(where,func(t *testing.T){
   s,p,f,priv:=fixtures()
   switch where {
   case "consumed":s.Attestation.ConsumedSeedIDs=append(s.Attestation.ConsumedSeedIDs,"Yggdrasil:70000")
   case "active":s.Attestation.ActiveSeedIDs=append(s.Attestation.ActiveSeedIDs,"Yggdrasil:70000")
   case "uncertain":s.Attestation.UncertainSeedIDs=append(s.Attestation.UncertainSeedIDs,"Yggdrasil:70000")
   }
   sign(&s,priv)
   expectBlocked(t,s,p,f)
  })
 }
}
func TestPriorOriginalAndCohortCollisionsReject(t *testing.T){
 s,p,f,priv:=fixtures()
 s.Attestation.Ledger.ConsumedCohorts=[]string{f.CohortSHA256}
 hash,_:=eligibility.LedgerFingerprint(s.Attestation.Ledger)
 p.LedgerSHA256=hash
 sign(&s,priv);expectBlocked(t,s,p,f)
 s,p,f,priv=fixtures()
 finger,err:=eligibility.Fingerprint(f);if err!=nil{t.Fatal(err)}
 s.Attestation.Ledger.Starts=[]eligibility.StartRecord{{FrozenSHA256:finger,State:"INDETERMINATE"}}
 hash,_=eligibility.LedgerFingerprint(s.Attestation.Ledger)
 p.LedgerSHA256=hash
 sign(&s,priv);expectBlocked(t,s,p,f)
}
func TestAmbiguousOrIncompleteSeedIndexReject(t *testing.T){
 s,p,f,priv:=fixtures()
 s.Attestation.UncertainSeedIDs=[]string{}
 s.Attestation.ActiveSeedIDs=nil
 sign(&s,priv)
 expectBlocked(t,s,p,f)
 s,p,f,priv=fixtures()
 s.Attestation.ActiveSeedIDs=[]string{"Wingless:100"}
 sign(&s,priv)
 expectBlocked(t,s,p,f)
}
func TestInvalidCandidateIdentityAndMissingSeedCannotPass(t *testing.T){
 scenarios:=[]struct{
  name string
  mutate func(*eligibility.Frozen)
 }{
  {"empty seeds",func(c *eligibility.Frozen){c.SeedIDs=nil}},
  {"duplicate seed",func(c *eligibility.Frozen){c.SeedIDs=[]string{"Yggdrasil:70000","Yggdrasil:70000"}}},
  {"another lane",func(c *eligibility.Frozen){c.Lane="Wingless"}},
  {"other project",func(c *eligibility.Frozen){c.CandidateID="Y-FORGE-F4-TEST-ONLY"}},
  {"unqualified source",func(c *eligibility.Frozen){c.SourceSHA="unknown"}},
  {"nondecimal seed",func(c *eligibility.Frozen){c.SeedIDs=[]string{"Yggdrasil:unknown"}}},
  {"zero budget",func(c *eligibility.Frozen){c.BudgetUnits=0}},
 }
 for _,tc:=range scenarios {
  t.Run(tc.name,func(t *testing.T){
   s,p,f,_:=fixtures()
   tc.mutate(&f)
   expectBlocked(t,s,p,f)
  })
 }
}

func TestDigestIsNotAuthentication(t *testing.T){
 s,p,f,priv:=fixtures()
 s.Attestation.ConsumedSeedIDs=append(s.Attestation.ConsumedSeedIDs,"Yggdrasil:70000")
 sum,_:=Digest(s.Attestation.Ledger)
 p.LedgerSHA256=sum
 // Inventing the correct ledger hash locally cannot replace the
 // independent custodian signature and must not clear first-use.
 expectBlocked(t,s,p,f)
 sign(&s,priv)
 expectBlocked(t,s,p,f)
}
