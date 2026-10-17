// Package groundingaudit evaluates frozen, source-authenticated TRAIN labels
// against the already-frozen F102 typed paths on a separate F100 graph index.
// This is PUBLIC DEVELOPMENT ONLY: never prospective scientific first-use.
package groundingaudit

import (
 "bytes"
 "errors"
 "fmt"
 "strings"

 "github.com/spoonman136668-ai/forge/noveltymechanisms/devroles"
 "github.com/spoonman136668-ai/forge/noveltymechanisms/langroles"
 "github.com/spoonman136668-ai/forge/noveltymechanisms/largegraph"
)

const MaxTrainBytes = 30 * 1024 * 1024
const MaxTrainRows = 300000

var ErrTrainSource = errors.New("FORGE_F103O_MALFORMED_TRAIN_SOURCE_DENIED")

type Cohort struct {
 Hops int `json:"hops"`
 SourceRows int `json:"source_rows"`
 Parsed int `json:"parsed"`
 ParserAbstained int `json:"parser_abstained"`
 GraphBudgetRefused int `json:"graph_budget_refused"`
 GraphMissingOrNoTargets int `json:"graph_missing_or_no_targets"`
 GraphResolvedExactSet int `json:"graph_resolved_exact_set"`
 GraphResolvedPartialOverlap int `json:"graph_resolved_partial_overlap"`
 GraphResolvedDisjoint int `json:"graph_resolved_disjoint"`
 GraphResolvedAmbiguous int `json:"graph_resolved_ambiguous"`
 GoldAnswerMembers int64 `json:"gold_answer_members"`
}

func (c Cohort) Valid() bool {
 categories:=c.ParserAbstained+c.GraphBudgetRefused+c.GraphMissingOrNoTargets+
  c.GraphResolvedExactSet+c.GraphResolvedPartialOverlap+c.GraphResolvedDisjoint
 return c.SourceRows>0 && categories==c.SourceRows &&
  c.Parsed==c.SourceRows-c.ParserAbstained &&
  c.GraphResolvedAmbiguous<=c.GraphResolvedExactSet+c.GraphResolvedPartialOverlap+c.GraphResolvedDisjoint
}

func goldSet(raw []byte)(map[string]struct{},error){
 if len(raw)==0{return nil,ErrTrainSource}
 values:=bytes.Split(raw,[]byte{'|'})
 result:=make(map[string]struct{},len(values))
 for _,v:=range values{
  if len(v)==0||bytes.ContainsAny(v,"\x00\r\n") {
   return nil,ErrTrainSource
  }
  k:=string(v)
  if _,exists:=result[k];exists{return nil,ErrTrainSource}
  result[k]=struct{}{}
 }
 return result,nil
}

// Evaluate reads exactly one complete original TRAIN cohort. The independently
// frozen parser sees only the question. Only this scorer inspects gold labels.
func Evaluate(index *largegraph.Index,data []byte,hops,expectedRows int)(Cohort,error){
 var denied Cohort
 if index==nil||len(data)==0||len(data)>MaxTrainBytes||
  expectedRows<1||expectedRows>MaxTrainRows||(hops!=2&&hops!=3) {
  return denied,ErrTrainSource
 }
 // Reject worktree normalization. Callers must provide immutable Git bytes.
 if data[len(data)-1]=='\n'{data=data[:len(data)-1]}
 rows:=bytes.Split(data,[]byte{'\n'})
 if len(rows)!=expectedRows {return denied,ErrTrainSource}
 c:=Cohort{Hops:hops,SourceRows:expectedRows}
 for _,row:=range rows{
  n:=bytes.IndexByte(row,'	')
  if n<=0||n+1>=len(row)||bytes.IndexByte(row[n+1:],'	')>=0 {
   return denied,ErrTrainSource
  }
  question:=string(row[:n])
  // No gold data crosses this call boundary.
  p:=devroles.Parse(question,hops)
  // Confirm *every* original answer row is valid, including abstentions.
  gold,err:=goldSet(row[n+1:])
  if err!=nil {return denied,err}
  c.GoldAnswerMembers+=int64(len(gold))
  if p.Status==langroles.Abstained{
   if p.Root!=""||len(p.Steps)!=0{return denied,ErrTrainSource}
   c.ParserAbstained++
   continue
  }
  if p.Status!=langroles.Matched||p.Root==""||len(p.Steps)!=hops {
   return denied,ErrTrainSource
  }
  c.Parsed++
  resolved,err:=index.Resolve(p.Root,p.Steps)
  if errors.Is(err,largegraph.ErrBudget){
   if len(resolved.Targets)!=0{return denied,ErrTrainSource}
   c.GraphBudgetRefused++
   continue
  }
  if err!=nil {return denied,fmt.Errorf("F103O_GRAPH_DENIED: %w",err)}
  if resolved.Candidates!=len(resolved.Targets){return denied,ErrTrainSource}
  if len(resolved.Targets)==0 {
   c.GraphMissingOrNoTargets++
   continue
  }
  if len(resolved.Targets)>1 {c.GraphResolvedAmbiguous++}
  hit:=0
  for _,target:=range resolved.Targets {
   if _,ok:=gold[target];ok{hit++}
  }
  if hit==len(gold)&&hit==len(resolved.Targets){
   c.GraphResolvedExactSet++
  }else if hit>0 {
   c.GraphResolvedPartialOverlap++
  }else {
   c.GraphResolvedDisjoint++
  }
 }
 if !c.Valid(){return denied,ErrTrainSource}
 return c,nil
}

// Only synthetic development fixtures call this; never use as a source
// of an accepted scientific claim or a training-policy reward.
func SyntheticSource(triples ...string)(*largegraph.Index,error) {
 return largegraph.Compile([]byte(strings.Join(triples,"\n")+"\n"))
}
