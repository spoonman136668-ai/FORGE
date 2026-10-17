package main

import (
	"errors"
	"reflect"
	"testing"

	"github.com/spoonman136668-ai/forge/noveltymechanisms/largegraph"
)

func TestF115SyntheticSourceOnlyExplicitPathTransfer(t *testing.T) {
	raw:=[]byte(
		"a|r.one|b\n"+
		"b|r.two|c\n"+
		"c|r.three|d\n"+
		"z|r.one|b\n"+
		"e|r.four|z\n"+
		"v|r.five|e\n"+
		"g|r.six|v\n"+
		"h|r.seven|g\n"+
		"j|r.eight|h\n"+
		"k|r.nine|j\n",
	)
	graph,err:=largegraph.Compile(raw)
	if err!=nil{t.Fatal(err)}
	lines:=[][]byte{}
	for _,line:=range []string{
		"a|r.one|b","b|r.two|c","c|r.three|d","z|r.one|b",
		"e|r.four|z","v|r.five|e","g|r.six|v","h|r.seven|g",
		"j|r.eight|h","k|r.nine|j",
	} {lines=append(lines,[]byte(line))}
	triples:=[]triple{}
	for _,line:=range lines {
		var q triple
		n,err:=fmtScanTriple(string(line),&q)
		if err!=nil||n!=3{t.Fatalf("synthetic test triple: %v",err)}
		triples=append(triples,q)
	}
	roleMap,err:=mappedRoles(triples)
	if err!=nil{t.Fatal(err)}
	if len(roleMap)!=9{t.Fatal("expected bijective nine-role mapping")}
	a,b,err:=compileVariants(lines,roleMap)
	if err!=nil{t.Fatal(err)}
	if a.Statistics()!=graph.Statistics()||b.Statistics()!=graph.Statistics(){
		t.Fatal("original synthetic edge census drift after relabeling")
	}
	for _,hops:=range []int{2,3} {
		paths,err:=selectPaths(triples,hops,1)
		if err!=nil{t.Fatalf("path depth %d %v",hops,err)}
		c,err:=evaluate(paths,graph,a,b,roleMap)
		if err!=nil{t.Fatal(err)}
		if c.Selected!=1||c.ForwardComplete!=1||
			c.ReversedRowOrderEquivalent!=1||
			c.BijectiveRoleNamesEquivalent!=1||
			c.ReverseWitnessPresent!=1 {
			t.Fatalf("synthetic invariants not complete: %+v",c)
		}
	}
}

func fmtScanTriple(raw string, dest *triple)(int,error){
	for i:=0;i<len(raw);i++ {if raw[i]=='|'{
		for j:=i+1;j<len(raw);j++{if raw[j]=='|'{
			dest.from=raw[:i];dest.role=raw[i+1:j];dest.to=raw[j+1:]
			return 3,nil
		}}
	}}
	return 0,errInvariant
}

func TestF115DirectionInverseAndExactOutcome(t *testing.T){
	s:=[]largegraph.Step{
		{Role:"r.a",Direction:largegraph.Forward},
		{Role:"r.b",Direction:largegraph.Reverse},
		{Role:"r.c",Direction:largegraph.Forward},
	}
	i:=inverseSteps(s)
	want:=[]largegraph.Step{
		{Role:"r.c",Direction:largegraph.Reverse},
		{Role:"r.b",Direction:largegraph.Forward},
		{Role:"r.a",Direction:largegraph.Reverse},
	}
	if !reflect.DeepEqual(i,want) {t.Fatalf("direction order incorrect: %+v",i)}
	if !reflect.DeepEqual(inverseSteps(i),s){t.Fatal("involution broken")}
	a:=largegraph.Resolution{Targets:[]string{"a","b"},Steps:2,Candidates:2}
	b:=largegraph.Resolution{Targets:[]string{"a","b"},Steps:2,Candidates:2}
	if !sameOutcome(a,b,nil,nil){t.Fatal("equal result should match")}
	b.Targets=[]string{"a"}
	if sameOutcome(a,b,nil,nil){t.Fatal("partial prefix must not count as equal")}
	if !sameOutcome(a,b,largegraph.ErrBudget,largegraph.ErrBudget){
		t.Fatal("same budget refusal class must be retained")
	}
	if sameOutcome(a,b,largegraph.ErrBudget,nil){t.Fatal("refusal cannot appear positive")}
}

func TestF115UnqualifiedSourceAndUnderpopulationAbstain(t *testing.T){
	if sourceBytesQualified([]byte("original Freebase graph?")){t.Fatal("fabricated source qualified")}
	if _,err:=audit([]byte("a|r|b\n"));!errors.Is(err,errInvariant){
		t.Fatalf("synthetic source must not impersonate actual pinned MetaQA: %v",err)
	}
	if _,err:=selectPaths([]triple{{"a","r","b"}},3,1);err==nil{
		t.Fatal("cannot manufacture a three-step source path")
	}
	if _,err:=mappedRoles([]triple{{"a","r","b"}});err==nil{
		t.Fatal("cannot invent missing source role namespace")
	}
}
