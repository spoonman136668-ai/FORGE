package main

import (
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"
)

func fixture(repo string) []byte {
 run:=map[string]any{
  "id":uint64(100),"run_attempt":uint64(1),"name":"observed CI",
  "head_sha":strings.Repeat("a",40),"head_branch":"test/pinned",
  "status":"completed","conclusion":"success","created_at":"2026-11-07T00:00:00Z",
  "html_url":"https://github.com/"+repo+"/actions/runs/100",
  "repository":map[string]any{"full_name":repo},
  "head_repository":map[string]any{"full_name":repo},
 }
 b,_:=json.Marshal(map[string]any{"total_count":uint64(1),"workflow_runs":[]any{run}})
 return b
}
func TestOptionalHybridFlagPreservesTwoLaneDefaultAndRejectsUnsafePaths(t *testing.T) {
 dir:=t.TempDir()
 paths:=[]string{filepath.Join(dir,"w.json"),filepath.Join(dir,"y.json"),filepath.Join(dir,"h.json")}
 repos:=[]string{"spoonman136668-ai/Wingless","spoonman136668-ai/Yggdrasil","spoonman136668-ai/TTT-Hybrid-Lab"}
 for i,p:=range paths{
  if err:=os.WriteFile(p,fixture(repos[i]),0600);err!=nil{t.Fatal(err)}
 }
 base:=[]string{"-wingless",paths[0],"-yggdrasil",paths[1]}
 old,err:=run(base)
 if err!=nil||old.Hybrid!=nil{t.Fatal("legacy observer changed",err)}
 full,err:=run(append(append([]string{},base...),"-hybrid",paths[2]))
 if err!=nil||full.Hybrid==nil||len(full.Hybrid.Runs)!=1||full.ExecutionAuthorized||full.ScientificAccepted{
  t.Fatal("hybrid observation failed closed or elevated authority",err)
 }
 for _,bad:=range []string{paths[0],paths[1],"relative.json"} {
  if _,err:=run(append(append([]string{},base...),"-hybrid",bad));err==nil{
   t.Fatal("accepted unsafe hybrid source path",bad)
  }
 }
}
