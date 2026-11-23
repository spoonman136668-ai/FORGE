// Package lanewitness verifies independently signed, read-only observations
// for the TWO existing research lanes before invoking FORGE shadow watchdog.
// It never provisions a scientific owner, queue, lease, repair, or worker.
package lanewitness

import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"

 "github.com/spoonman136668-ai/forge/watchdog"
)

const Schema="forge.existing-lane-witness.v1"
const domain="FORGE-EXISTING-LANE-WITNESS-V1\n"
const MaxObservationAgeSeconds uint64=300
var ErrUntrusted=errors.New("FORGE_EXISTING_LANE_OBSERVATION_UNTRUSTED")

type Claim struct{
 Schema string `json:"schema"`
 ExistingLaneID string `json:"existing_lane_id"`
 ExistingQueueID string `json:"existing_queue_id"`
 SourceRepo string `json:"source_repo"`
 SourceCommitSHA string `json:"source_commit_sha"`
 OwnerID string `json:"owner_id"`
 ObservationSequence uint64 `json:"observation_sequence"`
 ObservedAtUnix uint64 `json:"observed_at_unix"`
 Observation watchdog.Observation `json:"observation"`
}
type Signed struct{
 Claim Claim `json:"claim"`
 SignatureHex string `json:"signature_hex"`
}
type Pinned struct{
 Lane string
 ExistingLaneID string
 ExistingQueueID string
 SourceRepo string
 SourceCommitSHA string
 OwnerID string
 OwnerEpoch uint64
 JournalHeadSHA256 string
 MinimumObservationSequence uint64
 PublicKey ed25519.PublicKey
}
type Proof struct {
 Lane string `json:"lane"`
 ObservationSHA256 string `json:"observation_sha256"`
 ObservationSequence uint64 `json:"observation_sequence"`
}
type Assessment struct {
 Wingless watchdog.Result `json:"wingless"`
 Yggdrasil watchdog.Result `json:"yggdrasil"`
 Incidents []watchdog.Incident `json:"incidents"`
 Proofs [2]Proof `json:"proofs"`
 Mode string `json:"mode"`
}
func validHex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func Verify(s Signed,p Pinned,now uint64)(watchdog.Observation,Proof,error){
 var zero watchdog.Observation
 var proof Proof
 c:=s.Claim
 if now==0||len(p.PublicKey)!=ed25519.PublicKeySize||
  (p.Lane!="Wingless"&&p.Lane!="Yggdrasil")||
  p.OwnerEpoch==0||p.MinimumObservationSequence==0||
  !validHex(p.SourceCommitSHA,40)||!validHex(p.JournalHeadSHA256,64)||
  p.SourceRepo==""||p.ExistingLaneID==""||p.ExistingQueueID==""||p.OwnerID==""||
  c.Schema!=Schema||c.ExistingLaneID!=p.ExistingLaneID||
  c.ExistingQueueID!=p.ExistingQueueID||c.SourceRepo!=p.SourceRepo||
  c.SourceCommitSHA!=p.SourceCommitSHA||c.OwnerID!=p.OwnerID||
  c.ObservationSequence<p.MinimumObservationSequence||
  c.ObservedAtUnix==0||c.ObservedAtUnix>now||
  now-c.ObservedAtUnix>MaxObservationAgeSeconds||
  c.Observation.Lane!=p.Lane||
  c.Observation.OwnerEpoch!=p.OwnerEpoch||
  c.Observation.JournalHeadSHA256!=p.JournalHeadSHA256||
  c.Observation.LastProgressUnix==0||
  c.Observation.LastProgressUnix>c.ObservedAtUnix||
  c.Observation.OriginalExperimentID==""||
  !validHex(s.SignatureHex,ed25519.SignatureSize*2){
  return zero,proof,ErrUntrusted
 }
 // This collector cannot authenticate a scientific worker heartbeat.
 // A signed collector assertion is not a worker-origin receipt. A separate
 // verified worker receipt must be integrated before a heartbeat is trusted.
 if c.Observation.WorkerHeartbeatAuthenticated{return zero,proof,ErrUntrusted}
 raw,err:=json.Marshal(c)
 if err!=nil{return zero,proof,ErrUntrusted}
 sig,err:=hex.DecodeString(s.SignatureHex)
 if err!=nil||!ed25519.Verify(p.PublicKey,append([]byte(domain),raw...),sig){
  return zero,proof,ErrUntrusted
 }
 h:=sha256.Sum256(append([]byte(domain),raw...))
 o:=c.Observation
 o.Authenticated=true
 return o,Proof{Lane:p.Lane,ObservationSHA256:hex.EncodeToString(h[:]),ObservationSequence:c.ObservationSequence},nil
}
// AssessPair requires exactly the original Wingless and Yggdrasil lane
// identities. The same witness key may not certify both lanes.
func AssessPair(now uint64, signed []Signed, pins []Pinned)(Assessment,error){
 var out Assessment
 if len(signed)!=2||len(pins)!=2{return out,ErrUntrusted}
 expected:=map[string]Pinned{}
 for _,p:=range pins{
  if _,exists:=expected[p.Lane];exists{return out,ErrUntrusted}
  expected[p.Lane]=p
 }
 w,okW:=expected["Wingless"];y,okY:=expected["Yggdrasil"]
 if !okW||!okY||len(w.PublicKey)!=ed25519.PublicKeySize||len(y.PublicKey)!=ed25519.PublicKeySize||
  ed25519.PublicKey(w.PublicKey).Equal(y.PublicKey)||
  w.ExistingLaneID==y.ExistingLaneID||w.ExistingQueueID==y.ExistingQueueID||
  w.SourceRepo==y.SourceRepo{
  return out,ErrUntrusted
 }
 observed:=map[string]watchdog.Observation{}
 proof:=map[string]Proof{}
 for _,s:=range signed{
  lane:=s.Claim.Observation.Lane
  p,exists:=expected[lane]
  if !exists||observed[lane].Lane!=""{return out,ErrUntrusted}
  o,v,err:=Verify(s,p,now);if err!=nil{return out,fmt.Errorf("%w: %s",ErrUntrusted,lane)}
  observed[lane]=o;proof[lane]=v
 }
 if len(observed)!=2{return out,ErrUntrusted}
 obs:=[]watchdog.Observation{observed["Wingless"],observed["Yggdrasil"]}
 results,err:=watchdog.AssessBoth(now,obs)
 if err!=nil{return out,ErrUntrusted}
 incidents,err:=watchdog.DiagnoseBoth(now,obs)
 if err!=nil{return out,ErrUntrusted}
 return Assessment{Mode:"INACTIVE_SHADOW_VERIFIED_NO_AUTHORITY",
  Wingless:results[0],Yggdrasil:results[1],Incidents:incidents,
  Proofs:[2]Proof{proof["Wingless"],proof["Yggdrasil"]}},nil
}
