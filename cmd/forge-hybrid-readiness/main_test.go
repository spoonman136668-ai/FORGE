package main

import(
 "encoding/json"
 "fmt"
 "os"
 "path/filepath"
 "strings"
 "testing"
)
func TestOfflineReadinessCLI(t *testing.T){
 dir:=t.TempDir()
 path:=filepath.Join(dir,"snapshot.json")
 project:="spoonman136668-ai/TTT-Hybrid-Lab"
 sha:=strings.Repeat("a",40)
 rows:=make([]any,0,4)
 names:=[]string{"G4 CPU qualification","G5 authentic TTT CPU",
 "G7 pinned Mamba2 CPU import",
 "G7-S25 observed primary-action surprise residual qualification"}
 for i,n:=range names{
  rows=append(rows,map[string]any{
   "id":100+i,"run_attempt":1,"name":n,"head_sha":sha,
   "head_branch":"research/frozen","status":"completed","conclusion":"failure",
   "created_at":"2026-11-07T00:00:00Z",
   "html_url":fmt.Sprintf("https://github.com/%s/actions/runs/%d",project,100+i),
   "repository":map[string]string{"full_name":project},
   "head_repository":map[string]string{"full_name":project},
  })
 }
 raw,_:=json.Marshal(map[string]any{"total_count":len(rows),"workflow_runs":rows})
 if err:=os.WriteFile(path,raw,0600);err!=nil{t.Fatal(err)}
 args:=[]string{"-snapshot",path,"-source-sha",sha,"-experiment","G7-S25"}
 result,err:=run(args)
 if err!=nil||result.EngineeringCICompleteInSuppliedSnapshot||result.ExecutionAuthorized{
  t.Fatal("unsafe CLI observation",err,result)
 }
 for _,bad:=range [][]string{
  {},{"-snapshot","relative.json","-source-sha",sha,"-experiment","G7-S25"},
  {"-snapshot",dir,"-source-sha",sha,"-experiment","G7-S25"},
  {"-snapshot",path,"-source-sha","wrong","-experiment","G7-S25"},
 }{
  if _,err:=run(bad);err==nil{t.Fatal("accepted invalid CLI",bad)}
 }
 alias:=filepath.Join(dir,"alias.json")
 if err:=os.Symlink(path,alias);err==nil{
  if _,err:=run([]string{"-snapshot",alias,"-source-sha",sha,"-experiment","G7-S25"});err==nil{t.Fatal("symlink admitted")}
 }
}
