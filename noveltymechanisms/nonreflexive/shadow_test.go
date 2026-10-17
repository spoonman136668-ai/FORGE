package nonreflexive

import (
 "errors"
 "fmt"
 "reflect"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/noveltymechanisms/devroles"
 "github.com/spoonman136668-ai/forge/noveltymechanisms/groundingaudit"
 "github.com/spoonman136668-ai/forge/noveltymechanisms/largegraph"
)

const sameDirector="which movies share the same director of [Film A]?"
func row(q,ans string)string{return q+string([]byte{9})+ans}
func source(lines ...string)[]byte{return []byte(strings.Join(lines,string([]byte{10}))+string([]byte{10}))}

func TestF104OExactCandidateRootRemovalAndNoMutation(t *testing.T){
 s:=[]largegraph.Step{{Role:"directed_by",Direction:largegraph.Forward},
  {Role:"directed_by",Direction:largegraph.Reverse}}
 original:=[]string{"Film A","Film B","Film C"}
 proposed,d:=Propose("Film A",s,original)
 if !d.EligibleInverseTwoHop||!d.RootWasPresent||!d.RootRemoved||d.BecomesEmpty||
  !reflect.DeepEqual(proposed,[]string{"Film B","Film C"})||
  !reflect.DeepEqual(original,[]string{"Film A","Film B","Film C"}){t.Fatalf("root-only policy mutated source %+v %+v",proposed,d)}
 proposed[0]="MUTATION"
 if original[1]!="Film B"{t.Fatal("shared mutable returned state")}
 only,d:=Propose("Film A",s,[]string{"Film A"})
 if !d.BecomesEmpty||len(only)!=0{t.Fatalf("only source root was silently predicted %+v %+v",only,d)}
}

func TestF104ONegativeControlsWrongDirectionAndCase(t *testing.T){
 for _,s:=range [][]largegraph.Step{
  {{Role:"directed_by",Direction:largegraph.Forward}},
  {{Role:"directed_by",Direction:largegraph.Forward},{Role:"written_by",Direction:largegraph.Reverse}},
  {{Role:"directed_by",Direction:largegraph.Forward},{Role:"directed_by",Direction:largegraph.Forward}},
  {{Role:"directed_by",Direction:largegraph.Forward},{Role:"directed_by",Direction:largegraph.Reverse},{Role:"written_by",Direction:largegraph.Forward}},
  {{Role:"directed_by",Direction:largegraph.Forward},{Role:"directed_by",Direction:0}},
 }{
  unchanged,d:=Propose("Film A",s,[]string{"Film A","Film B"})
  if d.EligibleInverseTwoHop||d.RootRemoved||!reflect.DeepEqual(unchanged,[]string{"Film A","Film B"}){
   t.Fatalf("illegal heuristic applied %+v %+v",unchanged,d)
  }
 }
 inv:=[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Reverse},
  {Role:"starred_actors",Direction:largegraph.Forward}}
 unchanged,d:=Propose("FILM A",inv,[]string{"Film A","Film B"})
 if !d.EligibleInverseTwoHop||d.RootRemoved||!reflect.DeepEqual(unchanged,[]string{"Film A","Film B"}){
  t.Fatalf("source identity was case-folded %+v %+v",unchanged,d)
 }
}

func TestF104OExactTrainShadowTransitionsAndGoldRegressions(t *testing.T){
 idx,err:=SyntheticGraph("Film A|directed_by|Director Z","Film B|directed_by|Director Z")
 if err!=nil{t.Fatal(err)}
 raw:=source(
  row(sameDirector,"Film B"), // baseline partial -> shadow exact
  row(sameDirector,"Film A|Film B"), // baseline exact -> shadow partial
  row(sameDirector,"Film C"), // both disjoint
  row("unknown wording [Film A]?","Film B"), // unchanged abstention
 )
 c,err:=Compare(idx,raw,2,4)
 if err!=nil{t.Fatal(err)}
 if !c.Baseline.Valid()||!c.Shadow.Valid()||c.OriginalRows!=4||
  c.Baseline.GraphResolvedExactSet!=1||c.Shadow.GraphResolvedExactSet!=1||
  c.Baseline.ParserAbstained!=1||c.Shadow.ParserAbstained!=1||
  c.NewExactFromNonexact!=1||c.LostExactFromExact!=1||
  c.UnchangedExact!=0||c.EligibleInverseTwoHop!=3||
  c.RootWasPresent!=3||c.RootRemoved!=3||
  c.BaselineVsShadowDisagreement!=2 {
  t.Fatalf("frozen positive+negative proposal transitions %+v",c)
 }
}

func TestF104ORootOnlyReturnsEmptyRatherThanFalseExact(t *testing.T){
 idx,err:=SyntheticGraph("Film A|directed_by|Director Z")
 if err!=nil{t.Fatal(err)}
 c,err:=Compare(idx,source(row(sameDirector,"Film A")),2,1)
 if err!=nil||c.Baseline.GraphResolvedExactSet!=1||
  c.Shadow.GraphMissingOrNoTargets!=1||c.Shadow.GraphResolvedExactSet!=0||
  c.RootOnlyBecomesEmpty!=1||c.LostExactFromExact!=1 {
  t.Fatalf("single root was promoted or mislabeled %+v %v",c,err)
 }
}

