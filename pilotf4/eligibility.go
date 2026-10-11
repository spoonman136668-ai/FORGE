package pilotf4

import "errors"

// Eligibility is a pure preflight. It does not mint first-use authority.
type Eligibility struct {
 QualifiedSource string
 RequestedSource string
 FrozenBlob string
 FirstCreation bool
 FirstAttempt bool
 PreviouslyConsumed bool
 UncertainStart bool
 IndependentCommitVerified bool
 ExternalRawCustodyVerified bool
}
func CheckEligibility(e Eligibility) error {
 if !validSource(e.QualifiedSource)||e.RequestedSource!=e.QualifiedSource||
  e.FrozenBlob!=FreezeBlob{return errors.New("F4_RELEASE_IDENTITY_DRIFT")}
 if !e.FirstCreation||!e.FirstAttempt||e.PreviouslyConsumed||e.UncertainStart{
  return errors.New("F4_RELEASE_CONSUMED_OR_NOT_FIRST_USE")
 }
 if !e.IndependentCommitVerified||!e.ExternalRawCustodyVerified{
  return errors.New("F4_RELEASE_EXTERNAL_CUSTODY_UNVERIFIED")
 }
 return nil
}
