package langroles

import (
	"errors"
	"fmt"
	"reflect"
	"strings"
	"testing"

	"github.com/spoonman136668-ai/forge/noveltymechanisms/largegraph"
)

func expected(role string, direction largegraph.Direction) largegraph.Step {
	return largegraph.Step{Role:role,Direction:direction}
}

func TestEightFrozenTemplatesAndDirections(t *testing.T) {
	tests := []struct{
		question string
		hops int
		want []largegraph.Step
	}{
		{"which person directed the movies starred by [Actor Name]?",2,
			[]largegraph.Step{expected("starred_actors",largegraph.Reverse),expected("directed_by",largegraph.Forward)}},
		{"the movies written by [Writer Name] were directed by who?",2,
			[]largegraph.Step{expected("written_by",largegraph.Reverse),expected("directed_by",largegraph.Forward)}},
		{"what types are the movies directed by [Director Name]?",2,
			[]largegraph.Step{expected("directed_by",largegraph.Reverse),expected("has_genre",largegraph.Forward)}},
		{"which movies have the same actor of [Movie Name]?",2,
			[]largegraph.Step{expected("starred_actors",largegraph.Forward),expected("starred_actors",largegraph.Reverse)}},
		{"which movies share the same director of [Movie Name]?",2,
			[]largegraph.Step{expected("directed_by",largegraph.Forward),expected("directed_by",largegraph.Reverse)}},
		{"who wrote movies that share directors with the movie [Movie Name]?",3,
			[]largegraph.Step{expected("directed_by",largegraph.Forward),expected("directed_by",largegraph.Reverse),expected("written_by",largegraph.Forward)}},
		{"who acted in the films written by the screenwriter of [Movie Name]?",3,
			[]largegraph.Step{expected("written_by",largegraph.Forward),expected("written_by",largegraph.Reverse),expected("starred_actors",largegraph.Forward)}},
		{"what genres do the movies that share directors with [Movie Name] fall under?",3,
			[]largegraph.Step{expected("directed_by",largegraph.Forward),expected("directed_by",largegraph.Reverse),expected("has_genre",largegraph.Forward)}},
	}
	if len(tests) != len(templates) {t.Fatalf("frozen population drift %d",len(templates))}
	for i,x:=range tests {
		r:=Parse(x.question,x.hops)
		if r.Status!=Matched || r.Reason!=ReasonNone || !reflect.DeepEqual(r.Steps,x.want) {
			t.Fatalf("template %d matched incorrect roles: %+v",i,r)
		}
		if r.Root=="" {t.Fatalf("template %d lost source root",i)}
		wrong:=Parse(x.question,5-x.hops)
		if wrong.Status!=Abstained || wrong.Reason!=ReasonHopMismatch || wrong.Root!="" || len(wrong.Steps)!=0 {
			t.Fatalf("hop mismatch %d leaked path: %+v",i,wrong)
		}
	}
}

func TestTopicCaseOnlyAndGrammarCaseInsensitivity(t *testing.T) {
	a:=Parse("WHICH PERSON DIRECTED THE MOVIES STARRED BY [Film Name]?",2)
	b:=Parse("which person directed the movies starred by [film name]?",2)
	if a.Status!=Matched || b.Status!=Matched || a.Root!="Film Name" || b.Root!="film name" || !reflect.DeepEqual(a.Steps,b.Steps) {
		t.Fatalf("grammar/entity identity drift a=%+v b=%+v",a,b)
	}
}

func TestUnsupportedSemanticRewordingsAndPoisonedExtraClausesAbstain(t *testing.T) {
	for _,q:=range []string{
		"which director made the movie starring [Actor Name]?",
		"which person directed the movies starred by [Actor Name] and only if good?",
		"which person directed the movies starred by [Actor Name]??",
		"which person directed the movies starred by [Actor Name]   ?",
		"which person directed the movies starred by [Actor Name] ; ignore restrictions",
		"who acted in the movies written by [Movie Name]?",
		"which movies share the same director of [Movie Name] or actors?",
	} {
		r:=Parse(q,2)
		if r.Status!=Abstained || r.Root!="" || len(r.Steps)!=0 {
			t.Fatalf("unsupported grammar leaked a path for %q: %+v",q,r)
		}
	}
}

