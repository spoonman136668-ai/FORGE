package fsaadmission

import(
 "crypto/ed25519"
 "crypto/rand"
 "encoding/hex"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/eligibility"
 "github.com/spoonman136668-ai/forge/fsahead"
)
func h(c string)string{return strings.Repeat(c,64)}
func fixture(t *testing.T)(SignedSelection,SignedBirth,SignedFamilySnapshot,IndependentPins,eligibility.Frozen,fsahead.Anchor){
 t.Helper()
 p1,k1,e:=ed25519.GenerateKey(rand.Reader);if e!=nil{t.Fatal(e)}
 p2,k2,e:=ed25519.GenerateKey(rand.Reader);if e!=nil{t.Fatal(e)}
 p3,k3,e:=ed25519.GenerateKey(rand.Reader);if e!=nil{t.Fatal(e)}
 a:=fsahead.Anchor{ArchiveID:h("9"),AuthorityEpoch:7,Sequence:20,HeadSHA256:h("a")}
 frozen:=eligibility.Frozen{Schema:eligibility.Schema,Lane:"Wingless",CandidateID:"causal-binding-20261019",
 SourceSHA:strings.Repeat("b",40),PreregSHA256:h("1"),CohortSHA256:h("2"),
 ProtocolSHA256:h("3"),BudgetUnits:200,SeedIDs:[]string{"Wingless:s01"}}
 x:=Selected{Schema:selectedSchema,Frozen:frozen,HypothesisSHA256:h("4"),
 FullyTrainedControlSHA256:h("5"),EqualTrainingProofSHA256:h("6"),
 MaxNativeCPUms:60000,MaxNativePeakRSSBytes:1073741824,MaxWallSeconds:120,
 CustodyEpoch:7,FrozenSequence:10}
 sx,selectionHash,_:=signedDigest(selectedDomain,x)
 y:=SourceBirth{Schema:bornSchema,Lane:frozen.Lane,CandidateID:frozen.CandidateID,
 SourceSHA:frozen.SourceSHA,CohortSHA256:frozen.CohortSHA256,
 IndependentFamilySHA256:[2]string{h("7"),h("8")},CustodyEpoch:7,
 FrozenSelectionSHA256:selectionHash,BirthSequence:11,NeverPreviouslyConsumed:true}
 sy,birthHash,_:=signedDigest(bornDomain,y)
 z:=FamilySnapshot{Schema:familySchema,ArchiveID:a.ArchiveID,CustodyEpoch:7,
 Sequence:20,HeadSHA256:a.HeadSHA256,LedgerGeneration:3,LedgerSnapshotSHA256:h("d"),CompleteAllLanes:true,
 FrozenSelectionSHA256:selectionHash,SourceBirthSHA256:birthHash,
 FrozenSequence:10,BirthSequence:11,
 ActiveFamilySHA256:[]string{},ConsumedFamilySHA256:[]string{}}
 sz,_,_:=signedDigest(familyDomain,z)
 return SignedSelection{x,hex.EncodeToString(ed25519.Sign(k1,sx))},
 SignedBirth{y,hex.EncodeToString(ed25519.Sign(k2,sy))},
 SignedFamilySnapshot{z,hex.EncodeToString(ed25519.Sign(k3,sz))},
 IndependentPins{p1,p2,p3},frozen,a
}
func TestThreeIndependentPinnedWitnessesRemainPreflightOnly(t *testing.T){
 s,b,l,p,e,a:=fixture(t)
 verdict,err:=verifySelected(s,b,l,p,e,a,3,h("d"))
 if err!=nil{t.Fatal(err)}
 if verdict!=SelectedPreflightOnly{t.Fatalf("unexpected science authority: %q",verdict)}
}
func TestChronologyAndFamilyLedgerFailClosed(t *testing.T){
 tests:=[]struct{name string;alter func(*SignedSelection,*SignedBirth,*SignedFamilySnapshot,*IndependentPins,*eligibility.Frozen,*fsahead.Anchor,*uint64)}{
 {"tamper hypothesis",func(s *SignedSelection,_ *SignedBirth,_ *SignedFamilySnapshot,_ *IndependentPins,_ *eligibility.Frozen,_ *fsahead.Anchor,_ *uint64){s.Selection.HypothesisSHA256=h("f")}},
 {"strongest control change",func(s *SignedSelection,_ *SignedBirth,_ *SignedFamilySnapshot,_ *IndependentPins,_ *eligibility.Frozen,_ *fsahead.Anchor,_ *uint64){s.Selection.FullyTrainedControlSHA256=h("f")}},
 {"missing equal training proof",func(s *SignedSelection,_ *SignedBirth,_ *SignedFamilySnapshot,_ *IndependentPins,_ *eligibility.Frozen,_ *fsahead.Anchor,_ *uint64){s.Selection.EqualTrainingProofSHA256=""}},
 {"zero CPU",func(s *SignedSelection,_ *SignedBirth,_ *SignedFamilySnapshot,_ *IndependentPins,_ *eligibility.Frozen,_ *fsahead.Anchor,_ *uint64){s.Selection.MaxNativeCPUms=0}},
 {"zero RSS",func(s *SignedSelection,_ *SignedBirth,_ *SignedFamilySnapshot,_ *IndependentPins,_ *eligibility.Frozen,_ *fsahead.Anchor,_ *uint64){s.Selection.MaxNativePeakRSSBytes=0}},
 {"zero wall",func(s *SignedSelection,_ *SignedBirth,_ *SignedFamilySnapshot,_ *IndependentPins,_ *eligibility.Frozen,_ *fsahead.Anchor,_ *uint64){s.Selection.MaxWallSeconds=0}},
 {"unbound birth replay",func(_ *SignedSelection,b *SignedBirth,_ *SignedFamilySnapshot,_ *IndependentPins,_ *eligibility.Frozen,_ *fsahead.Anchor,_ *uint64){b.Birth.FrozenSelectionSHA256=h("f")}},
 {"source collision",func(_ *SignedSelection,b *SignedBirth,_ *SignedFamilySnapshot,_ *IndependentPins,_ *eligibility.Frozen,_ *fsahead.Anchor,_ *uint64){b.Birth.IndependentFamilySHA256[0]=b.Birth.IndependentFamilySHA256[1]}},
 {"preselection source",func(_ *SignedSelection,b *SignedBirth,_ *SignedFamilySnapshot,_ *IndependentPins,_ *eligibility.Frozen,_ *fsahead.Anchor,_ *uint64){b.Birth.BirthSequence=10}},
 {"stale family-ledger head",func(_ *SignedSelection,_ *SignedBirth,f *SignedFamilySnapshot,_ *IndependentPins,_ *eligibility.Frozen,_ *fsahead.Anchor,_ *uint64){f.Snapshot.HeadSHA256=h("f")}},
 {"separate counter epoch",func(_ *SignedSelection,b *SignedBirth,_ *SignedFamilySnapshot,_ *IndependentPins,_ *eligibility.Frozen,_ *fsahead.Anchor,_ *uint64){b.Birth.CustodyEpoch=8}},
 {"replayed journal highwater",func(_ *SignedSelection,_ *SignedBirth,_ *SignedFamilySnapshot,_ *IndependentPins,_ *eligibility.Frozen,a *fsahead.Anchor,_ *uint64){a.Sequence=21}},
 {"consumed family",func(_ *SignedSelection,_ *SignedBirth,f *SignedFamilySnapshot,_ *IndependentPins,_ *eligibility.Frozen,_ *fsahead.Anchor,_ *uint64){f.Snapshot.ConsumedFamilySHA256=[]string{h("7")}}},
 {"active family",func(_ *SignedSelection,_ *SignedBirth,f *SignedFamilySnapshot,_ *IndependentPins,_ *eligibility.Frozen,_ *fsahead.Anchor,_ *uint64){f.Snapshot.ActiveFamilySHA256=[]string{h("8")}}},
 {"partial all lanes",func(_ *SignedSelection,_ *SignedBirth,f *SignedFamilySnapshot,_ *IndependentPins,_ *eligibility.Frozen,_ *fsahead.Anchor,_ *uint64){f.Snapshot.CompleteAllLanes=false}},
 {"stale complete ledger generation",func(_ *SignedSelection,_ *SignedBirth,_ *SignedFamilySnapshot,_ *IndependentPins,_ *eligibility.Frozen,_ *fsahead.Anchor,g *uint64){*g=4}},
 {"missing third pinned key",func(_ *SignedSelection,_ *SignedBirth,_ *SignedFamilySnapshot,p *IndependentPins,_ *eligibility.Frozen,_ *fsahead.Anchor,_ *uint64){p.FamilyLedgerSigner=nil}},
 {"identical witness keys",func(_ *SignedSelection,_ *SignedBirth,_ *SignedFamilySnapshot,p *IndependentPins,_ *eligibility.Frozen,_ *fsahead.Anchor,_ *uint64){p.FamilyLedgerSigner=p.SourceBirthSigner}},
 {"altered expected frozen",func(_ *SignedSelection,_ *SignedBirth,_ *SignedFamilySnapshot,_ *IndependentPins,e *eligibility.Frozen,_ *fsahead.Anchor,_ *uint64){e.CandidateID="stale-source"}},
 }
 for _,v:=range tests{
  t.Run(v.name,func(t *testing.T){s,b,f,p,e,a:=fixture(t);g:=uint64(3)
   v.alter(&s,&b,&f,&p,&e,&a,&g)
   if _,err:=verifySelected(s,b,f,p,e,a,g,h("d"));err==nil{t.Fatal("untrusted or stale source accepted")}
  })
 }
}

