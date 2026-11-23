// Package workerfence revalidates the externally pinned FSA authority
// epoch immediately before a hypothetical worker step. It is an OBSERVER,
// not a scientific execution permit, launch interface or owner-fencing service.
package workerfence

import(
 "bytes"
 "context"
 "crypto/ed25519"
 "errors"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsaremote"
 "github.com/spoonman136668-ai/forge/researchlog"
 "github.com/spoonman136668-ai/forge/workerlease"
)

const Mode="REMOTE_FSA_EPOCH_OBSERVED_NO_EXECUTION_AUTHORITY"
var ErrBlocked=errors.New("FORGE_WORKER_REMOTE_EPOCH_FENCE_NOT_AUTHENTICATED")

type Observation struct{
 Mode string `json:"mode"`
 Lane string `json:"lane"`
 ExistingExperimentID string `json:"existing_experiment_id"`
 WorkerID string `json:"worker_id"`
 OwnerID string `json:"owner_id"`
 AuthorityEpoch uint64 `json:"authority_epoch"`
 AuthoritySequence uint64 `json:"authority_sequence"`
 AuthorityHeadSHA256 string `json:"authority_head_sha256"`
 LeaseSequence uint64 `json:"lease_sequence"`
 FirstUseReplayAuthorized bool `json:"first_use_replay_authorized"`
 WorkerDispatchAuthorized bool `json:"worker_dispatch_authorized"`
 ScienceActivated bool `json:"science_activated"`
}

func same(a,b fsahead.Anchor)bool{
 return a.ArchiveID==b.ArchiveID&&a.KeyID==b.KeyID&&
  bytes.Equal(a.PublicKey,b.PublicKey)&&
  a.AuthorityEpoch==b.AuthorityEpoch&&
  a.Sequence==b.Sequence&&a.HeadSHA256==b.HeadSHA256
}
func digest(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func pinned(a fsahead.Anchor)bool{
 if a.ArchiveID==""||!digest(a.ArchiveID,64)||
  a.KeyID==""||len(a.PublicKey)!=ed25519.PublicKeySize||
  a.AuthorityEpoch==0||a.Sequence>researchlog.MaxEntries||
  !digest(a.HeadSHA256,64){return false}
 return(a.Sequence==0&&a.HeadSHA256==researchlog.Genesis)||
  (a.Sequence>0&&a.HeadSHA256!=researchlog.Genesis)
}

// Observe is a read-only, negative-only worker integration seam against the
// REAL pinned-mTLS fsaremote.Client. It refuses first-use ambiguity, stale or
// expired leases, split owner epochs, unbound archives, unexpected heads and
// rollbacks. The FSA client authenticates TWO separate signed remote peers.
//
// A successful observation is NOT a fresh atomic worker-side epoch fence:
// work admission still requires live old-owner revocation, an independently
// linearizable FSA reservation, immutable first-use custody and signed worker
// attestations. No caller is authorized to act on a green observation alone.
func Observe(ctx context.Context,remote *fsaremote.Client,expected fsahead.Anchor,lease workerlease.Lease,now uint64)(Observation,error){
 if ctx==nil||ctx.Err()!=nil||remote==nil||!pinned(expected)||
  now==0||lease.FirstUseRisk||lease.OwnerEpoch!=expected.AuthorityEpoch||
  lease.Lane!="Wingless"&&lease.Lane!="Yggdrasil"||
  lease.ExperimentID==""||lease.WorkerID==""||lease.OwnerID==""{
  return Observation{},ErrBlocked
 }
 state,err:=workerlease.Inspect(lease,now,lease.OwnerID,expected.AuthorityEpoch)
 if err!=nil||state!=workerlease.Held{return Observation{},ErrBlocked}
 before,err:=remote.ReadAnchor(ctx)
 if err!=nil||!same(before,expected){return Observation{},ErrBlocked}
 bound,err:=remote.ConfirmArchiveBinding(ctx,expected.ArchiveID)
 if err!=nil||!bound||ctx.Err()!=nil{return Observation{},ErrBlocked}
 after,err:=remote.ReadAnchor(ctx)
 if err!=nil||!same(after,expected)||ctx.Err()!=nil{return Observation{},ErrBlocked}
 return Observation{Mode:Mode,Lane:lease.Lane,ExistingExperimentID:lease.ExperimentID,
  WorkerID:lease.WorkerID,OwnerID:lease.OwnerID,
  AuthorityEpoch:expected.AuthorityEpoch,AuthoritySequence:expected.Sequence,
  AuthorityHeadSHA256:expected.HeadSHA256,LeaseSequence:lease.LeaseSequence,
  FirstUseReplayAuthorized:false,WorkerDispatchAuthorized:false,
  ScienceActivated:false},nil
}
