package evoportfolio

import (
 "errors"
 "strings"
 "testing"
)
func policyFixture() PolicyFreeze {
 return PolicyFreeze{Schema:PolicyReplaySchema,Lane:"Wingless",TrainingThrough:2,Candidates:[]Observation{
 {ID:"e1a",Family:"a",SourceSHA:strings.Repeat("a",40),Class:"NEGATIVE",Compute:9,Epoch:1},
 {ID:"e1b",Family:"b",SourceSHA:strings.Repeat("b",40),Class:"SUPPORTED",Compute:1,Epoch:1},
 {ID:"e2a",Family:"a",SourceSHA:strings.Repeat("c",40),Class:"NEGATIVE",Compute:9,Epoch:2},
 {ID:"e2b",Family:"b",SourceSHA:strings.Repeat("d",40),Class:"SUPPORTED",Compute:1,Epoch:2},
 {ID:"e3a",Family:"a",SourceSHA:strings.Repeat("e",40),Class:"SUPPORTED",Compute:9,Epoch:3},
 {ID:"e3b",Family:"b",SourceSHA:strings.Repeat("f",40),Class:"NEGATIVE",Compute:1,Epoch:3},
 }}
}
func TestPolicyReplayTrainingSelectionAndSealedHoldout(t *testing.T){
 f:=policyFixture()
 r,err:=ReplayFrozenPolicies(f,ReplayPolicyDigest(f))
 if err!=nil{t.Fatal(err)}
 if r.SelectedPolicy!="diverse-efficiency"||r.Scores[0].TrainingUtility!=0||
 r.Scores[1].TrainingUtility!=6||r.Scores[0].HoldoutUtility!=3||
 r.Scores[1].HoldoutUtility!=0||r.DispatchAuthorized||r.AcceptedRefMutation{
 t.Fatalf("unexpected frozen replay: %+v",r)
 }
 // Flipping holdout results must not select a different trained policy.
 f.Candidates[4].Class="NEGATIVE";f.Candidates[5].Class="SUPPORTED"
 h,err:=ReplayFrozenPolicies(f,ReplayPolicyDigest(f))
 if err!=nil||h.SelectedPolicy!=r.SelectedPolicy{t.Fatalf("heldout leakage: %+v %v",h,err)}
}
func TestPolicyReplayFailClosed(t *testing.T){
 f:=policyFixture()
 if _,err:=ReplayFrozenPolicies(f,strings.Repeat("0",64));!errors.Is(err,ErrPolicyReplay){t.Fatal("wrong pin accepted")}
 for _,change:=range []func(*PolicyFreeze){
 func(p *PolicyFreeze){p.Candidates[0].Class="FUTURE"},
 func(p *PolicyFreeze){p.Candidates[0].SourceSHA="bad"},
 func(p *PolicyFreeze){p.Candidates[1].ID=p.Candidates[0].ID},
 func(p *PolicyFreeze){p.TrainingThrough=10},
 func(p *PolicyFreeze){p.Lane="CKB"},
 func(p *PolicyFreeze){p.Candidates[1].Compute=0},
 }{
 x:=policyFixture();change(&x)
 if _,err:=ReplayFrozenPolicies(x,ReplayPolicyDigest(x));!errors.Is(err,ErrPolicyReplay){t.Fatalf("invalid freeze accepted: %+v",x)}
 }
}
