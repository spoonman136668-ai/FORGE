package pilotf4

import (
 "testing"
 "github.com/spoonman136668-ai/forge/fsagithubcustody"
)
func TestGitHubCannotMintF4Custody(t *testing.T){
 for _,r:=range []fsagithubcustody.Report{
  {},
  {RemoteReadSuccessful:true,BranchProtected:true,RulesetCount:1},
  {RemoteReadSuccessful:true,BranchProtected:true,RulesetCount:3,
   IndependentKeyCustodyProven:true,MonotonicPhysicalCASProven:true,
   ScientificExecutionAuthorized:true,Disposition:"ACCEPTED"},
 }{
  if CheckCustody(r)==nil{t.Fatal("GitHub posture became first-use authority")}
 }
}