func TestF104OPreserveReverseForwardAndThreeHop(t *testing.T){
 idx,err:=SyntheticGraph(
  "Film A|directed_by|Director Z","Film B|directed_by|Director Z",
  "Film B|written_by|Writer Y",
  "Film A|starred_actors|Actor One",
  "Film B|starred_actors|Actor One",
 )
 if err!=nil{t.Fatal(err)}
 c2,err:=Compare(idx,source(row("the actor [Actor One] acted together with who?","Actor One")),2,1)
 if err!=nil||c2.RootRemoved!=1||c2.Baseline.GraphResolvedExactSet!=1||
  c2.Shadow.GraphMissingOrNoTargets!=1{t.Fatalf("reverse/forward inverse changed %+v %v",c2,err)}
 q3:="who wrote movies that share directors with the movie [Film A]?"
 p:=devroles.Parse(q3,3)
 if len(p.Steps)!=3{t.Fatal(p)}
 c3,err:=Compare(idx,source(row(q3,"Writer Y")),3,1)
 if err!=nil||c3.EligibleInverseTwoHop!=0||c3.RootRemoved!=0||
  c3.Baseline!=c3.Shadow{t.Fatalf("3-hop query shadow illegally altered %+v %v",c3,err)}
}

func TestF104OExactFrontier4096AndRefusal4097(t *testing.T){
 const q="which movies have the same actor of [Film Root]?"
 var lines []string
 lines=append(lines,"Film Root|starred_actors|Actor One")
 for i:=0;i<largegraph.MaxFrontier;i++{
  lines=append(lines,fmt.Sprintf("Film%d|starred_actors|Actor One",i))
 }
 oversized,err:=SyntheticGraph(lines...)
 if err!=nil{t.Fatal(err)}
 denied,err:=Compare(oversized,source(row(q,"Film0")),2,1)
 if err!=nil||denied.Baseline.GraphBudgetRefused!=1||
  denied.Shadow.GraphBudgetRefused!=1||denied.RootRemoved!=0{
  t.Fatalf("overbudget truncated to favorable candidate %+v %v",denied,err)
 }
 boundary,err:=SyntheticGraph(lines[:len(lines)-1]...)
 if err!=nil{t.Fatal(err)}
 within,err:=Compare(boundary,source(row(q,"Film0")),2,1)
 if err!=nil||within.Baseline.GraphBudgetRefused!=0||
  within.Shadow.GraphBudgetRefused!=0||within.RootRemoved!=1{
  t.Fatalf("exact 4096 erroneously refused %+v %v",within,err)
 }
}

func TestF104OFailClosedInvalidGoldEntireOriginalCohortAndDuplicates(t *testing.T){
 idx,err:=SyntheticGraph("Film A|directed_by|Director Z","Film B|directed_by|Director Z")
 if err!=nil{t.Fatal(err)}
 for _,bad:=range []string{
  row(sameDirector,""),row(sameDirector,"Film B|"),
  row(sameDirector,"Film B|Film B"),
  row(sameDirector,"Film B"+string([]byte{13})),
  row("unknown wording [Film A]?","Film B|Film B"),
  sameDirector,row("","Film B"),
  row(sameDirector,"Film B")+string([]byte{9})+"extra",
 }{
  _,err:=Compare(idx,source(bad),2,1)
  if !(errors.Is(err,ErrAudit)||errors.Is(err,groundingaudit.ErrTrainSource)){t.Fatalf("bad source accepted %q %v",bad,err)}
 }
 if _,err:=Compare(idx,source(row(sameDirector,"Film B")),2,2);!(errors.Is(err,ErrAudit)||errors.Is(err,groundingaudit.ErrTrainSource)){
  t.Fatalf("cohort denominator narrowed without denial %v",err)
 }
 data:=source(row(sameDirector,"Film B"),row(sameDirector,"Film B"))
 c,err:=Compare(idx,data,2,2)
 if err!=nil||c.RootRemoved!=2||c.OriginalRows!=2{t.Fatalf("duplicate source rows hidden %+v %v",c,err)}
}

func TestF104OAnswerChangesNeverChangeFrozenPathOrRootDecision(t *testing.T){
 idx,err:=SyntheticGraph("Film A|directed_by|Director Z","Film B|directed_by|Director Z")
 if err!=nil{t.Fatal(err)}
 p:=devroles.Parse(sameDirector,2)
 resolution,err:=idx.Resolve(p.Root,p.Steps)
 if err!=nil{t.Fatal(err)}
 target,d:=Propose(p.Root,p.Steps,resolution.Targets)
 if !d.RootRemoved||!reflect.DeepEqual(target,[]string{"Film B"}){t.Fatal(target,d)}
 a,err:=Compare(idx,source(row(sameDirector,"Film B")),2,1)
 if err!=nil{t.Fatal(err)}
 b,err:=Compare(idx,source(row(sameDirector,"Film A|Film B")),2,1)
 if err!=nil||a.Baseline.Parsed!=b.Baseline.Parsed||
  a.RootRemoved!=b.RootRemoved||a.EligibleInverseTwoHop!=b.EligibleInverseTwoHop{
  t.Fatalf("answer informed frozen policy %+v %+v %v",a,b,err)
 }
}
