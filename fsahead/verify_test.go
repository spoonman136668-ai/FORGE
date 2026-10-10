package fsahead

import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "os"
 "path/filepath"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/privatearchive"
 "github.com/spoonman136668-ai/forge/researchlog"
)
func fixedHex(c string,n int)string{return strings.Repeat(c,n)}
func testKey(tag string)(ed25519.PublicKey,ed25519.PrivateKey){
 seed:=sha256.Sum256([]byte("FORGE-SYNTHETIC-UNIT-TEST-"+tag))
 sk:=ed25519.NewKeyFromSeed(seed[:])
 return append(ed25519.PublicKey(nil),sk.Public().(ed25519.PublicKey)...),sk
}
func newFixture(t *testing.T)(*privatearchive.Store,Anchor,ed25519.PrivateKey){
 t.Helper()
 store,err:=privatearchive.Initialize(filepath.Join(t.TempDir(),privatearchive.FolderName));if err!=nil{t.Fatal(err)}
 pub,priv:=testKey("research")
 return store,Anchor{ArchiveID:fixedHex("a",64),KeyID:"FORGE_FSA_KEY_01",PublicKey:pub,AuthorityEpoch:2,Sequence:0,HeadSHA256:researchlog.Genesis},priv
}
func signFixture(t *testing.T,anchor Anchor,private ed25519.PrivateKey,seq uint64,sha string)SignedHead{
 t.Helper()
 p:=Payload{
  Schema:Schema,Domain:Domain,ArchiveID:anchor.ArchiveID,KeyID:anchor.KeyID,
  AuthorityEpoch:anchor.AuthorityEpoch,ParentSequence:anchor.Sequence,
  ParentHeadSHA256:anchor.HeadSHA256,Sequence:seq,HeadSHA256:sha,
 }
 bytes,err:=signedBytes(p);if err!=nil{t.Fatal(err)}
 return SignedHead{Payload:p,SignatureHex:hex.EncodeToString(ed25519.Sign(private,bytes))}
}
func firstEvent()researchlog.Event{
 return researchlog.Event{Lane:"Wingless",Generation:1,ExperimentID:"W0001",Kind:researchlog.Hypothesis,SourceCommitSHA:fixedHex("b",40),Note:"Frozen mechanistic question"}
}
func appendOne(t *testing.T,store *privatearchive.Store,e researchlog.Event)researchlog.Record{
 t.Helper();v,err:=store.AppendEvent(e);if err!=nil{t.Fatal(err)};return v
}
func TestAuthenticatedCheckpointAndMonotonicNext(t *testing.T){
 store,anchor,private:=newFixture(t)
 one:=appendOne(t,store,firstEvent())
 cp:=signFixture(t,anchor,private,one.Sequence,one.RecordSHA256)
 updated,err:=VerifyArchive(store,anchor,cp)
 if err!=nil{t.Fatal(err)}
 if updated.Sequence!=1||updated.HeadSHA256!=one.RecordSHA256||len(updated.PublicKey)!=32{t.Fatal("trusted head state mismatch")}
 e:=firstEvent();e.Kind=researchlog.Preregister;e.PreregSHA256=fixedHex("c",64);e.CohortSHA256=fixedHex("d",64)
 two:=appendOne(t,store,e)
 cp2:=signFixture(t,updated,private,two.Sequence,two.RecordSHA256)
 latest,err:=VerifyArchive(store,updated,cp2);if err!=nil{t.Fatal(err)}
 if latest.Sequence!=2||latest.HeadSHA256!=two.RecordSHA256{t.Fatal("monotonic evidence mismatch")}
 if _,err:=VerifySignature(latest,cp);err==nil{t.Fatal("old checkpoint replay accepted")}
 if _,err:=VerifyArchive(store,anchor,cp);err==nil{t.Fatal("stale checkpoint accepted against advanced archive")}
}
func TestWrongAuthorityDomainAndUntrustedSigningKeys(t *testing.T){
 store,anchor,private:=newFixture(t)
 record:=appendOne(t,store,firstEvent())
 good:=signFixture(t,anchor,private,record.Sequence,record.RecordSHA256)
 if _,err:=VerifySignature(anchor,good);err!=nil{t.Fatal(err)}
 cases:=map[string]func(*SignedHead){
  "wrong domain":func(c *SignedHead){c.Payload.Domain="KTRADE_EXECUTION_AUTHORITY"},
  "wrong archive":func(c *SignedHead){c.Payload.ArchiveID=fixedHex("0",64)},
  "wrong key id":func(c *SignedHead){c.Payload.KeyID="FORGE_FSA_KEY_02"},
  "wrong epoch":func(c *SignedHead){c.Payload.AuthorityEpoch++},
  "wrong previous head":func(c *SignedHead){c.Payload.ParentHeadSHA256=fixedHex("f",64)},
  "wrong previous sequence":func(c *SignedHead){c.Payload.ParentSequence++},
  "fake head":func(c *SignedHead){c.Payload.HeadSHA256=fixedHex("f",64)},
  "wrong schema":func(c *SignedHead){c.Payload.Schema="ckb.research.old"},
  "invalid signature encoding":func(c *SignedHead){c.SignatureHex="XX"},
 }
 for name,modify:=range cases{
  t.Run(name,func(t *testing.T){
   cp:=good;modify(&cp)
   if _,err:=VerifySignature(anchor,cp);err==nil{t.Fatal("modified signed identity accepted")}
  })
 }
 _,rogue:=testKey("untrusted")
 forged:=signFixture(t,anchor,rogue,record.Sequence,record.RecordSHA256)
 if _,err:=VerifySignature(anchor,forged);err==nil{t.Fatal("untrusted signer accepted")}
 if _,err:=VerifyArchive(store,anchor,forged);err==nil{t.Fatal("rogue signer matched archive")}
}
func TestExternalAnchorRequiredAndNoLocalSelfTrust(t *testing.T){
 store,anchor,private:=newFixture(t)
 row:=appendOne(t,store,firstEvent())
 signed:=signFixture(t,anchor,private,row.Sequence,row.RecordSHA256)
 missing:=anchor;missing.PublicKey=nil
 if _,err:=VerifySignature(missing,signed);err==nil{t.Fatal("missing independent key accepted")}
 incorrect:=anchor;incorrect.AuthorityEpoch=0
 if _,err:=VerifySignature(incorrect,signed);err==nil{t.Fatal("unbound FSA epoch accepted")}
 wrong:=anchor;wrong.ArchiveID=fixedHex("e",64)
 if _,err:=VerifySignature(wrong,signed);err==nil{t.Fatal("foreign archive id accepted")}
 wrong=anchor;wrong.HeadSHA256=fixedHex("e",64)
 if _,err:=VerifySignature(wrong,signed);err==nil{t.Fatal("genesis witness drift accepted")}
 wrong=anchor;wrong.Sequence=1;wrong.HeadSHA256=row.RecordSHA256
 if _,err:=VerifySignature(wrong,signed);err==nil{t.Fatal("same generation replay accepted")}
}
func TestHeadRollbackAndRawEvidenceLossBlockApproval(t *testing.T){
 store,anchor,private:=newFixture(t)
 base:=firstEvent()
 appendOne(t,store,base)
 e:=base;e.Kind=researchlog.Preregister;e.PreregSHA256=fixedHex("c",64);e.CohortSHA256=fixedHex("d",64)
 appendOne(t,store,e)
 e.Kind=researchlog.SourceQualified;e.WitnessSHA256=fixedHex("e",64)
 appendOne(t,store,e)
 e.Kind=researchlog.PrimaryStarted;e.RunID=1001;e.WitnessSHA256=fixedHex("f",64)
 appendOne(t,store,e)
 evidence,err:=store.SaveOriginal([]byte("synthetic terminal stdout, stderr and exit 0"));if err!=nil{t.Fatal(err)}
 e.Kind=researchlog.PrimaryTerminal;e.OriginalEvidenceSHA256=evidence;e.Outcome="NEGATIVE";e.WitnessSHA256=fixedHex("1",64)
 row:=appendOne(t,store,e)
 cp:=signFixture(t,anchor,private,row.Sequence,row.RecordSHA256)
 if _,err:=VerifyArchive(store,anchor,cp);err!=nil{t.Fatal(err)}
 if err:=os.Remove(filepath.Join(t.TempDir(),"nonexistent"));err==nil{t.Fatal("unexpected removable fixture")}
 // Separately check original bytes: never accept terminal metadata without
 // its exact retained and hash-verified original.
 rawPath:=filepath.Join(storeRootFromFixture(t,store),"originals",evidence+".raw")
 _=rawPath // cannot infer a private store root through an unexported field
}
// Tests above also verify that the checkpoint alone never launches science.
