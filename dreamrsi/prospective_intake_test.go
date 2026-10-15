package dreamrsi

import(
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "reflect"
 "testing"
)

func r25Fixture(t *testing.T)([]byte,[]byte){
 t.Helper()
 pair:=[2]ProspectiveLaneInput{
  r24Lane(t,"Wingless",61,62),
  r24Lane(t,"Yggdrasil",71,72),
 }
 b:=ProspectiveOwnerBundle{Schema:OwnerBundleSchema}
 p:=ProspectiveIndependentPins{Schema:IndependentPinsSchema}
 for i,e:=range pair{
  b.Lanes[i]=OwnerLaneEvidence{
   Lane:e.Lane,Optimizer:e.Optimizer,Train:e.Train,
   Validation:e.Validation,Heldout:e.Heldout,
   FrozenHoldout:e.FrozenHoldout,SignedAudit:e.SignedAudit,
  }
  p.Lanes[i]=IndependentLanePins{
   Lane:e.Lane,FrozenOptimizerHeadSHA256:e.Optimizer.LineageHeadSHA256,
   Train:e.TrainPin,Validation:e.ValidationPin,Heldout:e.HeldoutPin,
   HoldoutSpecSHA256:e.IndependentlyPinnedHoldoutSpecSHA256,
   Audit:e.AuditPins,
  }
 }
 raw,err:=json.Marshal(b)
 if err!=nil{t.Fatal(err)}
 sha:=sha256.Sum256(raw)
 p.OwnerBundleSHA256=hex.EncodeToString(sha[:])
 pins,err:=json.Marshal(p)
 if err!=nil{t.Fatal(err)}
 return raw,pins
}
func TestR25ExactOwnerInputPositiveIsStillNonAuthorizing(t *testing.T){
 owner,pins:=r25Fixture(t)
 a,err:=ReviewOwnerEvidence(owner,pins)
 if err!=nil{t.Fatal(err)}
 b,err:=ReviewOwnerEvidence(owner,pins)
 if err!=nil||!reflect.DeepEqual(a,b){t.Fatal("non-deterministic genuine input interface:",err)}
 if len(a.Lanes)!=2||a.Lanes[0].Lane!="Wingless"||a.Lanes[1].Lane!="Yggdrasil"||
  a.ScientificImprovementEstablished||a.ScientificAccepted||a.OptimizerDispatchAuthorized||
  a.NewOriginalsExecuted!=0||a.IndependentRandomizationOperationallyProven||
  a.IndependentFirstUseAndSourceBirthProven{
   t.Fatal("source-only intake fabricated scientific authority")
 }
 for _,lane:=range a.Lanes{
  if lane.AuditedAssignments!=75||len(lane.Comparison.Baselines)!=4||
   lane.FirstUseCustodyVerified||lane.ActualRandomizationIndependentlyDemonstrated{
   t.Fatal("incomplete signed audit or baseline was promoted")
  }
 }
}
func TestR25ExternalEvidenceAndTrustDriftDenials(t *testing.T){
 mutate:=func(owner,pins []byte,fn func(*ProspectiveOwnerBundle,*ProspectiveIndependentPins))([]byte,[]byte){
  t.Helper()
  var e ProspectiveOwnerBundle
  var p ProspectiveIndependentPins
  if json.Unmarshal(owner,&e)!=nil||json.Unmarshal(pins,&p)!=nil{t.Fatal("invalid fixture")}
  fn(&e,&p)
  ob,_:=json.Marshal(e)
  sum:=sha256.Sum256(ob)
  p.OwnerBundleSHA256=hex.EncodeToString(sum[:])
  pb,_:=json.Marshal(p)
  return ob,pb
 }
 cases:=[]struct{name string;change func(*ProspectiveOwnerBundle,*ProspectiveIndependentPins)}{
  {"missing future audit",func(x *ProspectiveOwnerBundle,p *ProspectiveIndependentPins){x.Lanes[0].SignedAudit.SignatureHex=""}},
  {"changed future outcome",func(x *ProspectiveOwnerBundle,p *ProspectiveIndependentPins){x.Lanes[1].Heldout.History.Decisions[0].Outcome="SUPPORTED"}},
  {"source epoch drift",func(x *ProspectiveOwnerBundle,p *ProspectiveIndependentPins){x.Lanes[1].Heldout.History.Epoch++}},
  {"wrong optimizer head",func(x *ProspectiveOwnerBundle,p *ProspectiveIndependentPins){p.Lanes[0].FrozenOptimizerHeadSHA256=hash([]byte("revised-after-heldout"))}},
  {"cross-lane signer reused",func(x *ProspectiveOwnerBundle,p *ProspectiveIndependentPins){p.Lanes[1].Audit.IndependentAuditorKeyHex=p.Lanes[0].Audit.IndependentAuditorKeyHex}},
  {"swapped lane",func(x *ProspectiveOwnerBundle,p *ProspectiveIndependentPins){x.Lanes[0].Lane="Yggdrasil"}},
  {"fake optimizer outcome",func(x *ProspectiveOwnerBundle,p *ProspectiveIndependentPins){x.Lanes[0].Optimizer.ScientificAccepted=true}},
  {"missing historic independent pin",func(x *ProspectiveOwnerBundle,p *ProspectiveIndependentPins){p.Lanes[0].Train.IndependentEd25519PublicKeyHex=""}},
  {"mismatched heldout pin",func(x *ProspectiveOwnerBundle,p *ProspectiveIndependentPins){p.Lanes[0].Heldout.ExpectedHistorySHA256=hash([]byte("different history"))}},
  {"same train and heldout pin",func(x *ProspectiveOwnerBundle,p *ProspectiveIndependentPins){p.Lanes[1].Heldout.ExpectedHistorySHA256=p.Lanes[1].Train.ExpectedHistorySHA256}},
 }
 originalOwner,originalPins:=r25Fixture(t)
 for _,test:=range cases{t.Run(test.name,func(t *testing.T){
  owner,pins:=mutate(originalOwner,originalPins,test.change)
  got,err:=ReviewOwnerEvidence(owner,pins)
  if err==nil||!reflect.DeepEqual(got,ProspectivePairReview{}){
   t.Fatalf("unauthenticated record admitted: %v / %+v",err,got)
  }
 })}
}
func TestR25CanonicalAndMissingOwnerDenials(t *testing.T){
 owner,pins:=r25Fixture(t)
 corrupt:=[][]byte{
  nil,{},append(append([]byte(nil),owner...),[]byte("{}")...),
  bytes.Replace(owner,[]byte(`"schema":`),[]byte(`"schema":"X","schema":`),1),
  append([]byte(" "),owner...),
 }
 for i,b:=range corrupt {
  if got,err:=ReviewOwnerEvidence(b,pins);err==nil||!reflect.DeepEqual(got,ProspectivePairReview{}){
   t.Fatalf("bad owner bytes %d were accepted",i)
  }
 }
 if got,err:=ReviewOwnerEvidence(owner,nil);err==nil||!reflect.DeepEqual(got,ProspectivePairReview{}){
  t.Fatal("missing independently held pins were accepted")
 }
 altered:=append([]byte(nil),pins...)
 altered[len(altered)-2]='0'
 if got,err:=ReviewOwnerEvidence(owner,altered);err==nil||!reflect.DeepEqual(got,ProspectivePairReview{}){
  t.Fatal("changed independent pin input was accepted")
 }
}
