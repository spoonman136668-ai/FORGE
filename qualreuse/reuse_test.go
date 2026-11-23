package qualreuse

import (
 "errors"
 "strings"
 "testing"
)
func fixture(lane string)Identity{
 return Identity{Lane:lane,BaselineCommitSHA:strings.Repeat("1",40),
  SourceTreeSHA:strings.Repeat("2",40),
  PreregistrationBlobSHA:strings.Repeat("3",40),
  DependenciesTreeSHA:strings.Repeat("4",40),
  InterfacesTreeSHA:strings.Repeat("5",40),
  HarnessTreeSHA:strings.Repeat("6",40),
  ToolchainSHA256:strings.Repeat("7",64),
  BudgetSHA256:strings.Repeat("8",64),
  CohortSHA256:strings.Repeat("9",64),
  FocusedCommandSHA256:strings.Repeat("a",64)}
}
func receipt(i Identity)FocusedReceipt{
 return FocusedReceipt{Schema:Schema,Identity:i,
  QualificationSourceCommitSHA:strings.Repeat("b",40),
  IndependentEvidenceSHA256:strings.Repeat("c",64),
  SourceBirthProvenanceSHA256:strings.Repeat("d",64),
  IndependentVerifierAuthenticated:true,
  FocusedPassed:true,NegativeControlsPassed:true}
}
func assertSafety(t *testing.T,p Plan){
 t.Helper()
 if !p.FullRegressionRequired||!p.BuildRequired||
  !p.IndependentScientificAdmissionRequired||
  p.ExecutionAuthorized||p.AcceptedRefMutation||
  p.FocusedTestsReused==p.FocusedTestsRequired{
  t.Fatalf("scope reuse escaped safety: %+v",p)
 }
}
func TestExactFocusedQualificationReuseButNeverFullRegression(t *testing.T){
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  t.Run(lane,func(t *testing.T){
   id:=fixture(lane)
   frozen:=receipt(id)
   p,err:=PlanFocusedReuse(id,&frozen)
   if err!=nil||!p.FocusedTestsReused{t.Fatal(p,err)}
   assertSafety(t,p)
   noCache,err:=PlanFocusedReuse(id,nil)
   if err!=nil||noCache.FocusedTestsReused{t.Fatal(noCache,err)}
   assertSafety(t,noCache)
   again,err:=PlanFocusedReuse(id,&frozen)
   if err!=nil||again!=p{t.Fatal("nondeterministic cache identity",err)}
  })
 }
}
func TestCompositionalIdentityChangesInvalidateAllFocusedCache(t *testing.T){
 original:=fixture("Wingless")
 previous:=receipt(original)
 changes:=[]struct{name string;change func(*Identity)}{
  {"lane",func(x *Identity){x.Lane="Yggdrasil"}},
  {"baseline",func(x *Identity){x.BaselineCommitSHA=strings.Repeat("e",40)}},
  {"source",func(x *Identity){x.SourceTreeSHA=strings.Repeat("e",40)}},
  {"prereg",func(x *Identity){x.PreregistrationBlobSHA=strings.Repeat("e",40)}},
  {"dependency",func(x *Identity){x.DependenciesTreeSHA=strings.Repeat("e",40)}},
  {"interface",func(x *Identity){x.InterfacesTreeSHA=strings.Repeat("e",40)}},
  {"harness",func(x *Identity){x.HarnessTreeSHA=strings.Repeat("e",40)}},
  {"toolchain",func(x *Identity){x.ToolchainSHA256=strings.Repeat("e",64)}},
  {"budget",func(x *Identity){x.BudgetSHA256=strings.Repeat("e",64)}},
  {"cohort",func(x *Identity){x.CohortSHA256=strings.Repeat("e",64)}},
  {"command",func(x *Identity){x.FocusedCommandSHA256=strings.Repeat("e",64)}},
 }
 for _,tt:=range changes{
  t.Run(tt.name,func(t *testing.T){
   altered:=original;tt.change(&altered)
   p,err:=PlanFocusedReuse(altered,&previous)
   if err!=nil||p.FocusedTestsReused{t.Fatal("scope drift reused stale proof",p,err)}
   assertSafety(t,p)
  })
 }
}
func TestFocusedReuseRejectsUntrustedLeakedOrUnsafeProof(t *testing.T){
 original:=fixture("Wingless")
 tests:=[]struct{name string;mutate func(*FocusedReceipt)}{
  {"receipt_schema",func(r *FocusedReceipt){r.Schema="legacy"}},
  {"missing_evidence",func(r *FocusedReceipt){r.IndependentEvidenceSHA256=""}},
  {"missing_origin",func(r *FocusedReceipt){r.SourceBirthProvenanceSHA256=""}},
  {"unsafe_first_use",func(r *FocusedReceipt){r.OriginalFirstUseConsumed=true}},
  {"sealed_leak",func(r *FocusedReceipt){r.SealedOutcomesRead=true}},
  {"capacity_widening",func(r *FocusedReceipt){r.BudgetWidened=true}},
 }
 for _,tt:=range tests{
  t.Run(tt.name,func(t *testing.T){
   r:=receipt(original);tt.mutate(&r)
   if _,err:=PlanFocusedReuse(original,&r);!errors.Is(err,ErrInvalid){
    t.Fatal("unsafe or malformed proof accepted",err)
   }
  })
 }
 unverified:=receipt(original);unverified.IndependentVerifierAuthenticated=false
 for _,r:=range []FocusedReceipt{unverified,func()FocusedReceipt{
  x:=receipt(original);x.FocusedPassed=false;return x
 }(),func()FocusedReceipt{x:=receipt(original);x.NegativeControlsPassed=false;return x}()}{
  p,err:=PlanFocusedReuse(original,&r)
  if err!=nil||p.FocusedTestsReused{t.Fatal("unqualified cache reused",p,err)}
  assertSafety(t,p)
 }
}
func TestInvalidIdentityRejectsAllReuse(t *testing.T){
 id:=fixture("Wingless")
 id.Lane="CKB-plane"
 if _,err:=PlanFocusedReuse(id,nil);!errors.Is(err,ErrInvalid){t.Fatal(err)}
 id=fixture("Wingless");id.FocusedCommandSHA256=""
 if _,err:=PlanFocusedReuse(id,nil);!errors.Is(err,ErrInvalid){t.Fatal(err)}
}
