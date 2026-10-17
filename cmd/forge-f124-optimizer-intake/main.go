// forge-f124-optimizer-intake binds existing FORGE optimizer packages to real,
// SHA-256-pinned F124 TRAIN evidence. It does NOT generate or accept science.
package main

import (
 "crypto/sha1"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "os"
 "path/filepath"

 "github.com/spoonman136668-ai/forge/evoportfolio"
 "github.com/spoonman136668-ai/forge/genenv"
 "github.com/spoonman136668-ai/forge/promptlineage"
)

const (
 schema="forge.research.f124m.authentic-training-optimizer-advisory.v1"
 freezeBlob="e1e878a26fefb86278f62c98f3aef2959a646520"
 jSHA="d2e3a3bb89065e5dbb084ff0eb0601bcdef63e44774f330e5135e0728e9a2eda"
 iSHA="c97f51a04769caeadeee03889daf056cad38be826d18aada453a07371e71fb1e"
 originalSource="404ace81943d20cf34be13a2f1b7a0d31fc5180e"
)
var errIntake=errors.New("F124M_AUTHENTIC_TRAIN_INTAKE_QUARANTINED")
type measured struct {Pairs int `json:"pairs"`; Paired int `json:"paired_correct"`}
type armReport struct {Paired int `json:"frozen_original_train_paired_correct"`; Weight string `json:"frozen_weight_sha256"`; Strata map[string]measured `json:"strata"`}
type iLane struct {Lane string `json:"lane"`; Arms map[string]armReport `json:"arms"`}
type iReport struct {
 Schema string `json:"schema"`
 Parent string `json:"parent_original_source_head"`
 TrainSHA string `json:"original_train_weights_receipt_sha256"`
 CandidateSHA string `json:"authenticated_candidate_vectors_sha256"`
 WeightsUnchanged bool `json:"exact_original_weights_unchanged"`
 Retrained bool `json:"retraining_occurred"`
 Confirm int `json:"reserved_confirmation_examples_generated"`
 Promoted int `json:"optimizer_promotions"`
 Lanes []iLane `json:"lanes"`
}
type control struct {Paired int `json:"paired_correct"`; Work struct {
 EdgeScans int64 `json:"public_edge_scans"`
 RawBits int64 `json:"actual_raw_bit_comparisons"`
 } `json:"work"`}
