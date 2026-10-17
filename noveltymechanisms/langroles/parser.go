// Package langroles defines a frozen, narrow public-development translator from
// eight explicit English question forms to typed directed graph paths.
// No answer, expected target, model, scoring, or trainable parameter enters it.
package langroles

import (
	"strings"
	"unicode"
	"unicode/utf8"

	"github.com/spoonman136668-ai/forge/noveltymechanisms/largegraph"
)

type Status string

const (
	Matched Status = "matched"
	Abstained Status = "abstained"
)
type Reason string
const (
	ReasonNone Reason = ""
	ReasonMalformed Reason = "malformed_question"
	ReasonTopic Reason = "invalid_topic"
	ReasonUnsupported Reason = "unsupported_grammar"
	ReasonHopMismatch Reason = "wrong_hop_count"
)

type Result struct {
	Status Status
	Reason Reason
	Root string
	Steps []largegraph.Step
}

type template struct {
	shape string
	hops int
	steps []largegraph.Step
}

var templates = []template{
	{"which person directed the movies starred by []", 2,
		[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"directed_by",Direction:largegraph.Forward}}},
	{"the movies written by [] were directed by who", 2,
		[]largegraph.Step{{Role:"written_by",Direction:largegraph.Reverse},{Role:"directed_by",Direction:largegraph.Forward}}},
	{"what types are the movies directed by []", 2,
		[]largegraph.Step{{Role:"directed_by",Direction:largegraph.Reverse},{Role:"has_genre",Direction:largegraph.Forward}}},
	{"which movies have the same actor of []", 2,
		[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse}}},
	{"which movies share the same director of []", 2,
		[]largegraph.Step{{Role:"directed_by",Direction:largegraph.Forward},{Role:"directed_by",Direction:largegraph.Reverse}}},
	{"who wrote movies that share directors with the movie []", 3,
		[]largegraph.Step{{Role:"directed_by",Direction:largegraph.Forward},{Role:"directed_by",Direction:largegraph.Reverse},{Role:"written_by",Direction:largegraph.Forward}}},
	{"who acted in the films written by the screenwriter of []", 3,
		[]largegraph.Step{{Role:"written_by",Direction:largegraph.Forward},{Role:"written_by",Direction:largegraph.Reverse},{Role:"starred_actors",Direction:largegraph.Forward}}},
	{"what genres do the movies that share directors with [] fall under", 3,
		[]largegraph.Step{{Role:"directed_by",Direction:largegraph.Forward},{Role:"directed_by",Direction:largegraph.Reverse},{Role:"has_genre",Direction:largegraph.Forward}}},
}

func no(reason Reason) Result {
	return Result{Status:Abstained, Reason:reason}
}

func asciiFold(s string) string {
	chars := []byte(s)
	for i := range chars {
		if chars[i] >= 'A' && chars[i] <= 'Z' {
			chars[i] += 'a' - 'A'
		}
	}
	return string(chars)
}

func validTopic(s string) bool {
	if len(s)==0 || len(s)>512 || !utf8.ValidString(s) || s != strings.TrimSpace(s) {
		return false
	}
	for _,r := range s {
		if !(unicode.IsLetter(r) || unicode.IsDigit(r) || r==' ') {
			return false
		}
	}
	return true
}

// Parse accepts only a question and the independently specified hop count.
// A non-match never returns a guessed path, root, or partial result.
func Parse(question string, hops int) Result {
	if len(question)==0 || len(question)>1024 || !utf8.ValidString(question) ||
		(hops != 2 && hops != 3) {
		return no(ReasonMalformed)
	}
	for _,r:=range question {
		if unicode.IsControl(r) { return no(ReasonMalformed) }
	}
	i:=strings.IndexByte(question, '[')
	j:=strings.IndexByte(question, ']')
	if i<0 || j<=i || strings.Count(question,"[")!=1 ||
		strings.Count(question,"]")!=1 {
		return no(ReasonMalformed)
	}
	root:=question[i+1:j]
	if !validTopic(root) {return no(ReasonTopic)}
	shape:=question[:i]+"[]"+question[j+1:]
	if strings.HasSuffix(shape,"?") || strings.HasSuffix(shape,".") {
		shape=shape[:len(shape)-1]
	}
	shape=asciiFold(shape)
	for _,t:=range templates {
		if shape == t.shape {
			if hops != t.hops { return no(ReasonHopMismatch) }
			steps:=make([]largegraph.Step,len(t.steps))
			copy(steps,t.steps)
			return Result{Status:Matched,Root:root,Steps:steps}
		}
	}
	return no(ReasonUnsupported)
}
