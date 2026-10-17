package groundingaudit

import (
 "errors"
 "fmt"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/noveltymechanisms/devroles"
 "github.com/spoonman136668-ai/forge/noveltymechanisms/largegraph"
)

const sameDirector = "which movies share the same director of [Film A]?"

func TestF103OFrozenSixExclusiveScoreClassesAndAmbiguity(t *testing.T){
 idx,err:=SyntheticSource(
  "Film A|directed_by|Director Z","Film B|directed_by|Director Z",
  "Film C|directed_by|Director Q",
 )
 if err!=nil{t.Fatal(err)}
 raw:=strings.Join([]string{
  sameDirector+"\tFilm A|Film B",
  sameDirector+"\tFilm B",
  sameDirector+"\tFilm C",
  "which movies share the same director of [Unknown]?\tFilm A",
  "unknown wording in [Film A]?\tFilm A",
  },"\n")+"\n"
 c,err:=Evaluate(idx,[]byte(raw),2,5)
 if err!=nil{t.Fatal(err)}
 if !c.Valid()||c.SourceRows!=5||c.Parsed!=4||
  c.ParserAbstained!=1||c.GraphMissingOrNoTargets!=1||
  c.GraphResolvedExactSet!=1||c.GraphResolvedPartialOverlap!=1||
  c.GraphResolvedDisjoint!=1||c.GraphBudgetRefused!=0||
  c.GraphResolvedAmbiguous!=3||c.GoldAnswerMembers!=6{
  t.Fatalf("scoring buckets or denominators drift %+v",c)
 }
}

func TestF103OOriginalAnswerSetIdentityCaseAndNoSubsetPromotion(t *testing.T){
 idx,err:=SyntheticSource("Film A|directed_by|Director Z","Film B|directed_by|Director Z")
 if err!=nil{t.Fatal(err)}
 test:=sameDirector+"\tFilm A|film b\n" // lower-case is NOT exact.
 c,err:=Evaluate(idx,[]byte(test),2,1)
 if err!=nil||c.GraphResolvedPartialOverlap!=1||c.GraphResolvedExactSet!=0{
  t.Fatalf("overlap promoted to exact or name lowercased %+v %v",c,err)
 }
}

func TestF103ODuplicateOriginalRowsRetainWholeDenominator(t *testing.T){
 idx,err:=SyntheticSource("Film A|directed_by|Director Z","Film B|directed_by|Director Z")
 if err!=nil{t.Fatal(err)}
 raw:=sameDirector+"\tFilm A|Film B\n"
 c,err:=Evaluate(idx,[]byte(raw+raw),2,2)
 if err!=nil||c.GraphResolvedExactSet!=2||c.SourceRows!=2||
  c.GoldAnswerMembers!=4{t.Fatalf("original repeated QA rows lost %+v %v",c,err)}
}

func TestF103OAnswerPerturbationCannotChangeParserOrGraphPath(t *testing.T){
 idx,err:=SyntheticSource("Film A|directed_by|Director Z","Film B|directed_by|Director Z")
 if err!=nil{t.Fatal(err)}
 p1:=devroles.Parse(sameDirector,2)
 p2:=devroles.Parse(sameDirector,2)
 if p1.Root!=p2.Root||len(p1.Steps)!=2||p1.Steps[0]!=p2.Steps[0]{
  t.Fatal("parser contaminated by label",p1,p2)
 }
 same,err:=Evaluate(idx,[]byte(sameDirector+"\tFilm A|Film B\n"),2,1)
 if err!=nil||same.GraphResolvedExactSet!=1{t.Fatal(same,err)}
 changed,err:=Evaluate(idx,[]byte(sameDirector+"\tFilm C\n"),2,1)
 if err!=nil||changed.GraphResolvedDisjoint!=1||changed.Parsed!=same.Parsed{
  t.Fatalf("label changed grammar or contaminated graph %+v %v",changed,err)
 }
}

func TestF103ORejectMalformedOriginalTrainGoldAndIncompleteCohort(t *testing.T){
 idx,err:=SyntheticSource("Film A|directed_by|Director Z")
 if err!=nil{t.Fatal(err)}
 for _,row:=range []string{
  sameDirector+"\t",sameDirector+"\tFilm A|",
  sameDirector+"\tFilm A|Film A",
  sameDirector+"\tFilm A\tother",
  sameDirector, "\tFilm A",sameDirector+"\tFilm A\r",
  "unknown [x]?\tFilm A|Film A", // parse abstains but malformed gold still denied
 }{
  if _,err:=Evaluate(idx,[]byte(row+"\n"),2,1);!errors.Is(err,ErrTrainSource){
   t.Fatalf("malformed source accepted %q: %v",row,err)
  }
 }
 good:=[]byte(sameDirector+"\tFilm A\n")
 if _,err:=Evaluate(idx,good,2,2);!errors.Is(err,ErrTrainSource){t.Fatal("partial corpus",err)}
 if _,err:=Evaluate(idx,good,3,1);err!=nil{t.Fatalf("unsupported 2-hop grammar should abstain in 3-hop not crash %v",err)}
}

func TestF103OExact4096FrontierAnd4097WholeQueryRefusal(t *testing.T){
 const q="the actor of [Movie Root] also starred in which films?"
 var lines []string
 lines=append(lines,"Movie Root|starred_actors|Actor Root")
 for i:=0;i<largegraph.MaxFrontier;i++{lines=append(lines,fmt.Sprintf("Film%d|starred_actors|Actor Root",i))}
 idx,err:=largegraph.Compile([]byte(strings.Join(lines,"\n")+"\n"))
 if err!=nil{t.Fatal(err)}
 within,err:=Evaluate(idx,[]byte(q+"\tFilm0\n"),2,1)
 if err!=nil||within.GraphBudgetRefused!=1||within.GraphResolvedExactSet!=0{
  // The first role traversal is 1 actor; inverse returns 4097 movies (Root + 4096).
  t.Fatalf("whole frontier budget was truncated instead of refused %+v %v",within,err)
 }
 // Exact 4096 targets (including Movie Root) remains resolvable.
 idx2,err:=largegraph.Compile([]byte(strings.Join(lines[:len(lines)-1],"\n")+"\n"))
 if err!=nil{t.Fatal(err)}
 accepted,err:=Evaluate(idx2,[]byte(q+"\tFilm0\n"),2,1)
 if err!=nil||accepted.GraphBudgetRefused!=0||accepted.GraphResolvedPartialOverlap!=1{
  t.Fatalf("boundary 4096 was refused unexpectedly %+v %v",accepted,err)
 }
}

func TestF103OStableCategoriesUnderRowOrderPermutation(t *testing.T){
 idx,err:=SyntheticSource("Film A|directed_by|Director Z","Film B|directed_by|Director Z")
 if err!=nil{t.Fatal(err)}
 lines:=[]string{sameDirector+"\tFilm A|Film B",sameDirector+"\tDifferent", "unknown wording [Film A]?\tFilm A"}
 a,err:=Evaluate(idx,[]byte(strings.Join(lines,"\n")+"\n"),2,3)
 if err!=nil{t.Fatal(err)}
 b,err:=Evaluate(idx,[]byte(strings.Join([]string{lines[2],lines[0],lines[1]},"\n")+"\n"),2,3)
 if err!=nil||a!=b{t.Fatalf("source row ordering changed aggregate %+v %+v %v",a,b,err)}
}
