package preusebinding

// R41: project ONE R30-signed, pinned, experiment-specific owner decision
// into the existing R35 immutable D1 claim tuple. No second signing event,
// local mutation, D1 network call, independent witness, or worker release.
import (
 "crypto/sha256"
 "encoding/hex"
 "errors"
 "math"

 "github.com/spoonman136668-ai/forge/originalclaim"
)

var ErrR41 = errors.New("FORGE_R41_CANONICAL_OWNER_PREDECISION_NOT_QUALIFIED")

// FromOwnerPredecision is a pure fail-closed projection. R30 retains
// experiment, frozen source, run, worker, four controls and signer domain.
// The D1 row carries their exact signed event digest, not a new R36 signature.
// Physical signer custody, true pre-outcome timing and original authorization
// must still be verified independently by the existing scientific owner.
func FromOwnerPredecision(s originalclaim.SignedPredecision, c originalclaim.Claim, p originalclaim.PinnedTrust) (Claim, error) {
 var zero Claim
 if originalclaim.VerifyPredecision(s,c,p)!=nil ||
  c.OwnerEpoch > math.MaxInt64 || s.Event.DecisionSequence > math.MaxInt64 {
  return zero,ErrR41
 }
 digest,err:=originalclaim.PredecisionHash(s.Event)
 if err!=nil || digest!=p.ExpectedPredecisionSHA256 {
  return zero,ErrR41
 }
 // Reuse originalclaim's irrevocable lane+experiment identity convention;
 // source, worker, run and frozen cohort are protected by digest above.
 key:=sha256.Sum256([]byte(c.Lane+"\x00"+c.ExperimentID))
 // Pin order and digest are the same as R36's D1 row convention; pin
 // authenticity and distinct administration remain external requirements.
 pin:=sha256.Sum256([]byte(p.OwnerPublicKeyHex+"\x00"+p.WitnessPublicKeyHex))
 return Claim{
  OriginalKeySHA256:hex.EncodeToString(key[:]),
  Lane:c.Lane,
  OwnerEpoch:c.OwnerEpoch,
  SourceCommitSHA:c.SourceCommitSHA,
  FrozenPredecisionSHA256:digest,
  ExternalOwnerWitnessPinSHA256:hex.EncodeToString(pin[:]),
  ClaimedSequence:s.Event.DecisionSequence,
  ScientificAuthorized:false,
 },nil
}