type jLane struct {
 Lane string `json:"lane"`
 Selected string `json:"frozen_selected_arm"`
 BPaired int `json:"original_train_selected_B_pairs"`
 Controls map[string]control `json:"controls"`
}
type jReport struct {
 Schema string `json:"schema"`
 IHead string `json:"original_f124i_head"`
 ISHA string `json:"original_f124i_report_sha256"`
 HTrain string `json:"original_f124h_train_sha256"`
 Frozen bool `json:"original_B_weights_unchanged"`
 Confirm int `json:"reserved_confirmation_cases_generated"`
 Science bool `json:"independent_original_first_use"`
 Accepted int `json:"accepted_scientific_results"`
 Promoted int `json:"optimizer_promotions"`
 Lanes []jLane `json:"lanes"`
}
type laneOutput struct {
 Lane string `json:"lane"`
 HistoricalF124HScore int `json:"f124h_B_train_paired"`
 StrongestApproxBaseline int `json:"fixed_14of16_train_paired"`
 ExactPublicCeiling int `json:"fixed_16of16_train_paired"`
 NegativeVsBaseline bool `json:"learned_B_negative_vs_baseline"`
 HistoricalPortfolio evoportfolio.Decision `json:"evoportfolio_source_advisory"`
 Pareto evoportfolio.IslandParetoResult `json:"shinka_pareto_historical_advisory"`
 Environment genenv.Result `json:"genenv_untested_advisory"`
 Prompt promptlineage.Result `json:"promptbreeder_untested_advisory"`
 PolicySelection string `json:"dream_rsi_policy_selection"`
 Theta string `json:"theta_training"`
 ImplementedCandidatePrograms int `json:"new_executable_candidate_programs"`
 ProtectedInputs int `json:"protected_confirmation_inputs"`
}
type result struct {
 Schema string `json:"schema"`
 ParentSource string `json:"source_head"`
 FrozenSpecGitBlob string `json:"frozen_spec_git_blob"`
 JReportSHA256 string `json:"f124j_report_sha256"`
 IReportSHA256 string `json:"f124i_report_sha256"`
 EvidenceKind string `json:"evidence_kind"`
 Lanes []laneOutput `json:"lanes"`
 ScientificFirstUse bool `json:"scientific_first_use"`
 ProtectedInputs int `json:"protected_inputs"`
 AcceptedScience int `json:"scientific_acceptances"`
 NewOriginals int `json:"new_scientific_originals"`
 ModelCalls int `json:"api_or_codex_model_calls"`
 AcceptedRefMutations int `json:"accepted_ref_mutations"`
 OptimizerPromotions int `json:"optimizer_promotions"`
 ExternalPolicyWitnessQualified bool `json:"external_policy_witness_qualified"`
}
func shasum(b []byte) string {v:=sha256.Sum256(b);return hex.EncodeToString(v[:])}
func sha1id(s string)string{v:=sha1.Sum([]byte(s));return hex.EncodeToString(v[:])}
func pin(b []byte)string{return shasum(b)}
func freeze(root string) error {
 b,err:=os.ReadFile(filepath.Join(root,"reference","research-intake","f124m-authentic-optimizer-freeze.json"))
 if err!=nil{return err}
 h:=sha1.Sum(append(append([]byte(fmt.Sprintf("blob %d",len(b))),byte(0)),b...))
 if hex.EncodeToString(h[:])!=freezeBlob{return errIntake}
 var p struct {
  Schema string `json:"schema"`
  Status string `json:"status"`
  Parent string `json:"parent_head"`
  Authority map[string]bool `json:"authority"`
 }
 if err=json.Unmarshal(b,&p);err!=nil{return err}
 if p.Schema!="forge.research.f124m.authentic-development-optimizer-intake-freeze.v1"||
    p.Status!="PREIMPLEMENTATION_FROZEN"||p.Parent!=originalSource{return errIntake}
 for _,v:=range p.Authority {if !v{return errIntake}}
 return nil
}
func readVerified(path,expected string,v any)error{
 b,err:=os.ReadFile(path);if err!=nil{return err}
 if shasum(b)!=expected{return fmt.Errorf("%w:sha256:%s",errIntake,path)}
 if err=json.Unmarshal(b,v);err!=nil{return err}
 return nil
}
func validReports(j jReport,i iReport)bool{
 if j.Schema!="forge.research.f124j.public-resource-controls-and-confirmation-preflight.v1"||
 i.Schema!="forge.research.f124i.frozen-train-mechanism-resource-audit.v1"||
 j.ISHA!=iSHA ||j.HTrain!="3ce0356ad9c19aeb4557ffe0b138908707c65ab3ce4b6af952adbf9899988254"||
 !j.Frozen || j.Confirm!=0||j.Science||j.Accepted!=0||j.Promoted!=0||
 !i.WeightsUnchanged||i.Retrained||i.Confirm!=0||i.Promoted!=0||
 i.CandidateSHA!="12da879272212b899c6b942004ff38dc21ffa6bb20e7a81eac21d691746b474d"||
 len(j.Lanes)!=2||len(i.Lanes)!=2{return false}
 for n,lane:=range []string{"Wingless","Yggdrasil"}{
  if j.Lanes[n].Lane!=lane||i.Lanes[n].Lane!=lane||j.Lanes[n].Selected!="B"{return false}
  jlane:=j.Lanes[n];ilane:=i.Lanes[n]
  if jlane.BPaired!=ilane.Arms["B"].Paired ||
    jlane.Controls["16"].Paired!=48 ||
    jlane.Controls["14"].Paired<=jlane.BPaired ||
    jlane.Controls["12"].Paired>=jlane.Controls["14"].Paired||
    len(ilane.Arms["B"].Strata)!=5||len(ilane.Arms["A"].Strata)!=5{return false}
  total:=0
  for _,v:=range ilane.Arms["B"].Strata{if v.Pairs<1||v.Paired<0||v.Paired>v.Pairs{return false};total+=v.Pairs}
  if total!=48{return false}
 }
 return true
}
func scoreCandidate(lane string,n int,cid,family,cl string) evoportfolio.Candidate{
 // Derived candidate identifiers are NOT independent Git source attestations.
 identity:=originalSource+"|"+lane+"|"+cid
 return evoportfolio.Candidate{ID:cid,Family:family,Signature:cid,SourceSHA:sha1id(identity),
  ScreenSHA:shasum([]byte(identity+"|"+fmt.Sprint(n)+"|"+jSHA)),
  HistoricalClass:cl,Score:int64(n),ScreenCompute:1,SealedCompute:1}
}
func runLane(j jLane,i iLane)(laneOutput,error){
 var zero laneOutput
 lane:=j.Lane
 if lane!="Wingless"&&lane!="Yggdrasil"{return zero,errIntake}
 // C16 is an *ineligible algorithmic ceiling*, the A and B negatives stay
 // archived. Evoportfolio and Pareto are advisory and use abstract slot units,
 // NEVER claims of matched inference computation.
 candidates:=[]evoportfolio.Candidate{
  scoreCandidate(lane,i.Arms["A"].Paired,"ArmA","learned","NEGATIVE"),
  scoreCandidate(lane,j.BPaired,"ArmB","learned","NEGATIVE"),
  scoreCandidate(lane,j.Controls["12"].Paired,"C12","fixed","NEGATIVE"),
  scoreCandidate(lane,j.Controls["14"].Paired,"C14","fixed","MIXED"),
  scoreCandidate(lane,j.Controls["16"].Paired,"C16","ceiling","CONSUMED_INDETERMINATE"),
 }
 f:=evoportfolio.Frozen{Schema:evoportfolio.Schema,Lane:lane,Epoch:124,HistoricalSourceSHA:jSHA,
  MaxScreenCompute:5,MaxSealedCompute:2,MaxFinalists:2,MaxPerFamily:1,MaxScreensPerFamily:5,
  Candidates:candidates}
 fpin:=evoportfolio.Digest(f)
 decision,err:=evoportfolio.Select(f,fpin);if err!=nil{return zero,err}
 lineages:=make([]evoportfolio.IslandLineage,0,len(candidates))
 for _,c:=range candidates{
  lineages=append(lineages,evoportfolio.IslandLineage{CandidateID:c.ID,
   Family:c.Family,IslandID:c.Family,SourceSHA:c.SourceSHA,ScreenSHA:c.ScreenSHA,
   HistoricalClass:c.HistoricalClass,OperatorSHA256:shasum([]byte("F124M|"+c.ID+"|"+lane))})
 }
 par:=evoportfolio.ParetoFreeze{Schema:evoportfolio.ParetoFreezeSchema,Lane:lane,
  PortfolioSHA256:fpin,LineageSHA256:evoportfolio.DigestIslandLineage(lineages),
  BaselineID:"C14",Islands:[]string{"ceiling","fixed","learned"},
  MaxFinalists:2,MaxIslandFinalists:1,FixedBeforeScreening:true,HistoricalOnly:true}
 pareto,err:=evoportfolio.ParetoAdvisory(f,fpin,par,evoportfolio.DigestParetoFreeze(par),lineages)
 if err!=nil{return zero,err}
 if decision.ScientificAccepted||decision.DispatchAuthorized||decision.AcceptedRefMutation||
    pareto.ScientificAccepted||pareto.DispatchAuthorized||pareto.AcceptedRefMutation||
    pareto.ImprovementScientificallyEstablished||pareto.MutationRuntimeActivated{return zero,errIntake}
 // Derive real training-only challenge coordinates from original B/A error
 // strata, not made-up positive discoveries. Shape indices are predeclared.
 errvec:=func(a armReport) []int64 {
  names:=[]string{"parallel_multiedge","late_cross_route","near_collision"}
  v:=make([]int64,0,3)
  for _,name:=range names{
   x:=a.Strata[name]
   n:=int64(x.Pairs-x.Paired);if n>3{n=3}
   v=append(v,n)
  }
  return v
 }
 aVec,bVec:=errvec(i.Arms["A"]),errvec(i.Arms["B"])
 base:=[]int64{1,1,1}
 // A validation requirement, not a silent repair if a future history changes.
 equal:=func(a,b []int64)bool{for n:=range a{if a[n]!=b[n]{return false}};return true}
 if equal(aVec,bVec)||equal(aVec,base)||equal(bVec,base){return zero,errIntake}
 history:=genenv.History{Schema:genenv.HistorySchema,Lane:lane,SourceSHA:originalSource,
  Records:[]genenv.Record{
   {Sequence:1,EvidenceSHA256:i.Arms["A"].Weight,TrainingOnly:true,Classification:"NEGATIVE",Vector:aVec},
   {Sequence:2,EvidenceSHA256:i.Arms["B"].Weight,TrainingOnly:true,Classification:"NEGATIVE",Vector:bVec},
  }}
 // Source weights are SHA256 and exact original report contains them; no
 // accepted independent outcome is fabricated from a development score.
 hpin:=genenv.HistoryDigest(history)
 env:=genenv.Frozen{Schema:genenv.FrozenSchema,Lane:lane,SourceSHA:originalSource,
  Epoch:124,HistorySHA256:hpin,Base:base,MaxLevel:3,MaxCandidates:2,MaxOperations:3,
  Requests:[]genenv.Request{
   {ID:"stress-parallel",Changes:[]genenv.Change{{Index:0,Delta:1}}},
   {ID:"stress-cross",Changes:[]genenv.Change{{Index:1,Delta:1}}},
  }}
 generated,err:=genenv.Generate(env,genenv.FrozenDigest(env),history,hpin);if err!=nil{return zero,err}
 prompt:=promptlineage.Frozen{Schema:promptlineage.Schema,Lane:lane,Epoch:124,SourceSHA:originalSource,
  Parent:"test causal competition readout",Vocabulary:[]string{"parallel","balanced"},
  MaxOperations:2,Operations:[]promptlineage.Operation{
   {Kind:"replace",Position:2,Replacement:"parallel"},
   {Kind:"replace",Position:1,Replacement:"balanced"},
  }}
 prompts,err:=promptlineage.Generate(prompt,promptlineage.Digest(prompt));if err!=nil{return zero,err}
 if generated.ScientificAccepted||generated.DispatchAuthorized||generated.SealedHoldoutConsumed||
 prompts.ScientificAccepted||prompts.DispatchAuthorized||prompts.SealedEvaluationConsumed ||
 generated.NegativeCount!=2||len(generated.Candidates)!=2||len(prompts.Candidates)!=2{return zero,errIntake}
 // A Pareto finalist is not an accepted policy or a new source-level mechanism.
 return laneOutput{Lane:lane,HistoricalF124HScore:j.BPaired,
  StrongestApproxBaseline:j.Controls["14"].Paired,ExactPublicCeiling:j.Controls["16"].Paired,
  NegativeVsBaseline:true,HistoricalPortfolio:decision,Pareto:pareto,
  Environment:generated,Prompt:prompts,
  PolicySelection:"DREAM_RSI_AND_PARETO_PROSPECTIVE_SELECTION_BLOCKED",
  Theta:"BLOCKED_NO_INDEPENDENTLY_ACCEPTED_NEW_RESULTS"},nil
}
func execute(root,jpath,ipath string)(result,error){
 var out result
 if err:=freeze(root);err!=nil{return out,err}
 var j jReport;var i iReport
 if err:=readVerified(jpath,jSHA,&j);err!=nil{return out,err}
 if err:=readVerified(ipath,iSHA,&i);err!=nil{return out,err}
 if !validReports(j,i){return out,errIntake}
 out=result{Schema:schema,ParentSource:originalSource,
  FrozenSpecGitBlob:freezeBlob,JReportSHA256:jSHA,IReportSHA256:iSHA,
  EvidenceKind:"AUTHENTIC_ORIGINAL_TRAIN_ONLY_NOT_PROSPECTIVE",
  Lanes:make([]laneOutput,0,2)}
 for n:=range j.Lanes{v,err:=runLane(j.Lanes[n],i.Lanes[n]);if err!=nil{return result{},err};out.Lanes=append(out.Lanes,v)}
 return out,nil
}
func main(){
 root:=flag.String("root",".","repository root")
 j:=flag.String("f124j-report","","original real F124J json")
 i:=flag.String("f124i-report","","original real F124I json")
 output:=flag.String("output","","new JSON receipt path")
 flag.Parse()
 if *j==""||*i==""||*output==""{fmt.Fprintln(os.Stderr,errIntake);os.Exit(2)}
 result,err:=execute(*root,*j,*i)
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 bytes,err:=json.MarshalIndent(result,"","  ");if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 bytes=append(bytes,byte(10))
 f,err:=os.OpenFile(*output,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 if _,err=f.Write(bytes);err!=nil{f.Close();fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 if err=f.Close();err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 fmt.Println("F124M_DUAL_LANE_ORIGINAL_TRAIN_OPTIMIZER_ADVISORY_SHA256="+pin(bytes))
}
