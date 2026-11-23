// Package dreamrsi implements bounded FORGE-native exploration optimization.
// History is independently signed and externally pinned. The optimizer has
// NO FSA, execution, scheduler, broker, or scientific acceptance authority.
package dreamrsi

import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "sort"
)

const (
 HistorySchema="forge.dreamrsi.history.v1"
 AttestationDomain="FORGE-DREAMRSI-HISTORY-V1\x00"
 SpecSchema="forge.dreamrsi.frozen-optimization.v1"
 RecordSchema="forge.dreamrsi.policy-record.v1"
 ContractSchema="forge.dreamrsi.fsa-selection-request.v1"
)
var ErrEvidence=errors.New("FORGE_DREAMRSI_EVIDENCE_INVALID_OR_UNAUTHENTICATED")
var ErrFrozen=errors.New("FORGE_DREAMRSI_FROZEN_BUDGET_OR_IDENTITY_DRIFT")
var ErrUnsupported=errors.New("FORGE_DREAMRSI_COUNTERFACTUAL_UNSUPPORTED")
const (
 Observational="OBSERVATIONAL"
 Randomized="RANDOMIZED_PROPENSITY_AUDITED"
)
type Option struct {
 ID string `json:"id"`
 CohortSHA256 string `json:"cohort_sha256"`
 Family string `json:"family"`
 Impact int `json:"impact"`
 Novelty int `json:"novelty"`
 Robustness int `json:"robustness"`
 Diversity int `json:"diversity"`
 EstimatedCost int `json:"estimated_cost"`
 Risk int `json:"risk"`
}
type Decision struct {
 Tick uint64 `json:"tick"`
 ContextSHA256 string `json:"context_sha256"`
 SourceCommitSHA string `json:"source_commit_sha"`
 ReceiptSHA256 string `json:"receipt_sha256"`
 Options []Option `json:"options"`
 ChosenID string `json:"chosen_id"`
 ChosenCohortSHA256 string `json:"chosen_cohort_sha256"`
 Outcome string `json:"outcome"`
 ComputeUnits int `json:"compute_units"`
 LoggingMode string `json:"logging_mode"`
 LoggedActionProbabilityBP int `json:"logged_action_probability_bp"`
 RandomizationProofSHA256 string `json:"randomization_proof_sha256,omitempty"`
}
type History struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 Epoch uint64 `json:"epoch"`
 Decisions []Decision `json:"decisions"`
}
type Envelope struct {
 History History `json:"history"`
 SignatureHex string `json:"signature_hex"`
}
type TrustPin struct {
 ExpectedHistorySHA256 string
 IndependentEd25519PublicKeyHex string
}
type Verified struct {
 Lane string
 HistorySHA256 string
 Epoch uint64
 Decisions []Decision
}
func hash(raw []byte)string{d:=sha256.Sum256(raw);return hex.EncodeToString(d[:])}
func validHex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,ch:=range s{if !((ch>='0'&&ch<='9')||(ch>='a'&&ch<='f')){return false}}
 return true
}
func validID(s string)bool{
 if len(s)<1||len(s)>96{return false}
 for _,ch:=range s{if !((ch>='0'&&ch<='9')||(ch>='a'&&ch<='z')||(ch>='A'&&ch<='Z')||(ch=='_')||(ch=='-')){return false}}
 return true
}
func validOption(o Option)bool{
 if !validID(o.ID)||!validID(o.Family)||!validHex(o.CohortSHA256,64){return false}
 for _,v:=range []int{o.Impact,o.Novelty,o.Robustness,o.Diversity,o.Risk}{
  if v<0||v>100{return false}
 }
 return o.EstimatedCost>0&&o.EstimatedCost<=1000000
}
func validOutcome(s string)bool {
 switch s{case "SUPPORTED","MIXED","NEGATIVE","INVALID","CONSUMED_INDETERMINATE":return true}
 return false
}
func VerifyEnvelope(env Envelope,pin TrustPin)(Verified,error){
 var empty Verified
 if !validHex(pin.ExpectedHistorySHA256,64)||!validHex(pin.IndependentEd25519PublicKeyHex,64)||
  !validHex(env.SignatureHex,128){return empty,ErrEvidence}
 raw,err:=json.Marshal(env.History);if err!=nil{return empty,ErrEvidence}
 if hash(raw)!=pin.ExpectedHistorySHA256{return empty,ErrEvidence}
 pub,_:=hex.DecodeString(pin.IndependentEd25519PublicKeyHex)
 sig,_:=hex.DecodeString(env.SignatureHex)
 if !ed25519.Verify(ed25519.PublicKey(pub),append([]byte(AttestationDomain),raw...),sig){
  return empty,ErrEvidence
 }
 h:=env.History
 if h.Schema!=HistorySchema||h.Epoch==0||h.Lane!="Wingless"&&h.Lane!="Yggdrasil"||
  len(h.Decisions)<1||len(h.Decisions)>20000{return empty,ErrEvidence}
 seenCohort:=map[string]bool{};seenReceipt:=map[string]bool{}
 var last uint64
 for i,d:=range h.Decisions{
  if d.Tick==0||(i>0&&d.Tick<=last)||!validHex(d.ContextSHA256,64)||
   !validHex(d.SourceCommitSHA,40)||!validHex(d.ReceiptSHA256,64)||
   !validHex(d.ChosenCohortSHA256,64)||len(d.Options)==0||len(d.Options)>32||
   !validID(d.ChosenID)||!validOutcome(d.Outcome)||d.ComputeUnits<=0||
   d.ComputeUnits>1000000000||seenReceipt[d.ReceiptSHA256]{
   return empty,ErrEvidence
  }
  last=d.Tick;seenReceipt[d.ReceiptSHA256]=true
  chosenCount:=0;seenOption:=map[string]bool{}
  for _,o:=range d.Options{
   if !validOption(o)||seenOption[o.ID]||seenCohort[o.CohortSHA256]&&o.ID==d.ChosenID{
    return empty,ErrEvidence
   }
   seenOption[o.ID]=true
   if o.ID==d.ChosenID{
    chosenCount++
    if o.CohortSHA256!=d.ChosenCohortSHA256{return empty,ErrEvidence}
   }
  }
  if chosenCount!=1{return empty,ErrEvidence}
  seenCohort[d.ChosenCohortSHA256]=true
  switch d.LoggingMode{
  case Observational:
   if d.LoggedActionProbabilityBP!=0||d.RandomizationProofSHA256!=""{return empty,ErrEvidence}
  case Randomized:
   if d.LoggedActionProbabilityBP<1000||d.LoggedActionProbabilityBP>10000||
    !validHex(d.RandomizationProofSHA256,64){return empty,ErrEvidence}
  default:return empty,ErrEvidence
  }
 }
 // Deep copy: callers cannot mutate evidence beneath a verified reference.
 copied:=make([]Decision,len(h.Decisions))
 for i,d:=range h.Decisions{
  copied[i]=d
  copied[i].Options=append([]Option(nil),d.Options...)
 }
 return Verified{Lane:h.Lane,HistorySHA256:hash(raw),Epoch:h.Epoch,Decisions:copied},nil
}
type FrozenSpec struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 Epoch uint64 `json:"epoch"`
 TrainHistorySHA256 string `json:"train_history_sha256"`
 ValidationHistorySHA256 string `json:"validation_history_sha256"`
 TrainUntilTick uint64 `json:"train_until_tick"`
 ValidateFromTick uint64 `json:"validate_from_tick"`
 MaxGenerations int `json:"max_generations"`
 Population int `json:"population"`
 MutationsPerGeneration int `json:"mutations_per_generation"`
 MaxEvaluations int `json:"max_evaluations"`
 MaxReplayDecisions int `json:"max_replay_decisions"`
 MinEffectiveSampleSize float64 `json:"min_effective_sample_size"`
 MinMatchBP int `json:"min_match_bp"`
 Seed uint64 `json:"seed"`
}
func VerifySpec(spec FrozenSpec,independentSHA string,train,validation Verified)error{
 b,e:=json.Marshal(spec)
 if e!=nil||!validHex(independentSHA,64)||hash(b)!=independentSHA||
  spec.Schema!=SpecSchema||spec.Lane!=train.Lane||spec.Lane!=validation.Lane||
  spec.Epoch!=train.Epoch||spec.Epoch!=validation.Epoch||spec.Epoch==0||
  spec.TrainHistorySHA256!=train.HistorySHA256||
  spec.ValidationHistorySHA256!=validation.HistorySHA256||
  spec.TrainUntilTick==0||spec.ValidateFromTick<=spec.TrainUntilTick||
  len(train.Decisions)==0||len(validation.Decisions)==0||
  train.Decisions[len(train.Decisions)-1].Tick>spec.TrainUntilTick||
  validation.Decisions[0].Tick<spec.ValidateFromTick||
  spec.MaxGenerations<1||spec.MaxGenerations>12||
  spec.Population<2||spec.Population>64||
  spec.MutationsPerGeneration<1||spec.MutationsPerGeneration>128||
  spec.MaxEvaluations<1||spec.MaxEvaluations>2048||
  spec.MaxReplayDecisions<1||spec.MaxReplayDecisions>5000000||
  spec.MinEffectiveSampleSize<4||spec.MinEffectiveSampleSize>10000||
  spec.MinMatchBP<1000||spec.MinMatchBP>10000||
  spec.Seed==0{return ErrFrozen}
 total:=len(train.Decisions)+len(validation.Decisions)
 if total>spec.MaxReplayDecisions{return ErrFrozen}
 seen:=map[string]bool{}
 for _,h:=range []Verified{train,validation}{
  for _,d:=range h.Decisions{
   if seen[d.ChosenCohortSHA256]||seen[d.ReceiptSHA256]{return ErrFrozen}
   seen[d.ChosenCohortSHA256]=true;seen[d.ReceiptSHA256]=true
  }
 }
 return nil
}
func VerifyTemporalHoldout(train,validation,heldout Verified,holdoutAfter uint64)error{
 if train.Lane!=heldout.Lane||validation.Lane!=heldout.Lane||
  train.Epoch!=heldout.Epoch||validation.Epoch!=heldout.Epoch||
  holdoutAfter<=validation.Decisions[len(validation.Decisions)-1].Tick||
  heldout.Decisions[0].Tick<=holdoutAfter{return ErrFrozen}
 ids:=map[string]bool{}
 for _,h:=range []Verified{train,validation,heldout}{
  for _,d:=range h.Decisions{
   if ids[d.ChosenCohortSHA256]||ids[d.ReceiptSHA256]{return ErrFrozen}
   ids[d.ChosenCohortSHA256]=true;ids[d.ReceiptSHA256]=true
  }
 }
 return nil
}
func EqualSourcePins(a,b Verified)error {
 if a.Lane!=b.Lane||a.Epoch!=b.Epoch{return fmt.Errorf("%w:lane-or-epoch",ErrFrozen)}
 return nil
}
func SortedPolicies(ps []Policy){
 sort.Slice(ps,func(i,j int)bool{return ps[i].ID()<ps[j].ID()})
}
