package optimizerbridge

import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "reflect"
 "testing"
)

func signedAuditFixture(t *testing.T,lane string)(LaneEvidence,LanePins,SignedSelectionAudit,SelectionAuditPin,string,ed25519.PrivateKey){
 t.Helper()
 e,p:=fixture(t,lane)
 a:=SignedSelectionAudit{Audit:SelectionAudit{
  Schema:SelectionAuditSchema,Lane:lane,
  TrainHistorySHA256:p.DreamTrainSHA256,
  ValidationHistorySHA256:p.DreamValidationSHA256,
 }}
 // Independent fixture attests the *claims*, not actual randomized allocation.
 for _,history:=range []int{0,1}{
  ds:=e.DreamTrain.History.Decisions
  if history==1{ds=e.DreamValidation.History.Decisions}
  for _,d:=range ds{
   a.Audit.Entries=append(a.Audit.Entries,SelectionAuditEntry{
    Tick:d.Tick,ReceiptSHA256:d.ReceiptSHA256,
    ChosenID:d.ChosenID,CohortSHA256:d.ChosenCohortSHA256,
    ProbabilityBP:d.LoggedActionProbabilityBP,
    RandomizationProofSHA256:d.RandomizationProofSHA256,
    AssignmentEventSHA256:shaHex([]byte(lane+"-test-only-assignment-"+d.ReceiptSHA256)),
   })
  }
 }
 seed:=sha256.Sum256([]byte("TEST-ONLY-SELECTION-AUDITOR-"+lane))
 key:=ed25519.NewKeyFromSeed(seed[:])
 ap:=SelectionAuditPin{
  IndependentAuditorPublicKeyHex:hex.EncodeToString(key.Public().(ed25519.PublicKey)),
 }
 resignSelectionAudit(&a,&ap,key)
 custodian:=shaHex([]byte("test-only-custodian"))
 return e,p,a,ap,custodian,key
}
func resignSelectionAudit(a *SignedSelectionAudit,p *SelectionAuditPin,k ed25519.PrivateKey){
 b,_:=json.Marshal(a.Audit)
 p.AuditSHA256=shaHex(b)
 a.SignatureHex=hex.EncodeToString(ed25519.Sign(k,append([]byte(SelectionAuditDomain),b...)))
}
func TestSignedSelectionAuditIsOnlyClaimConsistency(t *testing.T){
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  t.Run(lane,func(t *testing.T){
   e,p,a,ap,c,_:=signedAuditFixture(t,lane)
   first,err:=VerifySelectionAudit(e,p,a,ap,c)
   if err!=nil{t.Fatal(err)}
   second,err:=VerifySelectionAudit(e,p,a,ap,c)
   if err!=nil||!reflect.DeepEqual(first,second){t.Fatal("audit nondeterminism",err)}
   if !first.SignedClaimsConsistent||first.EntriesCrossChecked!=128||
    first.ActualRandomizationIndependentlyDemonstrated||
    first.ProspectiveScienceAuthorized||first.ScientificImprovementEstablished{
    t.Fatalf("unearned causal qualification: %+v",first)
   }
  })
 }
}
func TestSignedSelectionAuditFailClosed(t *testing.T){
 type mutator func(*LaneEvidence,*LanePins,*SignedSelectionAudit,*SelectionAuditPin,*string,ed25519.PrivateKey)
 cases:=[]struct{name string;change mutator}{
  {"missing auditor",func(e *LaneEvidence,p *LanePins,a *SignedSelectionAudit,ap *SelectionAuditPin,c *string,k ed25519.PrivateKey){ap.IndependentAuditorPublicKeyHex=""}},
  {"auditor is history signer",func(e *LaneEvidence,p *LanePins,a *SignedSelectionAudit,ap *SelectionAuditPin,c *string,k ed25519.PrivateKey){ap.IndependentAuditorPublicKeyHex=p.IndependentEd25519PublicKeyHex}},
  {"auditor is custodian",func(e *LaneEvidence,p *LanePins,a *SignedSelectionAudit,ap *SelectionAuditPin,c *string,k ed25519.PrivateKey){*c=ap.IndependentAuditorPublicKeyHex}},
  {"missing audit",func(e *LaneEvidence,p *LanePins,a *SignedSelectionAudit,ap *SelectionAuditPin,c *string,k ed25519.PrivateKey){a.Audit.Entries=nil;resignSelectionAudit(a,ap,k)}},
  {"missing assignment event",func(e *LaneEvidence,p *LanePins,a *SignedSelectionAudit,ap *SelectionAuditPin,c *string,k ed25519.PrivateKey){a.Audit.Entries[0].AssignmentEventSHA256="";resignSelectionAudit(a,ap,k)}},
  {"duplicate assignment",func(e *LaneEvidence,p *LanePins,a *SignedSelectionAudit,ap *SelectionAuditPin,c *string,k ed25519.PrivateKey){a.Audit.Entries[1].AssignmentEventSHA256=a.Audit.Entries[0].AssignmentEventSHA256;resignSelectionAudit(a,ap,k)}},
  {"signed mismatched probability",func(e *LaneEvidence,p *LanePins,a *SignedSelectionAudit,ap *SelectionAuditPin,c *string,k ed25519.PrivateKey){a.Audit.Entries[0].ProbabilityBP++;resignSelectionAudit(a,ap,k)}},
  {"signed mismatched outcome identity",func(e *LaneEvidence,p *LanePins,a *SignedSelectionAudit,ap *SelectionAuditPin,c *string,k ed25519.PrivateKey){a.Audit.Entries[0].ReceiptSHA256=shaHex([]byte("not original"));resignSelectionAudit(a,ap,k)}},
  {"swapped validation",func(e *LaneEvidence,p *LanePins,a *SignedSelectionAudit,ap *SelectionAuditPin,c *string,k ed25519.PrivateKey){a.Audit.TrainHistorySHA256,a.Audit.ValidationHistorySHA256=a.Audit.ValidationHistorySHA256,a.Audit.TrainHistorySHA256;resignSelectionAudit(a,ap,k)}},
  {"history changed",func(e *LaneEvidence,p *LanePins,a *SignedSelectionAudit,ap *SelectionAuditPin,c *string,k ed25519.PrivateKey){e.DreamTrain.History.Decisions[0].Outcome="SUPPORTED"}},
  {"signature invalid",func(e *LaneEvidence,p *LanePins,a *SignedSelectionAudit,ap *SelectionAuditPin,c *string,k ed25519.PrivateKey){a.SignatureHex=hex.EncodeToString(make([]byte,64))}},
  {"untrusted signature digest",func(e *LaneEvidence,p *LanePins,a *SignedSelectionAudit,ap *SelectionAuditPin,c *string,k ed25519.PrivateKey){ap.AuditSHA256=shaHex([]byte("forged"))}},
  {"observational claims",func(e *LaneEvidence,p *LanePins,a *SignedSelectionAudit,ap *SelectionAuditPin,c *string,k ed25519.PrivateKey){e.DreamTrain.History.Decisions[0].LoggingMode="OBSERVATIONAL"}},
 }
 for _,tt:=range cases{
  t.Run(tt.name,func(t *testing.T){
   e,p,a,ap,c,k:=signedAuditFixture(t,"Wingless")
   tt.change(&e,&p,&a,&ap,&c,k)
   got,err:=VerifySelectionAudit(e,p,a,ap,c)
   if err==nil||!reflect.DeepEqual(got,SelectionAuditReview{}){
    t.Fatalf("unqualified history accepted: %+v err=%v",got,err)
   }
  })
 }
}
