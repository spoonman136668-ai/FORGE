// Command forge-f101o-grammar-count consumes question strings ONLY from stdin.
// It exposes aggregate matching and abstention counts, never a question, root,
// path, answer, prediction, model inference or scientific acceptance.
package main

import (
	"bufio"
	"encoding/json"
	"flag"
	"fmt"
	"os"

	"github.com/spoonman136668-ai/forge/noveltymechanisms/langroles"
)

type Totals struct {
	Schema string `json:"schema"`
	Hops int `json:"hops"`
	Questions int `json:"questions"`
	Matched int `json:"matched"`
	Abstained int `json:"abstained"`
	Reasons map[langroles.Reason]int `json:"reasons"`
	QuestionOnlyDataFlow bool `json:"question_only_data_flow"`
	AnswersRead int `json:"answers_read"`
	ModelCalls int `json:"model_calls"`
	ScientificDispatch bool `json:"scientific_dispatch"`
	AcceptedRefMutation bool `json:"accepted_ref_mutation"`
	Status string `json:"status"`
}
func main() {
	hops:=flag.Int("hops",0,"independently frozen expected question hops")
	flag.Parse()
	if (*hops!=2 && *hops!=3) || len(flag.Args())!=0 {
		fmt.Fprintln(os.Stderr,"F101O_REQUIRES_EXACT_2_OR_3_HOP_COHORT")
		os.Exit(2)
	}
	t:=Totals{
		Schema:"forge.optimizer.f101o.public-fixed-grammar-count.v1",
		Hops:*hops, Reasons:map[langroles.Reason]int{
			langroles.ReasonMalformed:0, langroles.ReasonTopic:0,
			langroles.ReasonUnsupported:0, langroles.ReasonHopMismatch:0,
		},
		QuestionOnlyDataFlow:true,
		Status:"PUBLIC_FIXED_GRAMMAR_COVERAGE_ONLY",
	}
	scanner:=bufio.NewScanner(os.Stdin)
	scanner.Buffer(make([]byte,4096),4096)
	for scanner.Scan() {
		t.Questions++
		x:=langroles.Parse(scanner.Text(),*hops)
		if x.Status==langroles.Matched {
			t.Matched++
		} else {
			t.Abstained++
			if _,known:=t.Reasons[x.Reason];!known {
				fmt.Fprintln(os.Stderr,"F101O_UNKNOWN_ABSTENTION_REASON")
				os.Exit(1)
			}
			t.Reasons[x.Reason]++
		}
	}
	if scanner.Err()!=nil || t.Questions==0 || t.Questions!=t.Matched+t.Abstained {
		fmt.Fprintln(os.Stderr,"F101O_QUESTION_POPULATION_INVALID")
		os.Exit(1)
	}
	if err:=json.NewEncoder(os.Stdout).Encode(t);err!=nil {
		fmt.Fprintln(os.Stderr,"F101O_AGGREGATE_SERIALIZATION_FAILED")
		os.Exit(1)
	}
}
