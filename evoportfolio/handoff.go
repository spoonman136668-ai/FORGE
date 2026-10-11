package evoportfolio

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
)

// Handoff is a replay-safe advisory record, never an executable queue.
// It preserves every screened candidate, even those not selected.
type Handoff struct{
 Schema string `json:"schema"`
 FrozenSHA256 string `json:"frozen_sha256"`
 DecisionSHA256 string `json:"decision_sha256"`
 Lane string `json:"lane"`
 OrderedFinalistIDs []string `json:"ordered_finalist_ids"`
 OrderedNonfinalistIDs []string `json:"ordered_nonfinalist_ids"`
 InvalidCount int `json:"invalid_count"`
 IndeterminateCount int `json:"indeterminate_count"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 ScientificAccepted bool `json:"scientific_accepted"`
}
func BuildHandoff(f Frozen,pin string)(Handoff,error){
 var zero Handoff
 d,err:=Select(f,pin);if err!=nil{return zero,err}
 if len(d.Archive)!=len(f.Candidates){return zero,ErrFrozen}
 m:=make(map[string]bool,len(d.Finalists))
 for _,c:=range d.Finalists{
  if m[c.ID]||c.HistoricalClass=="INVALID"||c.HistoricalClass=="CONSUMED_INDETERMINATE"{
   return zero,ErrFrozen
  }
  m[c.ID]=true
 }
 h:=Handoff{Schema:"forge.evoportfolio.handoff.v1",FrozenSHA256:pin,Lane:d.Lane,
  OrderedFinalistIDs:make([]string,0,len(d.Finalists)),
  OrderedNonfinalistIDs:make([]string,0,len(d.Archive))}
 for _,c:=range d.Finalists{h.OrderedFinalistIDs=append(h.OrderedFinalistIDs,c.ID)}
 for _,c:=range d.Archive{
  if !m[c.ID]{h.OrderedNonfinalistIDs=append(h.OrderedNonfinalistIDs,c.ID)}
  if c.HistoricalClass=="INVALID"{h.InvalidCount++}
  if c.HistoricalClass=="CONSUMED_INDETERMINATE"{h.IndeterminateCount++}
 }
 if len(h.OrderedFinalistIDs)+len(h.OrderedNonfinalistIDs)!=len(f.Candidates){
  return zero,errors.New("FORGE_PORTFOLIO_NONFINALIST_LOSS")
 }
 b,err:=json.Marshal(d);if err!=nil{return zero,ErrFrozen}
 sum:=sha256.Sum256(b);h.DecisionSHA256=hex.EncodeToString(sum[:])
 return h,nil
}
