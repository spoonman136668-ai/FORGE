package evoportfolio
import("crypto/sha256";"encoding/hex";"encoding/json";"testing")
func TestCheckpointBodyMatchesFrozenPortfolio(t *testing.T){
 f:=fixture();h,err:=BuildHandoff(f,Digest(f));if err!=nil{t.Fatal(err)}
 raw,_:=json.Marshal(map[string]string{"candidate_id":"alpha","source_sha":f.Candidates[0].SourceSHA,"outcome":"NEGATIVE"})
 hash:=sha256.Sum256(raw)
 c:=Completion{CandidateID:"alpha",SourceSHA:f.Candidates[0].SourceSHA,
  EvidenceSHA256:hex.EncodeToString(hash[:]),FrozenSHA256:h.FrozenSHA256,DecisionSHA256:h.DecisionSHA256,Outcome:"NEGATIVE"}
 cp,err:=AdvanceCheckpoint(h,Checkpoint{},c);if err!=nil{t.Fatal(err)}
 r:=Receipt{CandidateID:c.CandidateID,SourceSHA:c.SourceSHA,EvidenceSHA256:c.EvidenceSHA256,Outcome:c.Outcome,Body:raw}
 if err=VerifyCheckpointEvidence(f,Digest(f),h,cp,[]Receipt{r});err!=nil{t.Fatal(err)}
 r.Body=append([]byte(nil),raw...);r.Body[3]='Z'
 if VerifyCheckpointEvidence(f,Digest(f),h,cp,[]Receipt{r})==nil{t.Fatal("tampered evidence admitted")}
 r.Body=raw
 h.OrderedFinalistIDs[0]="beta"
 if VerifyCheckpointEvidence(f,Digest(f),h,cp,[]Receipt{r})==nil{t.Fatal("mutated order admitted")}
}
