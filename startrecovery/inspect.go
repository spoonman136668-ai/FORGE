// Package startrecovery provides read-only, fail-closed primary-start
// reconciliation. It cannot issue a start receipt, dispatch, or accept science.
package startrecovery

import (
 "errors"
 "fmt"
 "github.com/spoonman136668-ai/forge/researchlog"
)

var ErrBlocked=errors.New("FORGE_FSA_START_RECOVERY_BLOCKED")
type TrustedHead struct{
 Sequence uint64
 SHA256 string
 // IndependentlyAuthenticated must be supplied by separate FORGE authority.
 IndependentlyAuthenticated bool
}
type Decision string
const (
 NoPriorStart Decision="NO_PRIOR_START_OBSERVED_NOT_AUTHORIZED"
 Started Decision="STARTED_NEVER_REDISPATCH"
 Terminal Decision="TERMINAL_NEVER_REDISPATCH"
)
// Inspect verifies the full source journal and its independently authenticated
// exact current head before classifying a single lane/experiment. A nil error
// never confers dispatch authority. Ambiguous/incomplete identities fail closed.
func Inspect(j researchlog.Journal,head TrustedHead,lane,experiment string)(Decision,error){
 if !head.IndependentlyAuthenticated||head.Sequence==0||head.SHA256==""||
  (lane!="Wingless"&&lane!="Yggdrasil")||experiment==""{
  return "",fmt.Errorf("%w: missing independent head or identity",ErrBlocked)
 }
 if err:=researchlog.Verify(j);err!=nil{return "",fmt.Errorf("%w: journal invalid: %v",ErrBlocked,err)}
 if uint64(len(j.Entries))!=head.Sequence||j.Entries[len(j.Entries)-1].RecordSHA256!=head.SHA256{
  return "",fmt.Errorf("%w: stale or forked archive",ErrBlocked)
 }
 var found,starts,terminals int
 var stage researchlog.Kind
 for _,r:=range j.Entries {
  e:=r.Event
  if e.Lane!=lane||e.ExperimentID!=experiment{continue}
  found++
  stage=e.Kind
  if e.Kind==researchlog.PrimaryStarted{starts++}
  if e.Kind==researchlog.PrimaryTerminal{terminals++}
 }
 if found==0{return "",fmt.Errorf("%w: experiment not established",ErrBlocked)}
 if starts>1||terminals>1||terminals>starts{return "",fmt.Errorf("%w: conflicting primary receipts",ErrBlocked)}
 if starts==0{
  // Only a source-qualified frozen experiment can be classified not started.
  if stage!=researchlog.SourceQualified{return "",fmt.Errorf("%w: experiment not qualified",ErrBlocked)}
  return NoPriorStart,nil
 }
 if terminals==0{
  if stage!=researchlog.PrimaryStarted{return "",fmt.Errorf("%w: incomplete start state",ErrBlocked)}
  return Started,nil
 }
 if stage!=researchlog.PrimaryTerminal&&stage!=researchlog.IndependentReview&&stage!=researchlog.FinalArchive{
  return "",fmt.Errorf("%w: terminal continuity lost",ErrBlocked)
 }
 return Terminal,nil
}
