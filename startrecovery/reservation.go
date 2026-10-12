package startrecovery

import (
 "context"
 "errors"
)

// ReservationAuthority is intentionally an interface only. Its implementation
// must live in a separately provisioned, authenticated, linearizable FSA
// failure domain. Never implement this using a public GitHub action, local
// archive sibling file, caller-controlled map or research worker.
//
// Read returns independently authenticated authoritative status. A timeout
// or error, including an uncertain commit, does not permit re-dispatch.
// ReserveOnce is one atomic durable operation that may commit before error.
// The caller must reconcile independently instead of retrying blindly.
type ReservationAuthority interface {
 Read(context.Context, Intent) (Status, error)
 ReserveOnce(context.Context, Intent) (bool, error)
}
var ErrReservationUnavailable=errors.New("FORGE_FSA_RESERVATION_AUTHORITY_UNAVAILABLE")
var ErrReservationIndeterminate=errors.New("FORGE_FSA_RESERVATION_COMMIT_INDETERMINATE_NO_RETRY")

// ConsiderReservation is a model-free, non-executing preflight. It never calls
// ReserveOnce because reservation requires a separate authorized admission
// protocol with frozen, budgeted cohort and verified journal generation.
// No output here can be used as an authorization to start science.
func ConsiderReservation(ctx context.Context, authority ReservationAuthority, intent Intent)(Recovery,error){
 if _,err:=ReconcileIntent(intent,Observation{Intent:intent,Status:NoReservation,IndependentlyAuthenticated:true});err!=nil{return "",err}
 if ctx==nil||ctx.Err()!=nil||authority==nil{return "",ErrReservationUnavailable}
 status,err:=authority.Read(ctx,intent)
 if err!=nil||ctx.Err()!=nil{return "",ErrReservationIndeterminate}
 recovery,err:=ReconcileIntent(intent,Observation{Intent:intent,Status:status,IndependentlyAuthenticated:true})
 if err!=nil{return "",err}
 return recovery,nil
}
