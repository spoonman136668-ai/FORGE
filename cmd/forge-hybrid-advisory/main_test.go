package main

import (
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/hybridresearch"
)
func TestReadOnlyHybridCLI(t *testing.T) {
 dir:=t.TempDir()
 path:=filepath.Join(dir,"hybrid.json")
 r:=hybridresearch.Project
 snap:=hybridresearch.Snapshot{
  Schema:hybridresearch.SnapshotSchema,Repository:r,
  Candidates:[]hybridresearch.Candidate{{
   ExperimentID:"G7-S24",PullRequest:39,HeadSHA:strings.Repeat("a",40),
   ProtocolSHA256:strings.Repeat("b",64),
   PullRequestURL:"https://github.com/"+r+"/pull/39",
   Stage:"ENGINEERING_CANDIDATE",
  }},
 }
 b,_:=json.Marshal(snap)
 if err:=os.WriteFile(path,b,0600);err!=nil {t.Fatal(err)}
 out,err:=run([]string{"--snapshot",path})
 if err!=nil||len(out.Candidates)!=1||out.ExecutionAuthorized||out.ScientificAccepted {t.Fatal("unexpected result",err)}
 for _,bad:=range [][]string{
  {},{"--snapshot","relative.json"},{"--snapshot",dir},
  {"--snapshot",path,"extra"},
 }{
  if _,err:=run(bad);err==nil {t.Fatal("accepted unsafe CLI input",bad)}
 }
 alias:=filepath.Join(dir,"alias.json")
 if err:=os.Symlink(path,alias);err==nil {
  if _,err:=run([]string{"--snapshot",alias});err==nil {t.Fatal("symlink accepted")}
 }
}
