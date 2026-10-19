package fsaadmission

import (
 "crypto/ed25519"
 "crypto/rand"
 "encoding/hex"
 "encoding/json"
 "testing"

 "github.com/spoonman136668-ai/forge/eligibility"
)
func makeSigned(t *testing.T)(SignedSelection,SignedBirth,IndependentPins,eligibility.Frozen){
 t.Helper()
 pub1,priv1,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 pub2,priv2,err:=ed25519.GenerateKey(rand.Reader);if err!=nil{t.Fatal(err)}
 f:=eligibility.Frozen{Schema:eligibility.Schema,Lane:"Wingless",CandidateID:"causal-binding-20261019",
  SourceSHA:"",PreregSHA256:"",CohortSHA256:"",ProtocolSHA256:"",BudgetUnits:200,SeedIDs:[]string{"Wingless:s01"}}
 f.SourceSHA="a"+"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
 f.PreregSHA256="1"+"111111111111111111111111111111111111111111111111111111111111111"
 f.CohortSHA256="2"+"222222222222222222222222222222222222222222222222222222222222222"
 f.ProtocolSHA256="3"+"333333333333333333333333333333333333333333333333333333333333333"
 x:=Selected{Schema:selectedSchema,Frozen:f,HypothesisSHA256:"4"+"444444444444444444444444444444444444444444444444444444444444444",
 FullyTrainedControlSHA256:"5"+"555555555555555555555555555555555555555555555555555555555555555",
 EqualTrainingProofSHA256:"6"+"666666666666666666666666666666666666666666666666666666666666666",
 MaxNativeCPUms:60000,MaxNativePeakRSSBytes:1073741824,MaxWallSeconds:120,
 FrozenSequence:10}
 y:=SourceBirth{Schema:bornSchema,Lane:f.Lane,CandidateID:f.CandidateID,
 SourceSHA:f.SourceSHA,CohortSHA256:f.CohortSHA256,
 IndependentFamilySHA256:[2]string{"7"+"777777777777777777777777777777777777777777777777777777777777777",
 "8"+"888888888888888888888888888888888888888888888888888888888888888"},
 BirthSequence:11,NeverPreviouslyConsumed:true}
 sx,_:=json.Marshal(x);sy,_:=json.Marshal(y)
 return SignedSelection{x,hex.EncodeToString(ed25519.Sign(priv1,append([]byte(selectedDomain),sx...)))},
 SignedBirth{y,hex.EncodeToString(ed25519.Sign(priv2,append([]byte(bornDomain),sy...)))},
 IndependentPins{pub1,pub2},f
}
func TestSignedScienceStillCannotDispatch(t *testing.T){
 s,b,p,f:=makeSigned(t)
 value,err:=VerifySelected(s,b,p,f)
 if err!=nil{t.Fatal(err)}
 if value!=SelectedPreflightOnly||value=="AUTHORIZED_TO_DISPATCH"{t.Fatal("scientific authority minted")}
}
func TestAuthenticSourceAndFirstUseMustAgree(t *testing.T){
 fresh:=func() (SignedSelection,SignedBirth,IndependentPins,eligibility.Frozen){return makeSigned(t)}
 tests:=[]struct{name string;mutate func(*SignedSelection,*SignedBirth,*IndependentPins,*eligibility.Frozen)}{
 {"changed hypothesis",func(s *SignedSelection,_ *SignedBirth,_ *IndependentPins,_ *eligibility.Frozen){s.Selection.HypothesisSHA256="9"+s.Selection.HypothesisSHA256[1:]}},
 {"changed trained control",func(s *SignedSelection,_ *SignedBirth,_ *IndependentPins,_ *eligibility.Frozen){s.Selection.FullyTrainedControlSHA256="9"+s.Selection.FullyTrainedControlSHA256[1:]}},
 {"unequal training missing",func(s *SignedSelection,_ *SignedBirth,_ *IndependentPins,_ *eligibility.Frozen){s.Selection.EqualTrainingProofSHA256=""}},
 {"unbounded CPU",func(s *SignedSelection,_ *SignedBirth,_ *IndependentPins,_ *eligibility.Frozen){s.Selection.MaxNativeCPUms=0}},
 {"unbounded peak RSS",func(s *SignedSelection,_ *SignedBirth,_ *IndependentPins,_ *eligibility.Frozen){s.Selection.MaxNativePeakRSSBytes=0}},
 {"missing wall cap",func(s *SignedSelection,_ *SignedBirth,_ *IndependentPins,_ *eligibility.Frozen){s.Selection.MaxWallSeconds=0}},
 {"different source",func(_ *SignedSelection,b *SignedBirth,_ *IndependentPins,_ *eligibility.Frozen){b.Birth.SourceSHA="b"+b.Birth.SourceSHA[1:]}},
 {"family collision",func(_ *SignedSelection,b *SignedBirth,_ *IndependentPins,_ *eligibility.Frozen){b.Birth.IndependentFamilySHA256[0]=b.Birth.IndependentFamilySHA256[1]}},
 {"born before freeze",func(s *SignedSelection,b *SignedBirth,_ *IndependentPins,_ *eligibility.Frozen){b.Birth.BirthSequence=s.Selection.FrozenSequence}},
 {"already consumed",func(_ *SignedSelection,b *SignedBirth,_ *IndependentPins,_ *eligibility.Frozen){b.Birth.NeverPreviouslyConsumed=false}},
 {"same attestor cannot self-certify",func(_ *SignedSelection,_ *SignedBirth,p *IndependentPins,_ *eligibility.Frozen){p.SourceBirthSigner=p.FrozenSigner}},
 {"missing independent key",func(_ *SignedSelection,_ *SignedBirth,p *IndependentPins,_ *eligibility.Frozen){p.SourceBirthSigner=nil}},
 {"altered external frozen identity",func(_ *SignedSelection,_ *SignedBirth,_ *IndependentPins,f *eligibility.Frozen){f.CandidateID="different"}},
 }
 for _,v:=range tests{
  t.Run(v.name,func(t *testing.T){s,b,p,f:=fresh();v.mutate(&s,&b,&p,&f);if _,err:=VerifySelected(s,b,p,f);err==nil{t.Fatal("unsigned, stale, or unbounded admission passed")}})
 }
}
