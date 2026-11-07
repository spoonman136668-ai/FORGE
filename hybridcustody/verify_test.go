package hybridcustody

import (
 "bytes"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/json"
 "strings"
 "testing"
)
func testInput()([]byte,[]byte,Statement,Expected,ed25519.PrivateKey){
 protocol:=[]byte("{\"frozen\":\"s24\",\"seeds\":\"development-only\"}")
 artifact:=[]byte("{\"engineering_checks\":96,\"scientific_executed\":false}")
 seed:=sha256.Sum256([]byte("synthetic-test-only-signature-seed"))
 private:=ed25519.NewKeyFromSeed(seed[:])
 expected:=Expected{SourceSHA:strings.Repeat("a",40),PullRequest:39,
  ProtocolPath:"experiments/g7_s24_frozen_good_views.json",
  TrustedPublicKey:private.Public().(ed25519.PublicKey)}
 s:=Statement{
  Schema:StatementSchema,Repository:Project,PullRequest:39,
  PullRequestURL:"https://github.com/"+Project+"/pull/39",
  SourceSHA:expected.SourceSHA,ProtocolPath:expected.ProtocolPath,
  ProtocolSHA256:digest(protocol),EvidenceKind:"ENGINEERING_RECEIPT",
  ArtifactName:"s24_engineering_receipt.json",ArtifactSHA256:digest(artifact),
  WorkflowRunID:42413529245,WorkflowAttempt:1,
 }
 return protocol,artifact,s,expected,private
}
func signed(s Statement,private ed25519.PrivateKey)([]byte,[]byte){
 raw,_:=json.Marshal(s)
 signature:=ed25519.Sign(private,append([]byte(SignatureDomain),raw...))
 return raw,signature
}
func TestDetachedEngineeringReceiptConsistencyIsNotScience(t *testing.T){
 protocol,artifact,s,expected,key:=testInput()
 raw,signature:=signed(s,key)
 r,err:=Verify(protocol,artifact,raw,signature,expected)
 if err!=nil {t.Fatal(err)}
 if r.Schema!=ReportSchema||r.Mode!="SIGNED_CONSISTENCY_ONLY_NO_SCIENTIFIC_OR_EXECUTION_AUTHORITY"||
  !r.SignatureVerified||!r.PayloadDigestsMatch||
  r.GitHubSourceAuthenticated||r.FirstUseAuthenticated||
  r.ExecutionAuthorized||r.ScientificAccepted||
  r.PublicKeySHA256!=digest(expected.TrustedPublicKey)||
  r.ArtifactSHA256!=digest(artifact){t.Fatalf("authority elevated or evidence corrupted: %+v",r)}
 again,err:=Verify(protocol,artifact,raw,signature,expected)
 if err!=nil||again.AttestationSHA256!=r.AttestationSHA256 {t.Fatal("non-deterministic evidence",err)}
}
func TestProtocolAttestationOnlyHasNoRunOrTrainingClaim(t *testing.T){
 protocol,_,s,expected,key:=testInput()
 s.EvidenceKind="FROZEN_PROTOCOL"
 s.ArtifactName="protocol"
 s.ArtifactSHA256=s.ProtocolSHA256
 s.WorkflowRunID=0
 s.WorkflowAttempt=0
 raw,signature:=signed(s,key)
 report,err:=Verify(protocol,protocol,raw,signature,expected)
 if err!=nil||report.WorkflowRunID!=0||report.FirstUseAuthenticated||
  report.ExecutionAuthorized||report.ScientificAccepted{
  t.Fatal("protocol attestation elevated to execution",err)
 }
}
func TestHybridEvidenceRejectsSignatureAndCustodyDrift(t *testing.T){
 protocol,artifact,s,expected,key:=testInput()
 originalRaw,originalSig:=signed(s,key)
 badSeed:=sha256.Sum256([]byte("other-synthetic-test-key"))
 other:=ed25519.NewKeyFromSeed(badSeed[:]).Public().(ed25519.PublicKey)
 cases:=[]struct{
  name string
  mutate func(*Statement,*Expected,*[]byte,*[]byte,*[]byte,*[]byte)
 }{
  {"alter protocol",func(_ *Statement,_ *Expected,p,_,_,_ *[]byte){*p=[]byte("different")}},
  {"alter artifact",func(_ *Statement,_ *Expected,_,a,_,_ *[]byte){*a=[]byte("different")}},
  {"wrong repository",func(s *Statement,_ *Expected,_,_,_,_ *[]byte){s.Repository="untrusted/Other"}},
  {"wrong PR",func(s *Statement,_ *Expected,_,_,_,_ *[]byte){s.PullRequest=40;s.PullRequestURL="https://github.com/"+Project+"/pull/40"}},
  {"wrong head",func(s *Statement,_ *Expected,_,_,_,_ *[]byte){s.SourceSHA=strings.Repeat("b",40)}},
  {"wrong protocol path",func(s *Statement,_ *Expected,_,_,_,_ *[]byte){s.ProtocolPath="experiments/g7_s25_frozen_contradiction_ttt.json"}},
  {"path traversal",func(s *Statement,e *Expected,_,_,_,_ *[]byte){s.ProtocolPath="experiments/g7_s24_../bad.json";e.ProtocolPath=s.ProtocolPath}},
  {"wrong protocol digest",func(s *Statement,_ *Expected,_,_,_,_ *[]byte){s.ProtocolSHA256=strings.Repeat("f",64)}},
  {"invalid evidence kind",func(s *Statement,_ *Expected,_,_,_,_ *[]byte){s.EvidenceKind="SCIENTIFIC_PASS"}},
  {"invalid run id",func(s *Statement,_ *Expected,_,_,_,_ *[]byte){s.WorkflowRunID=0}},
  {"invalid run attempt",func(s *Statement,_ *Expected,_,_,_,_ *[]byte){s.WorkflowAttempt=0}},
  {"unknown name",func(s *Statement,_ *Expected,_,_,_,_ *[]byte){s.ArtifactName="../private.json"}},
  {"changed expected head",func(_ *Statement,e *Expected,_,_,_,_ *[]byte){e.SourceSHA=strings.Repeat("c",40)}},
  {"changed expected PR",func(_ *Statement,e *Expected,_,_,_,_ *[]byte){e.PullRequest=40}},
  {"other verifier key",func(_ *Statement,e *Expected,_,_,_,_ *[]byte){e.TrustedPublicKey=other}},
  {"no verifier key",func(_ *Statement,e *Expected,_,_,_,_ *[]byte){e.TrustedPublicKey=nil}},
  {"wrong signature",func(_ *Statement,_ *Expected,_,_,_,sig *[]byte){(*sig)[0]^=0xff}},
  {"no signature",func(_ *Statement,_ *Expected,_,_,_,sig *[]byte){*sig=nil}},
  {"trailing JSON",func(_ *Statement,_ *Expected,_,_,raw,_ *[]byte){*raw=append(*raw,[]byte("{}")...)}},
  {"duplicate JSON key",func(_ *Statement,_ *Expected,_,_,raw,_ *[]byte){*raw=bytes.Replace(*raw,[]byte(`"schema"`),[]byte(`"schema":"x","schema"`),1)}},
  {"case folded duplicate JSON key",func(_ *Statement,_ *Expected,_,_,raw,_ *[]byte){*raw=bytes.Replace(*raw,[]byte(`"schema"`),[]byte(`"Schema":"x","schema"`),1)}},
  {"unknown JSON key",func(_ *Statement,_ *Expected,_,_,raw,_ *[]byte){*raw=bytes.Replace(*raw,[]byte(`"schema"`),[]byte(`"execute":true,"schema"`),1)}},
  {"oversized protocol",func(_ *Statement,_ *Expected,p,_,_,_ *[]byte){*p=bytes.Repeat([]byte("x"),MaxProtocolBytes+1)}},
  {"oversized artifact",func(_ *Statement,_ *Expected,_,a,_,_ *[]byte){*a=bytes.Repeat([]byte("x"),MaxArtifactBytes+1)}},
 }
 for _,tc:=range cases{
  t.Run(tc.name,func(t *testing.T){
   p:=append([]byte(nil),protocol...)
   a:=append([]byte(nil),artifact...)
   e:=expected
   e.TrustedPublicKey=append(ed25519.PublicKey(nil),expected.TrustedPublicKey...)
   ss:=s
   raw:=append([]byte(nil),originalRaw...)
   sig:=append([]byte(nil),originalSig...)
   tc.mutate(&ss,&e,&p,&a,&raw,&sig)
   // Changes to fields are signed by the same test fixture issuer, so
   // rejections test semantic constraints rather than signature failure.
   if ss!=s{raw,sig=signed(ss,key)}
   if _,err:=Verify(p,a,raw,sig,e);err==nil{
    t.Fatal("unsafe evidence was accepted")
   }
  })
 }
}
