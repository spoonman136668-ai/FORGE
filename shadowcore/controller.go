// Package shadowcore integrates the existing FORGE components into a
// strictly read-only, evidence-conscious research controller observation.
// It never issues leases, accepts results, creates lanes or dispatches science.
package shadowcore

import (
 "errors"
 "github.com/spoonman136668-ai/forge/researchstate"
 "github.com/spoonman136668-ai/forge/recoverplan"
)
var ErrUnsafe=errors.New("FORGE_SHADOW_INTEGRATION_UNSAFE")
type State struct {
 Lane string `json:"lane"`
 ExperimentID string `json:"experiment_id"`
 Phase researchstate.Phase `json:"phase"`
 Recovery researchstate.Recovery `json:"recovery"`
 OriginalReplayPermitted bool `json:"original_replay_permitted"`
}
type Snapshot struct {
 Mode string `json:"mode"`
 JournalHeadSHA256 string `json:"journal_head_sha256"`
 Wingless []State `json:"wingless"`
 Yggdrasil []State `json:"yggdrasil"`
 UnattendedScientificCycles uint64 `json:"unattended_scientific_cycles"`
}
// Observe uses only independently supplied journal entries. Counts remain
// zero until a separate authenticated *real* execution trail is integrated.
func Observe(j researchstate.Journal)(Snapshot,error){
 head,err:=researchstate.Head(j);if err!=nil{return Snapshot{},ErrUnsafe}
 s:=Snapshot{Mode:"INACTIVE_SHADOW_NO_AUTHORITY",JournalHeadSHA256:head,Wingless:[]State{},Yggdrasil:[]State{}}
 seen:=map[string]bool{}
 for _,e:=range j.Entries{
  key:=e.Lane+":"+e.ExperimentID
  if seen[key]{continue}
  seen[key]=true
  phase,ok,err:=researchstate.Status(j,e.Lane,e.ExperimentID)
  if err!=nil||!ok{return Snapshot{},ErrUnsafe}
  recover,err:=researchstate.ClassifyRecovery(j,e.Lane,e.ExperimentID)
  if err!=nil{return Snapshot{},ErrUnsafe}
  state:=State{Lane:e.Lane,ExperimentID:e.ExperimentID,Phase:phase,Recovery:recover}
  if e.Lane=="Wingless"{s.Wingless=append(s.Wingless,state)}else if e.Lane=="Yggdrasil"{s.Yggdrasil=append(s.Yggdrasil,state)}else{return Snapshot{},ErrUnsafe}
 }
 if len(s.Wingless)==0||len(s.Yggdrasil)==0{return Snapshot{},ErrUnsafe}
 return s,nil
}
// AssessRecovery binds the recovery rules to the same verified archive, not
// to a GitHub Actions success status or an untrusted remote status message.
func AssessRecovery(j researchstate.Journal,observation recoverplan.Observation)(recoverplan.Plan,error){
 if _,err:=Observe(j);err!=nil{return recoverplan.Plan{},err}
 return recoverplan.Decide(j,observation)
}
