package largegraph

import (
	"bytes"
	"errors"
	"fmt"
	"strings"
	"testing"

	f95 "github.com/spoonman136668-ai/forge/noveltymechanisms"
)

func mustIndex(t *testing.T, raw string) *Index {
	t.Helper()
	index, err := Compile([]byte(raw))
	if err != nil {
		t.Fatalf("unexpected source denial: %v", err)
	}
	return index
}

func TestF100ODirectionalMultihopAndStrongAmbiguity(t *testing.T) {
	index := mustIndex(t, "a|parent|b\nb|works-at|c\nb|works-at|d\nc|located|x\nd|located|y\n")
	out, err := index.Resolve("a", []Step{{"parent", Forward}, {"works-at", Forward}, {"located", Forward}})
	if err != nil || out.Candidates != 2 || out.UniqueTarget ||
		strings.Join(out.Targets, ",") != "x,y" || out.Steps != 3 {
		t.Fatalf("role-binding ambiguity erased %+v %v", out, err)
	}
	reverse, err := index.Resolve("x", []Step{{"located", Reverse}, {"works-at", Reverse}, {"parent", Reverse}})
	if err != nil || reverse.Candidates != 1 || reverse.Targets[0] != "a" {
		t.Fatalf("reverse typed arc mismatch %+v %v", reverse, err)
	}
	wrong, err := index.Resolve("x", []Step{{"located", Forward}})
	if err != nil || len(wrong.Targets) != 0 {
		t.Fatalf("role direction shortcut was silently allowed %+v %v", wrong, err)
	}
}

func TestF100OExactIdentityPreserved(t *testing.T) {
	index := mustIndex(t, "Movie Name|Acted In|Person B\nmovie name|acted in|person b\n")
	tests := []struct{
		root, role, wanted string
	}{
		{"Movie Name", "Acted In", "Person B"},
		{"movie name", "acted in", "person b"},
	}
	for _, tt := range tests {
		res, err := index.Resolve(tt.root, []Step{{tt.role, Forward}})
		if err != nil || len(res.Targets) != 1 || res.Targets[0] != tt.wanted {
			t.Fatalf("name normalization leaked: %+v %v", res, err)
		}
	}
	mismatch, err := index.Resolve("Movie Name", []Step{{"acted in", Forward}})
	if err != nil || mismatch.Candidates != 0 {
		t.Fatalf("role was silently case-folded: %+v %v", mismatch, err)
	}
}

func TestF100ODuplicateOrderAndSelfRelationAccounting(t *testing.T) {
	p := mustIndex(t, "a|link|b\nb|link|b\na|link|b\n")
	q := mustIndex(t, "b|link|b\na|link|b\na|link|b\n")
	if p.Statistics() != q.Statistics() { t.Fatalf("input order drift %+v / %+v",p.Statistics(),q.Statistics()) }
	s := p.Statistics()
	if s.SourceRows != 3 || s.DistinctTriples != 2 || s.DuplicateRows != 1 ||
		s.SelfRelations != 1 || s.DistinctEntities != 2 || s.SearchableArcs != 4 {
		t.Fatalf("provenance counts were normalized away: %+v", s)
	}
	for _, idx := range []*Index{p,q} {
		out,err:=idx.Resolve("b", []Step{{"link", Reverse}})
		if err!=nil || strings.Join(out.Targets,",")!="a,b" {t.Fatalf("reverse self-edges %+v %v",out,err)}
	}
}

func TestF100OExactFrontierBudgetAndHardRefusal(t *testing.T) {
	var lines []string
	for i:=0;i<MaxFrontier;i++ {
		lines=append(lines,fmt.Sprintf("root|r|node%d",i))
	}
	within:=mustIndex(t,strings.Join(lines,"\n")+"\n")
	allowed,err:=within.Resolve("root",[]Step{{"r",Forward}})
	if err!=nil || allowed.Candidates!=MaxFrontier {t.Fatalf("exact budget rejected %+v %v",allowed,err)}
	lines=append(lines,fmt.Sprintf("root|r|node%d",MaxFrontier))
	over:=mustIndex(t,strings.Join(lines,"\n")+"\n")
	out,err:=over.Resolve("root",[]Step{{"r",Forward}})
	if !errors.Is(err,ErrBudget) || out.Candidates!=0 || len(out.Targets)>0 {
		t.Fatalf("overflow was partially resolved %+v %v",out,err)
	}
}

