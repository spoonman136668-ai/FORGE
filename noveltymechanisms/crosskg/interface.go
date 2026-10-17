// Package crosskg defines a typed boundary for future non-MetaQA graph
// adapters. Source data, gold parses and labels never enter this interface.
// No qualified Freebase linker, role translator or graph currently exists.
package crosskg

import (
 "errors"
 "sort"
 "strings"
 "unicode"
 "unicode/utf8"

 "github.com/spoonman136668-ai/forge/noveltymechanisms/largegraph"
)

const (
 DomainSynthetic = "synthetic-test-graph"
 DomainFreebaseQA = "freebaseqa"
 MaxQuestionBytes = 2048
)
var (
 ErrMalformed = errors.New("FORGE_F106O_INVALID_CROSS_GRAPH_PLAN")
 ErrNotReady = errors.New("FORGE_F106O_FREEBASE_LINKER_GRAPH_AND_ROLE_MAPPING_NOT_QUALIFIED")
 ErrBudget = largegraph.ErrBudget
)

// Candidate is a typed plan supplied by a future independent entity linker
// and language-to-relation translator. A plan is NOT an answer or a score.
// The only currently executable target is synthetic fixture infrastructure.
type Candidate struct {
 Domain string
 RawQuestion string
 Anchor string
 Steps []largegraph.Step
}

type Resolver interface {
 Resolve(root string, steps []largegraph.Step) (largegraph.Resolution,error)
}

func validText(s string,max int) bool {
 if s==""||len(s)>max||!utf8.ValidString(s){return false}
 for _,r:=range s{if unicode.IsControl(r){return false}}
 return true
}

func validRole(s string) bool {
 if !validText(s,largegraph.MaxFieldBytes){return false}
 for _,r:=range s {
  if !(r>='a'&&r<='z'||r>='0'&&r<='9'||r=='.'||r=='_'||r=='-'||r=='/') {
   return false
  }
 }
 return true
}

func validPlan(c Candidate) bool {
 if c.Domain!=DomainSynthetic && c.Domain!=DomainFreebaseQA{return false}
 if !validText(c.RawQuestion,MaxQuestionBytes)||!validText(c.Anchor,largegraph.MaxFieldBytes){
  return false
 }
 if strings.ContainsAny(c.Anchor,"|[]") {return false}
 if len(c.Steps)==0||len(c.Steps)>largegraph.MaxSteps{return false}
 for _,step:=range c.Steps{
  if !validRole(step.Role)||
   (step.Direction!=largegraph.Forward&&step.Direction!=largegraph.Reverse) {
   return false
  }
 }
 return true
}

// Prepare validates a proposed typed shape, but NEVER certifies its provenance
// or authorizes using gold FreebaseQA label-side annotations as a plan.
func Prepare(c Candidate)(Candidate,error) {
 if !validPlan(c){return Candidate{},ErrMalformed}
 if c.Domain==DomainFreebaseQA {
  return Candidate{},ErrNotReady
 }
 steps:=append([]largegraph.Step(nil),c.Steps...)
 return Candidate{Domain:c.Domain,RawQuestion:c.RawQuestion,Anchor:c.Anchor,Steps:steps},nil
}

// RunSynthetic is usable exclusively by a test graph; a real FreebaseQA
// source is hard-blocked even if a caller fabricates fields or passes a graph.
func RunSynthetic(c Candidate,g Resolver)(largegraph.Resolution,error){
 plan,err:=Prepare(c)
 if err!=nil{return largegraph.Resolution{},err}
 if g==nil{return largegraph.Resolution{},ErrNotReady}
 input:=append([]largegraph.Step(nil),plan.Steps...)
 answer,err:=g.Resolve(plan.Anchor,input)
 if err!=nil{return largegraph.Resolution{},err}
 if answer.Steps!=len(input)||
  answer.Candidates!=len(answer.Targets)||
  answer.UniqueTarget!=(len(answer.Targets)==1) {
  return largegraph.Resolution{},ErrMalformed
 }
 if len(answer.Targets)>largegraph.MaxFrontier{
  return largegraph.Resolution{},ErrBudget
 }
 output:=append([]string(nil),answer.Targets...)
 sorted:=append([]string(nil),output...)
 sort.Strings(sorted)
 for i,target:=range sorted {
  if !validText(target,largegraph.MaxFieldBytes)||
   (i>0&&target==sorted[i-1]){
   return largegraph.Resolution{},ErrMalformed
  }
 }
 answer.Targets=sorted
 return answer,nil
}
