package optimizerbridge

// ExternalTrainingObservation is the strictly segregated intake for experiments
// conducted outside FORGE's research-decision loop. It is NOT a dreamrsi.Envelope,
// signed original, randomized decision log, or provenance authority.
import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "strings"
)

const ExternalTrainingSchema="forge.optimizer.external-training-observations.v1"
const ExternalTrainingMode="READ_ONLY_GITHUB_TRAIN_ONLY_NOT_SIGNED_POLICY_HISTORY"
const MaxExternalTrainingBytes=96*1024
var ErrExternalTrainingEvidence=errors.New("FORGE_EXTERNAL_TRAINING_EVIDENCE_NOT_ELIGIBLE_FOR_AUTHORITY")

type ExternalStudy struct {
 Lane string `json:"lane"`
 Gate string `json:"gate"`
 ResearchPR uint64 `json:"research_pr"`
 EvidenceIssue uint64 `json:"evidence_issue"`
 RunID uint64 `json:"run_id"`
 HeadSHA string `json:"head_sha"`
 WorkflowPath string `json:"workflow_path"`
 ArtifactID uint64 `json:"artifact_id"`
 ArtifactName string `json:"artifact_name"`
 ArtifactSHA256 string `json:"artifact_sha256"`
 PreregistrationCommitSHA string `json:"preregistration_commit_sha"`
 CandidateCorrect int `json:"candidate_correct"`
 StrongestFairCorrect int `json:"strongest_fair_correct"`
 Total int `json:"total"`
 CandidateMethod string `json:"candidate_method"`
 StrongestFairMethod string `json:"strongest_fair_method"`
 ResearchFamily string `json:"research_family"`
 FailedChecks []string `json:"failed_checks"`
 ScientificGate string `json:"scientific_gate"`
 OriginalFirstUse bool `json:"original_first_use"`
 RandomizedOptimizerAssignment bool `json:"randomized_optimizer_assignment"`
 IndependentSourceCustody bool `json:"independent_source_custody"`
 ScientificAccepted bool `json:"scientific_accepted"`
}
type ExternalTrainingManifest struct {
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Studies []ExternalStudy `json:"studies"`
}
type ExternalTrainingAdvisory struct {
 Lane string `json:"lane"`
 Gate string `json:"gate"`
 ResearchFamily string `json:"research_family"`
 StudyRunID uint64 `json:"study_run_id"`
 StudyHeadSHA string `json:"study_head_sha"`
 ArtifactSHA256 string `json:"artifact_sha256"`
 TrainingOnlyNegative bool `json:"training_only_negative"`
 PositiveAccuracySignal bool `json:"positive_accuracy_signal"`
 CandidateCorrect int `json:"candidate_correct"`
 StrongestFairCorrect int `json:"strongest_fair_correct"`
 Total int `json:"total"`
 FailedChecks []string `json:"failed_checks"`
}
type ExternalTrainingReport struct {
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 SourceManifestSHA256 string `json:"source_manifest_sha256"`
 Observations []ExternalTrainingAdvisory `json:"observations"`
 WinglessCount int `json:"wingless_count"`
 YggdrasilCount int `json:"yggdrasil_count"`
 NegativeGateCount int `json:"negative_gate_count"`
 PositiveAccuracySignalCount int `json:"positive_accuracy_signal_count"`
 SourceRunArtifactMetadataRechecked bool `json:"source_run_artifact_metadata_rechecked"`
 ExperimentResultBytesIndependentlyVerified bool `json:"experiment_result_bytes_independently_verified"`
 SignedPolicyHistoryAvailable bool `json:"signed_policy_history_available"`
 DreamRSIProspectiveUseQualified bool `json:"dream_rsi_prospective_use_qualified"`
 ParetoPromotionAuthorized bool `json:"pareto_promotion_authorized"`
 ThetaAcceptedOutcomeUpdateAllowed bool `json:"theta_accepted_outcome_update_allowed"`
 PromptGenenvLiveDispatchAuthorized bool `json:"prompt_genenv_live_dispatch_authorized"`
 ScientificImprovementEstablished bool `json:"scientific_improvement_established"`
 ScientificAccepted bool `json:"scientific_accepted"`
 FirstUseConsumed bool `json:"first_use_consumed"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 AcceptedRefMutation bool `json:"accepted_ref_mutation"`
}
func externalHex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,r:=range s{if !(r>='0'&&r<='9'||r>='a'&&r<='f'){return false}}
 return true
}
func externalToken(s string)bool{
 if len(s)<2||len(s)>100{return false}
 for _,r:=range s{
  if !((r>='0'&&r<='9')||(r>='A'&&r<='Z')||(r>='a'&&r<='z')||r=='_'||r=='-'){return false}
 }
 return true
}
// reject repeated and mixed-case duplicate JSON keys at ANY depth, to avoid
// Go json.Unmarshal's normal "last value wins" ambiguity.
func externalUnambiguous(raw []byte)bool{
 d:=json.NewDecoder(bytes.NewReader(raw))
 var parse func(int)bool
 parse=func(depth int)bool{
  if depth>32{return false}
  token,err:=d.Token();if err!=nil{return false}
  kind,ok:=token.(json.Delim);if !ok{return true}
  if kind!='{'&&kind!='['{return false}
  seen:=map[string]bool{}
  for d.More(){
   if kind=='{'{
    key,err:=d.Token();if err!=nil{return false}
    name,ok:=key.(string);if !ok||len(name)==0||len(name)>128{return false}
    folded:=strings.ToLower(name)
    if seen[folded]{return false};seen[folded]=true
   }
   if !parse(depth+1){return false}
  }
  close,err:=d.Token()
  return err==nil&&close==json.Delim(map[json.Delim]rune{'{':'}','[':']'}[kind])
 }
 if !parse(0){return false}
 _,err:=d.Token()
 return errors.Is(err,io.EOF)
}
func validExternalStudy(s ExternalStudy,wantLane,wantGate string)bool{
 if s.Lane!=wantLane||s.Gate!=wantGate||s.ResearchPR<1||s.EvidenceIssue<1||
  s.RunID<1||s.ArtifactID<1||!externalHex(s.HeadSHA,40)||
  !externalHex(s.PreregistrationCommitSHA,40)||!externalHex(s.ArtifactSHA256,64)||
  s.Total<=0||s.Total>4096||s.CandidateCorrect<0||s.StrongestFairCorrect<0||
  s.CandidateCorrect>s.Total||s.StrongestFairCorrect>s.Total||
  s.ScientificGate!="FAILED_PREREGISTERED_TRAIN_ONLY"||
  s.OriginalFirstUse||s.RandomizedOptimizerAssignment||
  s.IndependentSourceCustody||s.ScientificAccepted||
  !externalToken(s.ArtifactName)||!externalToken(s.CandidateMethod)||
  !externalToken(s.StrongestFairMethod)||!externalToken(s.ResearchFamily)||
  s.CandidateMethod==s.StrongestFairMethod||len(s.FailedChecks)<1||len(s.FailedChecks)>8 {
  return false
 }
 prefix:="w-";if s.Lane=="Yggdrasil"{prefix="y-"}
 if !strings.HasPrefix(s.WorkflowPath,".github/workflows/"+prefix+strings.ToLower(s.Gate)+"-")||
  !strings.HasSuffix(s.WorkflowPath,".yml")||strings.Contains(s.WorkflowPath,"..")||
  strings.Contains(s.WorkflowPath,"\\")||len(s.WorkflowPath)>128{return false}
 permitted:=map[string]bool{"accuracy":true,"accuracy_gain":true,
   "family_nondegradation":true,"compute_parity":true,
   "mechanism_nondegradation":true,"paired_feature_ablation":true,
   "hash_gate_gain":true,"first_read_ablation":true}
 fail:=map[string]bool{}
 for _,x:=range s.FailedChecks{
  if !permitted[x]||fail[x]{return false}
  fail[x]=true
 }
 return true
}
// ObserveExternalTraining makes historical candidates accessible to the
// optimizerbridge *advisory research-intake* surface. It never converts them to
// independently signed Dream histories or to qualifying Pareto/Theta outcomes.
func ObserveExternalTraining(raw []byte)(ExternalTrainingReport,error){
 var zero ExternalTrainingReport
 if len(raw)==0||len(raw)>MaxExternalTrainingBytes||!externalUnambiguous(raw){
  return zero,ErrExternalTrainingEvidence
 }
 var m ExternalTrainingManifest
 dec:=json.NewDecoder(bytes.NewReader(raw));dec.DisallowUnknownFields()
 if dec.Decode(&m)!=nil||dec.Decode(new(any))!=io.EOF||
  m.Schema!=ExternalTrainingSchema||m.Mode!=ExternalTrainingMode||
  (len(m.Studies)!=8&&len(m.Studies)!=12){return zero,ErrExternalTrainingEvidence}
 seenRun:=map[uint64]bool{}
 seenArtifact:=map[uint64]bool{}
 seenHead:=map[string]bool{}
 out:=ExternalTrainingReport{Schema:"forge.optimizer.external-training-advisory.v1",
  Mode:"OBSERVATIONAL_TRAIN_ONLY_UNVERIFIED_OUTCOME_BYTES_NO_OPTIMIZER_AUTHORITY",
  Observations:make([]ExternalTrainingAdvisory,0,8)}
 sha:=sha256.Sum256(raw);out.SourceManifestSHA256=hex.EncodeToString(sha[:])
 width:=len(m.Studies)/2
 for i,s:=range m.Studies{
  lane:="Wingless";if i>=width{lane="Yggdrasil"}
  gate:=fmt.Sprintf("F%d",42+i%width)
  if !validExternalStudy(s,lane,gate)||seenRun[s.RunID]||
   seenArtifact[s.ArtifactID]||seenHead[s.HeadSHA]{
   return zero,ErrExternalTrainingEvidence
  }
  seenRun[s.RunID]=true;seenArtifact[s.ArtifactID]=true;seenHead[s.HeadSHA]=true
  x:=ExternalTrainingAdvisory{Lane:s.Lane,Gate:s.Gate,
   ResearchFamily:s.ResearchFamily,StudyRunID:s.RunID,
   StudyHeadSHA:s.HeadSHA,ArtifactSHA256:s.ArtifactSHA256,
   TrainingOnlyNegative:true,PositiveAccuracySignal:s.CandidateCorrect>s.StrongestFairCorrect,
   CandidateCorrect:s.CandidateCorrect,StrongestFairCorrect:s.StrongestFairCorrect,
   Total:s.Total,FailedChecks:append([]string(nil),s.FailedChecks...)}
  out.Observations=append(out.Observations,x)
  out.NegativeGateCount++
  if x.PositiveAccuracySignal{out.PositiveAccuracySignalCount++}
  if s.Lane=="Wingless"{out.WinglessCount++}else{out.YggdrasilCount++}
 }
 // Everything *not* explicitly set in the report remains false. An upstream
 // verifier may separately attest GitHub metadata and/or study bytes; source
 // claims in this manifest cannot self-verify their own authority.
 return out,nil
}
