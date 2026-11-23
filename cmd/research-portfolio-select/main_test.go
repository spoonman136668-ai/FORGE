package main

import (
  "encoding/json"
  "os"
  "path/filepath"
  "testing"
  "github.com/spoonman136668-ai/forge/evoportfolio"
)

func TestBothResearchLanesUseFrozenPortfolio(t *testing.T){
  out,err:=build(".")
  if err!=nil{t.Fatal(err)}
  if len(out.Decisions)!=2||out.Decisions[0].Lane!="Wingless"||out.Decisions[1].Lane!="Yggdrasil"{
    t.Fatalf("lane separation failed: %+v",out)
  }
  for _,d:=range out.Decisions {
    if len(d.Archive)!=3||len(d.Finalists)!=2||d.ScreenComputeSpent!=6||
       d.SealedComputeReserved!=4||d.ScientificAccepted||d.DispatchAuthorized||d.AcceptedRefMutation {
      t.Fatalf("budget or authority breach for %s: %+v",d.Lane,d)
    }
    if d.Finalists[0].Family==d.Finalists[1].Family{t.Fatal("lost family diversity")}
  }
  if out.Decisions[0].Finalists[0].ID!="WR7-BOUNDARY-INFERENCE"||
     out.Decisions[1].Finalists[0].ID!="Y020-DEFICIENCY-WITNESS"{
     t.Fatalf("unexpected frozen selection: %+v",out.Decisions)
  }
  a,_:=json.Marshal(out)
  b,_:=build(".")
  other,_:=json.Marshal(b)
  if string(a)!=string(other){t.Fatal("nondeterministic selection")}
}

func TestRejectMutatedManifestAndKeepNegativeHistory(t *testing.T){
  dir:=t.TempDir()
  for _,lane:=range []string{"wingless","yggdrasil"}{
    data,err:=os.ReadFile(lane+".json")
    if err!=nil{t.Fatal(err)}
    if err=os.WriteFile(filepath.Join(dir,lane+".json"),data,0600);err!=nil{t.Fatal(err)}
  }
  blob,err:=os.ReadFile(filepath.Join(dir,"wingless.json"))
  if err!=nil{t.Fatal(err)}
  var frozen evoportfolio.Frozen
  if err=json.Unmarshal(blob,&frozen);err!=nil{t.Fatal(err)}
  frozen.Candidates[2].HistoricalClass="NEGATIVE"
  changed,_:=json.Marshal(frozen)
  if err=os.WriteFile(filepath.Join(dir,"wingless.json"),changed,0600);err!=nil{t.Fatal(err)}
  if _,err=build(dir);err==nil{t.Fatal("unqualified historical rewrite admitted")}
}

func TestFrozenLaneFilesExact(t *testing.T){
  for _,lane:=range []string{"wingless","yggdrasil"}{
    data,err:=os.ReadFile(lane+".json")
    if err!=nil{t.Fatal(err)}
    var f evoportfolio.Frozen
    if err=json.Unmarshal(data,&f);err!=nil{t.Fatal(err)}
    if evoportfolio.Digest(f)!=pins[lane] {t.Fatal("manifest identity changed: "+lane)}
  }
}
