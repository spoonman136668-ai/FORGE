package researchfeed

import (
 "context"
 "crypto/sha1"
 "crypto/sha256"
 "encoding/hex"
 "errors"
 "strconv"
 "strings"
 "testing"
)
type stubOriginal struct {
 reads int
 blob OriginalBlob
 err error
}
func(s *stubOriginal)ReadOriginalAt(_ context.Context,_,_,_ string)(OriginalBlob,error){
 s.reads++
 if s.err!=nil{return OriginalBlob{},s.err}
 return s.blob,nil
}
func originalFixture()(OriginalPin,*stubOriginal,[]byte){
 c:=sixLanes()[0]
 data:=[]byte(`{"research_id":"W-01","outcome":"NEGATIVE"}`)
 framed:=append([]byte("blob "+strconv.Itoa(len(data))+"\x00"),data...)
 blob:=sha1.Sum(framed)
 digest:=sha256.Sum256(data)
 p:=OriginalPin{Lane:c.Lane,ResearchID:c.ResearchID,SourceRepo:c.SourceRepo,
  SourceCommit:c.SourceCommit,SourcePath:c.SourcePath,
  BlobSHA1:hex.EncodeToString(blob[:]),BytesSHA256:hex.EncodeToString(digest[:])}
 s:=&stubOriginal{blob:OriginalBlob{SourceRepo:c.SourceRepo,SourceCommit:c.SourceCommit,
  SourcePath:c.SourcePath,BlobSHA1:p.BlobSHA1,Bytes:data}}
 return p,s,encode(sixLanes())
}
func rejectOriginal(t *testing.T,raw []byte,p OriginalPin,s ReadonlyOriginalSource){
 t.Helper()
 if _,err:=ObserveOriginalIntegrity(context.Background(),raw,p,s);err==nil{t.Fatal("unsafe source accepted")}
}
func TestRSH04IntegrityOnlyNoScientificAuthority(t *testing.T){
 p,s,raw:=originalFixture()
 got,err:=ObserveOriginalIntegrity(context.Background(),raw,p,s)
 if err!=nil{t.Fatal(err)}
 if !got.AdvisoryOnly||!got.BlobIntegrityVerified||got.OriginalBytesAuthenticated||
  got.ExternalSignerVerified||got.OriginalFirstUseCleared||got.ScientificAccepted||
  got.DispatchAuthorized||got.BytesSHA256!=p.BytesSHA256||got.OriginalSize==0||
  got.IndexSHA256==""||s.reads!=1{t.Fatalf("false authority %#v",got)}
}
func TestRSH04ChangedOriginalRejected(t *testing.T){p,s,raw:=originalFixture();s.blob.Bytes=append(s.blob.Bytes,1);rejectOriginal(t,raw,p,s)}
func TestRSH04FakeGitBlobRejected(t *testing.T){p,s,raw:=originalFixture();s.blob.BlobSHA1=strings.Repeat("f",40);rejectOriginal(t,raw,p,s)}
func TestRSH04WrongSourcePathRejected(t *testing.T){p,s,raw:=originalFixture();s.blob.SourcePath="research/other.json";rejectOriginal(t,raw,p,s)}
func TestRSH04WrongSourceCommitRejected(t *testing.T){p,s,raw:=originalFixture();s.blob.SourceCommit=strings.Repeat("b",40);rejectOriginal(t,raw,p,s)}
func TestRSH04WrongIndexCommitRejectedBeforeRead(t *testing.T){
 p,s,_:=originalFixture();a:=sixLanes();a[0].SourceCommit=strings.Repeat("b",40)
 rejectOriginal(t,encode(a),p,s);if s.reads!=0{t.Fatal("invalid index queried source")}
}
func TestRSH04WrongReportedDigestRejectedBeforeRead(t *testing.T){
 p,s,_:=originalFixture();a:=sixLanes();a[0].ReportedSHA256=strings.Repeat("a",64)
 rejectOriginal(t,encode(a),p,s);if s.reads!=0{t.Fatal("bad digest queried source")}
}
func TestRSH04UnknownExperimentRejected(t *testing.T){
 p,s,raw:=originalFixture();p.ResearchID="not-here"
 rejectOriginal(t,raw,p,s);if s.reads!=0{t.Fatal("unknown source queried")}
}
func TestRSH04MissingSourceRejected(t *testing.T){p,_,raw:=originalFixture();rejectOriginal(t,raw,p,nil)}
func TestRSH04SourceTransportFailureRejected(t *testing.T){p,s,raw:=originalFixture();s.err=errors.New("offline");rejectOriginal(t,raw,p,s)}
func TestRSH04OversizedOriginalRejected(t *testing.T){p,s,raw:=originalFixture();s.blob.Bytes=make([]byte,MaxOriginalBytes+1);rejectOriginal(t,raw,p,s)}
func TestRSH04EmptyOriginalRejected(t *testing.T){p,s,raw:=originalFixture();s.blob.Bytes=nil;rejectOriginal(t,raw,p,s)}
func TestRSH04CancelledContextNoRead(t *testing.T){
 p,s,raw:=originalFixture();ctx,cancel:=context.WithCancel(context.Background());cancel()
 if _,err:=ObserveOriginalIntegrity(ctx,raw,p,s);err==nil{t.Fatal("cancel accepted")}
 if s.reads!=0{t.Fatal("cancel queried source")}
}
func TestRSH04BadExternalPinNoRead(t *testing.T){
 p,s,raw:=originalFixture();p.BlobSHA1="not-a-git-blob"
 rejectOriginal(t,raw,p,s);if s.reads!=0{t.Fatal("bad pin queried source")}
}
func TestRSH04FalseScientificAcceptanceNoRead(t *testing.T){
 p,s,_:=originalFixture();a:=sixLanes();a[0].ScientificAccepted=true
 rejectOriginal(t,encode(a),p,s);if s.reads!=0{t.Fatal("false science queried source")}
}
