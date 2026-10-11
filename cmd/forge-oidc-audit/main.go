// forge-oidc-audit requests one ephemeral GitHub OIDC token and locally
// verifies GitHub's real RS256 signature. Token never enters logs/artifacts.
package main

import (
 "bytes"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "net/http"
 "net/url"
 "os"
 "path/filepath"
 "strings"
 "time"

 "github.com/spoonman136668-ai/forge/oidcaudit"
)
var ErrDenied=errors.New("FORGE_R11_OIDC_NOT_VERIFIED_NO_FSA")
const limit=131072
func client()*http.Client{
 return &http.Client{Timeout:14*time.Second,
  CheckRedirect:func(*http.Request,[]*http.Request)error{return http.ErrUseLastResponse}}
}
func getJSON(c *http.Client,request *http.Request,target any)error{
 response,err:=c.Do(request)
 if err!=nil{return ErrDenied}
 defer response.Body.Close()
 if response.StatusCode!=http.StatusOK{return ErrDenied}
 body,err:=io.ReadAll(io.LimitReader(response.Body,limit+1))
 if err!=nil||len(body)==0||len(body)>limit{return ErrDenied}
 d:=json.NewDecoder(bytes.NewReader(body))
 if d.Decode(target)!=nil{return ErrDenied}
 var extra any
 if d.Decode(&extra)!=io.EOF{return ErrDenied}
 return nil
}
func getToken(c *http.Client)(string,error){
 rawURL:=os.Getenv("ACTIONS_ID_TOKEN_REQUEST_URL")
 secret:=os.Getenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
 if len(secret)<8||len(rawURL)==0{return "",ErrDenied}
 u,err:=url.Parse(rawURL)
 if err!=nil||u.Scheme!="https"||u.User!=nil||
  !strings.HasSuffix(u.Hostname(),".actions.githubusercontent.com")||
  u.Fragment!=""||u.Host==""{return "",ErrDenied}
 q:=u.Query();q.Set("audience",oidcaudit.Audience);u.RawQuery=q.Encode()
 req,err:=http.NewRequest(http.MethodGet,u.String(),nil)
 if err!=nil{return "",ErrDenied}
 req.Header.Set("Authorization","bearer "+secret)
 req.Header.Set("Accept","application/json")
 var result struct{Value string `json:"value"`}
 if err=getJSON(c,req,&result);err!=nil||len(result.Value)<100||len(result.Value)>16384{
  return "",ErrDenied
 }
 return result.Value,nil
}
func getKeys(c *http.Client)(oidcaudit.JWKS,error){
 var zero oidcaudit.JWKS
 req,err:=http.NewRequest(http.MethodGet,oidcaudit.JWKSURL,nil)
 if err!=nil{return zero,ErrDenied}
 var keys oidcaudit.JWKS
 if err=getJSON(c,req,&keys);err!=nil{return zero,err}
 if len(keys.Keys)==0||len(keys.Keys)>32{return zero,ErrDenied}
 return keys,nil
}
func run(path string)error{
 if !filepath.IsAbs(path){return ErrDenied}
 context:=oidcaudit.Context{
  Repository:os.Getenv("GITHUB_REPOSITORY"),
  RepositoryID:os.Getenv("GITHUB_REPOSITORY_ID"),
  SourceSHA:os.Getenv("GITHUB_SHA"),
  RunID:os.Getenv("GITHUB_RUN_ID"),
  Attempt:os.Getenv("GITHUB_RUN_ATTEMPT"),
  Ref:os.Getenv("GITHUB_REF"),
  Event:os.Getenv("GITHUB_EVENT_NAME"),
 }
 c:=client()
 jwt,err:=getToken(c);if err!=nil{return ErrDenied}
 keys,err:=getKeys(c);if err!=nil{return ErrDenied}
 receipt,err:=oidcaudit.VerifySignedToken(jwt,keys,context,time.Now())
 jwt="" // Never persist or emit bearer tokens or even JWT claims.
 if err!=nil{return ErrDenied}
 raw,err:=json.MarshalIndent(receipt,"","  ")
 if err!=nil{return ErrDenied}
 file,err:=os.OpenFile(path,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{return ErrDenied}
 if _,err=file.Write(append(raw,'\n'));err!=nil{_ =file.Close();return ErrDenied}
 if file.Sync()!=nil{_ =file.Close();return ErrDenied}
 if file.Close()!=nil{return ErrDenied}
 fmt.Println("FORGE_R11_GITHUB_OIDC=SIGNATURE_AND_RUN_CLAIMS_VERIFIED")
 fmt.Println("FORGE_R11_FSA_AUTHORITY=false scientific_dispatch=false original_experiments=0")
 return nil
}
func main(){
 if len(os.Args)!=2||run(os.Args[1])!=nil{
  fmt.Fprintln(os.Stderr,"FORGE_R11_OIDC=BLOCKED_NO_FSA_AUTHORITY")
  os.Exit(2)
 }
}
