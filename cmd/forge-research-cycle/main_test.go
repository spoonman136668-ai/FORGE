package main

import (
 "context"
 "encoding/json"
 "errors"
 "os"
 "path/filepath"
 "strings"
 "testing"
)
func dirs(t *testing.T)(string,string){
 t.Helper()
 portfolio,err:=filepath.Abs("../research-portfolio-select")
 if err!=nil{t.Fatal(err)}
 history,err:=filepath.Abs("fixtures")
 if err!=nil{t.Fatal(err)}
 return portfolio,history
}
func TestIntegratedResearchEnhancementsBothLanesAndSealedHistory(t *testing.T){
 portfolio,history:=dirs(t)
 out,err:=plan(portfolio,history)
 if err!=nil{t.Fatal("frozen policy/portfolio integration",err)}
 if len(out)!=2||out[0].Lane!="Wingless"||out[1].Lane!="Yggdrasil"{
  t.Fatalf("both lanes required: %+v",out)
 }
 for _,lane:=range out{
  if lane.Policy!="baseline-family"||
   lane.HistoricalNegativeCount!=2||lane.HistoricalMixedCount!=1||
   len(lane.Finalists)!=2||len(lane.Nonfinalists)!=1||
   lane.NextCandidateID!=lane.Finalists[0]||lane.ScreenComputeSpent!=6||
   lane.SealedComputeReserved!=4||lane.DispatchAuthorized||lane.ScientificAccepted{
   t.Fatalf("missing preserved enhancement or authority boundary for %s: %+v",lane.Lane,lane)
  }
  if lane.PortfolioFrozenSHA256==""||lane.PolicyHistoryFrozenSHA256==""||
   lane.DecisionSHA256==""{t.Fatal("unpinned research handoff")}
 }
 raw,_:=json.Marshal(out)
 again,err:=plan(portfolio,history)
 if err!=nil{t.Fatal(err)}
 reraw,_:=json.Marshal(again)
 if string(raw)!=string(reraw){t.Fatal("nondeterministic two-lane plan")}
}
func TestIntegratedPlanRefusesTamperedHoldoutAndChangedBudgets(t *testing.T){
 portfolio,history:=dirs(t)
 tmp:=t.TempDir()
 for _,name:=range []string{"wingless-synthetic-history.json","yggdrasil-synthetic-history.json"}{
  data,err:=os.ReadFile(filepath.Join(history,name));if err!=nil{t.Fatal(err)}
  if err=os.WriteFile(filepath.Join(tmp,name),data,0600);err!=nil{t.Fatal(err)}
 }
 data,err:=os.ReadFile(filepath.Join(tmp,"wingless-synthetic-history.json"))
 if err!=nil{t.Fatal(err)}
 changed:=strings.Replace(string(data),`"NEGATIVE"`,`"SUPPORTED"`,1)
 if changed==string(data){t.Fatal("negative fixture missing")}
 if err=os.WriteFile(filepath.Join(tmp,"wingless-synthetic-history.json"),[]byte(changed),0600);err!=nil{t.Fatal(err)}
 if _,err=plan(portfolio,tmp);!errors.Is(err,ErrBlocked){
  t.Fatal("history/holdout rewrite bypassed external pin",err)
 }
}
func TestOperationalCLIRequiresSyntheticAckAndNeverStartsOriginal(t *testing.T){
 portfolio,history:=dirs(t)
 root:=filepath.Join(t.TempDir(),"forge-synthetic-processes")
 for _,args:=range [][]string{
  nil,
  {"--portfolio-dir",portfolio,"--history-dir",history},
  {"--synthetic-only","--portfolio-dir",portfolio,"--history-dir",history,
   "--new-dir",root,"--worker-executable","/missing/worker","--worker-sha256",strings.Repeat("f",64)},
 }{
  if _,err:=run(context.Background(),args);!errors.Is(err,ErrBlocked){
   t.Fatal("incomplete worker authority unexpectedly accepted",err)
  }
 }
 if _,err:=os.Stat(root);!os.IsNotExist(err){
  t.Fatal("synthetic handoff or malformed binary created worker evidence",err)
 }
}
