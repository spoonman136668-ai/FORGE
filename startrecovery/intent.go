package startrecovery

import (
 "errors"
 "strings"
)

// Intent is a proposed one-shot primary-start identity, not a receipt.
// A durable, separately authenticated monotonic FSA authority must atomically
// reserve this identity before any runner is allowed to start the primary.
type Intent struct {
 Lane string
 ExperimentID string
 FrozenSHA256 string
 SourceSHA string
 Generation uint64
 CohortSHA256 string
 NonceSHA256 string
}

// Status is an observation from the authoritative start-intent service,
// NEVER a caller-provided instruction to execute.
type Status string
const (
 NoReservation Status = "NO_RESERVATION"
 Reserved Status = "RESERVED_NEVER_AUTOREPLAY"
 Dispatched Status = "DISPATCHED_NEVER_AUTOREPLAY"
 Completed Status = "COMPLETED_NEVER_AUTOREPLAY"
 Uncertain Status = "UNKNOWN_NEVER_AUTOREPLAY"
)
type Recovery string
const (
 RequestIndependentReservation Recovery = "REQUEST_INDEPENDENT_RESERVATION"
 HoldNoReplay Recovery = "HOLD_NEVER_REDISPATCH"
)
var ErrInvalidIntent=errors.New("FORGE_FSA_START_INTENT_INVALID")

func lowerHex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s {if !((c>='0'&&c<='9')||(c>='a'&&c<='f')){return false}}
 return true
}

// ReconcileIntent only recommends whether a new independently authenticated
// reservation MAY be requested. Even NoReservation is not a start permit.
// Indeterminate CAS outcomes, restart, timeouts and lost acknowledgements
// always remain held until external proof resolves the prior attempt.
func ReconcileIntent(i Intent, observed Status, independentlyAuthenticated bool)(Recovery,error){
 if (i.Lane!="Wingless"&&i.Lane!="Yggdrasil") ||
  i.ExperimentID==""||len(i.ExperimentID)>96||
  strings.ContainsAny(i.ExperimentID,"\\/\r\n\x00 ")||
  !lowerHex(i.FrozenSHA256,64)||!lowerHex(i.SourceSHA,40)||
  !lowerHex(i.CohortSHA256,64)||!lowerHex(i.NonceSHA256,64)||
  i.Generation==0||!independentlyAuthenticated{
   return "",ErrInvalidIntent
 }
 switch observed {
 case NoReservation:return RequestIndependentReservation,nil
 case Reserved,Dispatched,Completed,Uncertain:return HoldNoReplay,nil
 default:return "",ErrInvalidIntent
 }
}
