package researchintake

import (
 "encoding/json"
 "strings"
 "testing"
)
func example(lane string,n uint64,sha string) Source{return Source{Lane:lane,PR:n,HeadSHA:sha,Title:"A bounded scientific experiment",URL:"https://github.com/spoonman136668-ai/"+lane+"/pull/"+map[uint64]string{1:"1",2:"2"}[n],State:"open",Draft:true,UpdatedAt:"2026-10-14T22:13:52Z"}}
func marshal(v any) []byte {b,_:=json.Marshal(v);return b}
func snapshot(s ...Source) []byte {return marshal(Snapshot{Schema:SnapshotSchema,Sources:s})}
func TestComposableAndReplay(t *testing.T){
 a:=example("Wingless",1,strings.Repeat("a",40));b:=example("Yggdrasil",2,strings.Repeat("b",40))
 initial,err:=Ingest(snapshot(a,b),nil);if err!=nil{t.Fatal(err)}
 if initial.WinglessRevisions!=1||initial.YggdrasilRevisions!=1||initial.ScientificAccepted||initial.FirstUseCleared||initial.HistoricalCompletenessVerified{t.Fatal("claim inflation")}
 prev:=marshal(initial)
 same,err:=Ingest(snapshot(a,b),prev);if err!=nil||string(marshal(same))!=string(prev){t.Fatal("replay mutated report",err)}
 a.HeadSHA=strings.Repeat("c",40)
 next,err:=Ingest(snapshot(a),prev);if err!=nil{t.Fatal(err)}
 if next.TotalRevisions!=3||next.WinglessRevisions!=2||next.YggdrasilRevisions!=1{t.Fatal("history lost")}
 if validateReport(next)!=nil{t.Fatal("broken digest")}
 if _,err=Ingest(snapshot(a),marshal(next));err!=nil{t.Fatal("incremental replay")}
}
func TestRejectMalformed(t *testing.T){
 a:=example("Wingless",1,strings.Repeat("a",40));b:=example("Yggdrasil",2,strings.Repeat("b",40))
 for _,raw:=range [][]byte{[]byte(`{"schema":"forge.cross-lane-research-pr-snapshot.v1","SCHEMA":"forge.cross-lane-research-pr-snapshot.v1","sources":[]}`),append(snapshot(a),[]byte(`{}`)...),snapshot(a,a)}{
  if _,err:=Ingest(raw,nil);err==nil{t.Fatal("accepted malformed snapshot",string(raw))}
 }
 baseline,_:=Ingest(snapshot(a,b),nil);prev:=marshal(baseline)
 var tampered Report=jsonCopy(baseline);tampered.Revisions[0].ScientificAccepted=true
 if _,err:=Ingest(snapshot(a),marshal(tampered));err==nil{t.Fatal("tampered prior accepted")}
 a.URL="https://evil.example/pull/1"
 if _,err:=Ingest(snapshot(a),prev);err==nil{t.Fatal("untrusted URL accepted")}
 a=example("Wingless",1,strings.Repeat("a",40));a.Title="bad\nline"
 if _,err:=Ingest(snapshot(a),prev);err==nil{t.Fatal("unsafe title accepted")}
}
func jsonCopy(r Report)Report{var o Report;_ =json.Unmarshal(marshal(r),&o);return o}
