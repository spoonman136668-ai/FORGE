package fsaadmission

import (
 "context"
 "fmt"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsatrust"
 "github.com/spoonman136668-ai/forge/privatearchive"
 "github.com/spoonman136668-ai/forge/startrecovery"
)

// AssessArchived remains the existing negative-only public API. It never
// writes, issues an independent attestation or starts an experiment.
func AssessArchived(ctx context.Context,backend fsatrust.Authority,
 archive *privatearchive.Store,identity fsatrust.Identity,
 evidence Evidence)(Disposition,error){
 decision,_,err:=assessArchivedAnchor(ctx,backend,archive,identity,evidence)
 return decision,err
}

// Only this internal path may pass an authenticated archive head to signed
// source-family checks. Caller-provided head flags never enter that verifier.
func assessArchivedAnchor(ctx context.Context,backend fsatrust.Authority,
 archive *privatearchive.Store,identity fsatrust.Identity,
 evidence Evidence)(Disposition,fsahead.Anchor,error){
 var absent fsahead.Anchor
 anchor,err:=fsatrust.Recover(ctx,backend,archive,identity)
 if err!=nil{return "",absent,fmt.Errorf("%w: authenticated archive recovery: %v",ErrBlocked,err)}
 journal,err:=archive.Load()
 if err!=nil{return "",absent,fmt.Errorf("%w: archive load: %v",ErrBlocked,err)}
 if err:=archive.VerifyTrustedHead(anchor.Sequence,anchor.HeadSHA256);err!=nil{
  return "",absent,fmt.Errorf("%w: post-recovery archive drift: %v",ErrBlocked,err)
 }
 second,err:=fsatrust.Recover(ctx,backend,archive,identity)
 if err!=nil{return "",absent,fmt.Errorf("%w: final originals and head recovery: %v",ErrBlocked,err)}
 if second.Sequence!=anchor.Sequence||second.HeadSHA256!=anchor.HeadSHA256||
  second.AuthorityEpoch!=anchor.AuthorityEpoch||second.ArchiveID!=anchor.ArchiveID{
  return "",absent,fmt.Errorf("%w: archive identity advanced during assessment",ErrBlocked)
 }
 evidence.Journal=journal
 evidence.JournalHead=startrecovery.TrustedHead{
  Sequence:anchor.Sequence,SHA256:anchor.HeadSHA256,IndependentlyAuthenticated:true,
 }
 disposition,err:=Assess(evidence)
 if err!=nil{return "",absent,err}
 return disposition,second,nil
}
