package originalinventory

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "strings"
 "testing"
)
func digest(b []byte)string{sum:=sha256.Sum256(b);return hex.EncodeToString(sum[:])}
func syntheticEvidence()(Manifest,[]byte,[]byte){
 w:=[]byte("{\"classification\":\"NATIVE_VERIFIER_BOUNDARY\",\"model_calls\":0,\"claim_limit\":\"mock only\"}\n")
 y:=[]byte("{\"classification\":\"NO_BENEFIT\",\"model_calls\":0,\"heldout\":{\"1\":{\"gain\":0}}}\n")
 return Manifest{Schema:Schema,Pins:[]Pin{
  {Lane:"Wingless",Repo:"spoonman136668-ai/Wingless",RunID:38381594390,
   CommitSHA:strings.Repeat("a",40),ArtifactID:11803299743,
   ArtifactName:"W-R39-original-native-verifier",FileName:"W-R39-original.json",
   RawSHA256:digest(w),ExpectedReportedClassification:"NATIVE_VERIFIER_BOUNDARY"},
  {Lane:"Yggdrasil",Repo:"spoonman136668-ai/Yggdrasil",RunID:38381070805,
   CommitSHA:strings.Repeat("b",40),ArtifactID:11802529893,
   ArtifactName:"Y056-original-native-perception-ablation",FileName:"Y056-original.json",
   RawSHA256:digest(y),ExpectedReportedClassification:"NO_BENEFIT"},
 }},w,y
}
func encode(t *testing.T,m Manifest)[]byte{
 t.Helper();b,err:=json.Marshal(m);if err!=nil{t.Fatal(err)}
 return append(b,'\n')
}
func TestRealFormatSourceBoundTwoLaneClaimsAndNegativePreservation(t *testing.T){
 m,w,y:=syntheticEvidence()
 report,err:=Build(encode(t,m),w,y)
 if err!=nil{t.Fatal(err)}
 if report.Schema!=ResultSchema||report.Wingless.Lane!="Wingless"||
  report.Yggdrasil.Lane!="Yggdrasil"||
  report.Wingless.ReportedClassification!="NATIVE_VERIFIER_BOUNDARY"||
  report.Yggdrasil.ReportedClassification!="NO_BENEFIT"||
  report.Yggdrasil.Preservation!="REPORTED_NEGATIVE_PRESERVED_UNQUALIFIED"||
  report.Wingless.ScientificAccepted||report.Yggdrasil.ScientificAccepted||
  report.Yggdrasil.OriginalFirstUseReconciled||
  report.Yggdrasil.PreregistrationVerified||
  report.Yggdrasil.SourceBirthVerified||report.Yggdrasil.IndependentQualificationVerified||
  report.OriginalScientificExecutionsAuthorized||report.AcceptedRefMutation||
  report.CKBOriginalCustodyReconciled||
  report.Wingless.ModelCallsReported==nil||*report.Wingless.ModelCallsReported!=0{
  t.Fatalf("reported negative/original custody escaped qualification: %+v",report)
 }
 again,err:=Build(encode(t,m),w,y)
 if err!=nil||again.ManifestSHA256!=report.ManifestSHA256{
  t.Fatal("content-addressed original inventory nondeterminism",err)
 }
}
func TestOriginalArtifactsRejectChangedClassificationAndCrossLaneSwap(t *testing.T){
 m,w,y:=syntheticEvidence();pins:=encode(t,m)
 mutated:=[]byte(strings.Replace(string(y),"NO_BENEFIT","SUPPORTED",1))
 if _,err:=Build(pins,w,mutated);!errors.Is(err,ErrBlocked){
  t.Fatal("negative scientific finding overwritten",err)
 }
 if _,err:=Build(pins,y,w);!errors.Is(err,ErrBlocked){
  t.Fatal("Wingless/Yggdrasil artifact substitution",err)
 }
 repeated:=[]byte("{\"classification\":\"NO_BENEFIT\",\"classification\":\"SUPPORTED\"}\n")
 altered:=m
 altered.Pins=append([]Pin(nil),m.Pins...)
 altered.Pins[1].RawSHA256=digest(repeated)
 if _,err:=Build(encode(t,altered),w,repeated);!errors.Is(err,ErrBlocked){
  t.Fatal("duplicate JSON classification bypassed canonical original",err)
 }
}
func TestOriginalManifestRejectsUnverifiedProvenanceOrHiddenScope(t *testing.T){
 mods:=[]struct{name string;change func(*Manifest)}{
  {"foreign source",func(m *Manifest){m.Pins[0].Repo="CKB-plane"}},
  {"invalid git commit",func(m *Manifest){m.Pins[0].CommitSHA="head"}},
  {"missing artifact identity",func(m *Manifest){m.Pins[0].ArtifactID=0}},
  {"old negative redescription",func(m *Manifest){m.Pins[1].ExpectedReportedClassification="SUPPORTED"}},
  {"symlink-style filename",func(m *Manifest){m.Pins[1].FileName="../Y056-original.json"}},
  {"duplicate artifact",func(m *Manifest){m.Pins[1].ArtifactID=m.Pins[0].ArtifactID}},
  {"lane reordering",func(m *Manifest){m.Pins[0],m.Pins[1]=m.Pins[1],m.Pins[0]}},
 }
 for _,tc:=range mods{
  t.Run(tc.name,func(t *testing.T){
   m,w,y:=syntheticEvidence();tc.change(&m)
   if _,err:=Build(encode(t,m),w,y);!errors.Is(err,ErrBlocked){
    t.Fatal("changed provenance/classification accepted",err)
   }
  })
 }
}
func TestOriginalArtifactsRejectTrailingDataInvalidTopLevelAndMissingFields(t *testing.T){
 m,w,y:=syntheticEvidence()
 invalids:=[][]byte{
  append(append([]byte(nil),w...),[]byte("{}")...),
  []byte("[]"),
  []byte("{}"),
  []byte("{\"classification\":123}"),
  []byte("{\"classification\":\"NATIVE_VERIFIER_BOUNDARY\",\"model_calls\":-1}"),
 }
 for _,bad:=range invalids{
  altered:=m;altered.Pins=append([]Pin(nil),m.Pins...)
  altered.Pins[0].RawSHA256=digest(bad)
  if _,err:=Build(encode(t,altered),bad,y);!errors.Is(err,ErrBlocked){
   t.Fatal("malformed original artifact admitted",string(bad),err)
  }
 }
}
