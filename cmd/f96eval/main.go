// f96eval verifies that the evaluated suite is byte-identical to its Git
// commit FROZEN BEFORE THE EVALUATOR SOURCE WAS ADDED, then prints all control
// results. No scientific owner, external witness, live research or credentials.
package main

import (
 "bytes"
 "encoding/json"
 "errors"
 "fmt"
 "os"
 "os/exec"
 "strings"

 "github.com/spoonman136668-ai/forge/noveltyeval"
)
var ErrSource=errors.New("FORGE_F96_FROZEN_SOURCE_IDENTITY_MISMATCH")
func git(args ...string)([]byte,error){
 cmd:=exec.Command("git",args...)
 cmd.Env=append(os.Environ(),"GIT_CONFIG_NOSYSTEM=1","GIT_OPTIONAL_LOCKS=0")
 return cmd.Output()
}
func run()error{
 head,err:=git("rev-parse","HEAD")
 if err!=nil{return err}
 sha:=strings.TrimSpace(string(head))
 if len(sha)!=40||sha==noveltyeval.FrozenBeforeEvaluationCommit{
  return ErrSource
 }
 if expected:=os.Getenv("GITHUB_SHA");expected!=""&&sha!=expected{
  return fmt.Errorf("%w:action_head",ErrSource)
 }
 if _,err:=git("merge-base","--is-ancestor",noveltyeval.FrozenBeforeEvaluationCommit,sha);err!=nil{
  return fmt.Errorf("%w:not_descendant",ErrSource)
 }
 if _,err:=git("merge-base","--is-ancestor",noveltyeval.BaseF95Commit,sha);err!=nil{
  return fmt.Errorf("%w:missing_f95_source",ErrSource)
 }
 const file="noveltyeval/f96_cases.json"
 frozen,err:=git("show",noveltyeval.FrozenBeforeEvaluationCommit+":"+file)
 if err!=nil{return fmt.Errorf("%w:git_read",ErrSource)}
 current,err:=git("show",sha+":"+file)
 if err!=nil||!bytes.Equal(frozen,current){
  return fmt.Errorf("%w:head_fixture_changed",ErrSource)
 }
 working,err:=os.ReadFile(file)
 if err!=nil||!bytes.Equal(frozen,working){
  return fmt.Errorf("%w:working_fixture_changed",ErrSource)
 }
 report,err:=noveltyeval.EvaluateFrozen(frozen)
 if err!=nil{return err}
 if report.FixtureFreezeCommit!=noveltyeval.FrozenBeforeEvaluationCommit||
  report.FixtureCaseCount!=16||!report.EveryCaseRetained||
  !report.EquivalentReferenceIsRequiredControl||
  report.AuthenticOriginalFirstUse||report.AnyScientificSuperiorityEstablished||
  report.DreamParetoPromotionAuthorized||report.ThetaEvolveAcceptedTrainingEnabled||
  report.AcceptedScientificReferenceMutation||report.ScientificDispatchAuthorized{
  return fmt.Errorf("%w:false_evidence",ErrSource)
 }
 envelope:=struct{
  Schema string `json:"schema"`
  EvaluatedSourceSHA string `json:"evaluated_source_sha"`
  FixtureCommitSHA string `json:"fixture_commit_sha"`
  ExactCommitFixturesRetained bool `json:"exact_commit_fixtures_retained"`
  IndependentlyPreparedSealedScience bool `json:"independently_prepared_sealed_science"`
  Report noveltyeval.Report `json:"report"`
 }{"forge.optimizer.f96.exact-head-source-report.v1",
  sha,noveltyeval.FrozenBeforeEvaluationCommit,true,false,report}
 enc:=json.NewEncoder(os.Stdout);enc.SetIndent("","  ")
 return enc.Encode(envelope)
}
func main(){
 if err:=run();err!=nil{
  fmt.Fprintln(os.Stderr,"F96_GATE_BLOCKED:",err)
  os.Exit(1)
 }
}
