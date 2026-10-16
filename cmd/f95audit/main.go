// f95audit verifies source blobs against exact repository Git trees.
// It makes no model or network calls and does not assert scientific novelty.
package main

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "os"
 "os/exec"
 "strings"

 "github.com/spoonman136668-ai/forge/optimizerstages"
)

const baseline="dce583ff9e1be25effe2d7c1988a92c0ede6780e"
func git(args ...string)([]byte,error){
 c:=exec.Command("git",args...)
 c.Env=append(os.Environ(),"GIT_CONFIG_NOSYSTEM=1","GIT_OPTIONAL_LOCKS=0")
 return c.Output()
}
func hash(v []byte)string{
 h:=sha256.Sum256(v);return hex.EncodeToString(h[:])
}
func marker(s string)string{return hash([]byte("F95-CANONICAL-SOURCE-REHEARSAL:"+s))}
func validate()error{
 headBytes,err:=git("rev-parse","HEAD")
 if err!=nil{return fmt.Errorf("F95_GIT_HEAD: %w",err)}
 head:=strings.TrimSpace(string(headBytes))
 if len(head)!=40||head==baseline{return fmt.Errorf("F95_UNEXPECTED_GIT_HEAD")}
 if expected:=os.Getenv("GITHUB_SHA");expected!=""&&expected!=head{
  return fmt.Errorf("F95_GITHUB_SHA_MISMATCH")
 }
 if _,err:=git("merge-base","--is-ancestor",baseline,head);err!=nil{
  return fmt.Errorf("F95_PROTECTED_PARENT_NOT_ANCESTOR")
 }
 roles:=[]struct{parent,candidate string}{
  {"genenv/genenv.go","noveltymechanisms/f95_representation.go"},
  {"promptlineage/lineage.go","noveltymechanisms/f95_consumer.go"},
  {"genenv/genenv_test.go","noveltymechanisms/f95_environment_test.go"},
 }
 var p,c [3][]byte
 for i,r:=range roles{
  p[i],err=git("show",baseline+":"+r.parent)
  if err!=nil{return fmt.Errorf("F95_PARENT_BLOB_MISSING_%d",i)}
  // The new implementation must be genuinely added after the frozen
  // baseline, not a renamed or claimed hash of an existing target file.
  if _,oldErr:=git("cat-file","-e",baseline+":"+r.candidate);oldErr==nil{
   return fmt.Errorf("F95_CANDIDATE_EXISTED_AT_FROZEN_BASELINE")
  }
  c[i],err=git("show",head+":"+r.candidate)
  if err!=nil{return fmt.Errorf("F95_NEW_GIT_BLOB_MISSING_%d",i)}
 }
 f:=optimizerstages.F94Freeze{
  Schema:optimizerstages.F94FreezeSchema,Lane:"Wingless",SourceSHA:baseline,Epoch:1,
  PromptPlanSHA256:marker("prompt-plan"),
  EnvironmentPlanSHA256:marker("env-plan"),
  TrainingHistorySHA256:marker("history"),
  ParentRepresentationSHA256:hash(p[0]),
  ParentConsumerSHA256:hash(p[1]),
  ParentTestEnvironmentSHA256:hash(p[2]),
  FrozenTestProtocolSHA256:marker("test-protocol"),
  FrozenControlsSHA256:[]string{marker("control-one"),marker("control-two")},
  MinimumHistoricalDistance:1,MaximumProposals:4,
 }
 claim:=optimizerstages.F94ImplementationClaim{
  Generator:"DGM/GenEnv",
  GeneratorCandidateSHA256:marker("UNTESTED-GENERATOR-LINK-ONLY"),
  NewRepresentationSHA256:hash(c[0]),
  NewConsumerSHA256:hash(c[1]),
  NewTestEnvironmentSHA256:hash(c[2]),
 }
 audit,err:=optimizerstages.AuditF95SourceBytes(f,
  optimizerstages.F94FreezeDigest(f),claim,
  optimizerstages.F95ThreeSourceArtifacts{
   Representation:optimizerstages.F95ArtifactBytes{Parent:p[0],Candidate:c[0]},
   Consumer:optimizerstages.F95ArtifactBytes{Parent:p[1],Candidate:c[1]},
   TestEnvironment:optimizerstages.F95ArtifactBytes{Parent:p[2],Candidate:c[2]},
  })
 if err!=nil{return fmt.Errorf("F95_AST_ROLE_SOURCE_AUDIT: %w",err)}
 if !audit.SourceBytesMatchClaims||!audit.AllThreeGoASTShapesChanged||
  audit.VerifiedExternalGitObjectCustody||
  audit.GeneratedCandidateScientificallyNovel||
  audit.RealProspectiveHoldoutQualified||
  audit.ScientificCausalGainAccepted||
  audit.DreamParetoPromotionAuthorized||
  audit.ThetaEvolveTrainingEnabled||
  audit.ScientificOriginalDispatchAuthorized||
  audit.AcceptedReferenceMutation{return fmt.Errorf("F95_UNEARNED_SCIENTIFIC_AUTHORITY")}
 result:=struct{
  Schema string `json:"schema"`
  Baseline string `json:"baseline"`
  Head string `json:"head"`
  RealGitObjectsRead bool `json:"real_git_objects_read"`
  F94GeneratorLineageIndependentlyPinned bool `json:"f94_generator_lineage_independently_pinned"`
  NovelCodeScientificResultsAccepted bool `json:"novel_code_scientific_results_accepted"`
  Audit optimizerstages.F95SourceReview `json:"audit"`
 }{"forge.f95.exact-git-blob-readback.v1",baseline,head,true,false,false,audit}
 output,err:=json.MarshalIndent(result,"","  ")
 if err!=nil{return err}
 fmt.Println(string(output))
 return nil
}
func main(){
 if err:=validate();err!=nil{
  fmt.Fprintln(os.Stderr,"F95_SOURCE_GATE_BLOCKED:",err)
  os.Exit(1)
 }
}
