// Package nonreflexive tests a preregistered answer-blind *shadow* policy.
// It cannot alter F100 graph, F102 language rules or accepted scientific refs.
package nonreflexive

import (
 "github.com/spoonman136668-ai/forge/noveltymechanisms/largegraph"
)

type Decision struct {
 EligibleInverseTwoHop bool
 RootWasPresent bool
 RootRemoved bool
 BecomesEmpty bool
}

// Propose copies a COMPLETE graph result. It removes exactly the original
// root iff two roles are identical and directions are strict inverses.
// No question label, answer target, score, reranker or model is accepted.
func Propose(root string, steps []largegraph.Step, complete []string) ([]string,Decision) {
 out:=append([]string(nil),complete...)
 d:=Decision{}
 if len(steps)!=2 || steps[0].Role=="" ||
  steps[0].Role!=steps[1].Role ||
  !((steps[0].Direction==largegraph.Forward&&steps[1].Direction==largegraph.Reverse)||
    (steps[0].Direction==largegraph.Reverse&&steps[1].Direction==largegraph.Forward)) {
  return out,d
 }
 d.EligibleInverseTwoHop=true
 if root==""||len(out)==0{return out,d}
 for i,candidate:=range out {
  if candidate!=root{continue}
  d.RootWasPresent=true
  d.RootRemoved=true
  // Preserve every other source-grounded target and its original ordering.
  out=append(out[:i],out[i+1:]...)
  d.BecomesEmpty=len(out)==0
  break
 }
 return out,d
}
