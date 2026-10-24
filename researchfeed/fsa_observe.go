// RSH-02 composes the six-lane SOURCE-POINTER preview with FORGE's existing
// read-only FSA archive-head/binding observation interface. The caller must
// independently provision/authenticate the FSA reader and operator trust pin.
// No caller-provided scientific result is accepted as a witness.
package researchfeed

import (
 "bytes"
 "context"
 "crypto/ed25519"
 "encoding/hex"
 "errors"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/researchlog"
)

var ErrFSAPreview=errors.New("FORGE_SIX_LANE_FSA_CUSTODY_OBSERVATION_BLOCKED")

// ReadonlyFSA matches the existing fsaservice.AuthorityStore read methods.
// Implementations MUST be independently authenticated read-only endpoints;
// never supply a research-worker-local checkpoint or a synthetic scientific
// admission assertion. This package has no writer or CAS dependency.
type ReadonlyFSA interface {
 ReadAnchor(context.Context)(fsahead.Anchor,error)
 ReadBinding(context.Context,string)(string,bool,error)
}
// TrustedPin is provided out-of-band by an authenticated operator. It must
// never be constructed from Mind-Palace or the proposed research submission.
type TrustedPin struct{
 ArchiveID string
 KeyID string
 PublicKey ed25519.PublicKey
 Epoch uint64
 MinimumSequence uint64
 BindingSHA256 string
}
// FSAObservation is only an archive-head continuity observation. It does not
// authenticate candidate research bytes or grant FSA science acceptance.
type FSAObservation struct {
 Schema string `json:"schema"`
 IntakeSHA256 string `json:"intake_sha256"`
 ResearchLanes []string `json:"research_lanes"`
 ArchiveID string `json:"archive_id"`
 AuthorityEpoch uint64 `json:"authority_epoch"`
 AnchorSequence uint64 `json:"anchor_sequence"`
 AnchorHeadSHA256 string `json:"anchor_head_sha256"`
 AdvisoryOnly bool `json:"advisory_only"`
 ArchiveBindingObserved bool `json:"archive_binding_observed"`
 OriginalBytesAuthenticated bool `json:"original_bytes_authenticated"`
 FirstUseAuthorized bool `json:"first_use_authorized"`
 ScientificAccepted bool `json:"scientific_accepted"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
}
func validPin(p TrustedPin)bool{
 if !hexLower(p.ArchiveID,64)||!hexLower(p.BindingSHA256,64)||
 len(p.PublicKey)!=ed25519.PublicKeySize||p.Epoch==0||p.MinimumSequence==0||
 p.MinimumSequence>researchlog.MaxEntries||len(p.KeyID)<3||len(p.KeyID)>80{return false}
 for _,ch:=range p.KeyID{if !((ch>='0'&&ch<='9')||(ch>='a'&&ch<='z')||(ch>='A'&&ch<='Z')||ch=='-'||ch=='_'){return false}}
 return true
}
func matchesAnchor(a fsahead.Anchor,p TrustedPin)bool{
 if a.ArchiveID!=p.ArchiveID||a.KeyID!=p.KeyID||
 !bytes.Equal(a.PublicKey,p.PublicKey)||a.AuthorityEpoch!=p.Epoch||
 a.Sequence<p.MinimumSequence||a.Sequence>researchlog.MaxEntries||
 !hexLower(a.HeadSHA256,64)||a.HeadSHA256==researchlog.Genesis{return false}
 return true
}
func stableAnchor(a,b fsahead.Anchor)bool{
 return a.ArchiveID==b.ArchiveID&&a.KeyID==b.KeyID&&
 bytes.Equal(a.PublicKey,b.PublicKey)&&a.AuthorityEpoch==b.AuthorityEpoch&&
 a.Sequence==b.Sequence&&a.HeadSHA256==b.HeadSHA256
}
// ObserveFSA first revalidates ORIGINAL UNTRUSTED INDEX BYTES, then observes
// externally pinned FSA head -> independent binding -> identical head. It
// cannot silently infer any per-research scientific custody or authenticity.
// Success is negative-only and never changes currently admitted work.
func ObserveFSA(ctx context.Context,raw []byte,reader ReadonlyFSA,pin TrustedPin)(FSAObservation,error){
 var empty FSAObservation
 if ctx==nil||ctx.Err()!=nil||reader==nil||!validPin(pin){return empty,ErrFSAPreview}
 entries,err:=PreviewCandidates(raw)
 if err!=nil||!entries.AdvisoryOnly||entries.ScientificAccepted||entries.ExecutionAuthorized{return empty,ErrFSAPreview}
 before,err:=reader.ReadAnchor(ctx)
 if err!=nil||ctx.Err()!=nil||!matchesAnchor(before,pin){return empty,ErrFSAPreview}
 digest,bound,err:=reader.ReadBinding(ctx,pin.ArchiveID)
 if err!=nil||!bound||digest!=pin.BindingSHA256||ctx.Err()!=nil{return empty,ErrFSAPreview}
 after,err:=reader.ReadAnchor(ctx)
 if err!=nil||ctx.Err()!=nil||!matchesAnchor(after,pin)||!stableAnchor(before,after){return empty,ErrFSAPreview}
 lanes:=make([]string,0,len(entries.Entries))
 seen:=map[string]bool{}
 for _,entry:=range entries.Entries{if !seen[entry.Lane]{seen[entry.Lane]=true;lanes=append(lanes,entry.Lane)}}
 // deterministic lane ordering from PreviewCandidates, with no raw private bytes.
 return FSAObservation{Schema:"forge.six-lane-fsa-readonly-observation.v1",
  IntakeSHA256:entries.InputSHA256,ResearchLanes:lanes,
  ArchiveID:pin.ArchiveID,AuthorityEpoch:pin.Epoch,
  AnchorSequence:before.Sequence,AnchorHeadSHA256:before.HeadSHA256,
  AdvisoryOnly:true,ArchiveBindingObserved:true},nil
}
var _=hex.EncodeToString
