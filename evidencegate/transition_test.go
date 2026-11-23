package evidencegate

import (
 "crypto/sha256"
 "encoding/hex"
 "os"
 "path/filepath"
 "strings"
 "testing"
 "github.com/spoonman136668-ai/forge/researchstate"
)
func TestSealedNegativeOriginalDoesNotImplySuccessor(t *testing.T){
 original:=[]byte("genuine test-only negative original")
 path:=filepath.Join(t.TempDir(),"raw")
 if err:=os.WriteFile(path,original,0600);err!=nil{t.Fatal(err)}
 hash:=sha256.Sum256(original)
 pin:=strings.Repeat("a",64)
 m:=Manifest{Lane:"Yggdrasil",ExperimentID:"existing_trial",FrozenSHA256:pin,
  OriginalRunID:"existing_first_use",OriginalSHA256:hex.EncodeToString(hash[:]),
  OriginalBytes:int64(len(original)),Classification:"NEGATIVE"}
 j:=researchstate.New()
 steps:=[]struct{from,to researchstate.Phase;risk bool}{
  {"",researchstate.Proposed,false},{researchstate.Proposed,researchstate.Preregistered,false},
  {researchstate.Preregistered,researchstate.Qualifying,false},
  {researchstate.Qualifying,researchstate.Qualified,false},
  {researchstate.Qualified,researchstate.Authorized,false},
  {researchstate.Authorized,researchstate.Executing,true},
 }
 for _,s:=range steps{
  h,err:=researchstate.Head(j);if err!=nil{t.Fatal(err)}
  e:=researchstate.Event{Lane:m.Lane,ExperimentID:m.ExperimentID,FrozenSHA256:pin,From:s.from,To:s.to,IrreversibleRisk:s.risk}
  if s.to==researchstate.Qualified||s.to==researchstate.Authorized||s.to==researchstate.Executing{e.EvidenceSHA256=m.OriginalSHA256}
  j,err=researchstate.Append(j,e,h);if err!=nil{t.Fatal(err)}
 }
 next,err:=SealOriginal(j,m.Lane,m.ExperimentID,pin,m,path);if err!=nil{t.Fatal(err)}
 phase,_,err:=researchstate.Status(next,m.Lane,m.ExperimentID)
 if err!=nil||phase!=researchstate.EvidenceSealed{t.Fatal(phase,err)}
 allowed,err:=SuccessorEligibility(next,m.Lane,m.ExperimentID)
 if err!=nil||allowed{t.Fatal("unclassified negative incorrectly authorized successor")}
 if _,err:=SealOriginal(next,m.Lane,m.ExperimentID,pin,m,path);err==nil{t.Fatal("double seal accepted")}
 m.Classification="INCONCLUSIVE"
 if _,err:=SealOriginal(j,"Wingless",m.ExperimentID,pin,m,path);err==nil{t.Fatal("cross-lane seal accepted")}
 if err:=os.WriteFile(path,[]byte("tamper"),0600);err!=nil{t.Fatal(err)}
 if _,err:=SealOriginal(j,m.Lane,m.ExperimentID,pin,m,path);err==nil{t.Fatal("tampered source accepted")}
}
