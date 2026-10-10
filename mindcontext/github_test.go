package mindcontext

import (
 "context"
 "encoding/base64"
 "encoding/json"
 "io"
 "net/http"
 "strings"
 "testing"
)
type replyFunc func(*http.Request)(*http.Response,error)
func (f replyFunc)RoundTrip(r *http.Request)(*http.Response,error){return f(r)}
func response(body string,status int)*http.Response {
 return &http.Response{StatusCode:status,Body:io.NopCloser(strings.NewReader(body)),Header:make(http.Header)}
}
func TestGitHubTransportIsReadOnlyAndPinned(t *testing.T){
 pin:=strings.Repeat("a",40)
 token:="fixture-private-token"
 called:=0
 tr:=replyFunc(func(r *http.Request)(*http.Response,error){
  called++
  if r.Method!="GET"||r.URL.Host!="api.github.com"||r.URL.Scheme!="https"||!strings.Contains(r.URL.Path,"/repos/spoonman136668-ai/Mind-Palace/") {
   t.Fatal("unexpected network authority")
  }
  if r.Header.Get("Authorization")!="Bearer "+token{t.Fatal("scoped auth missing")}
  if strings.HasSuffix(r.URL.Path,"/commits/main"){return response(`{"sha":"`+pin+`"}`,200),nil}
  if r.URL.Query().Get("ref")!=pin{t.Fatal("GitHub contents ref was not pinned")}
  if !strings.HasSuffix(r.URL.Path,"/"+BootstrapPath){t.Fatal("unexpected path")}
  bytes:=[]byte(`{"schema":"fixture"}`)
  // A GitHub content response supplies exact, bounded base64 file bytes.
  payload,_:=json.Marshal(map[string]any{
   "type":"file","encoding":"base64","sha":strings.Repeat("b",40),"size":len(bytes),
   "content":base64.StdEncoding.EncodeToString(bytes),
  })
  return response(string(payload),200),nil
 })
 github,err:=NewGitHub(token,&http.Client{Transport:tr});if err!=nil{t.Fatal(err)}
 commit,err:=github.ResolveMain(context.Background());if err!=nil||commit!=pin{t.Fatal(err)}
 b,err:=github.ReadAt(context.Background(),pin,BootstrapPath)
 if err!=nil||string(b)!=`{"schema":"fixture"}`{t.Fatal(err)}
 if called!=2{t.Fatal("unexpected number of reads")}
 if _,err:=github.ReadAt(context.Background(),pin,"../secrets");err==nil{t.Fatal("unexpected path permitted")}
 if _,err:=github.ReadAt(context.Background(),"main",IndexPath);err==nil{t.Fatal("unpinned ref permitted")}
 if called!=2{t.Fatal("unsafe query reached transport")}
}
func TestGitHubStatusAndSecretsNotEchoed(t *testing.T){
 github,err:=NewGitHub("sensitive-fixture",&http.Client{Transport:replyFunc(func(r *http.Request)(*http.Response,error){
  return response(`{"message":"forbidden"}`,403),nil
 })})
 if err!=nil{t.Fatal(err)}
 _,err=github.ResolveMain(context.Background())
 if err==nil||strings.Contains(err.Error(),"sensitive-fixture"){t.Fatal("credential exposure or missing status failure")}
 if _,err=NewGitHub("",nil);err==nil{t.Fatal("private read without credential")}
}
func TestGitHubResponseBounds(t *testing.T){
 github,_:=NewGitHub("synthetic",&http.Client{Transport:replyFunc(func(r *http.Request)(*http.Response,error){
  return response(strings.Repeat("A",maxAPIResponse+2),200),nil
 })})
 if _,err:=github.ResolveMain(context.Background());err==nil{t.Fatal("oversized response accepted")}
}
