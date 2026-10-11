package pilotf3

import (
 "encoding/json"
 "os"
 "os/exec"
 "path/filepath"
 "strings"
 "testing"
)

func TestF3ImmutablePreregBeforeAnyEvaluation(t *testing.T){
 data,err:=exec.Command("git","show","HEAD:research/pilot-f3/frozen.json").Output()
 if err!=nil{t.Fatal(err)}
 path:=filepath.Join(t.TempDir(),"preregistered.json")
 if err=os.WriteFile(path,data,0600);err!=nil{t.Fatal(err)}
 if err=ConfirmFreeze(path);err!=nil{t.Fatal(err)}
 path=filepath.Join(t.TempDir(),"modified.json")
 if err=os.WriteFile(path,append(data,' '),0600);err!=nil{t.Fatal(err)}
 if err=ConfirmFreeze(path);err==nil{t.Fatal("modified frozen science accepted")}
}
func TestF3InputsFailClosedBeforeAnyOriginal(t *testing.T){
 for _,tc:=range []struct{lane,run,sha string}{
  {"unknown","19",strings.Repeat("a",40)},
  {"Wingless","",strings.Repeat("a",40)},
  {"Wingless","x",strings.Repeat("a",40)},
  {"Yggdrasil","19","bad"},
 }{
  if _,err:=newRaw(tc.lane,tc.run,tc.sha);err==nil{t.Fatal("accepted unsafe original identity")}
 }
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  if _,err:=Classify(nil,lane);err==nil{t.Fatal("classified absent original")}
  if _,err:=Classify([]byte("{}"),lane);err==nil{t.Fatal("classified forged empty original")}
 }
}
func TestF3SyntheticClassificationPreservesNegativeAndInvalid(t *testing.T){
 r,err:=newRaw("Wingless","9876",strings.Repeat("a",40))
 if err!=nil{t.Fatal(err)}
 for i:=range wingTrain{
  r.Wingless=append(r.Wingless,WinglessRow{
   TrainSeed:wingTrain[i],HeldoutSeed:wingHold[i],
   Cases:256,LabeledExamples:35,InputsDisjoint:true,
  })
 }
 b,err:=json.Marshal(r);if err!=nil{t.Fatal(err)}
 out,err:=Classify(b,"Wingless")
 if err!=nil||out.Disposition!="MIXED"||out.Cases!=1024{
  t.Fatalf("negative performance and valid integrity must remain MIXED, not NEGATIVE: %+v %v",out,err)
 }
 r.Wingless[0].InputsDisjoint=false
 invalid,_:=json.Marshal(r)
 if _,err:=Classify(invalid,"Wingless");err==nil{
  t.Fatal("invalid provenance treated as negative or supported")
 }
}
func TestF3DistinctSeedsAndNoExistingFirstUse(t *testing.T){
 previous:=map[int]bool{}
 for _,values:=range [][]int{
  {6101,6113,6121,6131,6151,6163,6173,6197},
  {7103,7117,7121,7129,7151,7159,7177,7187},
  {7207,7211,7213,7219,7229,7237,7243,7253},
 }{
  for _,v:=range values{previous[v]=true}
 }
 for _,cohort:=range [][]int{
  wingTrain[:],wingHold[:],yggTrain[:],yggHold[:],
 }{
  for _,v:=range cohort{
   if previous[v]{t.Fatal("F1/F2 seed reused")}
   previous[v]=true
  }
 }
 if FreezeBlob==""||!validSHA(FreezeBlob,40){t.Fatal("F3 freeze identity missing")}
}
