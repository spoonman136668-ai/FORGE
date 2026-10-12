package shadowcore

import (
 "errors"
 "github.com/spoonman136668-ai/forge/researchstate"
)

// CycleTrace is an authenticated observation supplied by independent
// scientific witnesses, not a statement created from CI green status.
type CycleTrace struct {
 Lane string
 ParentExperimentID string
 ChildExperimentID string
 ParentHeadSHA256 string
 ChildHeadSHA256 string
 OriginalStartReceiptSHA256 string
 TerminalReceiptSHA256 string
 RawEvidenceSHA256 string
 IndependentClassificationSHA256 string
 SuccessorQualificationSHA256 string
 OwnerEpoch uint64
 IndependentlyAuthenticated bool
}
var ErrCycleUnverified=errors.New("FORGE_SCIENCE_CYCLE_NOT_INDEPENDENTLY_VERIFIED")
func validDigest(s string)bool{
 if len(s)!=64{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
// VerifyCycleTrace only verifies lifecycle ancestry and expected exact
// witness identifiers. The external witness must independently authenticate
// every signature and content hash before setting IndependentlyAuthenticated.
// This does not issue authorization or count a live autonomous cycle.
func VerifyCycleTrace(parent,child researchstate.Journal,trace CycleTrace)error{
 if !trace.IndependentlyAuthenticated||trace.OwnerEpoch==0||
  (trace.Lane!="Wingless"&&trace.Lane!="Yggdrasil")||
  trace.ParentExperimentID==""||trace.ChildExperimentID==""||
  trace.ParentExperimentID==trace.ChildExperimentID||
  !validDigest(trace.ParentHeadSHA256)||!validDigest(trace.ChildHeadSHA256)||
  !validDigest(trace.OriginalStartReceiptSHA256)||!validDigest(trace.TerminalReceiptSHA256)||
  !validDigest(trace.RawEvidenceSHA256)||!validDigest(trace.IndependentClassificationSHA256)||
  !validDigest(trace.SuccessorQualificationSHA256){return ErrCycleUnverified}
 pHead,e:=researchstate.Head(parent);if e!=nil||pHead!=trace.ParentHeadSHA256{return ErrCycleUnverified}
 cHead,e:=researchstate.Head(child);if e!=nil||cHead!=trace.ChildHeadSHA256{return ErrCycleUnverified}
 p,ok,e:=researchstate.Status(parent,trace.Lane,trace.ParentExperimentID)
 if e!=nil||!ok||p!=researchstate.SuccessorReady{return ErrCycleUnverified}
 childPhase,ok,e:=researchstate.Status(child,trace.Lane,trace.ChildExperimentID)
 if e!=nil||!ok||childPhase!=researchstate.Qualified{return ErrCycleUnverified}
 // A qualified child must be a genuinely new immutable original, and
 // prior-parent identity must persist without mutation.
 prior,ok,e:=researchstate.Status(child,trace.Lane,trace.ParentExperimentID)
 if e!=nil||!ok||prior!=researchstate.SuccessorReady{return ErrCycleUnverified}
 if len(child.Entries)<=len(parent.Entries){return ErrCycleUnverified}
 for i:=range parent.Entries{
  if child.Entries[i]!=parent.Entries[i]{return ErrCycleUnverified}
 }
 return nil
}
