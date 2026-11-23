package evoportfolio

import "testing"

func TestR19BSourcePinnedR196DifferentialCases(t *testing.T){
 cases:=[]struct{name string;rows []ProgressState;want string}{
  {"planned",[]ProgressState{{Status:"PLANNED"}},"AWAITING_INDEPENDENT_CANDIDATE_QUALIFICATION"},
  {"active",[]ProgressState{{Status:"RUNNING"}},"EXISTING_SCIENTIFIC_RUN_ACTIVE"},
  {"blocked",[]ProgressState{{Status:"BLOCKED"}},"AWAITING_BOUNDED_INFRASTRUCTURE_REQUALIFICATION"},
  {"invalid-stops",[]ProgressState{{Status:"CLASSIFIED",Classification:"INVALID"},{Status:"PLANNED"}},"INVALID_RESULT_REQUIRES_EXISTING_CKB_RECOVERY"},
  {"negative-advances",[]ProgressState{{Status:"CLASSIFIED",Classification:"NEGATIVE"},{Status:"PLANNED"}},"AWAITING_INDEPENDENT_CANDIDATE_QUALIFICATION"},
  {"mixed-advances",[]ProgressState{{Status:"CLASSIFIED",Classification:"MIXED"},{Status:"BLOCKED"}},"AWAITING_BOUNDED_INFRASTRUCTURE_REQUALIFICATION"},
  {"supported-advances",[]ProgressState{{Status:"CLASSIFIED",Classification:"SUPPORTED"},{Status:"RUNNING"}},"EXISTING_SCIENTIFIC_RUN_ACTIVE"},
  {"all-terminal",[]ProgressState{{Status:"CLASSIFIED",Classification:"SUPPORTED"},{Status:"CLASSIFIED",Classification:"NEGATIVE"},{Status:"CLASSIFIED",Classification:"MIXED"}},"REQUEST_NEW_FROZEN_SCREEN_GENERATION"},
 }
 for _,tc:=range cases{
  t.Run(tc.name,func(t *testing.T){
   got,err:=R196Disposition(tc.rows)
   if err!=nil||got!=tc.want{t.Fatalf("got %q error %v want %q",got,err,tc.want)}
  })
 }
 for _,rows:=range [][]ProgressState{
  {},{{Status:"CLASSIFIED",Classification:"SEALED"}},{{Status:"RUNNING",Classification:"NEGATIVE"}},{{Status:"FAKE"}},
 }{
  if _,err:=R196Disposition(rows);err==nil{t.Fatal("invalid R196 fixture passed")}
 }
}
