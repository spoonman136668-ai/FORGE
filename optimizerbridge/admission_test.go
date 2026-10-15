package optimizerbridge

import (
 "encoding/json"
 "reflect"
 "testing"
)

func makeSignedAuditExport(t *testing.T)(
 SignedExport,ExternalTrust,[2][]byte,[]LanePins,[2]SignedSelectionAudit,[2]SelectionAuditPin,
) {
 t.Helper()
 export,trust,raw,pins,_:=makePinnedExport(t)
 var audits [2]SignedSelectionAudit
 var auditPins [2]SelectionAuditPin
 for i,lane:=range []string{"Wingless","Yggdrasil"}{
  _,p,a,ap,_,_:=signedAuditFixture(t,lane)
  if !reflect.DeepEqual(p,pins[i]){t.Fatal("fixture history drift")}
  audits[i]=a
  auditPins[i]=ap
 }
 return export,trust,raw,pins,audits,auditPins
}
func TestSignedTwoLaneShadowAdmissionIsNonauthorizing(t *testing.T){
 e,p,raw,pins,a,ap:=makeSignedAuditExport(t)
 first,err:=EvaluatePinnedExportWithAudits(e,p,raw,pins,a,ap)
 if err!=nil{t.Fatal(err)}
 again,err:=EvaluatePinnedExportWithAudits(e,p,raw,pins,a,ap)
 if err!=nil||!reflect.DeepEqual(first,again){t.Fatal("non-deterministic report",err)}
 if first.Mode!="EXTERNAL_EXPORT_AND_SIGNED_ASSIGNMENT_CLAIMS_SHADOW_ONLY"||
  len(first.SelectionAudits)!=2||len(first.HistoricalComparisons)!=2||
  first.ScientificImprovementEstablished||first.ScientificAccepted||
  first.DispatchAuthorized||first.CompleteFirstUseReconciliationVerified||
  first.RemoteReadOperationallyWitnessed||first.Shadow.FirstUseConsumed {
   t.Fatalf("unearned admission: %+v",first)
 }
 for _,c:=range first.HistoricalComparisons{
  if c.Lane==""||!c.OutcomeEvidenceFullyPreserved||
   c.CausalImprovementEstablished||c.ProspectiveGeneralizationEstablished||
   len(c.BaselineFinalists)==0||len(c.ParetoFinalists)==0 {
   t.Fatalf("incorrect historical label: %+v",c)
  }
 }
 // Output must be deterministic as JSON too.
 j1,_:=json.Marshal(first);j2,_:=json.Marshal(again)
 if string(j1)!=string(j2){t.Fatal("unstable shadow report bytes")}
}
func TestSignedTwoLaneShadowAuditFailuresAreAtomic(t *testing.T){
 type change func(*SignedExport,*ExternalTrust,*[2][]byte,*[]LanePins,*[2]SignedSelectionAudit,*[2]SelectionAuditPin)
 cases:=[]struct{name string;mutate change}{
  {"missing auditor",func(e *SignedExport,p *ExternalTrust,r *[2][]byte,l *[]LanePins,a *[2]SignedSelectionAudit,ap *[2]SelectionAuditPin){ap[1].IndependentAuditorPublicKeyHex=""}},
  {"same auditor key",func(e *SignedExport,p *ExternalTrust,r *[2][]byte,l *[]LanePins,a *[2]SignedSelectionAudit,ap *[2]SelectionAuditPin){ap[1].IndependentAuditorPublicKeyHex=ap[0].IndependentAuditorPublicKeyHex}},
  {"missing audit",func(e *SignedExport,p *ExternalTrust,r *[2][]byte,l *[]LanePins,a *[2]SignedSelectionAudit,ap *[2]SelectionAuditPin){a[0]=SignedSelectionAudit{}}},
  {"wrong audit pin",func(e *SignedExport,p *ExternalTrust,r *[2][]byte,l *[]LanePins,a *[2]SignedSelectionAudit,ap *[2]SelectionAuditPin){ap[0].AuditSHA256=shaHex([]byte("wrong"))}},
  {"history drift",func(e *SignedExport,p *ExternalTrust,r *[2][]byte,l *[]LanePins,a *[2]SignedSelectionAudit,ap *[2]SelectionAuditPin){r[1]=[]byte("{}")}},
  {"auditor matches foreign history signer",func(e *SignedExport,p *ExternalTrust,r *[2][]byte,l *[]LanePins,a *[2]SignedSelectionAudit,ap *[2]SelectionAuditPin){ap[0].IndependentAuditorPublicKeyHex=(*l)[1].IndependentEd25519PublicKeyHex}},
  {"duplicate event across lanes",func(e *SignedExport,p *ExternalTrust,r *[2][]byte,l *[]LanePins,a *[2]SignedSelectionAudit,ap *[2]SelectionAuditPin){
    a[1].Audit.Entries[0].AssignmentEventSHA256=a[0].Audit.Entries[0].AssignmentEventSHA256
    _,_,_,_,_,key:=signedAuditFixture(t,"Yggdrasil")
    resignSelectionAudit(&a[1],&ap[1],key)
   }},
  {"duplicate receipt across lanes",func(e *SignedExport,p *ExternalTrust,r *[2][]byte,l *[]LanePins,a *[2]SignedSelectionAudit,ap *[2]SelectionAuditPin){
    a[1].Audit.Entries[0].ReceiptSHA256=a[0].Audit.Entries[0].ReceiptSHA256
    _,_,_,_,_,key:=signedAuditFixture(t,"Yggdrasil")
    resignSelectionAudit(&a[1],&ap[1],key)
   }},
  {"same historic signer",func(e *SignedExport,p *ExternalTrust,r *[2][]byte,l *[]LanePins,a *[2]SignedSelectionAudit,ap *[2]SelectionAuditPin){(*l)[0].IndependentEd25519PublicKeyHex=(*l)[1].IndependentEd25519PublicKeyHex}},
 }
 for _,tt:=range cases {
  t.Run(tt.name,func(t *testing.T){
   e,p,raw,pins,a,ap:=makeSignedAuditExport(t)
   tt.mutate(&e,&p,&raw,&pins,&a,&ap)
   got,err:=EvaluatePinnedExportWithAudits(e,p,raw,pins,a,ap)
   if err==nil||!reflect.DeepEqual(got,ExportReview{}){
    t.Fatalf("unqualified admission: %+v %v",got,err)
   }
  })
 }
}
func TestAuditKeysAreActuallyDistinct(t *testing.T){
 _,_,_,pins,_,ap:=makeSignedAuditExport(t)
 if ap[0].IndependentAuditorPublicKeyHex==ap[1].IndependentAuditorPublicKeyHex||
  ap[0].IndependentAuditorPublicKeyHex==pins[0].IndependentEd25519PublicKeyHex{
  t.Fatal("audit fixture keys not independent")
 }
}
