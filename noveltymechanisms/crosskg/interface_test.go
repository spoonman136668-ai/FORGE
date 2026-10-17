package crosskg

import (
 "errors"
 "reflect"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/noveltymechanisms/largegraph"
)

func testPlan() Candidate {
 return Candidate{
  Domain:DomainSynthetic,
  RawQuestion:"Which directors worked with Film One?",
  Anchor:"Film One",
  Steps:[]largegraph.Step{
   {Role:"/film/film/directed_by",Direction:largegraph.Forward},
   {Role:"/film/film/directed_by",Direction:largegraph.Reverse},
  },
 }
}

func TestSyntheticDirectionalTypedPlanPreservesRootsAndSteps(t *testing.T){
 g,err:=largegraph.Compile([]byte(
  "Film One|/film/film/directed_by|Director A\n"+
  "Film Two|/film/film/directed_by|Director A\n"))
 if err!=nil{t.Fatal(err)}
 c:=testPlan()
 got,err:=RunSynthetic(c,g)
 if err!=nil||!reflect.DeepEqual(got.Targets,[]string{"Film One","Film Two"})||
  got.Steps!=2||got.UniqueTarget {t.Fatalf("typed traversal changed %+v %v",got,err)}
 c.Steps[0].Role="mutated"
 second,err:=RunSynthetic(testPlan(),g)
 if err!=nil||!reflect.DeepEqual(second.Targets,got.Targets){
  t.Fatalf("caller altered graph or first result %+v %v",second,err)
 }
}

func TestFreebaseQAGraphAndLabelPlanCannotBeForged(t *testing.T){
 g,err:=largegraph.Compile([]byte("Film One|/film/film/directed_by|Director A\n"))
 if err!=nil{t.Fatal(err)}
 c:=testPlan()
 c.Domain=DomainFreebaseQA
 c.Anchor="/m/01fw"
 _,err=Prepare(c)
 if !errors.Is(err,ErrNotReady){t.Fatalf("unqualified Freebase plan prepared %v",err)}
 r,err:=RunSynthetic(c,g)
 if !errors.Is(err,ErrNotReady)||len(r.Targets)!=0 {
  t.Fatalf("unqualified domain used synthetic graph %+v %v",r,err)
 }
}

func TestUntrustedAndLabelInjectedPlansRejected(t *testing.T){
 tests:=[]Candidate{
  {},
  {Domain:"freebase",RawQuestion:"A",Anchor:"a",Steps:[]largegraph.Step{{Role:"r",Direction:largegraph.Forward}}},
  {Domain:DomainSynthetic,RawQuestion:"",Anchor:"A",Steps:[]largegraph.Step{{Role:"r",Direction:largegraph.Forward}}},
  {Domain:DomainSynthetic,RawQuestion:"Hello\nLabel",Anchor:"A",Steps:[]largegraph.Step{{Role:"r",Direction:largegraph.Forward}}},
  {Domain:DomainSynthetic,RawQuestion:"Who?\tAnswer",Anchor:"A",Steps:[]largegraph.Step{{Role:"r",Direction:largegraph.Forward}}},
  {Domain:DomainSynthetic,RawQuestion:"A",Anchor:"",Steps:[]largegraph.Step{{Role:"r",Direction:largegraph.Forward}}},
  {Domain:DomainSynthetic,RawQuestion:"A",Anchor:"film|leak",Steps:[]largegraph.Step{{Role:"r",Direction:largegraph.Forward}}},
  {Domain:DomainSynthetic,RawQuestion:"A",Anchor:"x",Steps:nil},
  {Domain:DomainSynthetic,RawQuestion:"A",Anchor:"x",Steps:[]largegraph.Step{{Role:"r",Direction:0}}},
  {Domain:DomainSynthetic,RawQuestion:"A",Anchor:"x",Steps:[]largegraph.Step{{Role:"r",Direction:3}}},
  {Domain:DomainSynthetic,RawQuestion:"A",Anchor:"x",Steps:[]largegraph.Step{{Role:"ROLE|ANSWER",Direction:largegraph.Forward}}},
  {Domain:DomainSynthetic,RawQuestion:"A",Anchor:"x",Steps:[]largegraph.Step{{Role:"r",Direction:largegraph.Forward},{Role:"r",Direction:largegraph.Forward},{Role:"r",Direction:largegraph.Forward},{Role:"r",Direction:largegraph.Forward}}},
 }
 tests=append(tests,Candidate{Domain:DomainSynthetic,RawQuestion:string([]byte{0xff}),Anchor:"a",Steps:[]largegraph.Step{{Role:"r",Direction:largegraph.Forward}}})
 tests=append(tests,Candidate{Domain:DomainSynthetic,RawQuestion:strings.Repeat("Q",MaxQuestionBytes+1),Anchor:"a",Steps:[]largegraph.Step{{Role:"r",Direction:largegraph.Forward}}})
 for _,x:=range tests {
  got,err:=Prepare(x)
  if !errors.Is(err,ErrMalformed)||got.Anchor!=""||len(got.Steps)!=0{
   t.Fatalf("invalid plan accepted %+v %+v %v",x,got,err)
  }
 }
}

