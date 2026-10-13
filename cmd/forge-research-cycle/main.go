// forge-research-cycle composes the EXISTING qualified portfolio, train-only
// Dream-RSI replay and bounded OS workers into one non-authorizing synthetic
// end-to-end integration acceptance. It never runs original science.
package main

import (
 "context"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"
 "path/filepath"
 "strings"

 "github.com/spoonman136668-ai/forge/evoportfolio"
 "github.com/spoonman136668-ai/forge/subprocesssupervisor"
)
var ErrBlocked=errors.New("FORGE_INTEGRATED_CYCLE_BLOCKED_NO_SCIENCE_AUTHORITY")

type lanePins struct{
 portfolio string
 history string
}
var frozenPins=map[string]lanePins{
 "Wingless":{portfolio:"88661c123beecb204326ec2f187ecc777e68cb01d5035a0aa533d0a5414a281b",
  history:"9a7f93b85f735af26b448b3a78485e81d6e2b08911c36b93bc7cc98ce2f3dd1e"},
 "Yggdrasil":{portfolio:"45a4bcad9cd8b019da4bcb675e84218c7301cad63df6fd6133b2a1e1a98db967",
  history:"4ae6e96ed144a9e355a6dd0fccc1d81c22fedcbfaf4ab784b6134fd3b9d6c4cc"},
}
type LaneProof struct{
 Lane string `json:"lane"`
 Policy string `json:"train_selected_policy"`
 HistoricalNegativeCount int `json:"historical_negative_count"`
 HistoricalMixedCount int `json:"historical_mixed_count"`
 PortfolioFrozenSHA256 string `json:"portfolio_frozen_sha256"`
 PolicyHistoryFrozenSHA256 string `json:"policy_history_frozen_sha256"`
 DecisionSHA256 string `json:"portfolio_decision_sha256"`
 NextCandidateID string `json:"next_candidate_id"`
 Finalists []string `json:"finalists"`
 Nonfinalists []string `json:"nonfinalists"`
 ScreenComputeSpent int64 `json:"screen_compute_spent"`
 SealedComputeReserved int64 `json:"sealed_compute_reserved"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 ScientificAccepted bool `json:"scientific_accepted"`
}
type Report struct{
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Lanes []LaneProof `json:"lanes"`
 Synthetic subprocesssupervisor.Result `json:"synthetic"`
 ResearchOriginalsExecuted int `json:"research_originals_executed"`
 ScientificExecutionAuthorized bool `json:"scientific_execution_authorized"`
 AcceptedRefMutation bool `json:"accepted_ref_mutation"`
}
func readFrozen[T any](path string)(T,error){
 var zero T
 info,err:=os.Lstat(path)
 if err!=nil||!info.Mode().IsRegular()||info.Size()<=0||info.Size()>65536{return zero,ErrBlocked}
 b,err:=os.ReadFile(path);if err!=nil{return zero,ErrBlocked}
 decoder:=json.NewDecoder(strings.NewReader(string(b)))
 decoder.DisallowUnknownFields()
 if err=decoder.Decode(&zero);err!=nil{return zero,ErrBlocked}
 var trailing any
 if err=decoder.Decode(&trailing);err!=io.EOF{return zero,ErrBlocked}
 return zero,nil
}
// plan refuses any changed frozen manifest, historical split, cross-lane
// portfolio source collisions or historical reinterpretation. It never
// authorizes science. Synthetic history is NEVER an authentic scientific
// result; it is an explicitly public offline integration fixture.
func plan(portfolioDir,historyDir string)([]LaneProof,error){
 if !filepath.IsAbs(portfolioDir)||!filepath.IsAbs(historyDir){return nil,ErrBlocked}
 out:=make([]LaneProof,0,2)
 crossLaneSource:=map[string]bool{}
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  lower:=strings.ToLower(lane)
  f,err:=readFrozen[evoportfolio.Frozen](filepath.Join(portfolioDir,lower+".json"))
  if err!=nil||f.Lane!=lane||evoportfolio.Digest(f)!=frozenPins[lane].portfolio{
   return nil,ErrBlocked
  }
  for _,candidate:=range f.Candidates{
   if crossLaneSource[candidate.SourceSHA]{return nil,ErrBlocked}
   crossLaneSource[candidate.SourceSHA]=true
  }
  history,err:=readFrozen[evoportfolio.PolicyFreeze](filepath.Join(historyDir,lower+"-synthetic-history.json"))
  if err!=nil||history.Lane!=lane||
   evoportfolio.ReplayPolicyDigest(history)!=frozenPins[lane].history{return nil,ErrBlocked}
  neg,mixed:=0,0
  for _,o:=range history.Candidates{
   if o.Class=="NEGATIVE"{neg++}
   if o.Class=="MIXED"{mixed++}
  }
  checked,err:=evoportfolio.PlanAfterReplay(history,frozenPins[lane].history,
   f,frozenPins[lane].portfolio)
  if err!=nil{return nil,ErrBlocked}
  decision,err:=evoportfolio.Select(f,frozenPins[lane].portfolio)
  if err!=nil||len(checked.Portfolio.OrderedFinalistIDs)==0||
   checked.Next.NextID!=checked.Portfolio.OrderedFinalistIDs[0]||
   checked.Policy.DispatchAuthorized||checked.Policy.AcceptedRefMutation||
   checked.Next.DispatchAuthorized||checked.Portfolio.ScientificAccepted||
   checked.Portfolio.DispatchAuthorized||checked.DispatchAuthorized||
   decision.DispatchAuthorized||decision.ScientificAccepted||
   decision.AcceptedRefMutation||len(decision.Archive)!=len(f.Candidates){
   return nil,ErrBlocked
  }
  out=append(out,LaneProof{Lane:lane,Policy:checked.Policy.SelectedPolicy,
   HistoricalNegativeCount:neg,HistoricalMixedCount:mixed,
   PortfolioFrozenSHA256:frozenPins[lane].portfolio,
   PolicyHistoryFrozenSHA256:frozenPins[lane].history,
   DecisionSHA256:checked.Portfolio.DecisionSHA256,
   NextCandidateID:checked.Next.NextID,
   Finalists:checked.Portfolio.OrderedFinalistIDs,
   Nonfinalists:checked.Portfolio.OrderedNonfinalistIDs,
   ScreenComputeSpent:decision.ScreenComputeSpent,
   SealedComputeReserved:decision.SealedComputeReserved})
 }
 if out[0].Lane==out[1].Lane{return nil,ErrBlocked}
 return out,nil
}
func run(ctx context.Context,args []string)(Report,error){
 var empty Report
 flags:=flag.NewFlagSet("forge-research-cycle",flag.ContinueOnError)
 ack:=flags.Bool("synthetic-only",false,"required non-authorizing offline execution")
 worker:=flags.String("worker-executable","","absolute already-built test worker binary")
 workerSHA:=flags.String("worker-sha256","","external SHA256 of exact test worker binary")
 dir:=flags.String("new-dir","","brand-new forge-synthetic-processes root")
 portfolio:=flags.String("portfolio-dir","","absolute directory containing pinned historical portfolio fixtures")
 history:=flags.String("history-dir","","absolute directory containing pinned synthetic policy histories")
 if err:=flags.Parse(args);err!=nil{return empty,err}
 if !*ack||flags.NArg()!=0||ctx==nil||ctx.Err()!=nil||
  !filepath.IsAbs(*dir)||filepath.Base(filepath.Clean(*dir))!="forge-synthetic-processes"||
  !filepath.IsAbs(*worker)||len(*workerSHA)!=64{return empty,ErrBlocked}
 lanes,err:=plan(*portfolio,*history)
 if err!=nil{return empty,err}
 validated,err:=subprocesssupervisor.Run(ctx,*worker,*workerSHA,*dir)
 if err!=nil||!validated.WinglessVerified||!validated.YggdrasilVerified||
  validated.RealScientificCycles!=0{return empty,ErrBlocked}
 return Report{Schema:"forge.integrated-research-cycle.v1",
  Mode:"HISTORICAL_POLICY_AND_SYNTHETIC_WORKERS_ONLY",
  Lanes:lanes,Synthetic:validated},nil
}
func main(){
 result,err:=run(context.Background(),os.Args[1:])
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 if err=json.NewEncoder(os.Stdout).Encode(result);err!=nil{
  fmt.Fprintln(os.Stderr,err);os.Exit(1)
 }
}
