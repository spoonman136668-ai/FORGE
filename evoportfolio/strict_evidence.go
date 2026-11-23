package evoportfolio

import (
 "bytes"
 "encoding/json"
 "errors"
 "io"
)

// StrictEvidence rejects ambiguous and overbroad JSON before it can be used
// by the frozen portfolio recovery verifier.
func StrictEvidence(body []byte)(string,string,string,error){
 if len(body)==0||len(body)>1048576{return "","","",ErrFrozen}
 dec:=json.NewDecoder(bytes.NewReader(body))
 tok,err:=dec.Token();if err!=nil||tok!=json.Delim('{'){return "","","",ErrFrozen}
 seen:=map[string]bool{}
 fields:=map[string]string{}
 for dec.More(){
  key,err:=dec.Token();if err!=nil{return "","","",ErrFrozen}
  k,ok:=key.(string);if !ok||seen[k]{return "","","",ErrFrozen}
  if k!="candidate_id"&&k!="source_sha"&&k!="outcome"{return "","","",ErrFrozen}
  seen[k]=true
  var value string
  if dec.Decode(&value)!=nil{return "","","",ErrFrozen}
  fields[k]=value
 }
 if tok,err=dec.Token();err!=nil||tok!=json.Delim('}'){return "","","",ErrFrozen}
 if dec.Decode(new(any))!=io.EOF||len(seen)!=3{return "","","",ErrFrozen}
 if !validID(fields["candidate_id"])||!isHex(fields["source_sha"],40)||
  (fields["outcome"]!="SUPPORTED"&&fields["outcome"]!="MIXED"&&fields["outcome"]!="NEGATIVE"&&fields["outcome"]!="INVALID"){
  return "","","",errors.New("FORGE_EVIDENCE_UNTRUSTED_FIELDS")
 }
 return fields["candidate_id"],fields["source_sha"],fields["outcome"],nil
}

// StrictRecovery composes the existing provenance and checkpoint verifier with
// strict raw evidence parsing; still advisory and no external custody assertion.
func StrictRecovery(f Frozen,pin string,h Handoff,cps []Checkpoint,receipts []Receipt)error{
 if len(cps)!=len(receipts)||len(receipts)==0{return ErrFrozen}
 for _,r:=range receipts{
  id,sha,outcome,err:=StrictEvidence(r.Body)
  if err!=nil||id!=r.CandidateID||sha!=r.SourceSHA||outcome!=r.Outcome{return ErrFrozen}
 }
 return AuditSourceBinding(f,pin,h,cps,receipts)
}