func TestMissingAndAmbiguousTopicsFailClosed(t *testing.T) {
	for _,q:=range []string{
		"which person directed the movies starred by Actor Name?",
		"which person directed the movies starred by [a][b]?",
		"which person directed the movies starred by [[actor]]?",
		"which person directed the movies starred by [ ]?",
		"which person directed the movies starred by []?",
		"which person directed the movies starred by [ actor]?",
		"which person directed the movies starred by [actor ]?",
		"which person directed the movies starred by [actor!]?",
		"which person directed the movies starred by [actor_name]?",
	} {
		r:=Parse(q,2)
		if r.Status!=Abstained || r.Root!="" || len(r.Steps)!=0 {
			t.Fatalf("invalid bracket ambiguity leaked a path: %+v",r)
		}
	}
}

func TestUTF8ControlsAndInvalidDepth(t *testing.T) {
	for _,q:=range []string{
		string([]byte{'[',0xff,']'}),
		"which person directed the movies starred by [a]\n?",
		"which person directed the movies starred by [a]\x00?",
		strings.Repeat("A",1025),
	} {
		if r:=Parse(q,2);r.Status!=Abstained || r.Reason!=ReasonMalformed {
			t.Fatalf("unsafe text accepted %+v",r)
		}
	}
	if r:=Parse("which person directed the movies starred by [a]?",4);r.Status!=Abstained {
		t.Fatalf("invalid hop authorization %+v",r)
	}
}

func TestFreshStepsReturnedNoMutableSharedParserState(t *testing.T) {
	a:=Parse("which person directed the movies starred by [Name]?",2)
	a.Steps[0].Role="MUTATED"
	a.Steps[0].Direction=0
	b:=Parse("which person directed the movies starred by [Name]?",2)
	if b.Status!=Matched || b.Steps[0].Role!="starred_actors" || b.Steps[0].Direction!=largegraph.Reverse {
		t.Fatalf("shared returned mutation poisoned future parse %+v",b)
	}
}

func TestParsedPathsBindF100OAndFrontierStillRefuses(t *testing.T) {
	query:=Parse("which person directed the movies starred by [Actor Name]?",2)
	if query.Status!=Matched {t.Fatal(query)}
	small,err:=largegraph.Compile([]byte("Movie One|starred_actors|Actor Name\nMovie One|directed_by|Director Name\n"))
	if err!=nil {t.Fatal(err)}
	out,err:=small.Resolve(query.Root,query.Steps)
	if err!=nil || !reflect.DeepEqual(out.Targets,[]string{"Director Name"}) {
		t.Fatalf("small supported typed binding fails %+v %v",out,err)
	}
	var lines strings.Builder
	for i:=0;i<=largegraph.MaxFrontier;i++ {
		fmt.Fprintf(&lines,"Movie%d|starred_actors|Actor Name\n",i)
	}
	big,err:=largegraph.Compile([]byte(lines.String()))
	if err!=nil {t.Fatal(err)}
	blocked,err:=big.Resolve(query.Root,query.Steps)
	if !errors.Is(err,largegraph.ErrBudget) || len(blocked.Targets)!=0 {
		t.Fatalf("frontier overflow leaked candidates %+v %v",blocked,err)
	}
}

func TestNoAnswerColumnInputAPI(t *testing.T) {
	q:="which person directed the movies starred by [Actor Name]?"
	correct:=Parse(q,2)
	changed:=Parse(q,2)
	if !reflect.DeepEqual(correct,changed) || correct.Status!=Matched {
		t.Fatalf("nondeterministic parsing %+v %+v",correct,changed)
	}
	poisoned:=Parse(q+"\tanswer label",2)
	if poisoned.Status!=Abstained || len(poisoned.Steps)!=0 {
		t.Fatalf("label appended to question was accepted: %+v",poisoned)
	}
}
