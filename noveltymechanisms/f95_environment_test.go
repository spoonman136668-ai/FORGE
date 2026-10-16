package noveltymechanisms

import "testing"

// These are new source-level test conditions, not an independent scientific
// holdout. They are deliberately adversarial to identity memorization,
// one-step lookup shortcuts and role-insensitive graph traversal.
func TestF95NovelRelationshipComposition(t *testing.T){
 m,err:=Compile([]Relation{
  {"node-a","mentor-of","node-b"},{"node-b","owns","artifact-c"},
  {"artifact-c","located-at","room-d"},{"room-d","contains","token-e"},
  {"node-a","owns","distractor-a"},{"node-b","located-at","distractor-b"},
  {"node-b","mentor-of","distractor-c"},{"distractor-a","contains","token-f"},
 })
 if err!=nil{t.Fatal(err)}
 got,err:=Resolve(m,"node-a",[]string{"mentor-of","owns","located-at","contains"})
 if err!=nil||!got.UniqueAnswer||got.CandidatePaths!=1||
  len(got.Targets)!=1||got.Targets[0]!="token-e"||got.TraversedRoles!=4{
  t.Fatalf("failed four-role composition %+v %v",got,err)
 }
 answer,err:=Verify(m,"node-a",[]string{"mentor-of","owns","located-at","contains"},"token-e")
 if err!=nil||!answer{t.Fatalf("binding not satisfied: %v",err)}
 wrong,err:=Verify(m,"node-a",[]string{"mentor-of","located-at","contains"},"token-e")
 if err!=nil||wrong{t.Fatalf("role omission shortcut passed: %v",err)}
}
func TestF95HoldoutStyleRoleSwapAndDistractors(t *testing.T){
 m,err:=Compile([]Relation{
  {"subject","sibling-of","person-one"},{"subject","guardian-of","person-two"},
  {"person-one","located-at","site-one"},{"person-two","located-at","site-two"},
  {"subject","located-at","shortcut"},
  {"site-one","contains","marker-one"},{"site-two","contains","marker-two"},
 })
 if err!=nil{t.Fatal(err)}
 for _,tc:=range []struct{roles []string;expected string}{
  {[]string{"sibling-of","located-at","contains"},"marker-one"},
  {[]string{"guardian-of","located-at","contains"},"marker-two"},
 }{
  ok,err:=Verify(m,"subject",tc.roles,tc.expected)
  if err!=nil||!ok{t.Fatalf("novel role binding failed %v %v",tc.roles,err)}
 }
 rejected,err:=Verify(m,"subject",[]string{"sibling-of","located-at","contains"},"marker-two")
 if err!=nil||rejected{t.Fatalf("identity shortcut leaked: %v",err)}
}
func TestF95AmbiguityNoFalsePositive(t *testing.T){
 m,err:=Compile([]Relation{
  {"user","has-member","entity-a"},{"user","has-member","entity-b"},
  {"entity-a","reports-to","chief-x"},{"entity-b","reports-to","chief-y"},
 })
 if err!=nil{t.Fatal(err)}
 r,err:=Resolve(m,"user",[]string{"has-member","reports-to"})
 if err!=nil||r.UniqueAnswer||r.CandidatePaths!=2||len(r.Targets)!=2{
  t.Fatalf("ambiguous binding collapsed: %+v %v",r,err)
 }
 ok,err:=Verify(m,"user",[]string{"has-member","reports-to"},"chief-x")
 if err!=nil||ok{t.Fatalf("ambiguous answer accepted: %v",err)}
}
func TestF95MalformedSourceAndBudgetFailClosed(t *testing.T){
 invalid:=[][]Relation{
  nil,{{From:"a",Role:"r",To:"a"}},
  {{From:"A",Role:"r",To:"b"}},
  {{From:"a",Role:"r",To:"b"},{From:"a",Role:"r",To:"b"}},
 }
 for i,x:=range invalid{
  if _,err:=Compile(x);err==nil{t.Fatalf("bad relation %d accepted",i)}
 }
 m,err:=Compile([]Relation{{"a","r","b"}})
 if err!=nil{t.Fatal(err)}
 if _,err:=Resolve(m,"a",nil);err==nil{t.Fatal("missing query accepted")}
 if _,err:=Resolve(m,"a",[]string{"R"});err==nil{t.Fatal("invalid role accepted")}
 if _,err:=Resolve(m,"a",[]string{"r","r","r","r","r","r","r","r","r"});err==nil{
  t.Fatal("unbounded query accepted")
 }
}
