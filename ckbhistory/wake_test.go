package ckbhistory

import(
 "context"
 "encoding/json"
 "fmt"
 "net/http"
 "net/http/httptest"
 "strconv"
 "strings"
 "testing"
)
const wakeID int64=38281455598
const wakeSHA="6b1cc147d34f2dbacdeba13229b725050db74599"

func wakeServer(t *testing.T,result run,status int)(*Client,func()){
 t.Helper()
 route:="/repos/spoonman136668-ai/ckb-plane/actions/runs/"+strconv.FormatInt(wakeID,10)
 mux:=http.NewServeMux()
 mux.HandleFunc(route,func(w http.ResponseWriter,r *http.Request){
  if r.Method!=http.MethodGet||r.URL.Path!=route||r.URL.RawQuery!=""||
   r.Header.Get("Authorization")!="Bearer "+goodToken{
   t.Errorf("unexpected non-readonly wake query")
  }
  w.Header().Set("Content-Type","application/json")
  w.WriteHeader(status)
  raw,_:=json.Marshal(result)
  _,_=fmt.Fprint(w,string(raw))
 })
 server:=httptest.NewServer(mux)
 return &Client{endpoint:server.URL+"/repos/spoonman136668-ai/ckb-plane",
  token:goodToken,httpClient:server.Client()},server.Close
}
func originalWake()run{
 conclusion:="failure"
 return run{ID:wakeID,Path:WakeWorkflowPath,HeadBranch:"main",
  HeadSHA:wakeSHA,RunAttempt:1,Status:"completed",
  Event:"workflow_dispatch",Conclusion:&conclusion}
}
func TestIssuerWakeFailureIsAuthenticatedButNeverClearsFirstUse(t *testing.T){
 client,close:=wakeServer(t,originalWake(),200);defer close()
 result,err:=client.InspectWake(context.Background(),wakeID,wakeSHA)
 if err!=nil||VerifyWakeEvidence(result)!=nil||result.FirstUseReplayAuthorized||
  result.Conclusion!="failure"||
  result.Classification!="FAILED_CKB_WAKE_FIRST_USE_STILL_UNRESOLVED_NO_REPLAY"{
  t.Fatal(result,err)
 }
 result.Classification="WAKE_FINISHED_SAFE_TO_RETRY"
 if VerifyWakeEvidence(result)==nil{t.Fatal("forged wake classification accepted")}
}
func TestWakeSourceOrIssuerIdentityDriftBlocks(t *testing.T){
 c,stop:=wakeServer(t,originalWake(),200);defer stop()
 if _,err:=c.InspectWake(context.Background(),wakeID,strings.Repeat("f",40));err==nil{
  t.Fatal("different CKB source commit accepted")
 }
 if _,err:=c.InspectWake(context.Background(),wakeID+1,wakeSHA);err==nil{
  t.Fatal("different CKB wake id accepted")
 }
 c2,done:=wakeServer(t,func()run{x:=originalWake();x.RunAttempt=2;return x}(),200)
 defer done()
 if _,err:=c2.InspectWake(context.Background(),wakeID,wakeSHA);err==nil{
  t.Fatal("rerun of original wake accepted")
 }
 c3,end:=wakeServer(t,func()run{x:=originalWake();x.Path=OriginalPath;return x}(),200)
 defer end()
 if _,err:=c3.InspectWake(context.Background(),wakeID,wakeSHA);err==nil{
  t.Fatal("scientific original workflow substituted for CKB wake")
 }
}
func TestWakeUnknownAndFailedHTTPFailClosed(t *testing.T){
 c,stop:=wakeServer(t,originalWake(),500);defer stop()
 if _,err:=c.InspectWake(context.Background(),wakeID,wakeSHA);err==nil{t.Fatal("HTTP failure treated as CKB release")}
 pending:=originalWake();pending.Status="in_progress";pending.Conclusion=nil
 c2,done:=wakeServer(t,pending,200);defer done()
 if _,err:=c2.InspectWake(context.Background(),wakeID,wakeSHA);err==nil{
  t.Fatal("unfinished wake accepted as terminal")
 }
 for _,p:=range []string{"/actions/runs/0","/actions/runs/-1","/actions/runs/123?x=1","/actions/runs/../original","/actions/runs/000123","/actions/workflows/bad"}{
  if safeWakePath(p){t.Fatalf("unbounded read endpoint accepted: %s",p)}
 }
}
