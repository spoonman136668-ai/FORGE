package sourcebirth
import (
 "crypto/ed25519"
 "encoding/hex"
 "strings"
 "testing"
)

// All signing keys are deterministic NONPRODUCTION test fixtures. Passing this
// test NEVER establishes physical signer independence or live authority.
func massFixture()(Signed,Pins,ed25519.PrivateKey,ed25519.PrivateKey){
 ip,ik:=kp("mass-t16c-issuer-fixture")
 wp,wk:=kp("mass-t16c-witness-fixture")
 statement:=Statement{
  Schema:Schema,Lane:"MassResearch",Repository:"spoonman136668-ai/FORGE",
  OriginalID:"MASS-T16C-UNBORN-FIXTURE",SourceCommitSHA:strings.Repeat("a",40),
  SourceTreeSHA:strings.Repeat("b",40),PreregSHA256:strings.Repeat("c",64),
  CohortSHA256:strings.Repeat("d",64),ArchiveSHA256:strings.Repeat("e",64),
  AuthorityEpoch:7,BirthSequence:19,WitnessRevision:20,
  FrozenUnix:101,BirthUnix:103,
 }
 pins:=Pins{Lane:statement.Lane,OriginalID:statement.OriginalID,
  SourceCommitSHA:statement.SourceCommitSHA,SourceTreeSHA:statement.SourceTreeSHA,
  PreregSHA256:statement.PreregSHA256,CohortSHA256:statement.CohortSHA256,
  ArchiveSHA256:statement.ArchiveSHA256,AuthorityEpoch:7,MinBirthSequence:19,
  MinWitnessRevision:20,IssuerPublicKey:ip,WitnessPublicKey:wp}
 sign:=func(s Statement)(string,string){
  return hex.EncodeToString(ed25519.Sign(ik,signedPayload(IssuerDomain,s))),
   hex.EncodeToString(ed25519.Sign(wk,signedPayload(WitnessDomain,s)))
 }
 a,b:=sign(statement)
 return Signed{Statement:statement,IssuerSignatureHex:a,WitnessSignatureHex:b},
  pins,ik,wk
}
func TestMassT16CExactRepoAndDualSignatureStillNoAuthority(t *testing.T){
 s,p,_,_:=massFixture()
 observation,err:=Verify(s,p)
 if err!=nil||!observation.TwoSignaturesVerified||
  observation.PhysicallyIndependent||observation.PersistentFirstUseProven||
  observation.ScientificExecutionAuthorized||observation.CutoverAuthorized{
  t.Fatalf("mass fixture conferred authority: %+v %v",observation,err)
 }
}
func TestMassT16CFailureMatrix(t *testing.T){
 changes:=map[string]func(*Signed,*Pins){
  "wrong-repository":func(s *Signed,p *Pins){s.Statement.Repository="spoonman136668-ai/Mass"},
  "wrong-lane":func(s *Signed,p *Pins){s.Statement.Lane="Wingless"},
  "wrong-original":func(s *Signed,p *Pins){p.OriginalID="consumed"},
  "different-source":func(s *Signed,p *Pins){p.SourceTreeSHA=strings.Repeat("f",40)},
  "wrong-prereg":func(s *Signed,p *Pins){p.PreregSHA256=strings.Repeat("f",64)},
  "wrong-cohort":func(s *Signed,p *Pins){p.CohortSHA256=strings.Repeat("f",64)},
  "wrong-archive":func(s *Signed,p *Pins){p.ArchiveSHA256=strings.Repeat("f",64)},
  "stale-sequence":func(s *Signed,p *Pins){p.MinBirthSequence=20},
  "stale-witness":func(s *Signed,p *Pins){p.MinWitnessRevision=21},
  "reused-issuer-key":func(s *Signed,p *Pins){p.WitnessPublicKey=p.IssuerPublicKey},
  "bad-issuer-signature":func(s *Signed,p *Pins){s.IssuerSignatureHex=strings.Repeat("0",128)},
  "bad-witness-signature":func(s *Signed,p *Pins){s.WitnessSignatureHex=strings.Repeat("0",128)},
  "reversed-freeze":func(s *Signed,p *Pins){s.Statement.BirthUnix=100},
 }
 for name,fn:=range changes{
  t.Run(name,func(t *testing.T){
   s,p,_,_:=massFixture()
   fn(&s,&p)
   if _,err:=Verify(s,p);err==nil{t.Fatal("untrusted source accepted")}
  })
 }
}
func TestMassT16CBothAuthenticSignaturesOverWrongSourceStillRejected(t *testing.T){
 s,p,issuer,witness:=massFixture()
 s.Statement.SourceCommitSHA=strings.Repeat("f",40)
 s.IssuerSignatureHex=hex.EncodeToString(ed25519.Sign(issuer,signedPayload(IssuerDomain,s.Statement)))
 s.WitnessSignatureHex=hex.EncodeToString(ed25519.Sign(witness,signedPayload(WitnessDomain,s.Statement)))
 if _,err:=Verify(s,p);err==nil{t.Fatal("mismatched independently pinned source passed")}
}
func TestMassT16COriginalRepositoriesRemainDistinct(t *testing.T){
 for _,lane:=range []string{"Wingless","Yggdrasil","MassResearch"}{
  if repo(lane)==""{t.Fatal("supported repo missing",lane)}
 }
 if repo("MassResearch")==repo("Wingless")||repo("MassResearch")==repo("Yggdrasil")||
  repo("CKB")!=""||repo("KTRADE")!="" {
  t.Fatal("lanes collapsed into an unrelated repository")
 }
}
