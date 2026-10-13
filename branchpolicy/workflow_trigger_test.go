package branchpolicy

import (
 "os"
 "strings"
 "testing"
)
// The check-runs source verifier accepts ONLY completed successes. Launching
// it on the same main push as the required jobs creates a false failure race.
func TestRulesetProposalDoesNotSelfRaceOnMainPush(t *testing.T){
 raw,err:=os.ReadFile("../.github/workflows/forge-ruleset-readiness.yml")
 if err!=nil{t.Fatal(err)}
 s:=string(raw)
 if strings.Contains(s,"\n  push:\n")||
  !strings.Contains(s,"\n  pull_request:\n")||
  !strings.Contains(s,"\n  workflow_dispatch:\n")||
  !strings.Contains(s,"EXPECTED_MAIN_SHA: ${{ github.event_name == 'pull_request' && github.event.pull_request.base.sha || github.sha }}"){
  t.Fatal("unsafe R20 check-run probe trigger/sha identity")
 }
 qualifier,err:=os.ReadFile("../.github/workflows/qualify.yml")
 if err!=nil{t.Fatal(err)}
 if !strings.Contains(string(qualifier),"\n  push:\n")||
  !strings.Contains(string(qualifier),"branches: [main]"){
  t.Fatal("merged-main full qualification must remain always-on")
 }
}
