// Package prospective defines the next FORGE Dream-RSI decision-time
// evidence contract. It cannot issue FSA authority or dispatch experiments.
package prospective

import (
 "bytes"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "os"
 "path/filepath"
 "sort"

 "github.com/spoonman136668-ai/forge/dreamrsi"
)

const (
 DecisionSchema = "forge.dreamrsi.predecision.v1"
 ResultSchema = "forge.dreamrsi.original-link.v1"
 JoinedSchema = "forge.dreamrsi.prospective-observation.v1"
 DecisionDomain = "FORGE-DREAMRSI-PREDECISION-V1\x00"
 ResultDomain = "FORGE-DREAMRSI-ORIGINAL-LINK-V1\x00"
 Observational = "OBSERVATIONAL"
 RandomizedUnaudited = "RANDOMIZED_UNAUDITED"
)
var ErrEvidence = errors.New("FORGE_DREAMRSI_PROSPECTIVE_EVIDENCE_REJECTED")

// Selection is the complete before-outcome information visible to the
// optimizer. It intentionally has no scientific outcome or dispatch field.
type Selection struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 Epoch uint64 `json:"epoch"`
 Tick uint64 `json:"tick"`
 SourceCommitSHA string `json:"source_commit_sha"`
 FrozenPreregSHA256 string `json:"frozen_prereg_sha256"`
 PolicySHA256 string `json:"policy_sha256"`
 PolicyLineageSHA256 string `json:"policy_lineage_sha256"`
 ContextSHA256 string `json:"context_sha256"`
 Options []dreamrsi.Option `json:"options"`
 ChosenID string `json:"chosen_id"`
 ChosenCohortSHA256 string `json:"chosen_cohort_sha256"`
 MaxComputeUnits int `json:"max_compute_units"`
 LoggingMode string `json:"logging_mode"`
 AssignedProbabilitiesBP map[string]int `json:"assigned_probabilities_bp,omitempty"`
 RandomnessCommitSHA256 string `json:"randomness_commit_sha256,omitempty"`
}

