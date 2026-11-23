package pilotf4

import (
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"
)

// Source-only negative and ambiguity controls. These tests DO NOT call
// Primary, consume a frozen holdout, or create an original experiment.
func TestF4OriginalNegativeRetainedAsNegativeNotCapacityOnlyMixed(t *testing.T) {
 raw,err:=os.ReadFile(filepath.Join("..","research","pilot-f4","frozen.json"))
 if err!=nil{t.Fatal(err)}
 tmp:=filepath.Join(t.TempDir(),"frozen.json")
 if err=os.WriteFile(tmp,raw,0600);err!=nil{t.Fatal(err)}
 frozen,err:=LoadFrozen(tmp)
 if err!=nil{t.Fatal(err)}
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  t.Run(lane,func(t *testing.T){
   r:=Raw{Schema:RawSchema,Generation:"F4",Lane:lane,
    SourceSHA:strings.Repeat("a",40),RunID:"1001",
    FreezeBlob:FreezeBlob,SyntheticOnly:true}
   var train,hold []int
   count:=240
   if lane=="Wingless"{train=frozen.Wingless.Train;hold=frozen.Wingless.Hold
   }else{train=frozen.Yggdrasil.Train;hold=frozen.Yggdrasil.Hold;count=20}
   for i:=range hold{
    r.Rows=append(r.Rows,Row{TrainSeed:train[i],HeldoutSeed:hold[i],
     Cases:count,Correct:0,Baseline:0,Control:0,Hot:0,Bounded:true})
   }
   b,_:=json.Marshal(r)
   disposition,err:=ClassifyOriginal(b,lane,frozen)
   if err!=nil||disposition.Status!="NEGATIVE"||disposition.ScientificAccepted||
    disposition.Clauses[0]||disposition.Clauses[1]||
    disposition.Clauses[2]||!disposition.Clauses[3]{
    t.Fatalf("negative finding was mislabeled from capacity: %+v: %v",disposition,err)
   }
   // Scientific raw is not a last-wins JSON map: duplicate keys, including
   // nested row fields, are irreconcilable original evidence.
   for name,bad:=range map[string][]byte{
    "duplicate top-level":[]byte(strings.Replace(string(b),
     `"schema":`,`"schema":"forge.f4.synthetic-original.v1","schema":`,1)),
    "duplicate nested row":[]byte(strings.Replace(string(b),
     `"cases":`,`"cases":1,"cases":`,1)),
    "trailing object":append(append([]byte(nil),b...),[]byte("{}")...),
   }{
    t.Run(name,func(t *testing.T){
     if _,err:=ClassifyOriginal(bad,lane,frozen);err==nil{
      t.Fatalf("ambiguous raw original was silently accepted")
     }
    })
   }
  })
 }
}

func TestF4FrozenOriginalCannotBeRetunedAfterLoading(t *testing.T){
 data,err:=os.ReadFile(filepath.Join("..","research","pilot-f4","frozen.json"))
 if err!=nil{t.Fatal(err)}
 path:=filepath.Join(t.TempDir(),"frozen.json")
 for _,variant:=range []struct{name string;raw []byte}{
  {"extra whitespace",append(append([]byte(nil),data...),' ')},
  {"reordered seeds",[]byte(strings.Replace(string(data),"10211","10103",1))},
  {"altered threshold",[]byte(strings.Replace(string(data),"0.85","0.84",1))},
 }{
  t.Run(variant.name,func(t *testing.T){
   if err:=os.WriteFile(path,variant.raw,0600);err!=nil{t.Fatal(err)}
   if _,err:=LoadFrozen(path);err==nil{
    t.Fatal("post-freeze threshold or cohort drift admitted")
   }
  })
 }
}
