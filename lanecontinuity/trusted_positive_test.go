package lanecontinuity

import (
 "context"
 "crypto/ed25519"
 "crypto/sha256"
 "errors"
 "path/filepath"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsatrust"
 "github.com/spoonman136668-ai/forge/privatearchive"
 "github.com/spoonman136668-ai/forge/researchlog"
)

type syntheticReadAuthority struct {
 anchor fsahead.Anchor
 readCount int
}
func (s *syntheticReadAuthority) ReadAnchor(context.Context)(fsahead.Anchor,error){
 s.readCount++;return s.anchor,nil
}
func (s *syntheticReadAuthority) ConfirmArchiveBinding(_ context.Context,id string)(bool,error){
 return id==s.anchor.ArchiveID,nil
}
func (s *syntheticReadAuthority) CompareAndSwap(context.Context,fsahead.Anchor,fsahead.Anchor)(bool,error){
 return false,errors.New("read-only test: CAS forbidden")
}
func setupSyntheticTrustedPair(t *testing.T,startedY bool)(*privatearchive.Store,*syntheticReadAuthority,fsatrust.Identity){
 t.Helper()
 archive,err:=privatearchive.Initialize(filepath.Join(t.TempDir(),privatearchive.FolderName))
 if err!=nil {t.Fatal(err)}
 h:=strings.Repeat("a",40)
 pre:=strings.Repeat("b",64)
 cohW:=strings.Repeat("c",64)
 cohY:=strings.Repeat("d",64)
 for _,entry:=range []struct{lane,id,cohort string}{
  {"Wingless","W001",cohW},{"Yggdrasil","Y001",cohY},
 }{
  e:=researchlog.Event{Lane:entry.lane,Generation:1,ExperimentID:entry.id,SourceCommitSHA:h}
  e.Kind=researchlog.Hypothesis
  if _,err=archive.AppendEvent(e);err!=nil{t.Fatal(err)}
  e.Kind=researchlog.Preregister
  e.PreregSHA256=pre
  e.CohortSHA256=entry.cohort
  if _,err=archive.AppendEvent(e);err!=nil{t.Fatal(err)}
  e.Kind=researchlog.SourceQualified
  e.WitnessSHA256=strings.Repeat("e",64)
  if _,err=archive.AppendEvent(e);err!=nil{t.Fatal(err)}
  if entry.lane=="Yggdrasil"&&startedY{
   e.Kind=researchlog.PrimaryStarted
   e.RunID=42
   e.WitnessSHA256=strings.Repeat("f",64)
   if _,err=archive.AppendEvent(e);err!=nil{t.Fatal(err)}
  }
 }
 j,err:=archive.Load();if err!=nil{t.Fatal(err)}
 seed:=sha256.Sum256([]byte("synthetic only FORGE independent recovery test key"))
 pub:=ed25519.NewKeyFromSeed(seed[:]).Public().(ed25519.PublicKey)
 anchor:=fsahead.Anchor{
  ArchiveID:strings.Repeat("1",64),KeyID:"FORGE_SYNTHETIC_ONLY",
  PublicKey:pub,AuthorityEpoch:1,
  Sequence:uint64(len(j.Entries)),HeadSHA256:j.Entries[len(j.Entries)-1].RecordSHA256,
 }
 id:=fsatrust.Identity{ArchiveID:anchor.ArchiveID,KeyID:anchor.KeyID,
  PublicKey:append(ed25519.PublicKey(nil),pub...),AuthorityEpoch:anchor.AuthorityEpoch}
 return archive,&syntheticReadAuthority{anchor:anchor},id
}
func TestTrustedPairSyntheticIndependentRecovery(t *testing.T){
 for _,startedY:=range []bool{false,true}{
  t.Run(map[bool]string{false:"both-qualified",true:"yggdrasil-started"}[startedY],func(t *testing.T){
   archive,backend,id:=setupSyntheticTrustedPair(t,startedY)
   wingless:=Input{Lane:Wingless,Failure:ModelQuota,QualifiedWorkAvailable:true}
   yggdrasil:=Input{Lane:Yggdrasil,Failure:ModelOffline,QualifiedWorkAvailable:true}
   got,err:=InspectTrustedPair(context.Background(),backend,archive,id,"W001","Y001",wingless,yggdrasil)
   if err!=nil{t.Fatal(err)}
   if got.Steps.Wingless.Classification!=ContinueEligible || !got.Steps.Wingless.CanRequestIndependentAdmission{
    t.Fatalf("Wingless held by peer: %+v",got)
   }
   if startedY{
    if got.Steps.Yggdrasil.Classification!=HoldLane||got.Steps.Yggdrasil.CanRequestIndependentAdmission{
     t.Fatalf("prior-start replay risk: %+v",got)
    }
   } else if got.Steps.Yggdrasil.Classification!=ContinueEligible{
    t.Fatalf("safe Yggdrasil held: %+v",got)
   }
   if backend.readCount<2{t.Fatal("authenticated readback missing")}
  })
 }
}
func TestTrustedPairRejectsStaleRemoteHead(t *testing.T){
 archive,backend,id:=setupSyntheticTrustedPair(t,false)
 backend.anchor.Sequence--
 wingless:=Input{Lane:Wingless,Failure:ModelQuota,QualifiedWorkAvailable:true}
 yggdrasil:=Input{Lane:Yggdrasil,Failure:ModelOffline,QualifiedWorkAvailable:true}
 got,err:=InspectTrustedPair(context.Background(),backend,archive,id,"W001","Y001",wingless,yggdrasil)
 if !errors.Is(err,ErrUntrustedState)||got!=(TrustedPair{}){
  t.Fatalf("stale external anchor accepted: %+v %v",got,err)
 }
}
