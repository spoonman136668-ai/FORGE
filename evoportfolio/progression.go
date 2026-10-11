package evoportfolio

import "errors"

// Progression is a deterministic advisory cursor for a frozen finalist list.
// It never dispatches a scientific original or consumes first-use authority.
type Progression struct {
 Schema string `json:"schema"`
 FrozenSHA256 string `json:"frozen_sha256"`
 DecisionSHA256 string `json:"decision_sha256"`
 Lane string `json:"lane"`
 CompletedIDs []string `json:"completed_ids"`
 NextID string `json:"next_id"`
 Exhausted bool `json:"exhausted"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
}
func NextAdvisory(h Handoff, completed []string)(Progression,error){
 var zero Progression
 if h.Schema!="forge.evoportfolio.handoff.v1"||!isHex(h.FrozenSHA256,64)||
  !isHex(h.DecisionSHA256,64)||(h.Lane!="Wingless"&&h.Lane!="Yggdrasil")||
  h.DispatchAuthorized||h.ScientificAccepted{return zero,ErrFrozen}
 seen:=map[string]bool{}
 order:=make(map[string]int,len(h.OrderedFinalistIDs))
 for i,id:=range h.OrderedFinalistIDs{
  if !validID(id)||seen[id]{return zero,ErrFrozen}
  seen[id]=true;order[id]=i
 }
 for _,id:=range h.OrderedNonfinalistIDs{
  if !validID(id)||seen[id]{return zero,ErrFrozen}
  seen[id]=true
 }
 if len(h.OrderedFinalistIDs)==0||len(seen)>160{return zero,ErrFrozen}
 done:=map[string]bool{}
 last:=-1
 for _,id:=range completed{
  idx,ok:=order[id]
  if !ok||done[id]||idx!=last+1{return zero,errors.New("FORGE_PORTFOLIO_PROGRESS_OUT_OF_ORDER")}
  last=idx;done[id]=true
 }
 p:=Progression{Schema:"forge.evoportfolio.progression.v1",
  FrozenSHA256:h.FrozenSHA256,DecisionSHA256:h.DecisionSHA256,
  Lane:h.Lane,CompletedIDs:append([]string(nil),completed...)}
 if len(completed)==len(h.OrderedFinalistIDs){p.Exhausted=true
 }else{p.NextID=h.OrderedFinalistIDs[len(completed)]}
 return p,nil
}
