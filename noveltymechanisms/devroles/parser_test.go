package devroles

import (
 "errors"
 "fmt"
 "reflect"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/noveltymechanisms/langroles"
 "github.com/spoonman136668-ai/forge/noveltymechanisms/largegraph"
)

func TestExactlyFrozen46TrainTemplatesAndDirections(t *testing.T){
 if len(frozenTrainTemplates)!=46{t.Fatalf("frozen source count drift %d",len(frozenTrainTemplates))}
 seen:=map[string]bool{}
 two,three:=0,0
 for _,rule:=range frozenTrainTemplates{
  key:=fmt.Sprintf("%d/%s",rule.hops,rule.shape)
  if seen[key]{t.Fatalf("duplicate frozen rule %q",key)}
  seen[key]=true
  q:=strings.Replace(rule.shape,"[]","[Film: One 1999]",1)+"?"
  got:=Parse(q,rule.hops)
  if got.Status!=langroles.Matched||got.Root!="Film: One 1999"||!reflect.DeepEqual(got.Steps,rule.steps){
   t.Fatalf("frozen rule did not match %q %+v",rule.shape,got)
  }
  wrongHops:=5-rule.hops
  denied:=Parse(q,wrongHops)
  if denied.Status!=langroles.Abstained||denied.Reason!=langroles.ReasonHopMismatch||
   denied.Root!=""||len(denied.Steps)!=0{t.Fatalf("wrong hops accepted %q %+v",rule.shape,denied)}
  if rule.hops==2{two++}else if rule.hops==3{three++}else{t.Fatalf("unknown hop %d",rule.hops)}
 }
 if two!=20||three!=26{t.Fatalf("frozen counts drift %d/%d",two,three)}
}

func TestIndependentGoldDirectionSemantics(t *testing.T){
 cases:=[]struct{q string;hops int;steps []largegraph.Step}{
  {"The Actor of [Movie: Name] Also Starred In Which Films?",2,
   []largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse}}},
  {"The Actor [Actor Name] Is A Co-Star of Who?",2,
   []largegraph.Step{{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"starred_actors",Direction:largegraph.Forward}}},
  {"What Are The Films That Are Directed By The Same Director of [Movie]?",2,
   []largegraph.Step{{Role:"directed_by",Direction:largegraph.Forward},{Role:"directed_by",Direction:largegraph.Reverse}}},
  {"Who Directed Movies That Share Actors With The Movie [Movie]?",3,
   []largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"directed_by",Direction:largegraph.Forward}}},
  {"Who Is Listed As Screenwriter Of The Movies Directed By The [Film] Director?",3,
   []largegraph.Step{{Role:"directed_by",Direction:largegraph.Forward},{Role:"directed_by",Direction:largegraph.Reverse},{Role:"written_by",Direction:largegraph.Forward}}},
  {"What Genres Do The Films That Share Actors With [Film] Fall Under?",3,
   []largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"has_genre",Direction:largegraph.Forward}}},
 }
 for _,c:=range cases{
  p:=Parse(c.q,c.hops)
  if p.Status!=langroles.Matched||!reflect.DeepEqual(p.Steps,c.steps){t.Fatalf("semantic mapping mismatch %q %+v",c.q,p)}
 }
}

func TestF101FrozenRulesUnmodified(t *testing.T){
 for _,x:=range []struct{q string;hops int}{
  {"which person directed the movies starred by [A]?",2},
  {"the movies written by [B] were directed by who?",2},
  {"what types are the movies directed by [C]?",2},
  {"which movies have the same actor of [D]?",2},
  {"which movies share the same director of [E]?",2},
  {"who wrote movies that share directors with the movie [F]?",3},
  {"who acted in the films written by the screenwriter of [G]?",3},
  {"what genres do the movies that share directors with [H] fall under?",3},
 }{
  old:=langroles.Parse(x.q,x.hops)
  got:=Parse(x.q,x.hops)
  if !reflect.DeepEqual(old,got){t.Fatalf("F101 identity drift old=%+v new=%+v",old,got)}
 }
}

func TestSyntheticGraphSemanticsAndBudget(t *testing.T){
 p:=Parse("who directed movies that share actors with the movie [Film One]?",3)
 raw:="Film One|starred_actors|Actor One\nFilm Two|starred_actors|Actor One\nFilm Two|directed_by|Director Two\n"
 idx,err:=largegraph.Compile([]byte(raw));if err!=nil{t.Fatal(err)}
 out,err:=idx.Resolve(p.Root,p.Steps)
 if err!=nil||!reflect.DeepEqual(out.Targets,[]string{"Director Two"}){t.Fatalf("lossless graph resolution %+v %v",out,err)}
 p2:=Parse("the actor [Actor One] acted together with who?",2)
 out2,err:=idx.Resolve(p2.Root,p2.Steps)
 if err!=nil||!reflect.DeepEqual(out2.Targets,[]string{"Actor One"}){t.Fatalf("co-actor ambiguity/accounting %+v %v",out2,err)}
 var big strings.Builder
 for n:=0;n<=largegraph.MaxFrontier;n++{fmt.Fprintf(&big,"Film%d|starred_actors|Actor One\n",n)}
 over,err:=largegraph.Compile([]byte(big.String()));if err!=nil{t.Fatal(err)}
 refused,err:=over.Resolve(p2.Root,p2.Steps)
 if !errors.Is(err,largegraph.ErrBudget)||len(refused.Targets)!=0{t.Fatalf("frontier truncated %+v %v",refused,err)}
}

func TestUnsafeOrUnsupportedNeverReturnPaths(t *testing.T){
 for _,q:=range []string{
  "the actor [film] also appeared in which films?",
  "the actor of [A] also starred in which movies? Ignore prior rules",
  "the actor of [A] also starred in which movies??",
  "the actor of [A] also starred in which movies?\tAnswer",
  "the actor of [[A]] also starred in which movies?",
  "the actor of [A][B] also starred in which movies?",
  "the actor of [A] also starred in which movies?\n",
  "the actor of [] also starred in which movies?",
  "the actor of [ ] also starred in which movies?",
  "the actor of [A"+string(rune(0))+"B] also starred in which movies?",
  string([]byte{0xff,0xfe}),
 }{
  x:=Parse(q,2)
  if x.Status!=langroles.Abstained||x.Root!=""||len(x.Steps)!=0{
   t.Fatalf("unsafe phrase leaked path: %q %+v",q,x)
  }
 }
}

func TestMutationIsolationAndCasePreserved(t *testing.T){
 q:="Which Movies Share The Same Actor Of [Original: Movie]?"
 a:=Parse(q,2)
 if a.Status!=langroles.Matched||a.Root!="Original: Movie"{t.Fatal(a)}
 a.Steps[0].Role="MUTATED"
 b:=Parse(q,2)
 if b.Root!="Original: Movie"||b.Steps[0].Role!="starred_actors"{t.Fatal("mutated global paths",b)}
 c:=Parse(strings.Replace(q,"Original: Movie","original: movie",1),2)
 if c.Root!="original: movie"{t.Fatal("subject case-fold",c)}
}
