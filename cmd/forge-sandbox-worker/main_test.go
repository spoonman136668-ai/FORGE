package main
import("os";"path/filepath";"testing";"github.com/spoonman136668-ai/forge/syntheticsupervisor")
func TestActualExecutableSyntheticWorkerHandshake(t *testing.T){
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  root:=filepath.Join(t.TempDir(),"forge-synthetic-worker")
  out,err:=run([]string{"--synthetic-only","--lane",lane,"--new-dir",root})
  if err!=nil{t.Fatal(lane,err)}
  if out.RealScientificCycles!=0||out.Recovery!=syntheticsupervisor.Terminal||out.Lane!=lane{t.Fatalf("false science claim %+v",out)}
  if _,err:=run([]string{"--synthetic-only","--lane",lane,"--new-dir",root});err==nil{t.Fatal("reused worker directory")}
 }
}
func TestCLIExplicitSandboxOnly(t *testing.T){
 root:=filepath.Join(t.TempDir(),"forge-synthetic-worker")
 if _,err:=run([]string{"--lane","Wingless","--new-dir",root});err==nil{t.Fatal("missing synthetic gate")}
 if _,err:=run([]string{"--synthetic-only","--lane","Untrusted","--new-dir",root});err==nil{t.Fatal("arbitrary lane")}
 if _,err:=os.Stat(root);!os.IsNotExist(err){t.Fatal("invalid arguments mutated directory")}
}
