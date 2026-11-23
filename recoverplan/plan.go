// Package recoverplan creates deterministic, bounded operational repair
// decisions for the two EXISTING scientific research lanes. Decisions are
// non-executing: no production authority, queue, cohort or lease is granted.
package recoverplan

import (
 "errors"
 "github.com/spoonman136668-ai/forge/researchstate"
)
var ErrBlocked=errors.New("FORGE_RECOVERY_PROVENANCE_BLOCKED")
type Category string
const(
 Infrastructure Category="RECOVERABLE_INFRASTRUCTURE"
 Qualification Category="RECOVERABLE_QUALIFICATION"
 Scientific Category="SCIENTIFIC_TERMINAL"
 Uncertain Category="CONSUMED_UNCERTAIN"
 Integrity Category="INTEGRITY_VIOLATION"
)
type Action string
const(
 Requalify Action="REQUALIFY_EXACT_IDENTITY"
 Reconcile Action="RECONCILE_ONLY_NO_REPLAY"
 PlanNew Action="PLAN_INDEPENDENT_NEW_EXPERIMENT"
 Freeze Action="FREEZE_AFFECTED_BOUNDARY"
)
type Observation struct{
 Lane string
 ExperimentID string
 Category Category
 ExactSourceSHA string
 FrozenSHA256 string
 PreviousAttempts uint64
 Budget uint64
}
type Plan struct{
 Lane string
 ExperimentID string
 Action Action
 NextAttempt uint64
}
func hex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
// Decide freezes the entire affected boundary on missing provenance. Once
// execution may have begun, even a nominal infrastructure error cannot cause
// a replay. Attempts count only reversible requalification, never original
// science starts. Callers must independently bind persisted budget counters.
func Decide(j researchstate.Journal,o Observation)(Plan,error){
 p:=Plan{Lane:o.Lane,ExperimentID:o.ExperimentID,Action:Freeze}
 if (o.Lane!="Wingless"&&o.Lane!="Yggdrasil")||
 o.ExperimentID==""||!hex(o.ExactSourceSHA,40)||!hex(o.FrozenSHA256,64)||
 o.Budget==0||o.Budget>20||o.PreviousAttempts>o.Budget{
  return p,ErrBlocked
 }
 phase,exists,err:=researchstate.Status(j,o.Lane,o.ExperimentID)
 if err!=nil||!exists{return p,ErrBlocked}
 match:=false
 for i:=len(j.Entries)-1;i>=0;i--{
  e:=j.Entries[i]
  if e.Lane==o.Lane&&e.ExperimentID==o.ExperimentID{
   match=e.FrozenSHA256==o.FrozenSHA256
   break
  }
 }
 if !match{return p,ErrBlocked}
 recovery,err:=researchstate.ClassifyRecovery(j,o.Lane,o.ExperimentID)
 if err!=nil{return p,err}
 if recovery==researchstate.RecoverReconcileFirstUse||recovery==researchstate.RecoverEvidence{
  p.Action=Reconcile;return p,nil
 }
 switch o.Category{
 case Integrity:
  return p,nil
 case Uncertain:
  p.Action=Reconcile
 case Infrastructure,Qualification:
  if recovery!=researchstate.RecoverReversible{return p,nil}
  if o.PreviousAttempts>=o.Budget{return p,nil}
  p.Action=Requalify;p.NextAttempt=o.PreviousAttempts+1
 case Scientific:
  if phase==researchstate.SuccessorReady{
   p.Action=PlanNew
  }
 default:
  return p,ErrBlocked
 }
 return p,nil
}
