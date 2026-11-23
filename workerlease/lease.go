// Package workerlease provides deterministic lease and fencing decisions.
// The caller must persist decisions through independent atomic authority CAS.
// This package grants no dispatch rights and provisions no workers.
package workerlease

import (
 "errors"
 "fmt"
)
var ErrBlocked=errors.New("FORGE_WORKER_LEASE_BLOCKED")
type Lease struct {
 Lane string
 ExperimentID string
 IntentSHA256 string
 OwnerID string
 OwnerEpoch uint64
 WorkerID string
 LeaseSequence uint64
 ExpiresAtUnix uint64
 FirstUseRisk bool
}
type Decision string
const(
 Available Decision="AVAILABLE_FOR_AUTHORITY_REVIEW"
 Held Decision="HELD_BY_CURRENT_OWNER"
 Quarantine Decision="RECONCILE_ORIGINAL_NO_REPLAY"
 Reject Decision="REJECT"
)
func hex64(s string)bool{if len(s)!=64{return false};for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}};return true}
func valid(l Lease)bool{
 return(l.Lane=="Wingless"||l.Lane=="Yggdrasil")&&l.ExperimentID!=""&&hex64(l.IntentSHA256)&&l.OwnerID!=""&&l.OwnerEpoch>0&&l.WorkerID!=""&&l.LeaseSequence>0&&l.ExpiresAtUnix>0
}
// Inspect never treats lease expiry as evidence that first-use was unused.
func Inspect(l Lease,now uint64,authenticatedOwner string,epoch uint64)(Decision,error){
 if !valid(l)||now==0||authenticatedOwner==""||epoch==0{return Reject,ErrBlocked}
 if l.FirstUseRisk{return Quarantine,nil}
 if l.OwnerEpoch!=epoch||l.OwnerID!=authenticatedOwner{return Reject,fmt.Errorf("%w: split ownership",ErrBlocked)}
 if now>=l.ExpiresAtUnix{return Available,nil}
 return Held,nil
}
// Renew models a bounded same-owner renewal; no local clock grants rights.
// Leases with original-start risk cannot be renewed into redispatch.
func Renew(l Lease,owner string,epoch,seq,expiry uint64)(Lease,error){
 if !valid(l)||l.FirstUseRisk||owner!=l.OwnerID||epoch!=l.OwnerEpoch||
 seq!=l.LeaseSequence+1||expiry<=l.ExpiresAtUnix{return Lease{},ErrBlocked}
 next:=l;next.LeaseSequence=seq;next.ExpiresAtUnix=expiry
 return next,nil
}
