package researchfeed

import (
 "context"
 "crypto/ed25519"
 "errors"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/fsahead"
)
type stubFSA struct{
 anchors []fsahead.Anchor
 reads int
 binding string
 bound bool
 err error
}
func(s *stubFSA)ReadAnchor(context.Context)(fsahead.Anchor,error){
 s.reads++
 if s.err!=nil{return fsahead.Anchor{},s.err}
 if len(s.anchors)==0{return fsahead.Anchor{},errors.New("no anchor")}
 i:=s.reads-1;if i>=len(s.anchors){i=len(s.anchors)-1}
 return s.anchors[i],nil
}
func(s *stubFSA)ReadBinding(_ context.Context,_ string)(string,bool,error){
 return s.binding,s.bound,s.err
}
func fsaFixture()(TrustedPin,*stubFSA){
 key:=ed25519.PublicKey(strings.Repeat("p",32))
 pin:=TrustedPin{ArchiveID:strings.Repeat("a",64),KeyID:"forge-archive",PublicKey:key,
 Epoch:3,MinimumSequence:2,BindingSHA256:strings.Repeat("b",64)}
 anchor:=fsahead.Anchor{ArchiveID:pin.ArchiveID,KeyID:pin.KeyID,
 PublicKey:append(ed25519.PublicKey(nil),key...),AuthorityEpoch:pin.Epoch,
 Sequence:2,HeadSHA256:strings.Repeat("c",64)}
 return pin,&stubFSA{anchors:[]fsahead.Anchor{anchor,anchor},binding:pin.BindingSHA256,bound:true}
}
func fsaPreview(t *testing.T,raw []byte,reader ReadonlyFSA,pin TrustedPin)FSAObservation{
 t.Helper();result,err:=ObserveFSA(context.Background(),raw,reader,pin);if err!=nil{t.Fatal(err)};return result
}
func denyFSA(t *testing.T,raw []byte,s ReadonlyFSA,p TrustedPin){
 t.Helper();if _,err:=ObserveFSA(context.Background(),raw,s,p);err==nil{t.Fatal("untrusted authority observation accepted")}
}
func TestReadOnlyCrossLaneFSAObservation(t *testing.T){
 p,store:=fsaFixture()
 got:=fsaPreview(t,encode(sixLanes()),store,p)
 if got.Schema!="forge.six-lane-fsa-readonly-observation.v1"||
 !got.ArchiveBindingObserved||!got.AdvisoryOnly||got.OriginalBytesAuthenticated||
 got.FirstUseAuthorized||got.ScientificAccepted||got.DispatchAuthorized||
 len(got.ResearchLanes)!=6||got.AnchorSequence!=2||len(got.IntakeSHA256)!=64||
 store.reads!=2{t.Fatalf("untrusted outcome: %#v",got)}
}
func TestFSAUnprovisionedIsBlocked(t *testing.T){
 p,_:=fsaFixture();denyFSA(t,encode(sixLanes()),nil,p)
}
func TestInvalidOperatorPinRejected(t *testing.T){
 p,store:=fsaFixture();p.Epoch=0;denyFSA(t,encode(sixLanes()),store,p)
}
func TestMissingExternalArchiveBindingRejected(t *testing.T){
 p,store:=fsaFixture();store.bound=false;denyFSA(t,encode(sixLanes()),store,p)
}
func TestIndependentBindingDigestDriftRejected(t *testing.T){
 p,store:=fsaFixture();store.binding=strings.Repeat("e",64);denyFSA(t,encode(sixLanes()),store,p)
}
func TestFSAHeadChangeDuringReadRejected(t *testing.T){
 p,store:=fsaFixture();store.anchors[1].Sequence=3
 denyFSA(t,encode(sixLanes()),store,p)
}
func TestFalseFSAIdentityRejected(t *testing.T){
 p,store:=fsaFixture();store.anchors[0].ArchiveID=strings.Repeat("d",64)
 denyFSA(t,encode(sixLanes()),store,p)
}
func TestFSARollbackRejected(t *testing.T){
 p,store:=fsaFixture();store.anchors[0].Sequence=1;denyFSA(t,encode(sixLanes()),store,p)
}
func TestFSAWitnessKeyDriftRejected(t *testing.T){
 p,store:=fsaFixture();store.anchors[0].PublicKey=ed25519.PublicKey(strings.Repeat("x",32));denyFSA(t,encode(sixLanes()),store,p)
}
func TestFSAReaderFailureRejected(t *testing.T){
 p,store:=fsaFixture();store.err=errors.New("authority missing");denyFSA(t,encode(sixLanes()),store,p)
}
func TestInvalidSourceIndexNeverQueriesFSA(t *testing.T){
 p,store:=fsaFixture()
 data:=sixLanes();data[0].ExecuteRequested=true
 denyFSA(t,encode(data),store,p)
 if store.reads!=0{t.Fatalf("FSA consulted for invalid input %d",store.reads)}
}
func TestFSAReadOnlyCancelledContext(t *testing.T){
 p,store:=fsaFixture();ctx,cancel:=context.WithCancel(context.Background());cancel()
 if _,err:=ObserveFSA(ctx,encode(sixLanes()),store,p);err==nil{t.Fatal("cancelled observation admitted")}
 if store.reads!=0{t.Fatal("cancelled read reached authority")}
}
func TestFSAObservationPreservesResearchOutcomesInIndex(t *testing.T){
 p,store:=fsaFixture();raw:=encode(sixLanes());observed:=fsaPreview(t,raw,store,p)
 view,err:=PreviewCandidates(raw)
 if err!=nil||observed.IntakeSHA256!=view.InputSHA256{t.Fatal("source digest mismatch")}
 if view.Entries[0].Outcome==""||len(view.Entries)!=6{t.Fatal("lost original outcome")}
 // FSA receipt reports index identity, never reclassifies POSITIVE/NEGATIVE.
 if observed.ScientificAccepted||observed.OriginalBytesAuthenticated{t.Fatal("promoted unverified source")}
}
