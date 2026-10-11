package evoportfolio

import("crypto/sha256";"encoding/hex";"encoding/json";"testing";"strings")
func TestRecoveryRejectsForgedSourceEvenWithMatchingBodyHash(t *testing.T){
 f:=fixture();pin:=Digest(f);h,err:=BuildHandoff(f,pin);if err!=nil{t.Fatal(err)}
 forged:=strings.Repeat("f",40)
 b,_:=json.Marshal(map[string]string{"candidate_id":"alpha","source_sha":forged,"outcome":"NEGATIVE"})
 digest:=sha256.Sum256(b);hash:=hex.EncodeToString(digest[:])
 c:=Completion{CandidateID:"alpha",SourceSHA:forged,EvidenceSHA256:hash,
 FrozenSHA256:pin,DecisionSHA256:h.DecisionSHA256,Outcome:"NEGATIVE"}
 cp,err:=AdvanceCheckpoint(h,Checkpoint{},c);if err!=nil{t.Fatal(err)}
 receipts:=[]Receipt{{CandidateID:"alpha",SourceSHA:forged,EvidenceSHA256:hash,Outcome:"NEGATIVE",Body:b}}
 if err:=RecoveryAudit(f,pin,h,[]Checkpoint{cp},receipts);err!=nil{t.Fatalf("fixture must demonstrate old gap: %v",err)}
 if err:=AuditSourceBinding(f,pin,h,[]Checkpoint{cp},receipts);err==nil{t.Fatal("forged source matched via self-consistent raw evidence")}
}
