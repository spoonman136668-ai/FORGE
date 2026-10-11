package fsaremote

// Probe is an observation-only diagnostic. It never executes a CAS, signs
// evidence, advances a floor, or asserts independent failure-domain custody.
import (
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"

 "github.com/spoonman136668-ai/forge/fsahead"
)

const ProbeSchema = "forge.fsa.remote-readonly-probe.v1"

// ProbeObservation describes an authenticated point-in-time network read,
// not proof of physically separate machines or durable independent storage.
type ProbeObservation struct {
 Schema string `json:"schema"`
 ArchiveID string `json:"archive_id"`
 AuthorityEpoch uint64 `json:"authority_epoch"`
 Sequence uint64 `json:"sequence"`
 HeadSHA256 string `json:"head_sha256"`
 WitnessRevision uint64 `json:"witness_revision"`
 WitnessSHA256 string `json:"witness_sha256"`
 BindingSHA256 string `json:"binding_sha256"`
 BindingConfirmed bool `json:"binding_confirmed"`
 PhysicalIndependenceVerified bool `json:"physical_independence_verified"`
 IndependentFloorVerified bool `json:"independent_floor_verified"`
 ScientificAccepted bool `json:"scientific_accepted"`
 ExecutionAuthorized bool `json:"execution_authorized"`
}

func equalObservationAnchor(a,b fsahead.Anchor)bool {
 return sameAnchor(a,b)
}

// Probe performs ONLY five authenticated GET requests (two consistent
// authority+witness reads with a binding observation between them). It
// deliberately rejects changes between reads rather than claiming an atomic
// snapshot. Calls to CompareAndSwap are forbidden in this path.
func (c *Client) Probe(ctx context.Context)(ProbeObservation,error) {
 var empty ProbeObservation
 if c==nil||ctx==nil||ctx.Err()!=nil{return empty,ErrRemote}
 first,w1,err:=c.receive(ctx)
 if err!=nil{return empty,err}
 bound,err:=c.archiveBinding(ctx,c.pin.ArchiveID)
 if err!=nil{return empty,err}
 if !bound{return empty,ErrMismatch}
 second,w2,err:=c.receive(ctx)
 if err!=nil{return empty,err}
 firstJSON,err:=json.Marshal(w1)
 if err!=nil{return empty,ErrWitness}
 secondJSON,err:=json.Marshal(w2)
 if err!=nil||!equalObservationAnchor(first,second)||
  string(firstJSON)!=string(secondJSON)||ctx.Err()!=nil {
  return empty,ErrWitness
 }
 sum:=sha256.Sum256(secondJSON)
 return ProbeObservation{
  Schema:ProbeSchema,
  ArchiveID:c.pin.ArchiveID,
  AuthorityEpoch:second.AuthorityEpoch,
  Sequence:second.Sequence,
  HeadSHA256:second.HeadSHA256,
  WitnessRevision:w2.Head.Revision,
  WitnessSHA256:hex.EncodeToString(sum[:]),
  BindingSHA256:c.pin.BindingSHA256,
  BindingConfirmed:true,
  PhysicalIndependenceVerified:false,
  IndependentFloorVerified:false,
  ScientificAccepted:false,
  ExecutionAuthorized:false,
 },nil
}
