package fsaprovision
import (
 "bytes"
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "errors"
 "strings"
 "testing"
)
func drillFixture(t *testing.T)(*Verifier,Bundle,DrillPin,SignedDrillReport) {
 t.Helper()
 base,bundle,_:=fixture(t)
 v,err:=New(base);if err!=nil{t.Fatal(err)}
 private:=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{9},32))
 pin:=DrillPin{ChallengeSHA256:strings.Repeat("e",64),
  SourceCommitSHA:strings.Repeat("a",40),
  AuditorPublicKey:private.Public().(ed25519.PublicKey)}
 report:=DrillReport{Schema:DrillSchema,SourceCommitSHA:pin.SourceCommitSHA,
  BundleSHA256:base.BundleSHA256,ArchiveID:base.ArchiveID,
  ProvisioningEpoch:base.ProvisioningEpoch,ChallengeSHA256:pin.ChallengeSHA256}
 for _,name:=range caseOrder() {
  x:=FaultRecord{Case:name,ChallengeSHA256:pin.ChallengeSHA256,
   BeforeHeadSHA256:strings.Repeat("d",64),AfterHeadSHA256:strings.Repeat("d",64),
   BeforeFloorRevision:5,AfterFloorRevision:5,
   IsolationTraceSHA256:strings.Repeat("1",64),RecoveryTraceSHA256:strings.Repeat("2",64),
   ExternalRetentionSHA256:strings.Repeat("3",64),
   FailClosedObserved:true,NoReplayObserved:true,NoUnauthorizedAdvanceObserved:true}
  if name==CaseHostReplacement {x.ReplacementProvisionSHA256=strings.Repeat("9",64)}
  report.Cases=append(report.Cases,x)
 }
 raw,_:=json.Marshal(report)
 signed:=SignedDrillReport{Report:report,AuditorSignatureHex:hex.EncodeToString(ed25519.Sign(private,append([]byte(drillDomain),raw...)))}
 rawSigned,_:=json.Marshal(signed)
 pin.ReportSHA256=sha256Text(rawSigned)
 return v,bundle,pin,signed
}
func signDrill(t *testing.T,pin *DrillPin,signed *SignedDrillReport){
 t.Helper()
 private:=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{9},32))
 raw,_:=json.Marshal(signed.Report)
 signed.AuditorSignatureHex=hex.EncodeToString(ed25519.Sign(private,append([]byte(drillDomain),raw...)))
 encoded,_:=json.Marshal(signed)
 pin.ReportSHA256=sha256Text(encoded)
}
func TestDrillReportCryptographicDocumentAndCanonicalWire(t *testing.T){
 v,b,p,s:=drillFixture(t)
 got,err:=v.VerifyDrillReport(b,p,s)
 if err!=nil||got.CheckedCases!=5||got.BundleSHA256!=s.Report.BundleSHA256{t.Fatalf("valid document rejected %+v %v",got,err)}
 raw,_:=json.Marshal(s)
 if _,err=v.VerifyDrillJSON(b,p,raw);err!=nil{t.Fatal(err)}
 p.AuditorPublicKey[0]^=1
 if _,err=v.VerifyDrillReport(b,p,s);!errors.Is(err,ErrDrillUnverified){t.Fatal("tampered auditor pin accepted",err)}
}
func TestDrillReportRefusesMissingOrDangerousClaims(t *testing.T){
 for _,tc:=range []struct{name string; mutate func(*DrillReport)}{
  {"missing_case",func(r *DrillReport){r.Cases=r.Cases[:4]}},
  {"reordered",func(r *DrillReport){r.Cases[0],r.Cases[1]=r.Cases[1],r.Cases[0]}},
  {"duplicate",func(r *DrillReport){r.Cases[1]=r.Cases[0]}},
  {"wrong_challenge",func(r *DrillReport){r.Cases[0].ChallengeSHA256=strings.Repeat("f",64)}},
  {"unwitnessed_outage",func(r *DrillReport){r.Cases[1].FailClosedObserved=false}},
  {"replayed_cas",func(r *DrillReport){r.Cases[2].NoReplayObserved=false}},
  {"unauthorized_advance",func(r *DrillReport){r.Cases[3].NoUnauthorizedAdvanceObserved=false}},
  {"head_changed",func(r *DrillReport){r.Cases[0].AfterHeadSHA256=strings.Repeat("f",64)}},
  {"floor_changed",func(r *DrillReport){r.Cases[0].AfterFloorRevision++}},
  {"host_replacement_without_reprovision",func(r *DrillReport){r.Cases[4].ReplacementProvisionSHA256=""}},
  {"same_reprovision_bundle",func(r *DrillReport){r.Cases[4].ReplacementProvisionSHA256=r.BundleSHA256}},
  {"unexpected_reprovision",func(r *DrillReport){r.Cases[0].ReplacementProvisionSHA256=strings.Repeat("9",64)}},
  {"lost_external_retention",func(r *DrillReport){r.Cases[1].ExternalRetentionSHA256=""}},
  {"foreign_bundle",func(r *DrillReport){r.BundleSHA256=strings.Repeat("f",64)}},
 } {
  t.Run(tc.name,func(t *testing.T){v,b,p,s:=drillFixture(t);tc.mutate(&s.Report);signDrill(t,&p,&s)
   if _,err:=v.VerifyDrillReport(b,p,s);!errors.Is(err,ErrDrillUnverified){t.Fatal("invalid report accepted",err)}
  })
 }
}
func TestDrillReportRefusesSignerAndPinDrift(t *testing.T){
 v,b,p,s:=drillFixture(t)
 p.AuditorPublicKey=v.pin.AuthorityAttestor
 if _,err:=v.VerifyDrillReport(b,p,s);!errors.Is(err,ErrDrillUnverified){t.Fatal("role attestor reused",err)}
 v,b,p,s=drillFixture(t);p.ChallengeSHA256=strings.Repeat("f",64)
 if _,err:=v.VerifyDrillReport(b,p,s);!errors.Is(err,ErrDrillUnverified){t.Fatal("challenge substituted",err)}
 v,b,p,s=drillFixture(t);p.ReportSHA256=strings.Repeat("f",64)
 if _,err:=v.VerifyDrillReport(b,p,s);!errors.Is(err,ErrDrillUnverified){t.Fatal("immutable report digest mismatch",err)}
 v,b,p,s=drillFixture(t);p.SourceCommitSHA=strings.Repeat("e",40)
 if _,err:=v.VerifyDrillReport(b,p,s);!errors.Is(err,ErrDrillUnverified){t.Fatal("source revision substituted",err)}
 v,b,p,s=drillFixture(t);s.AuditorSignatureHex=strings.Repeat("0",128)
 if _,err:=v.VerifyDrillReport(b,p,s);!errors.Is(err,ErrDrillUnverified){t.Fatal("forged auditor signature accepted",err)}
}
func TestDrillReportRejectsAmbiguousJSON(t *testing.T){
 v,b,p,s:=drillFixture(t);raw,_:=json.Marshal(s)
 bad:=[][]byte{
  append(bytes.Clone(raw),'\n'),
  append(bytes.Clone(raw),[]byte("{}")...),
  bytes.Replace(raw,[]byte(`"report":`),[]byte(`"extra":5,"report":`),1),
  []byte(`{"report":null,"report":null}`),
  bytes.Repeat([]byte("z"),MaxDrillBytes+1),
 }
 for _,sample:=range bad {
  if _,err:=v.VerifyDrillJSON(b,p,sample);!errors.Is(err,ErrDrillUnverified){t.Fatal("noncanonical input accepted",err)}
 }
}
