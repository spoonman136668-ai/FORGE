package main
import (
 "os"
 "path/filepath"
 "testing"
 "github.com/spoonman136668-ai/forge/researchstate"
)
func TestDurableTwoLaneRehearsalAndRestart(t *testing.T){
 root:=filepath.Join(t.TempDir(),"forge-synthetic-rehearsal")
 report,err:=run([]string{"--synthetic-only","--new-dir",root})
 if err!=nil{t.Fatal(err)}
 if report.CompleteExistingLanes!=2||report.SimulatedSuccessorCycles!=2||report.RealScientificCycles!=0{t.Fatalf("false autonomy claim: %+v",report)}
 j,err:=researchstate.LoadArchive(root);if err!=nil{t.Fatal(err)}
 if len(j.Entries)!=26{t.Fatal("incorrect durable event count",len(j.Entries))}
 if _,err:=run([]string{"--synthetic-only","--new-dir",root});err==nil{t.Fatal("reused synthetic original archive")}
 if err:=os.Remove(filepath.Join(root,"00000000000000000001.json"));err!=nil{t.Fatal(err)}
 if _,err:=researchstate.LoadArchive(root);err==nil{t.Fatal("torn original journal passed restart")}
}
func TestNeverTouchesNonDedicatedOrPreexistingDirectory(t *testing.T){
 parent:=t.TempDir()
 if _,err:=run([]string{"--new-dir",filepath.Join(parent,"forge-synthetic-rehearsal")});err==nil{t.Fatal("missing synthetic consent")}
 if _,err:=run([]string{"--synthetic-only","--new-dir",parent});err==nil{t.Fatal("non-dedicated directory accepted")}
 if _,err:=run([]string{"--synthetic-only","--new-dir","relative/forge-synthetic-rehearsal"});err==nil{t.Fatal("relative directory accepted")}
 root:=filepath.Join(parent,"forge-synthetic-rehearsal")
 if err:=os.Mkdir(root,0700);err!=nil{t.Fatal(err)}
 if _,err:=run([]string{"--synthetic-only","--new-dir",root});err==nil{t.Fatal("existing directory overwritten")}
}