func TestF100ORejectQueryShapeAndNoAnswerInput(t *testing.T) {
	idx:=mustIndex(t,"a|role|b\n")
	invalid:=[][]Step{nil,{{"role",0}},{{"role",3}},{{"",Forward}},
		{{"role",Forward},{"role",Forward},{"role",Forward},{"role",Forward}}}
	for _,steps:=range invalid {
		if _,err:=idx.Resolve("a",steps);!errors.Is(err,ErrQuery){t.Fatalf("invalid role shape %v accepted %v",steps,err)}
	}
	if _,err:=idx.Resolve("",[]Step{{"role",Forward}});!errors.Is(err,ErrQuery){t.Fatal("empty root accepted")}
	empty,err:=idx.Resolve("unseen",[]Step{{"role",Forward}})
	if err!=nil || empty.Candidates!=0 {t.Fatalf("unknown source should be negative, not a shortcut: %+v %v",empty,err)}
}

func TestF100OMalformedAndBinarySourceDeny(t *testing.T) {
	inputs:=[]string{"","a|b\n","a|b|c|d\n","a||c\n","a|b|\n","a|b|c\n\n",
		"a|b|c\r\n","a|b|c\x00\n"}
	for _,input:=range inputs{
		if _,err:=Compile([]byte(input));err==nil{t.Fatalf("malformed source accepted %q",input)}
	}
	if _,err:=Compile(bytes.Repeat([]byte("x"),MaxSourceBytes+1));!errors.Is(err,ErrBudget){
		t.Fatalf("oversized source accepted: %v",err)
	}
}

func TestF100OHardInputCaps(t *testing.T) {
	tooMany:=strings.Repeat("a|r|b\n",MaxRows+1)
	if _,err:=Compile([]byte(tooMany));!errors.Is(err,ErrBudget){
		t.Fatalf("row over-cap %v",err)
	}
	oversize:=strings.Repeat("n",MaxFieldBytes+1)+"|r|b\n"
	if _,err:=Compile([]byte(oversize));!errors.Is(err,ErrSource) {t.Fatalf("field oversize %v",err)}
}

func TestF100OImmutableReturnedTargetsAndStats(t *testing.T) {
	index:=mustIndex(t,"a|r|b\na|r|c\n")
	first,err:=index.Resolve("a",[]Step{{"r",Forward}})
	if err!=nil || first.Candidates!=2 {t.Fatalf("%+v %v",first,err)}
	first.Targets[0]="MUTATED"
	second,err:=index.Resolve("a",[]Step{{"r",Forward}})
	if err!=nil || strings.Join(second.Targets,",")!="b,c" {t.Fatalf("index exposed mutable internal slice: %+v",second)}
	stats:=index.Statistics()
	stats.SourceRows=0
	if index.Statistics().SourceRows!=2 {t.Fatal("statistics mutated index")}
}

func TestF100OF95SupportedGraphResultParity(t *testing.T) {
	source:=[]f95.Relation{
		{From:"a", Role:"parent", To:"b"}, {From:"b", Role:"works", To:"c"},
		{From:"b", Role:"works", To:"d"}, {From:"c", Role:"where", To:"e"},
	}
	legacy,err:=f95.Compile(source)
	if err!=nil {t.Fatal(err)}
	idx:=mustIndex(t,"a|parent|b\nb|works|c\nb|works|d\nc|where|e\n")
	roles:=[]string{"parent","works","where"}
	got,err:=f95.Resolve(legacy,"a",roles)
	if err!=nil {t.Fatal(err)}
	our,err:=idx.Resolve("a",[]Step{{"parent",Forward},{"works",Forward},{"where",Forward}})
	if err!=nil || strings.Join(our.Targets,",")!=strings.Join(got.Targets,",") ||
		our.Candidates!=len(got.Targets) || !our.UniqueTarget{
		t.Fatalf("supported F95 parity mismatch: legacy=%+v new=%+v %v",got,our,err)
	}
}
