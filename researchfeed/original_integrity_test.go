package researchfeed

import(
 "archive/zip"
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "strings"
 "testing"
)

func makeOriginalZIP(t *testing.T, files map[string][]byte)[]byte{
 t.Helper()
 var b bytes.Buffer
 z:=zip.NewWriter(&b)
 for name,data:=range files{
  writer,err:=z.Create(name)
  if err!=nil{t.Fatal(err)}
  if _,err=writer.Write(data);err!=nil{t.Fatal(err)}
 }
 if err:=z.Close();err!=nil{t.Fatal(err)}
 return b.Bytes()
}
func originalFixture(t *testing.T)([]byte,OriginalPin,RunReceipt,[]byte){
 t.Helper()
 payload:=[]byte(`{"schema":"forge.fixture.v1","classification":"NO_BENEFIT","measurements":[2,3,5]}`)
 archive:=makeOriginalZIP(t,map[string][]byte{"Y056-original.json":payload})
 pin:=OriginalPin{
  Lane:"Yggdrasil",ResearchID:"Y056",
  SourceRepo:"spoonman136668-ai/Yggdrasil",SourceCommit:strings.Repeat("b",40),
  SourcePath:"research/contrib/chatgpt/20261013-native-y056-perception-ablation/execute.py",
  WorkflowRunID:38381070805,ArtifactID:11802529893,
  ArtifactName:"Y056-original-native-perception-ablation",FileName:"Y056-original.json",
  ZipSHA256:sumHex(archive),RawSHA256:sumHex(payload),
  ExpectedClassification:"NO_BENEFIT",ExpectedOutcome:"NEGATIVE",
 }
 receipt:=RunReceipt{SourceRepo:pin.SourceRepo,HeadSHA:pin.SourceCommit,
  WorkflowRunID:pin.WorkflowRunID,ArtifactID:pin.ArtifactID,
  ArtifactName:pin.ArtifactName,Status:"completed",Conclusion:"success"}
 inputs:=sixLanes()
 inputs[1]=Candidate{
  Lane:pin.Lane,ResearchID:pin.ResearchID,SourceRepo:pin.SourceRepo,
  SourceCommit:pin.SourceCommit,SourcePath:pin.SourcePath,Outcome:"NEGATIVE",
  EvidenceState:"REPORTED_BYTES_UNAUTHENTICATED",ReportedSHA256:pin.RawSHA256,
 }
 raw:=encode(inputs)
 return raw,pin,receipt,archive
}
func rejectOriginal(t *testing.T,index []byte,p OriginalPin,r RunReceipt,zipBytes []byte){
 t.Helper()
 o,e:=VerifyOriginalArtifact(index,p,r,zipBytes)
 if e==nil || o.Schema!=""||o.OriginalRawHashVerified||o.AdvisoryOnly{
  t.Fatalf("original integrity gate accepted invalid material: %#v, %v",o,e)
 }
}
func TestRSH04ExactArchivePinPreservesScientificNegative(t *testing.T){
 idx,p,run,archive:=originalFixture(t)
 got,err:=VerifyOriginalArtifact(idx,p,run,archive)
 if err!=nil{t.Fatal(err)}
 if !got.AdvisoryOnly||!got.EvidenceZIPHashVerified||!got.OriginalRawHashVerified||
 !got.SourceRunMetadataMatched||got.PreservedClassification!="NO_BENEFIT"||
 got.PreservedOutcome!="NEGATIVE"||got.OriginalBytesAuthenticated||
 got.FirstUseAuthorized||got.ScientificAccepted||got.DispatchAuthorized||
 got.FSAWitnessAuthenticated||got.Schema!="forge.rsh04-original-integrity-observation.v1"{
  t.Fatalf("negative result promoted: %#v",got)
 }
}
func TestRSH04DeniedOnZIPAndRawDigestDrift(t *testing.T){
 idx,p,run,archive:=originalFixture(t)
 broken:=append([]byte(nil),archive...)
 broken[len(broken)/2]^=0x02
 rejectOriginal(t,idx,p,run,broken)
 p.ZipSHA256=strings.Repeat("a",64)
 rejectOriginal(t,idx,p,run,archive)
 idx,p,run,archive=originalFixture(t)
 p.RawSHA256=strings.Repeat("b",64)
 rejectOriginal(t,idx,p,run,archive)
}
func TestRSH04RunProvenanceTamperDenied(t *testing.T){
 idx,p,r,z:=originalFixture(t)
 for _,change:=range []func(*RunReceipt){
  func(x *RunReceipt){x.HeadSHA=strings.Repeat("a",40)},
  func(x *RunReceipt){x.SourceRepo="spoonman136668-ai/FORGE"},
  func(x *RunReceipt){x.WorkflowRunID++},
  func(x *RunReceipt){x.ArtifactID++},
  func(x *RunReceipt){x.ArtifactName="wrong"},
  func(x *RunReceipt){x.Status="queued"},
  func(x *RunReceipt){x.Conclusion="failure"},
 }{
  x:=r;change(&x);rejectOriginal(t,idx,p,x,z)
 }
}
func TestRSH04RejectWorkerIndexAliasAndFalseAuthority(t *testing.T){
 idx,p,run,z:=originalFixture(t)
 inputs:=sixLanes()
 inputs[1]=Candidate{Lane:p.Lane,ResearchID:p.ResearchID,SourceRepo:p.SourceRepo,
  SourceCommit:p.SourceCommit,SourcePath:p.SourcePath,Outcome:p.ExpectedOutcome,
  EvidenceState:"SOURCE_POINTER_ONLY"}
 for _,change:=range []func(*Candidate){
  func(x *Candidate){x.SourceCommit=strings.Repeat("a",40)},
  func(x *Candidate){x.SourcePath="research/forged.json"},
  func(x *Candidate){x.Outcome="POSITIVE"},
  func(x *Candidate){x.ReportedSHA256=strings.Repeat("d",64)},
  func(x *Candidate){x.ScientificAccepted=true},
  func(x *Candidate){x.ExecuteRequested=true},
 }{
  x:=append([]Candidate(nil),inputs...)
  change(&x[1])
  rejectOriginal(t,encode(x),p,run,z)
 }
 idx=append(idx,[]byte(" {}")...)
 rejectOriginal(t,idx,p,run,z)
}
func TestRSH04PinClassificationNotOriginalClassification(t *testing.T){
 idx,p,run,z:=originalFixture(t)
 p.ExpectedClassification="POSITIVE"
 rejectOriginal(t,idx,p,run,z)
 idx,p,run,z=originalFixture(t)
 p.ExpectedOutcome="POSITIVE"
 rejectOriginal(t,idx,p,run,z)
 idx,p,run,z=originalFixture(t)
 p.Lane="BIO"
 rejectOriginal(t,idx,p,run,z)
}
func TestRSH04DuplicateZIPEntryDenied(t *testing.T){
 idx,p,run,_:=originalFixture(t)
 payload:=[]byte(`{"classification":"NO_BENEFIT"}`)
 z:=makeOriginalZIP(t,map[string][]byte{"Y056-original.json":payload,"evil.json":payload})
 p.ZipSHA256=sumHex(z);p.RawSHA256=sumHex(payload)
 rejectOriginal(t,idx,p,run,z)
}
func TestRSH04ArchivePathTraversalDenied(t *testing.T){
 idx,p,run,_:=originalFixture(t)
 payload:=[]byte(`{"classification":"NO_BENEFIT"}`)
 z:=makeOriginalZIP(t,map[string][]byte{"../Y056-original.json":payload})
 p.ZipSHA256=sumHex(z);p.RawSHA256=sumHex(payload)
 rejectOriginal(t,idx,p,run,z)
}
func TestRSH04MalformedOrDuplicateJSONDenied(t *testing.T){
 idx,p,run,_:=originalFixture(t)
 for _,payload:=range [][]byte{
  []byte(`{"classification":"NO_BENEFIT","classification":"POSITIVE"}`),
  []byte(`{"Classification":"NO_BENEFIT","classification":"POSITIVE"}`),
  []byte(`{"classification":"NO_BENEFIT"`),
 }{
  z:=makeOriginalZIP(t,map[string][]byte{p.FileName:payload})
  pin:=p;pin.ZipSHA256=sumHex(z);pin.RawSHA256=sumHex(payload)
  rejectOriginal(t,idx,pin,run,z)
 }
}
func TestRSH04MissingOriginalAndOversizeDenied(t *testing.T){
 idx,p,run,_:=originalFixture(t)
 rejectOriginal(t,idx,p,run,nil)
 rejectOriginal(t,idx,p,run,make([]byte,MaxOriginalArchiveBytes+1))
}
func TestRSH04DoesNotMutateExistingSixLaneInput(t *testing.T){
 idx,p,run,z:=originalFixture(t)
 orig:=append([]byte(nil),idx...)
 _,err:=VerifyOriginalArtifact(idx,p,run,z)
 if err!=nil||!bytes.Equal(idx,orig){t.Fatal("original index mutated",err)}
 view,err:=PreviewCandidates(idx)
 if err!=nil||len(view.Entries)!=6||!view.AdvisoryOnly{t.Fatal("six-lane preview damaged",err)}
}
// Type safety: SHA pins are lowercase, strict length and cannot be empty.
func TestRSH04StrictPinsAndEvidenceState(t *testing.T){
 idx,p,run,z:=originalFixture(t)
 p.SourceCommit="main"
 rejectOriginal(t,idx,p,run,z)
 idx,p,run,z=originalFixture(t)
 p.ArtifactID=0
 rejectOriginal(t,idx,p,run,z)
 idx,p,run,z=originalFixture(t)
 p.RawSHA256=strings.ToUpper(p.RawSHA256)
 rejectOriginal(t,idx,p,run,z)
}
func TestRSH04CanonicalHashes(t *testing.T){
 digest:=sha256.Sum256([]byte("test"))
 if hex.EncodeToString(digest[:])!=sumHex([]byte("test")){t.Fatal("hash mismatch")}
}
func TestRSH04ObservationRoundTripsButDoesNotGrantAuthority(t *testing.T){
 idx,p,run,z:=originalFixture(t)
 view,err:=VerifyOriginalArtifact(idx,p,run,z)
 if err!=nil{t.Fatal(err)}
 bytes,err:=json.Marshal(view)
 if err!=nil{t.Fatal(err)}
 var decoded OriginalIntegrityObservation
 if err=json.Unmarshal(bytes,&decoded);err!=nil||decoded.OriginalBytesAuthenticated||
 decoded.FSAWitnessAuthenticated||decoded.ScientificAccepted||decoded.DispatchAuthorized{
  t.Fatalf("serialized receipt gained authority: %v %#v",err,decoded)
 }
}
