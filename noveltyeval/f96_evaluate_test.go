package noveltyeval

import (
 "bytes"
 "encoding/json"
 "errors"
 "os"
 "reflect"
 "testing"
)

func f96Fixture(t *testing.T)[]byte{
 t.Helper()
 raw,err:=os.ReadFile("f96_cases.json")
 if err!=nil{t.Fatal(err)}
 return raw
}
func TestF96FullSourceCohortAndStrongControlParity(t *testing.T){
 raw:=f96Fixture(t)
 a,err:=EvaluateFrozen(raw);if err!=nil{t.Fatal(err)}
 b,err:=EvaluateFrozen(raw);if err!=nil||!reflect.DeepEqual(a,b){
  t.Fatalf("non-deterministic source comparison: %v",err)
 }
 if a.Schema!=ReportSchema||a.FixtureFreezeCommit!=FrozenBeforeEvaluationCommit||
  a.FixtureCaseCount!=16||len(a.Results)!=16||len(a.Totals)!=4||
  !a.EveryCaseRetained||!a.EquivalentReferenceIsRequiredControl||
  a.SyntheticIndependentScience||a.IndependentSealedHoldoutConsumed||
  a.AuthenticOriginalFirstUse||a.AnyScientificSuperiorityEstablished||
  a.DreamParetoPromotionAuthorized||a.ThetaEvolveAcceptedTrainingEnabled||
  a.AcceptedScientificReferenceMutation||a.ScientificDispatchAuthorized{
  t.Fatalf("source-only benchmark claimed scientific release: %+v",a)
 }
 if a.Totals[0].Correct!=16||a.Totals[3].Correct!=16||
  a.Totals[0].Errors!=0||a.Totals[3].Errors!=0{
  t.Fatalf("F95 failed to match equivalent positive reference %+v",a.Totals)
 }
 if a.Totals[1].Errors==0||a.Totals[2].Errors==0{
  t.Fatalf("weak controls accidentally passed all novel conditions %+v",a.Totals)
 }
 categories:=map[string]bool{}
 for _,row:=range a.Results{
  categories[row.Category]=true
  if len(row.Models)!=4{
   t.Fatalf("missing/selected control case %+v",row)
  }
  if !row.Models[0].Correct||!row.Models[3].Correct||
   !reflect.DeepEqual(row.Models[0].ActualTargets,row.Models[3].ActualTargets){
   t.Fatalf("source-equivalent reference disagreement %+v",row)
  }
  for _,model:=range row.Models{
   if (model.ErrorClass=="CORRECT")!=model.Correct{
    t.Fatalf("negative result suppressed %+v",row)
   }
  }
 }
 if len(categories)<7{t.Fatalf("missing structural condition categories %+v",categories)}
}
func TestF96AllNegativeControlFindingsPreserved(t *testing.T){
 got,err:=EvaluateFrozen(f96Fixture(t));if err!=nil{t.Fatal(err)}
 totals:=map[string]int{}
 for _,row:=range got.Results{
  for _,model:=range row.Models{
   if !model.Correct{totals[model.Name]++}
  }
 }
 for _,total:=range got.Totals{
  if total.Errors!=totals[total.Model]||
   total.Cases!=total.Correct+total.Errors{
   t.Fatalf("negative evidentiary denominator drift %+v",total)
  }
 }
 if len(got.Results)!=16{t.Fatalf("results missing %+v",got)}
}
func TestF96TamperingAndCherryPickedSourceFails(t *testing.T){
 raw:=f96Fixture(t)
 mutations:=map[string]func(*Suite){
  "drop last outcome":func(s *Suite){s.Cases=s.Cases[:len(s.Cases)-1]},
  "reuse case id":func(s *Suite){s.Cases[1].ID=s.Cases[0].ID},
  "alter source provenance":func(s *Suite){s.BaselineSourceSHA="legacy"},
  "claim independent sealed holdout":func(s *Suite){s.ScientificHoldout=true},
  "turn off complete denominator":func(s *Suite){s.AllCasesRetained=false},
  "guess positive reference target":func(s *Suite){s.Cases[0].ExpectedTargets=[]string{"wrong"}},
  "substitute new causal shortcut":func(s *Suite){s.Cases[0].Relations[0].Role="shortcut"},
  "tamper frozen role":func(s *Suite){s.Cases[0].Roles[0]="shortcut"},
  "remove relation graph":func(s *Suite){s.Cases[0].Relations=nil},
  "change original schema":func(s *Suite){s.Schema="forge.optimizer.f96.science-release.v1"},
 }
 for name,mutate:=range mutations{
  t.Run(name,func(t *testing.T){
   var suite Suite
   if err:=json.Unmarshal(raw,&suite);err!=nil{t.Fatal(err)}
   mutate(&suite)
   modified,err:=json.Marshal(suite);if err!=nil{t.Fatal(err)}
   if _,err:=EvaluateFrozen(modified);!errors.Is(err,ErrF96){
    t.Fatalf("changed or cherry-picked source admitted %s: %v",name,err)
   }
  })
 }
 junk:=append(append([]byte(nil),raw...),[]byte(" \"\"")...)
 if _,err:=EvaluateFrozen(junk);!errors.Is(err,ErrF96){
  t.Fatal("extra JSON after frozen bundle accepted")
 }
}
func TestF96WhitespaceChangesAreDetectableBySourceDigest(t *testing.T){
 raw:=f96Fixture(t)
 first,err:=EvaluateFrozen(raw);if err!=nil{t.Fatal(err)}
 changed:=bytes.TrimSpace(raw)
 second,err:=EvaluateFrozen(changed);if err!=nil{t.Fatal(err)}
 if first.FixtureBytesSHA256==second.FixtureBytesSHA256{
  t.Fatal("different source bytes shared an identical fixture identity")
 }
 // Source digest change by itself does not mean different scientific
 // content, and neither exact bytes nor digest constitute first-use.
 if first.AuthenticOriginalFirstUse||second.AuthenticOriginalFirstUse{
  t.Fatal("source checksum laundered into original-use authority")
 }
}
