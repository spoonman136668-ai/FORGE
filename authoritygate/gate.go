// Package authoritygate evaluates immutable scientific execution admission identity.
// It cannot issue experiments, edit refs, consume first-use ledgers, or mutate queues.
package authoritygate

import (
 "errors"
 "fmt"
 "regexp"
)

var shaPattern=regexp.MustCompile("^[0-9a-f]{40}$")
var ErrUnqualified=errors.New("AUTHORITY_TREE_NOT_EXACTLY_QUALIFIED")
var ErrAmbiguous=errors.New("AUTHORITY_QUALIFICATION_AMBIGUOUS")
var ErrConsumed=errors.New("AUTHORITY_FIRST_USE_ALREADY_CONSUMED")
var ErrInvalid=errors.New("AUTHORITY_IDENTITY_INVALID")

type Attestation struct {
 RunID uint64
 TreeSHA string
 Qualified bool
 ImmutableEvidence bool
 NativeWindows bool
 FrozenControlsUnchanged bool
}

type Request struct {
 TreeSHA string
 FirstUseConsumed bool
 Qualifications []Attestation
}

type Decision struct {
 Eligible bool
 Reason string
 QualifierRunID uint64
}

// Assess is pure: it must not turn an unqualified/ambiguous attempt into an issuer call.
// Qualification is by exact Git tree, never by branch name, SHA prefix or latest-success status.
func Assess(in Request) (Decision,error) {
 if !shaPattern.MatchString(in.TreeSHA) { return Decision{Reason:"INVALID_IDENTITY"},ErrInvalid }
 if in.FirstUseConsumed { return Decision{Reason:"ALREADY_CONSUMED"},ErrConsumed }
 count:=0
 var witness uint64
 seen:=map[uint64]bool{}
 for _,a:=range in.Qualifications {
  if a.RunID==0 || !shaPattern.MatchString(a.TreeSHA) || seen[a.RunID] {
   return Decision{Reason:"INVALID_ATTESTATION"},ErrInvalid
  }
  seen[a.RunID]=true
  if a.TreeSHA!=in.TreeSHA {continue}
  if !(a.Qualified && a.ImmutableEvidence && a.NativeWindows && a.FrozenControlsUnchanged) {continue}
  count++
  witness=a.RunID
 }
 if count==0 {return Decision{Reason:"UNQUALIFIED_TREE"},ErrUnqualified}
 if count!=1 {return Decision{Reason:"AMBIGUOUS_EXACT_QUALIFIERS"},ErrAmbiguous}
 return Decision{Eligible:true,Reason:"EXACT_TREE_QUALIFIED",QualifierRunID:witness},nil
}
func (d Decision) String() string {return fmt.Sprintf("%s:%d",d.Reason,d.QualifierRunID)}
