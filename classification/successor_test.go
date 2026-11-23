package classification

import(
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "strings"
 "testing"
 "github.com/spoonman136668-ai/forge/researchstate"
)
func TestSuccessorRequiresExactSignedParentClassification(t *testing.T){
 seed:=sha256.Sum256([]byte("TEST ONLY successor classifier"))
 key:=ed25519.NewKeyFromSeed(seed[:])
 e:=Expected{Lane:"Wingless",ExperimentID:"original_w",FrozenSHA256:strings.Repeat("a",64),OriginalEvidenceSHA256:strings.Repeat("b",64),ReviewerID:"independent",TrustedKey:key.Public().(ed25519.PublicKey)}
 makeAtt:=func(outcome string)Attestation{
  a:=Attestation{Statement:Statement{Schema:Schema,Lane:e.Lane,ExperimentID:e.ExperimentID,FrozenSHA256:e.FrozenSHA256,OriginalEvidenceSHA256:e.OriginalEvidenceSHA256,ReviewerID:e.ReviewerID,Outcome:outcome}}
  body,err:=json.Marshal(a.Statement);if err!=nil{t.Fatal(err)}
  a.SignatureHex=hex.EncodeToString(ed25519.Sign(key,append([]byte(domain),body...)))
  return a
 }
 for _,outcome:=range []string{"POSITIVE","NEGATIVE","INCONCLUSIVE","INVALID"}{t.Run(outcome,func(t *testing.T){
  a:=makeAtt(outcome);hash,err:=Verify(a,e);if err!=nil{t.Fatal(err)}
  j:=researchstate.New();phases:=[]researchstate.Phase{researchstate.Proposed,researchstate.Preregistered,researchstate.Qualifying,researchstate.Qualified,researchstate.Authorized,researchstate.Executing,researchstate.EvidenceSealed,researchstate.Classified}
  from:=researchstate.Phase("")
  for _,to:=range phases{
   h,err:=researchstate.Head(j);if err!=nil{t.Fatal(err)}
   evt:=researchstate.Event{Lane:e.Lane,ExperimentID:e.ExperimentID,FrozenSHA256:e.FrozenSHA256,From:from,To:to,IrreversibleRisk:to==researchstate.Executing}
   if to==researchstate.Qualified||to==researchstate.Authorized||to==researchstate.Executing||to==researchstate.EvidenceSealed{evt.EvidenceSHA256=e.OriginalEvidenceSHA256}
   if to==researchstate.Classified{evt.EvidenceSHA256=hash}
   j,err=researchstate.Append(j,evt,h);if err!=nil{t.Fatal(err)}
   from=to
  }
  result,err:=AssessSuccessor(j,a,e);if err!=nil{t.Fatal(err)}
  if result.Eligible!=(outcome!="INVALID"){t.Fatal("wrong successor eligibility",result)}
  alt:=makeAtt("INVALID")
  if outcome!="INVALID"{if _,err:=AssessSuccessor(j,alt,e);err==nil{t.Fatal("mismatched parent classification accepted")}}
  if _,err:=AssessSuccessor(researchstate.New(),a,e);err==nil{t.Fatal("missing classified parent accepted")}
 })}
}