// Scientific result is separately attested after the original has consumed
// its cohort. This interface cannot establish raw scientific authenticity.
type OriginalLink struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 Epoch uint64 `json:"epoch"`
 Tick uint64 `json:"tick"`
 PredecisionSHA256 string `json:"predecision_sha256"`
 SourceCommitSHA string `json:"source_commit_sha"`
 FrozenPreregSHA256 string `json:"frozen_prereg_sha256"`
 ChosenID string `json:"chosen_id"`
 ConsumedCohortSHA256 string `json:"consumed_cohort_sha256"`
 RunID string `json:"run_id"`
 RunAttempt int `json:"run_attempt"`
 StartedSHA256 string `json:"started_sha256"`
 RawSHA256 string `json:"raw_sha256"`
 DispositionSHA256 string `json:"disposition_sha256"`
 Outcome string `json:"outcome"`
 ActualComputeUnits int `json:"actual_compute_units"`
}
type SignedSelection struct {
 Selection Selection `json:"selection"`
 SignatureHex string `json:"signature_hex"`
}
type SignedOriginal struct {
 Original OriginalLink `json:"original"`
 SignatureHex string `json:"signature_hex"`
}
type IndependentPin struct {
 ExpectedSHA256 string
 PublicKeyHex string
}
type VerifiedSelection struct {
 Selection Selection
 SHA256 string
 PublicKeyHex string
 verified bool
 verifiedKey string
}
type VerifiedOriginal struct {
 Original OriginalLink
 SHA256 string
 PublicKeyHex string
 verified bool
 verifiedKey string
}
type Observation struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 Epoch uint64 `json:"epoch"`
 Tick uint64 `json:"tick"`
 PredecisionSHA256 string `json:"predecision_sha256"`
 OriginalLinkSHA256 string `json:"original_link_sha256"`
 ChosenID string `json:"chosen_id"`
 ConsumedCohortSHA256 string `json:"consumed_cohort_sha256"`
 Outcome string `json:"outcome"`
 ActualComputeUnits int `json:"actual_compute_units"`
 OriginalScientificEvidenceIndependentlyAudited bool `json:"original_scientific_evidence_independently_audited"`
 RandomizationIndependentlyAudited bool `json:"randomization_independently_audited"`
 TemporalPredecisionOrderIndependentlyAttested bool `json:"temporal_predecision_order_independently_attested"`
 EligibleForCausalPolicyReplay bool `json:"eligible_for_causal_policy_replay"`
 ScientificAccepted bool `json:"scientific_accepted"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 AcceptedRefMutation bool `json:"accepted_ref_mutation"`
}
func hash(data []byte)string {
 sum:=sha256.Sum256(data)
 return hex.EncodeToString(sum[:])
}
func hexValid(s string,n int)bool {
 if len(s)!=n{return false}
 for _,c:=range s {if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func validID(s string)bool {
 if len(s)==0||len(s)>96{return false}
 for _,c:=range s {
  if !(c>='A'&&c<='Z'||c>='a'&&c<='z'||c>='0'&&c<='9'||c=='_'||c=='-'){return false}
 }
 return true
}
func verifySigned(data any,signature string,pin IndependentPin,domain string)(string,error){
 if !hexValid(signature,128)||!hexValid(pin.ExpectedSHA256,64)||!hexValid(pin.PublicKeyHex,64){return "",ErrEvidence}
 b,err:=json.Marshal(data);if err!=nil||len(b)>65536{return "",ErrEvidence}
 sha:=hash(b)
 if sha!=pin.ExpectedSHA256{return "",ErrEvidence}
 sig,_:=hex.DecodeString(signature)
 key,_:=hex.DecodeString(pin.PublicKeyHex)
 if !ed25519.Verify(ed25519.PublicKey(key),append([]byte(domain),b...),sig){return "",ErrEvidence}
 return sha,nil
}
func validOption(o dreamrsi.Option)bool{
 if !validID(o.ID)||!validID(o.Family)||!hexValid(o.CohortSHA256,64)||o.EstimatedCost<1||o.EstimatedCost>1000000{return false}
 for _,v:=range []int{o.Impact,o.Novelty,o.Robustness,o.Diversity,o.Risk} {
  if v<0||v>100{return false}
 }
 return true
}
func VerifySelection(s SignedSelection,pin IndependentPin,policy dreamrsi.Policy)(VerifiedSelection,error){
 var empty VerifiedSelection
 sha,err:=verifySigned(s.Selection,s.SignatureHex,pin,DecisionDomain)
 if err!=nil{return empty,err}
 d:=s.Selection
 if d.Schema!=DecisionSchema||d.Lane!="Wingless"&&d.Lane!="Yggdrasil"||
  d.Epoch==0||d.Tick==0||!hexValid(d.SourceCommitSHA,40)||
  !hexValid(d.FrozenPreregSHA256,64)||!hexValid(d.PolicyLineageSHA256,64)||
  !hexValid(d.ContextSHA256,64)||d.MaxComputeUnits<1||d.MaxComputeUnits>1000000||
  d.PolicySHA256!=policy.ID()||policy.Lane!=d.Lane||
  dreamrsi.VerifyPolicy(policy)!=nil||len(d.Options)==0||len(d.Options)>32||
  !validID(d.ChosenID)||!hexValid(d.ChosenCohortSHA256,64){
  return empty,ErrEvidence
 }
 ids:=map[string]bool{};cohorts:=map[string]bool{}
 found:=false;choiceCost:=0
 for _,o:=range d.Options{
  if !validOption(o)||ids[o.ID]||cohorts[o.CohortSHA256]{return empty,ErrEvidence}
  ids[o.ID]=true;cohorts[o.CohortSHA256]=true
  if o.ID==d.ChosenID {
   if o.CohortSHA256!=d.ChosenCohortSHA256{return empty,ErrEvidence}
   found=true;choiceCost=o.EstimatedCost
  }
 }
 if !found||choiceCost>d.MaxComputeUnits{return empty,ErrEvidence}
 switch d.LoggingMode {
 case Observational:
  if len(d.AssignedProbabilitiesBP)!=0||d.RandomnessCommitSHA256!=""{return empty,ErrEvidence}
  chosen,err:=dreamrsi.Select(policy,dreamrsi.Decision{Options:d.Options,ContextSHA256:d.ContextSHA256})
  if err!=nil||chosen!=d.ChosenID{return empty,ErrEvidence}
 case RandomizedUnaudited:
  if !hexValid(d.RandomnessCommitSHA256,64)||len(d.AssignedProbabilitiesBP)!=len(d.Options){return empty,ErrEvidence}
  total:=0
  for _,o:=range d.Options{
   weight:=d.AssignedProbabilitiesBP[o.ID]
   if weight<1000||weight>10000{return empty,ErrEvidence}
   total+=weight
  }
  if total!=10000{return empty,ErrEvidence}
 default:return empty,ErrEvidence
 }
 // Copy option slice and map so an untrusted caller cannot change verified contents.
 d.Options=append([]dreamrsi.Option(nil),d.Options...)
 if d.AssignedProbabilitiesBP!=nil{
  copied:=make(map[string]int,len(d.AssignedProbabilitiesBP))
  for key,value:=range d.AssignedProbabilitiesBP{copied[key]=value}
  d.AssignedProbabilitiesBP=copied
 }
 return VerifiedSelection{Selection:d,SHA256:sha,PublicKeyHex:pin.PublicKeyHex,verified:true,verifiedKey:pin.PublicKeyHex},nil
}
func VerifyOriginal(s SignedOriginal,pin IndependentPin)(VerifiedOriginal,error){
 var empty VerifiedOriginal
 sha,err:=verifySigned(s.Original,s.SignatureHex,pin,ResultDomain)
 if err!=nil{return empty,err}
 r:=s.Original
 if r.Schema!=ResultSchema||r.Lane!="Wingless"&&r.Lane!="Yggdrasil"||
  r.Epoch==0||r.Tick==0||!hexValid(r.PredecisionSHA256,64)||
  !hexValid(r.SourceCommitSHA,40)||!hexValid(r.FrozenPreregSHA256,64)||
  !hexValid(r.ConsumedCohortSHA256,64)||!validID(r.ChosenID)||
  !validID(r.RunID)||r.RunAttempt!=1||
  !hexValid(r.StartedSHA256,64)||!hexValid(r.RawSHA256,64)||
  !hexValid(r.DispositionSHA256,64)||r.ActualComputeUnits<=0||
  r.ActualComputeUnits>1000000{return empty,ErrEvidence}
 switch r.Outcome{
 case "SUPPORTED","MIXED","NEGATIVE","INVALID","CONSUMED_INDETERMINATE":
 default:return empty,ErrEvidence
 }
 return VerifiedOriginal{Original:r,SHA256:sha,PublicKeyHex:pin.PublicKeyHex,verified:true,verifiedKey:pin.PublicKeyHex},nil
}
func Join(pre VerifiedSelection,original VerifiedOriginal)(Observation,error){
 var empty Observation
 d,r:=pre.Selection,original.Original
 preRaw,preErr:=json.Marshal(d)
 originalRaw,originalErr:=json.Marshal(r)
 if !pre.verified||!original.verified||preErr!=nil||originalErr!=nil||
  hash(preRaw)!=pre.SHA256||hash(originalRaw)!=original.SHA256||
  pre.verifiedKey!=pre.PublicKeyHex||original.verifiedKey!=original.PublicKeyHex{
  return empty,ErrEvidence
 }
 if !hexValid(pre.SHA256,64)||!hexValid(original.SHA256,64)||
  !hexValid(pre.PublicKeyHex,64)||!hexValid(original.PublicKeyHex,64)||
  pre.PublicKeyHex==original.PublicKeyHex||d.Lane!=r.Lane||
  d.Epoch!=r.Epoch||d.Tick!=r.Tick||r.PredecisionSHA256!=pre.SHA256||
  d.SourceCommitSHA!=r.SourceCommitSHA||
  d.FrozenPreregSHA256!=r.FrozenPreregSHA256||
  d.ChosenID!=r.ChosenID||d.ChosenCohortSHA256!=r.ConsumedCohortSHA256||
  r.ActualComputeUnits>d.MaxComputeUnits{return empty,ErrEvidence}
 return Observation{Schema:JoinedSchema,Lane:d.Lane,Epoch:d.Epoch,Tick:d.Tick,
  PredecisionSHA256:pre.SHA256,OriginalLinkSHA256:original.SHA256,
  ChosenID:d.ChosenID,ConsumedCohortSHA256:d.ChosenCohortSHA256,
  Outcome:r.Outcome,ActualComputeUnits:r.ActualComputeUnits},nil
}
func VerifyChronologicalLane(observations []Observation,lane string)error{
 if lane!="Wingless"&&lane!="Yggdrasil"||len(observations)==0||len(observations)>20000{return ErrEvidence}
 seenPre:=map[string]bool{};seenCohort:=map[string]bool{};seenOriginal:=map[string]bool{}
 var last uint64
 var epoch uint64
 for i,o:=range observations{
  if o.Schema!=JoinedSchema||o.Lane!=lane||o.Epoch==0||o.Tick==0||
   o.ActualComputeUnits<1||o.ActualComputeUnits>1000000||
   !(o.Outcome=="SUPPORTED"||o.Outcome=="MIXED"||o.Outcome=="NEGATIVE"||
     o.Outcome=="INVALID"||o.Outcome=="CONSUMED_INDETERMINATE")||
   i>0&&(o.Epoch<epoch||o.Epoch==epoch&&o.Tick<=last)||
   !hexValid(o.PredecisionSHA256,64)||!hexValid(o.OriginalLinkSHA256,64)||
   !hexValid(o.ConsumedCohortSHA256,64)||seenPre[o.PredecisionSHA256]||
   seenOriginal[o.OriginalLinkSHA256]||seenCohort[o.ConsumedCohortSHA256]||
   o.EligibleForCausalPolicyReplay||o.ScientificAccepted||o.DispatchAuthorized||
   o.AcceptedRefMutation||o.RandomizationIndependentlyAudited||
   o.OriginalScientificEvidenceIndependentlyAudited||
   o.TemporalPredecisionOrderIndependentlyAttested {
   return ErrEvidence
  }
  seenPre[o.PredecisionSHA256]=true
  seenOriginal[o.OriginalLinkSHA256]=true
  seenCohort[o.ConsumedCohortSHA256]=true
  epoch=o.Epoch;last=o.Tick
 }
 return nil
}
func CompareLaneIsolation(left,right []Observation)error{
 if len(left)==0||len(right)==0{return ErrEvidence}
 if err:=VerifyChronologicalLane(left,"Wingless");err!=nil{return err}
 if err:=VerifyChronologicalLane(right,"Yggdrasil");err!=nil{return err}
 all:=map[string]bool{}
 for _,o:=range left{all[o.ConsumedCohortSHA256]=true}
 for _,o:=range right{
  if all[o.ConsumedCohortSHA256]{return ErrEvidence}
 }
 return nil
}
// PersistOnce writes a bounded, unprivileged observation locally with O_EXCL.
// Protected cross-host monotonic consumption is an independent FSA duty.
func PersistOnce(path string,o Observation)error{
 if !filepath.IsAbs(path)||VerifyChronologicalLane([]Observation{o},o.Lane)!=nil{return ErrEvidence}
 data,err:=json.Marshal(o)
 if err!=nil||len(data)>16384{return ErrEvidence}
 f,err:=os.OpenFile(path,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{return ErrEvidence}
 if _,err=f.Write(append(data,'\n'));err!=nil{_ = f.Close();return ErrEvidence}
 if err=f.Sync();err!=nil{_ = f.Close();return ErrEvidence}
 return f.Close()
}
func ParseSignedSelection(b []byte)(SignedSelection,error){
 var out SignedSelection
 if len(b)==0||len(b)>65536{return out,ErrEvidence}
 dec:=json.NewDecoder(bytes.NewReader(b));dec.DisallowUnknownFields()
 if err:=dec.Decode(&out);err!=nil{return SignedSelection{},ErrEvidence}
 var extra any
 if err:=dec.Decode(&extra);err!=io.EOF{return SignedSelection{},ErrEvidence}
 return out,nil
}
func ParseSignedOriginal(b []byte)(SignedOriginal,error){
 var out SignedOriginal
 if len(b)==0||len(b)>65536{return out,ErrEvidence}
 dec:=json.NewDecoder(bytes.NewReader(b));dec.DisallowUnknownFields()
 if err:=dec.Decode(&out);err!=nil{return SignedOriginal{},ErrEvidence}
 var extra any
 if err:=dec.Decode(&extra);err!=io.EOF{return SignedOriginal{},ErrEvidence}
 return out,nil
}
// StableHashes records immutable identities without treating a hash as a
// trusted external timestamp, independent signer, or FSA acceptance.
func StableHashes(observations []Observation)[]string{
 hashes:=make([]string,0,len(observations))
 for _,o:=range observations{b,_:=json.Marshal(o);hashes=append(hashes,hash(b))}
 sort.Strings(hashes)
 return hashes
}

// ToObservationalDecision copies only witnessed results. The FSA must
// independently assemble and sign the historical envelope. Randomized
// proposals remain OBSERVATIONAL until a separate genuine randomization
// and chronological precommit audit is independently qualified.
func ToObservationalDecision(pre VerifiedSelection,original VerifiedOriginal)(dreamrsi.Decision,error){
 o,err:=Join(pre,original)
 if err!=nil{return dreamrsi.Decision{},err}
 return dreamrsi.Decision{
  Tick:o.Tick,ContextSHA256:pre.Selection.ContextSHA256,
  SourceCommitSHA:pre.Selection.SourceCommitSHA,
  ReceiptSHA256:o.OriginalLinkSHA256,
  Options:append([]dreamrsi.Option(nil),pre.Selection.Options...),
  ChosenID:o.ChosenID,ChosenCohortSHA256:o.ConsumedCohortSHA256,
  Outcome:o.Outcome,ComputeUnits:o.ActualComputeUnits,
  LoggingMode:dreamrsi.Observational,
 },nil
}
