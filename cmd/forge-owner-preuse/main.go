// forge-owner-preuse is the existing-owner call-site adapter to R30's
// local write-before-first-use primitive. It never authorizes research.
package main

import (
 "bytes"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"
 "path/filepath"

 "github.com/spoonman136668-ai/forge/originalclaim"
)

var ErrR32=errors.New("FORGE_R32_OWNER_FIRST_USE_AUTHORITY_NOT_INDEPENDENTLY_QUALIFIED")
const MaxR32Input=16384

type Report struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 ExperimentID string `json:"experiment_id"`
 SourceCommitSHA string `json:"source_commit_sha"`
 LocalFirstUseClaimVerified bool `json:"local_first_use_claim_verified"`
 SignedOwnerPredecisionVerified bool `json:"signed_owner_predecision_verified"`
 IndependentSignerDeploymentVerified bool `json:"independent_signer_deployment_verified"`
 ExternalMonotonicFirstUseCASVerified bool `json:"external_monotonic_first_use_cas_verified"`
 GenuineRandomizationVerified bool `json:"genuine_randomization_verified"`
 ScientificExecutionAuthorized bool `json:"scientific_execution_authorized"`
 ScientificImprovementEstablished bool `json:"scientific_improvement_established"`
 OriginalsExecuted uint64 `json:"originals_executed"`
}
func readExact[T any](path string)(T,error){
 var zero T
 if !filepath.IsAbs(path){return zero,ErrR32}
 st,err:=os.Lstat(path)
 if err!=nil||!st.Mode().IsRegular()||st.Size()<1||st.Size()>MaxR32Input{return zero,ErrR32}
 raw,err:=os.ReadFile(path)
 if err!=nil||len(raw)<1||len(raw)>MaxR32Input{return zero,ErrR32}
 d:=json.NewDecoder(bytes.NewReader(raw))
 d.DisallowUnknownFields()
 var x T
 if d.Decode(&x)!=nil||d.Decode(new(any))!=io.EOF{return zero,ErrR32}
 canonical,err:=json.Marshal(x)
 if err!=nil||!(bytes.Equal(raw,canonical)||bytes.Equal(raw,append(canonical,'\n'))){
  return zero,ErrR32
 }
 return x,nil
}

// The owner must have ALREADY acquired genuinely external single-use
// authority before using this local record-keeping helper. A green exit
// means exact signed bytes and one local attempt were durably retained,
// and specifically NEVER constitutes permission to dispatch a worker.
func run(args []string,out io.Writer)(Report,error){
 var zero Report
 f:=flag.NewFlagSet("forge-owner-preuse",flag.ContinueOnError)
 f.SetOutput(io.Discard)
 claimPath:=f.String("claim","","absolute file containing frozen owner claim")
 signedPath:=f.String("signed-predecision","","absolute owner-and-witness signed choice")
 pinsPath:=f.String("independent-pins","","absolute external operator pinned identities")
 journal:=f.String("journal-dir","","existing trusted per-owner local first-use journal")
 lane:=f.String("expected-lane","","Wingless or Yggdrasil")
 exp:=f.String("expected-experiment","","exact frozen original ID")
 source:=f.String("expected-source-commit","","exact 40-hex immutable source commit")
 if f.Parse(args)!=nil||f.NArg()!=0||
  (*lane!="Wingless"&&*lane!="Yggdrasil")||*exp==""||*source==""||
  !filepath.IsAbs(*journal)||*claimPath==*pinsPath||*signedPath==*pinsPath||*claimPath==*signedPath{
  return zero,ErrR32
 }
 claim,err:=readExact[originalclaim.Claim](*claimPath)
 if err!=nil{return zero,ErrR32}
 signed,err:=readExact[originalclaim.SignedPredecision](*signedPath)
 if err!=nil{return zero,ErrR32}
 pins,err:=readExact[originalclaim.PinnedTrust](*pinsPath)
 if err!=nil{return zero,ErrR32}
 if claim.Lane!=*lane||claim.ExperimentID!=*exp||claim.SourceCommitSHA!=*source||
  signed.Event.Lane!=*lane||signed.Event.ExperimentID!=*exp||
  signed.Event.SourceCommitSHA!=*source||originalclaim.VerifyPredecision(signed,claim,pins)!=nil{
  return zero,ErrR32
 }
 if originalclaim.ConsumeWithPredecision(*journal,claim,signed,pins)!=nil{
  return zero,ErrR32
 }
 _,state,err:=originalclaim.ReadPredecision(*journal,claim,pins)
 if err!=nil||!state.ClaimVerified||!state.PredecisionSigned||
  state.ScientificExecutionAuthorized||state.IndependentExternalFirstUseVerified{
  return zero,ErrR32
 }
 report:=Report{Schema:"forge.original.r32-owner-local-preuse-record.v1",
  Lane:claim.Lane,ExperimentID:claim.ExperimentID,
  SourceCommitSHA:claim.SourceCommitSHA,
  LocalFirstUseClaimVerified:true,SignedOwnerPredecisionVerified:true}
 raw,err:=json.Marshal(report)
 if err!=nil{return zero,ErrR32}
 if _,err=out.Write(append(raw,'\n'));err!=nil{return zero,ErrR32}
 return report,nil
}
func main(){
 if _,err:=run(os.Args[1:],os.Stdout);err!=nil{
  fmt.Fprintln(os.Stderr,ErrR32)
  os.Exit(1)
 }
}
