package ckbhistory

import(
 "context"
 "encoding/json"
 "fmt"
 "net/http"
 "net/http/httptest"
 "strings"
 "testing"
)
const goodToken="test-only-workflow-read-token-123456789"
func source(t *testing.T, original, intents string,originalCode,intentCode int)(*Client,func()){
 t.Helper()
 mux:=http.NewServeMux()
 mux.HandleFunc("/repos/spoonman136668-ai/ckb-plane/actions/workflows/r216-s14-synthetic-execute.yml/runs",func(w http.ResponseWriter,r *http.Request){
  if r.Method!=http.MethodGet||r.URL.RawQuery!="per_page=100"||
   r.Header.Get("Authorization")!="Bearer "+goodToken{t.Errorf("unsafe original read")}
  w.WriteHeader(originalCode);_,_ = fmt.Fprint(w,original)
 })
 mux.HandleFunc("/repos/spoonman136668-ai/ckb-plane/actions/artifacts",func(w http.ResponseWriter,r *http.Request){
  if r.Method!=http.MethodGet||r.URL.Query().Get("name")!=ArtifactName||
   r.URL.Query().Get("per_page")!="100"||r.Header.Get("Authorization")!="Bearer "+goodToken{
   t.Errorf("unsafe issuer artifact read")
  }
  w.WriteHeader(intentCode);_,_ = fmt.Fprint(w,intents)
 })
 s:=httptest.NewServer(mux)
 client:=&Client{endpoint:s.URL+"/repos/spoonman136668-ai/ckb-plane",
  token:goodToken,httpClient:s.Client()}
 return client,s.Close
}
func runs(n int)string{
 if n==0{return `{"total_count":0,"workflow_runs":[]}`}
 row:=map[string]any{"id":int64(383001),"path":OriginalPath,
  "event":"workflow_dispatch","head_branch":"main","head_sha":strings.Repeat("a",40),
  "run_attempt":1,"status":"completed","conclusion":"failure"}
 data,_:=json.Marshal(row)
 return fmt.Sprintf(`{"total_count":%d,"workflow_runs":[%s]}`,n,string(data))
}
func artifacts(n int)string{
 if n==0{return `{"total_count":0,"artifacts":[]}`}
 row:=map[string]any{"id":int64(382900),"name":ArtifactName,
  "digest":"sha256:"+strings.Repeat("b",64),
  "expired":false,"workflow_run":map[string]any{"id":int64(383000)}}
 data,_:=json.Marshal(row)
 return fmt.Sprintf(`{"total_count":%d,"artifacts":[%s]}`,n,string(data))
}
func TestGitHubOriginalAndIssuerAreReadOnlyNoReplay(t *testing.T){
 c,close:=source(t,runs(1),artifacts(1),200,200);defer close()
 p,err:=c.InspectS14(context.Background())
 if err!=nil{t.Fatal(err)}
 if p.OriginalAttemptCount!=1||p.IntentArtifactCount!=1||
  p.Classification!="ORIGINAL_ATTEMPT_RECORDED_NO_REPLAY"||
  p.FirstUseReplayAuthorized||p.ScientificExecutionActivated||
  len(p.EvidenceSHA256)!=64{t.Fatalf("unsafe classification %+v",p)}
}
func TestMissingGitHubHistoryIsUnknownNotUnused(t *testing.T){
 c,close:=source(t,runs(0),artifacts(0),200,200);defer close()
 p,err:=c.InspectS14(context.Background())
 if err!=nil||p.OriginalAttemptCount!=0||p.IntentArtifactCount!=0||
  p.Classification!="NO_GITHUB_RECORD_IS_NOT_FIRST_USE_CLEARANCE"||
  p.FirstUseReplayAuthorized{t.Fatal(p,err)}
}
func TestRemoteFailureAndPartialEvidenceFailClosed(t *testing.T){
 cases:=map[string]struct{original,intents string;oc,ic int}{
  "first original workflow 500":{runs(0),artifacts(0),500,200},
  "issuer artifacts 500":{runs(0),artifacts(0),200,500},
  "truncated original pagination":{runs(2),artifacts(0),200,200},
  "duplicate keys":{`{"total_count":0,"total_count":0,"workflow_runs":[]}`,artifacts(0),200,200},
  "unparseable artifact":{runs(0),`{"total_count":1,"artifacts":[{"id":2}]}`,200,200},
 }
 for name,c:=range cases{t.Run(name,func(t *testing.T){
  client,stop:=source(t,c.original,c.intents,c.oc,c.ic);defer stop()
  if r,err:=client.InspectS14(context.Background());err==nil{
   t.Fatalf("untrusted incomplete GitHub history accepted: %+v",r)
  }
 })}
}
func TestNoInvalidTokenOrConsumedRetry(t *testing.T){
 if _,err:=New("bad");err==nil{t.Fatal("unauthenticated GitHub client accepted")}
 if _,err:=New(goodToken+"\n");err==nil{t.Fatal("injected header accepted")}
 c,close:=source(t,runs(1),artifacts(0),200,200);defer close()
 p,err:=c.InspectS14(context.Background())
 if err!=nil||p.Classification!="ORIGINAL_ATTEMPT_RECORDED_NO_REPLAY"{
  t.Fatal(p,err)
 }
}
