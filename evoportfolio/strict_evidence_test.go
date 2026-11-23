package evoportfolio

import("testing")
func TestStrictEvidenceRejectsAmbiguousDocuments(t *testing.T){
 good:=[]byte(`{"candidate_id":"alpha","source_sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","outcome":"NEGATIVE"}`)
 if _,_,_,err:=StrictEvidence(good);err!=nil{t.Fatal(err)}
 for _,v:=range [][]byte{
  []byte(`{"candidate_id":"alpha","candidate_id":"beta","source_sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","outcome":"NEGATIVE"}`),
  []byte(`{"candidate_id":"alpha","source_sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","outcome":"NEGATIVE","extra":1}`),
  []byte(`{"candidate_id":"alpha","source_sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","outcome":"NEGATIVE"} {}`),
  []byte(`{"candidate_id":"alpha","source_sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}`),
  []byte(`{"candidate_id":"alpha","source_sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","outcome":null}`),
 }{
  if _,_,_,err:=StrictEvidence(v);err==nil{t.Fatalf("accepted ambiguous evidence %s",v)}
 }
}
