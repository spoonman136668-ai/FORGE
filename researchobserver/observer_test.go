package researchobserver

import (
 "encoding/json"
 "strings"
 "testing"
)
func validEnvelope(lane,conclusion string)[]byte{
 repo:="spoonman136668-ai/"+lane
 r:=map[string]any{
  "id":float64(38379395699),"run_attempt":float64(1),
  "name":lane+" verified native first-use CI",
  "head_sha":strings.Repeat("a",40),"head_branch":"research/frozen-check",
  "status":"completed","conclusion":conclusion,
  "created_at":"2026-10-13T09:52:11Z",
  "html_url":"https://github.com/"+repo+"/actions/runs/38379395699",
  "repository":map[string]any{"full_name":repo},
  "head_repository":map[string]any{"full_name":repo},
 }
 raw,_:=json.Marshal(map[string]any{"total_count":200,"workflow_runs":[]any{r}})
 return raw
}
func TestResearchObserverPreservesFailureAsMetadataNotScientificNegative(t *testing.T){
 w:=validEnvelope("Wingless","success")
 y:=validEnvelope("Yggdrasil","failure")
 obs,err:=Build(w,y)
 if err!=nil{t.Fatal(err)}
 if obs.Schema!=Schema||len(obs.Wingless.Runs)!=1||
  len(obs.Yggdrasil.Runs)!=1||obs.Wingless.Runs[0].Conclusion!="success"||
  obs.Yggdrasil.Runs[0].Conclusion!="failure"||
  obs.Yggdrasil.Runs[0].ScientificClassification!="UNVERIFIED_NOT_A_SCIENTIFIC_RESULT"||
  obs.Wingless.HistoricalCompletenessVerified||obs.Yggdrasil.ScientificEvidenceAuthenticated||
  obs.ScientificAccepted||obs.ExecutionAuthorized||obs.AcceptedRefMutation||
  obs.ResearchOriginalsExecuted!=0{t.Fatalf("CI metadata was elevated to scientific authority: %+v",obs)}
 next,err:=Build(w,y)
 if err!=nil||next.Wingless.InputRawSHA256!=obs.Wingless.InputRawSHA256{
  t.Fatal("raw byte identity nondeterministic",err)
 }
}
func TestResearchObserverAdversarialSourceAndMetadataDrift(t *testing.T){
 good:=validEnvelope("Wingless","success")
 other:=validEnvelope("Yggdrasil","failure")
 for _,test:=range []struct{name string;change func([]byte)[]byte}{
  {"same payload",func(_ []byte)[]byte{return other}},
  {"bad SHA",func(b []byte)[]byte{return []byte(strings.Replace(string(b),strings.Repeat("a",40),"notasha",1))}},
  {"foreign origin",func(b []byte)[]byte{return []byte(strings.Replace(string(b),`"full_name":"spoonman136668-ai/Wingless"`,`"full_name":"another-org/Wingless"`,1))}},
  {"wrong url",func(b []byte)[]byte{return []byte(strings.Replace(string(b),"/actions/runs/38379395699","/actions/runs/1",1))}},
  {"unknown status",func(b []byte)[]byte{return []byte(strings.Replace(string(b),`"status":"completed"`,`"status":"live"`,1))}},
  {"absent conclusion",func(b []byte)[]byte{return []byte(strings.Replace(string(b),`"conclusion":"success"`,`"conclusion":null`,1))}},
  {"trailing object",func(b []byte)[]byte{return append(append([]byte(nil),b...),[]byte("{}")...)}},
 }{
  t.Run(test.name,func(t *testing.T){
   a:=test.change(append([]byte(nil),good...))
   if _,err:=Build(a,other);err==nil{
    t.Fatal("unsafe metadata origin accepted",test.name)
   }
  })
 }
}
func TestResearchObserverExcludesUnprovenScientificCoverage(t *testing.T){
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  b:=validEnvelope(lane,"success")
  var obj map[string]any
  if err:=json.Unmarshal(b,&obj);err!=nil{t.Fatal(err)}
  obj["workflow_runs"]=[]any{}
  empty,_:=json.Marshal(obj)
  if _,err:=readLane(empty,lane);err==nil{t.Fatal("empty unqualified history accepted")}
  obj["total_count"]=float64(0)
  obj["workflow_runs"]=[]any{map[string]any{"id":1}}
  corrupted,_:=json.Marshal(obj)
  if _,err:=readLane(corrupted,lane);err==nil{t.Fatal("untrusted partial GitHub row accepted")}
 }
}
