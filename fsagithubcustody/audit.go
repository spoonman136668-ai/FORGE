// Package fsagithubcustody audits actual GitHub-hosted protection evidence.
// This read-only diagnostic NEVER grants FORGE scientific authority.
package fsagithubcustody

import (
 "bytes"
 "context"
 "crypto/tls"
 "encoding/json"
 "errors"
 "io"
 "net/http"
 "time"
)

const (
 Repository = "spoonman136668-ai/FORGE"
 RepositoryID int64 = 1413298198
 baseURL = "https://api.github.com/repos/" + Repository
 maxBody = 262144
)
var ErrUnavailable=errors.New("FORGE_FSA_GITHUB_LIVE_AUDIT_UNAVAILABLE")
var ErrNoAuthority=errors.New("FORGE_FSA_INDEPENDENT_TRUST_UNPROVEN")

type Report struct {
 Schema string `json:"schema"`
 Repository string `json:"repository"`
 Branch string `json:"branch"`
 HeadSHA string `json:"head_sha"`
 BranchProtected bool `json:"branch_protected"`
 RulesetCount int `json:"ruleset_count"`
 RemoteReadSuccessful bool `json:"remote_read_successful"`
 IndependentKeyCustodyProven bool `json:"independent_key_custody_proven"`
 MonotonicPhysicalCASProven bool `json:"monotonic_physical_cas_proven"`
 ScientificExecutionAuthorized bool `json:"scientific_execution_authorized"`
 Disposition string `json:"disposition"`
}
type repository struct {
 ID int64 `json:"id"`
 FullName string `json:"full_name"`
 Private bool `json:"private"`
}
type branch struct {
 Name string `json:"name"`
 Protected bool `json:"protected"`
 Commit struct {SHA string `json:"sha"`} `json:"commit"`
}
type ruleset struct {ID int64 `json:"id"`}

func HTTPClient()*http.Client {
 return &http.Client{
  Timeout:12*time.Second,
  CheckRedirect:func(*http.Request,[]*http.Request)error{return http.ErrUseLastResponse},
  Transport:&http.Transport{TLSClientConfig:&tls.Config{MinVersion:tls.VersionTLS12},
   TLSHandshakeTimeout:5*time.Second,DisableCompression:true},
 }
}
func read(ctx context.Context,client *http.Client,suffix string,result any)error{
 if ctx==nil||ctx.Err()!=nil||client==nil{return ErrUnavailable}
 req,err:=http.NewRequestWithContext(ctx,http.MethodGet,baseURL+suffix,nil)
 if err!=nil{return ErrUnavailable}
 req.Header.Set("Accept","application/vnd.github+json")
 resp,err:=client.Do(req);if err!=nil{return ErrUnavailable}
 defer resp.Body.Close()
 if resp.StatusCode!=http.StatusOK||resp.Request==nil||
  resp.Request.URL.String()!=req.URL.String(){return ErrUnavailable}
 raw,err:=io.ReadAll(io.LimitReader(resp.Body,maxBody+1))
 if err!=nil||len(raw)==0||len(raw)>maxBody{return ErrUnavailable}
 decoder:=json.NewDecoder(bytes.NewReader(raw))
 if decoder.Decode(result)!=nil{return ErrUnavailable}
 var extra any
 if decoder.Decode(&extra)!=io.EOF{return ErrUnavailable}
 return nil
}
func hex40(s string)bool{
 if len(s)!=40{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
// Audit reads GitHub's REAL public REST endpoint. A protected branch or
// ruleset does not prove separate key custody, write authority isolation,
// off-host immutable storage or linearizable physical compare-and-swap.
func Audit(ctx context.Context,client *http.Client)(Report,error){
 r:=Report{Schema:"forge.fsa.github-live-audit.v1",
  Repository:Repository,Branch:"main",Disposition:"DENIED_REMOTE_UNVERIFIED"}
 var repo repository
 if err:=read(ctx,client,"",&repo);err!=nil{return r,err}
 if repo.ID!=RepositoryID||repo.FullName!=Repository||repo.Private{return r,ErrUnavailable}
 var b branch
 if err:=read(ctx,client,"/branches/main",&b);err!=nil{return r,err}
 if b.Name!="main"||!hex40(b.Commit.SHA){return r,ErrUnavailable}
 r.HeadSHA=b.Commit.SHA;r.BranchProtected=b.Protected
 var list []ruleset
 if err:=read(ctx,client,"/rulesets?per_page=100",&list);err!=nil{return r,err}
 if list==nil||len(list)>=100{return r,ErrUnavailable}
 for _,rule:=range list{if rule.ID<=0{return r,ErrUnavailable}}
 r.RulesetCount=len(list);r.RemoteReadSuccessful=true
 if !r.BranchProtected||len(list)==0{
  r.Disposition="DENIED_UNPROTECTED_NO_TRUST_CUSTODY"
 }else{
  r.Disposition="DENIED_RULESET_AND_INDEPENDENT_CUSTODY_NOT_QUALIFIED"
 }
 return r,nil
}
// DenyAuthority remains fail-closed regardless of any favorable branch flags.
func DenyAuthority(Report)error{return ErrNoAuthority}