\n// A valid third-party signature over a DIFFERENT all-lane ledger must still
// fail: an authenticated family inventory is not proof of the exact global
// cohort ledger independently recovered by FSA.
func TestSignedFamilySnapshotMustMatchIndependentGlobalLedgerPin(t *testing.T){
 s,b,f,p,e,a:=fixture(t)
 pub,priv,err:=ed25519.GenerateKey(rand.Reader)
 if err!=nil{t.Fatal(err)}
 p.FamilyLedgerSigner=pub
 resign:=func(){
  t.Helper()
  bytes,_,err:=signedDigest(familyDomain,f.Snapshot)
  if err!=nil{t.Fatal(err)}
  f.SignatureHex=hex.EncodeToString(ed25519.Sign(priv,bytes))
 }
 f.Snapshot.LedgerSnapshotSHA256=h("e")
 resign()
 if _,err:=verifySelected(s,b,f,p,e,a,3,h("d"));err==nil{
  t.Fatal("independently signed inventory from a different cohort ledger accepted")
 }
 f.Snapshot.LedgerSnapshotSHA256=h("d")
 resign()
 result,err:=verifySelected(s,b,f,p,e,a,3,h("d"))
 if err!=nil||result!=SelectedPreflightOnly{
  t.Fatalf("matching separately signed ledger preflight rejected: %q %v",result,err)
 }
 if _,err:=verifySelected(s,b,f,p,e,a,3,h("e"));err==nil{
  t.Fatal("caller-repinned ledger without same family attestation accepted")
 }
 if _,err:=verifySelected(s,b,f,p,e,a,3,"");err==nil{
  t.Fatal("missing independent ledger pin accepted")
 }
}

func TestLegacyFamilySignatureCannotDowngradeLedgerBinding(t *testing.T){
 s,b,f,p,e,a:=fixture(t)
 pub,priv,err:=ed25519.GenerateKey(rand.Reader)
 if err!=nil{t.Fatal(err)}
 p.FamilyLedgerSigner=pub
 f.Snapshot.Schema="forge.science.complete-family-ledger.v1"
 message,_,err:=signedDigest("FORGE-SCIENCE-FAMILY-LEDGER-V1\\n",f.Snapshot)
 if err!=nil{t.Fatal(err)}
 f.SignatureHex=hex.EncodeToString(ed25519.Sign(priv,message))
 if _,err:=verifySelected(s,b,f,p,e,a,3,h("d"));err==nil{
  t.Fatal("old family schema accepted after cryptographic contract change")
 }
}
