package evoportfolio

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
)
type Completion struct{
 CandidateID string `json:"candidate_id"`
 SourceSHA string `json:"source_sha"`
 EvidenceSHA256 string `json:"evidence_sha256"`
 FrozenSHA256 string `json:"frozen_sha256"`
 DecisionSHA256 string `json:"decision_sha256"`
 Outcome string `json:"outcome"`
}
type Checkpoint struct{
 Schema string `json:"schema"`
 HandoffDecisionSHA256 string `json:"handoff_decision_sha256"`
 PriorCheckpointSHA256 string `json:"prior_checkpoint_sha256"`
 Completions []Completion `json:"completions"`
 DigestSHA256 string `json:"digest_sha256"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
}
func AdvanceCheckpoint(h Handoff,prior Checkpoint,completion Completion)(Checkpoint,error){
 var empty Checkpoint
 if h.Schema!="forge.evoportfolio.handoff.v1"||!isHex(h.FrozenSHA256,64)||!isHex(h.DecisionSHA256,64)||
  len(h.OrderedFinalistIDs)==0||len(h.OrderedFinalistIDs)>5{return empty,ErrFrozen}
 if prior.Schema!=""{
  if prior.Schema!="forge.evoportfolio.checkpoint.v1"||prior.DispatchAuthorized||
   prior.HandoffDecisionSHA256!=h.DecisionSHA256||!isHex(prior.DigestSHA256,64){return empty,ErrFrozen}
  copyPrior:=prior;copyPrior.DigestSHA256=""
  b,_:=json.Marshal(copyPrior);sum:=sha256.Sum256(b)
  if prior.DigestSHA256!=hex.EncodeToString(sum[:]){return empty,ErrFrozen}
 }
 done:=make([]string,0,len(prior.Completions))
 for i,c:=range prior.Completions{
  if i>=len(h.OrderedFinalistIDs)||c.CandidateID!=h.OrderedFinalistIDs[i]||
   c.FrozenSHA256!=h.FrozenSHA256||c.DecisionSHA256!=h.DecisionSHA256||
   !isHex(c.EvidenceSHA256,64)||!isHex(c.SourceSHA,40)||
   (c.Outcome!="SUPPORTED"&&c.Outcome!="MIXED"&&c.Outcome!="NEGATIVE"){
   return empty,ErrFrozen
  }
  done=append(done,c.CandidateID)
 }
 progress,err:=NextAdvisory(h,done)
 if err!=nil||progress.Exhausted||progress.NextID!=completion.CandidateID{return empty,ErrFrozen}
 if completion.FrozenSHA256!=h.FrozenSHA256||completion.DecisionSHA256!=h.DecisionSHA256||
  !isHex(completion.EvidenceSHA256,64)||!isHex(completion.SourceSHA,40)||
  (completion.Outcome!="SUPPORTED"&&completion.Outcome!="MIXED"&&
   completion.Outcome!="NEGATIVE"){
  return empty,errors.New("FORGE_COMPLETION_PROVENANCE_INVALID")
 }
 checkpoint:=Checkpoint{Schema:"forge.evoportfolio.checkpoint.v1",
  HandoffDecisionSHA256:h.DecisionSHA256,
  PriorCheckpointSHA256:prior.DigestSHA256,
  Completions:append(append([]Completion(nil),prior.Completions...),completion)}
 b,_:=json.Marshal(checkpoint);sum:=sha256.Sum256(b)
 checkpoint.DigestSHA256=hex.EncodeToString(sum[:])
 return checkpoint,nil
}