type mockGraph struct{
 ret largegraph.Resolution
 err error
 lastAnchor string
 lastSteps []largegraph.Step
}
func(m *mockGraph)Resolve(root string,steps []largegraph.Step)(largegraph.Resolution,error){
 m.lastAnchor=root
 m.lastSteps=append([]largegraph.Step(nil),steps...)
 return m.ret,m.err
}

func TestGraphOutputNoTruncationNoHallucinationAndSorting(t *testing.T){
 c:=testPlan()
 for _,test:=range []struct{ret largegraph.Resolution;err error}{
  {ret:largegraph.Resolution{Targets:[]string{"b","a"},Candidates:2,Steps:2}},
  {ret:largegraph.Resolution{Targets:[]string{"one"},Candidates:2,Steps:2,UniqueTarget:true}},
  {ret:largegraph.Resolution{Targets:[]string{"a","a"},Candidates:2,Steps:2}},
  {ret:largegraph.Resolution{Targets:[]string{"a"},Candidates:1,Steps:3,UniqueTarget:true}},
 }{
  m:=&mockGraph{ret:test.ret,err:test.err}
  got,err:=RunSynthetic(c,m)
  if len(test.ret.Targets)==2&&test.ret.Targets[0]=="b"{
   if err!=nil||!reflect.DeepEqual(got.Targets,[]string{"a","b"}){
    t.Fatalf("deterministic sort failed %+v %v",got,err)
   }
  }else if !errors.Is(err,ErrMalformed)||len(got.Targets)!=0{
   t.Fatalf("inconsistent targets accepted %+v %v",got,err)
  }
 }
 targets:=make([]string,largegraph.MaxFrontier+1)
 for i:=range targets{targets[i]=strings.Repeat("a",i+1)}
 m:=&mockGraph{ret:largegraph.Resolution{Targets:targets,Candidates:len(targets),Steps:2}}
 r,err:=RunSynthetic(c,m)
 if !errors.Is(err,ErrBudget)||len(r.Targets)!=0{
  t.Fatalf("graph budget partial result %+v %v",r,err)
 }
}

func TestAbsentGraphAndHardUpstreamBudgetRefusal(t *testing.T){
 if _,err:=RunSynthetic(testPlan(),nil);!errors.Is(err,ErrNotReady){t.Fatal(err)}
 mock:=&mockGraph{err:largegraph.ErrBudget}
 r,err:=RunSynthetic(testPlan(),mock)
 if !errors.Is(err,largegraph.ErrBudget)||len(r.Targets)!=0{
  t.Fatalf("hard upper bound overridden %+v %v",r,err)
 }
}
