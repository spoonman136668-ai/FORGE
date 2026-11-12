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
 s:=strings.ReplaceAll(string(raw),"\r\n","\n")
 if strings.Contains(s,"\n  push:\n")||
  !strings.Contains(s,"\n  pull_request:\n")||
  !strings.Contains(s,"\n  workflow_dispatch:\n")||
  !strings.Contains(s,"EXPECTED_MAIN_SHA: ${{ github.event_name == 'pull_request' && github.event.pull_request.base.sha || github.sha }}"){
  t.Fatal("unsafe R20 check-run probe trigger/sha identity")
 }
 // The exact current original main SHA accumulates many unrelated skipped
 // checks from owner issue events. Never treat a truncated first page as a
 // complete check inventory or fabricate source verification.
 for _,context:=range []string{"linux","windows"}{
  if !strings.Contains(s,"check-runs?check_name="+context+"&per_page=100"){
   t.Fatalf("missing independently filtered required GitHub check: %s",context)
  }
 }
 if !strings.Contains(s,".total_count == 1")||
    !strings.Contains(s,"check_runs: (.[0].check_runs + .[1].check_runs)")||
    strings.Contains(s,"check-runs\" > \"$RUNNER_TEMP/main-checks.json\""){
  t.Fatal("main ruleset probe may consume truncated or unverified check page")
 }
 qualifier,err:=os.ReadFile("../.github/workflows/qualify.yml")
 if err!=nil{t.Fatal(err)}
 q:=strings.ReplaceAll(string(qualifier),"\r\n","\n")
 if !strings.Contains(q,"\n  push:\n")||
  !strings.Contains(q,"branches: [main]"){
  t.Fatal("merged-main full qualification must remain always-on")
 }
}
