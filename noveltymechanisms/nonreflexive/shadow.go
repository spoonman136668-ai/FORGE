package nonreflexive

import (
 "bytes"
 "errors"
 "fmt"
 "strings"

 "github.com/spoonman136668-ai/forge/noveltymechanisms/devroles"
 "github.com/spoonman136668-ai/forge/noveltymechanisms/groundingaudit"
 "github.com/spoonman136668-ai/forge/noveltymechanisms/langroles"
 "github.com/spoonman136668-ai/forge/noveltymechanisms/largegraph"
)

var ErrAudit = errors.New("FORGE_F104O_TRAIN_ONLY_SHADOW_SOURCE_DENIED")

type Comparison struct {
 Hops int `json:"hops"`
 OriginalRows int `json:"original_rows"`
 Baseline groundingaudit.Cohort `json:"f103o_baseline"`
 Shadow groundingaudit.Cohort `json:"f104o_nonreflexive_shadow"`
 EligibleInverseTwoHop int `json:"eligible_inverse_two_hop"`
 RootWasPresent int `json:"root_was_present"`
 RootRemoved int `json:"root_removed"`
 RootOnlyBecomesEmpty int `json:"root_only_becomes_empty"`
 NewExactFromNonexact int `json:"new_exact_from_nonexact"`
 LostExactFromExact int `json:"lost_exact_from_exact"`
 UnchangedExact int `json:"unchanged_exact"`
 BaselineVsShadowDisagreement int `json:"baseline_vs_shadow_disagreement"`
}

type category uint8
const (
 abstain category=iota
 budget
 empty
 exact
 partial
 disjoint
)

func score(targets []string, gold map[string]struct{}) category {
 if len(targets)==0{return empty}
 hit:=0
 for _,s:=range targets {
  if _,ok:=gold[s];ok{hit++}
 }
 if hit==len(targets)&&hit==len(gold){return exact}
 if hit!=0{return partial}
 return disjoint
}
func add(c *groundingaudit.Cohort,kind category,targetCount int){
 switch kind {
 case abstain: c.ParserAbstained++
 case budget: c.GraphBudgetRefused++
 case empty: c.GraphMissingOrNoTargets++
 case exact: c.GraphResolvedExactSet++
 case partial: c.GraphResolvedPartialOverlap++
 case disjoint: c.GraphResolvedDisjoint++
 }
 if kind!=abstain {c.Parsed++}
 if kind>=exact && targetCount>1{c.GraphResolvedAmbiguous++}
}

func gold(raw []byte)(map[string]struct{},error){
 if len(raw)==0{return nil,ErrAudit}
 values:=bytes.Split(raw,[]byte{124})
 m:=make(map[string]struct{},len(values))
 for _,v:=range values {
  if len(v)==0{return nil,ErrAudit}
  for _,c:=range v{if c==0||c==13||c==10{return nil,ErrAudit}}
  k:=string(v)
  if _,ok:=m[k];ok{return nil,ErrAudit}
  m[k]=struct{}{}
 }
 return m,nil
}

// Compare evaluates the entire unchanged original public TRAIN cohort.
// Baseline is independently rechecked against the exact F103-O evaluator.
// Each source row retains its original denominator regardless of outcome.
// Gold answers are touched only here, NEVER in frozen parser or proposal.
func Compare(index *largegraph.Index,raw []byte,hops,expectedRows int)(Comparison,error){
 var denied Comparison
 if index==nil||len(raw)==0||len(raw)>groundingaudit.MaxTrainBytes||
  expectedRows<1||expectedRows>groundingaudit.MaxTrainRows||
  (hops!=2&&hops!=3) {return denied,ErrAudit}
 prior,err:=groundingaudit.Evaluate(index,raw,hops,expectedRows)
 if err!=nil{return denied,err}
 if raw[len(raw)-1]==10{raw=raw[:len(raw)-1]}
 rows:=bytes.Split(raw,[]byte{10})
 if len(rows)!=expectedRows{return denied,ErrAudit}
 report:=Comparison{
  Hops:hops,OriginalRows:expectedRows,
  Baseline:groundingaudit.Cohort{Hops:hops,SourceRows:expectedRows},
  Shadow:groundingaudit.Cohort{Hops:hops,SourceRows:expectedRows},
 }
 for _,row:=range rows{
  n:=bytes.IndexByte(row,9)
  if n<=0||n>=len(row)-1||bytes.IndexByte(row[n+1:],9)>=0 {
   return denied,ErrAudit
  }
  // EXACT parse is question-only; gold never reaches parser or proposal.
  p:=devroles.Parse(string(row[:n]),hops)
  goldSet,e:=gold(row[n+1:])
  if e!=nil{return denied,e}
  report.Baseline.GoldAnswerMembers+=int64(len(goldSet))
  report.Shadow.GoldAnswerMembers+=int64(len(goldSet))
  if p.Status==langroles.Abstained {
   if p.Root!=""||len(p.Steps)!=0{return denied,ErrAudit}
   add(&report.Baseline,abstain,0)
   add(&report.Shadow,abstain,0)
   continue
  }
  if p.Status!=langroles.Matched||p.Root==""||len(p.Steps)!=hops{return denied,ErrAudit}
  result,e:=index.Resolve(p.Root,p.Steps)
  if errors.Is(e,largegraph.ErrBudget){
   if len(result.Targets)!=0{return denied,ErrAudit}
   add(&report.Baseline,budget,0)
   add(&report.Shadow,budget,0)
   continue
  }
  if e!=nil{return denied,fmt.Errorf("F104O_ORIGINAL_GRAPH_DENIED: %w",e)}
  if result.Candidates!=len(result.Targets){return denied,ErrAudit}
  base:=score(result.Targets,goldSet)
  proposed,d:=Propose(p.Root,p.Steps,result.Targets)
  changed:=score(proposed,goldSet)
  add(&report.Baseline,base,len(result.Targets))
  add(&report.Shadow,changed,len(proposed))
  if d.EligibleInverseTwoHop{report.EligibleInverseTwoHop++}
  if d.RootWasPresent{report.RootWasPresent++}
  if d.RootRemoved{report.RootRemoved++}
  if d.BecomesEmpty{report.RootOnlyBecomesEmpty++}
  if base!=changed{report.BaselineVsShadowDisagreement++}
  if base!=exact&&changed==exact{report.NewExactFromNonexact++}
  if base==exact&&changed!=exact{report.LostExactFromExact++}
  if base==exact&&changed==exact{report.UnchangedExact++}
 }
 if !report.Baseline.Valid()||!report.Shadow.Valid()||
  report.Baseline!=prior||report.RootWasPresent!=report.RootRemoved||
  report.RootRemoved>report.EligibleInverseTwoHop||
  report.RootOnlyBecomesEmpty>report.RootRemoved||
  report.BaselineVsShadowDisagreement>report.RootRemoved||
  report.NewExactFromNonexact+report.UnchangedExact!=report.Shadow.GraphResolvedExactSet||
  report.LostExactFromExact+report.UnchangedExact!=report.Baseline.GraphResolvedExactSet {
  return denied,ErrAudit
 }
 return report,nil
}

func SyntheticGraph(rows ...string)(*largegraph.Index,error){
 return largegraph.Compile([]byte(strings.Join(rows,string([]byte{10}))+string([]byte{10})))
}
