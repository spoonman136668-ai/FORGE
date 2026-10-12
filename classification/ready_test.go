package classification

import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "strings"
 "testing"
 "github.com/spoonman136668-ai/forge/researchstate"
)
func TestSuccessorReadyDoesNotCreateNewLaneOrReplay(t *testing.T){
 seed:=sha256.Sum256([]byte("TEST ONLY successor-ready"))
 key:=ed25519.NewKeyFromSeed(seed[:])
 e:=Expected{Lane:"Yggdrasil",ExperimentID:"old_y",FrozenSHA256:strings.Repeat("a",64),OriginalEvidenceSHA256:strings.Repeat("b",64),ReviewerID:"reviewer",TrustedKey:key.Public().(ed25519.PublicKey)}
 a:=Attestation{Statement:Statement{Schema:Schema,Lane:e.Lane,ExperimentID:e.ExperimentID,FrozenSHA256:e.FrozenSHA256,OriginalEvidenceSHA256:e.OriginalEvidenceSHA256,ReviewerID:e.ReviewerID,Outcome:"NEGATIVE"}}
 raw,err:=json.Marshal(a.Statement);if err!=nil{t.Fatal(err)}
 a.SignatureHex=hex.EncodeToString(ed25519.Sign(key,append([]byte(domain),raw...)))
 hash,err:=Verify(a,e);if err!=nil{t.Fatal(err)}
 j:=researchstate.New();prior:=researchstate.Phase("")
 for _,next:=range []researchstate.Phase{researchstate.Proposed,researchstate.Preregistered,researchstate.Qualifying,researchstate.Qualified,researchstate.Authorized,researchstate.Executing,researchstate.EvidenceSealed,researchstate.Classified}{
  h,err:=researchstate.Head(j);if err!=nil{t.Fatal(err)}
  ev:=researchstate.Event{Lane:e.Lane,ExperimentID:e.ExperimentID,FrozenSHA256:e.FrozenSHA256,From:prior,To:next,IrreversibleRisk:next==researchstate.Executing}
  if next==researchstate.Qualified||next==researchstate.Authorized||next==researchstate.Executing||next==researchstate.EvidenceSealed{ev.EvidenceSHA256=e.OriginalEvidenceSHA256}
  if next==researchstate.Classified{ev.EvidenceSHA256=hash}
  j,err=researchstate.Append(j,ev,h);if err!=nil{t.Fatal(err)}
  prior=next
 }
 ready,err:=MarkSuccessorReady(j,a,e);if err!=nil{t.Fatal(err)}
 if len(ready.Entries)!=len(j.Entries)+1{t.Fatal("unexpected successor work created")}
 phase,ok,err:=researchstate.Status(ready,e.Lane,e.ExperimentID)
 if err!=nil||!ok||phase!=researchstate.SuccessorReady{t.Fatal(phase,err)}
 if _,err:=MarkSuccessorReady(ready,a,e);err==nil{t.Fatal("duplicate ready accepted")}
 if _,err:=MarkSuccessorReady(researchstate.New(),a,e);err==nil{t.Fatal("unknown original accepted")}
}
