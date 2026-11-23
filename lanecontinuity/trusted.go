package lanecontinuity

import (
 "context"
 "errors"
 "fmt"

 "github.com/spoonman136668-ai/forge/fsatrust"
 "github.com/spoonman136668-ai/forge/privatearchive"
 "github.com/spoonman136668-ai/forge/startrecovery"
)

// ErrUntrustedState indicates that an external trust or archive continuity
// prerequisite could not be established. No scientific dispatch is permitted.
var ErrUntrustedState=errors.New("FORGE_MODEL_FREE_UNTRUSTED_SCIENCE_STATE")

// TrustedPair is a model-free negative-only projection of two independently
// reconciled experiments. It contains no runnable capability or authority.
type TrustedPair struct {
 Steps NextSteps
 WinglessStart startrecovery.Decision
 YggdrasilStart startrecovery.Decision
}

// InspectTrustedPair composes the FSA's independently provisioned read-only
// authority, immutable original archive, start-receipt reconciliation and
// model-free lane classifier. Neither a clean result nor CanRequestIndependentAdmission
// authorizes starting science. Frozen cohort/ledger admission and monotonic
// one-shot start intent issuance must still succeed before any dispatch.
func InspectTrustedPair(
 ctx context.Context,
 authority fsatrust.Authority,
 archive *privatearchive.Store,
 identity fsatrust.Identity,
 winglessExperiment string,
 yggdrasilExperiment string,
 wingless Input,
 yggdrasil Input,
)(TrustedPair,error){
 if winglessExperiment==""||yggdrasilExperiment==""||wingless.Lane!=Wingless||yggdrasil.Lane!=Yggdrasil{
  return TrustedPair{},ErrInvalidInput
 }
 // Validate both classifiers before any external activity. This avoids
 // exposing partial lane information for malformed or untrusted inputs.
 if _,err:=AssessPair(wingless,yggdrasil);err!=nil{return TrustedPair{},err}
 anchor,err:=fsatrust.Recover(ctx,authority,archive,identity)
 if err!=nil{return TrustedPair{},fmt.Errorf("%w: %v",ErrUntrustedState,err)}
 journal,err:=archive.Load()
 if err!=nil{return TrustedPair{},fmt.Errorf("%w: %v",ErrUntrustedState,err)}
 if err=archive.VerifyTrustedHead(anchor.Sequence,anchor.HeadSHA256);err!=nil{
  return TrustedPair{},fmt.Errorf("%w: archive changed after recovery: %v",ErrUntrustedState,err)
 }
 head:=startrecovery.TrustedHead{
  Sequence:anchor.Sequence,SHA256:anchor.HeadSHA256,IndependentlyAuthenticated:true,
 }
 wStart,wErr:=startrecovery.Inspect(journal,head,string(Wingless),winglessExperiment)
 yStart,yErr:=startrecovery.Inspect(journal,head,string(Yggdrasil),yggdrasilExperiment)
 // A missing, ambiguous or previously started experiment is not eligible
 // for another primary. Only the affected lane is held.
 if wErr!=nil||wStart!=startrecovery.NoPriorStart{
  wingless.Failure=UnknownStart
  wingless.QualifiedWorkAvailable=false
  wingless.QualifiedAlternativeRunner=false
 }
 if yErr!=nil||yStart!=startrecovery.NoPriorStart{
  yggdrasil.Failure=UnknownStart
  yggdrasil.QualifiedWorkAvailable=false
  yggdrasil.QualifiedAlternativeRunner=false
 }
 steps,err:=ProposePair(wingless,yggdrasil)
 if err!=nil{return TrustedPair{},err}
 return TrustedPair{Steps:steps,WinglessStart:wStart,YggdrasilStart:yStart},nil
}
