package mindcontext

import (
 "context"
 "crypto/sha1"
 "encoding/base64"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "net/http"
 "net/url"
 "strings"
 "strconv"
 "time"
)

const githubRepo = "spoonman136668-ai/Mind-Palace"
const maxAPIResponse = 2 * MaxRemoteBytes
// GitHub is a strictly read-only private repository content transport. It has
// no actions, dispatch, write, branch, mailbox, runner or local-exec methods.
// Pass only a narrowly scoped fine-grained token with Contents:read.
type GitHub struct {
 token string
 client *http.Client
}
func NewGitHub(token string,client *http.Client)(*GitHub,error){
 if token==""||strings.TrimSpace(token)!=token||strings.ContainsAny(token,"\r\n\x00 "){
  return nil,errors.New("FORGE_MIND_READ_ONLY_CREDENTIAL_REQUIRED")
 }
 if client==nil{
  client=&http.Client{Timeout:12*time.Second,CheckRedirect:func(*http.Request,[]*http.Request)error{return http.ErrUseLastResponse}}
 }
 // Never forward a bearer credential across redirects, including custom clients.
 copied:=*client
 copied.CheckRedirect=func(*http.Request,[]*http.Request)error{return http.ErrUseLastResponse}
 return &GitHub{token:token,client:&copied},nil
}
func (g *GitHub) get(ctx context.Context,route string)([]byte,error){
 if g==nil||g.client==nil{return nil,errors.New("FORGE_MIND_TRANSPORT_NOT_CONFIGURED")}
 // The base URL and repo are immutable; callers cannot inject another host.
 req,err:=http.NewRequestWithContext(ctx,http.MethodGet,"https://api.github.com/repos/"+githubRepo+"/"+route,nil)
 if err!=nil{return nil,errors.New("FORGE_MIND_READ_REQUEST_INVALID")}
 req.Header.Set("Accept","application/vnd.github+json")
 req.Header.Set("X-GitHub-Api-Version","2022-11-28")
 req.Header.Set("Authorization","Bearer "+g.token)
 resp,err:=g.client.Do(req)
 if err!=nil{return nil,errors.New("FORGE_MIND_PRIVATE_GITHUB_READ_FAILED")}
 defer resp.Body.Close()
 if resp.StatusCode!=http.StatusOK{return nil,fmt.Errorf("FORGE_MIND_PRIVATE_GITHUB_STATUS_%d",resp.StatusCode)}
 b,err:=io.ReadAll(io.LimitReader(resp.Body,maxAPIResponse+1))
 if err!=nil||len(b)==0||len(b)>maxAPIResponse{return nil,errors.New("FORGE_MIND_GITHUB_RESPONSE_BOUNDS")}
 return b,nil
}
func (g *GitHub) ResolveMain(ctx context.Context)(string,error){
 b,err:=g.get(ctx,"commits/main")
 if err!=nil{return "",err}
 var c struct { SHA string `json:"sha"` }
 if err=json.Unmarshal(b,&c);err!=nil||!lowerHex(c.SHA,40){return "",errors.New("FORGE_MIND_GITHUB_COMMIT_UNVERIFIED")}
 return c.SHA,nil
}
func (g *GitHub) ReadAt(ctx context.Context,pin,path string)([]byte,error){
 if !lowerHex(pin,40){return nil,errors.New("FORGE_MIND_GITHUB_UNPINNED_READ")}
 if path!=BootstrapPath&&path!=CatalogPath&&path!=IndexPath&&path!="governance/unified-final-authority.v1.json" {
  return nil,errors.New("FORGE_MIND_GITHUB_PATH_NOT_ALLOWED")
 }
 b,err:=g.get(ctx,"contents/"+path+"?ref="+url.QueryEscape(pin))
 if err!=nil{return nil,err}
 var f struct {
  Type string `json:"type"`
  Encoding string `json:"encoding"`
  Content string `json:"content"`
  SHA string `json:"sha"`
  Size int `json:"size"`
 }
 if err=json.Unmarshal(b,&f);err!=nil||f.Type!="file"||f.Encoding!="base64"||f.Size<1||f.Size>MaxRemoteBytes||f.SHA==""{
  return nil,errors.New("FORGE_MIND_GITHUB_FILE_FORMAT_INVALID")
 }
 raw,err:=base64.StdEncoding.DecodeString(strings.ReplaceAll(f.Content,"\n",""))
 if err!=nil||len(raw)!=f.Size||len(raw)>MaxRemoteBytes{return nil,errors.New("FORGE_MIND_GITHUB_DECODE_BOUNDS")}
 // GitHub content identity must match its Git blob byte encoding.
 blob:=append([]byte("blob "+strconv.Itoa(len(raw))+"\x00"),raw...)
 actual:=sha1.Sum(blob)
 if !lowerHex(f.SHA,40)||f.SHA!=hex.EncodeToString(actual[:]){
  return nil,errors.New("FORGE_MIND_GITHUB_BLOB_MISMATCH")
 }
 return raw,nil
}
var _ Source = (*GitHub)(nil)
