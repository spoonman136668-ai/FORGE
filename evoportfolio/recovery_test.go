package evoportfolio

import ("crypto/sha256";"encoding/hex";"encoding/json";"testing")
func TestRecoveryRejectsMissingSubstitutedAndReorderedBodies(t *testing.T){
 f:=fixture();pin:=Digest(f);h,err:=BuildHandoff(f,pin);if err!=nil{t.Fatal(err)}
 ids:=[]string{"alpha","gamma"}
 checkpoints:=[]Checkpoint{}
 receipts:=[]Receipt{}
 previous:=Checkpoint{}
 for _,id:=range ids {
  var source string
  for _,candidate:=range f.Candidates{if candidate.ID==id{source=candidate.SourceSHA}}
  body,_:=json.Marshal(map[string]string{"candidate_id":id,"source_sha":source,"outcome":"NEGATIVE"})
  hash:=sha256.Sum256(body);digest:=hex.EncodeToString(hash[:])
  c:=Completion{CandidateID:id,SourceSHA:source,EvidenceSHA256:digest,FrozenSHA256:pin,DecisionSHA256:h.DecisionSHA256,Outcome:"NEGATIVE"}
  next,e:=AdvanceCheckpoint(h,previous,c);if e!=nil{t.Fatal(e)}
  checkpoints=append(checkpoints,next)
  receipts=append(receipts,Receipt{CandidateID:id,SourceSHA:source,EvidenceSHA256:digest,Outcome:"NEGATIVE",Body:body})
  previous=next
 }
 if err:=RecoveryAudit(f,pin,h,checkpoints,receipts);err!=nil{t.Fatal(err)}
 if RecoveryAudit(f,pin,h,checkpoints,receipts[:1])==nil{t.Fatal("missing body accepted")}
 swapped:=append([]Receipt(nil),receipts...)
 swapped[0],swapped[1]=swapped[1],swapped[0]
 if RecoveryAudit(f,pin,h,checkpoints,swapped)==nil{t.Fatal("reordered bodies accepted")}
 tampered:=append([]Checkpoint(nil),checkpoints...)
 tampered[0],tampered[1]=tampered[1],tampered[0]
 if RecoveryAudit(f,pin,h,tampered,receipts)==nil{t.Fatal("reordered checkpoint accepted")}
}
