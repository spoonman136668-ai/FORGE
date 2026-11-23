package fsagithubcustody

import (
 "context"
 "errors"
 "io"
 "net/http"
 "strings"
 "testing"
)
type fakeTransport func(*http.Request)(*http.Response,error)
func (fn fakeTransport)RoundTrip(req *http.Request)(*http.Response,error){return fn(req)}
const repoJSON=`{"id":1413298198,"full_name":"spoonman136668-ai/FORGE","private":false}`
const unprotected=`{"name":"main","protected":false,"commit":{"sha":"fc50538f7d9151721299ffbb1ccfbb018354c08f"}}`
const protected=`{"name":"main","protected":true,"commit":{"sha":"fc50538f7d9151721299ffbb1ccfbb018354c08f"}}`
func client(branchBody,rulesBody string)*http.Client{
 return &http.Client{Transport:fakeTransport(func(req *http.Request)(*http.Response,error){
  if req.Method!="GET"||req.URL.Scheme!="https"||req.URL.Host!="api.github.com"||
   req.Header.Get("Authorization")!=""{return nil,errors.New("unexpected remote request")}
  contents:=map[string]string{
   "/repos/spoonman136668-ai/FORGE":repoJSON,
   "/repos/spoonman136668-ai/FORGE/branches/main":branchBody,
   "/repos/spoonman136668-ai/FORGE/rulesets?per_page=100":rulesBody,
  }
  body,ok:=contents[req.URL.RequestURI()]
  if !ok{return nil,errors.New("unknown remote path")}
  return &http.Response{StatusCode:200,Request:req,
   Body:io.NopCloser(strings.NewReader(body))},nil
 })}
}
func TestR15ActualGitHubEndpointShapeUnprotectedFailsClosed(t *testing.T){
 r,err:=Audit(context.Background(),client(unprotected,"[]"))
 if err!=nil{t.Fatal(err)}
 if !r.RemoteReadSuccessful||r.BranchProtected||r.RulesetCount!=0||
  r.Disposition!="DENIED_UNPROTECTED_NO_TRUST_CUSTODY"||
  r.IndependentKeyCustodyProven||r.MonotonicPhysicalCASProven||
  r.ScientificExecutionAuthorized||!errors.Is(DenyAuthority(r),ErrNoAuthority){
  t.Fatalf("unsafe GitHub authority claim: %+v",r)
 }
}
func TestR15ProtectedBranchStillNotScientificAuthority(t *testing.T){
 r,err:=Audit(context.Background(),client(protected,`[{"id":12}]`))
 if err!=nil||!r.BranchProtected||r.RulesetCount!=1||
  r.Disposition!="DENIED_RULESET_AND_INDEPENDENT_CUSTODY_NOT_QUALIFIED"||
  !errors.Is(DenyAuthority(r),ErrNoAuthority){
  t.Fatalf("protected GitHub was treated as independent FSA: %+v %v",r,err)
 }
}
func TestR15MalformedUnavailableAndCancelledFailClosed(t *testing.T){
 cases:=map[string][2]string{
  "malformed-branch":{"{","[]"},
  "invalid-SHA":{`{"name":"main","protected":true,"commit":{"sha":"bad"}} `,"[]"},
  "malformed-rules":{protected,"[{"},
  "unexpected-rule":{protected,`[{"id":0}]`},
  "missing-rules":{protected,"null"},
 }
 for name,pair:=range cases{
  t.Run(name,func(t *testing.T){
   r,err:=Audit(context.Background(),client(pair[0],pair[1]))
   if err==nil||r.ScientificExecutionAuthorized{t.Fatalf("%s passed: %+v %v",name,r,err)}
  })
 }
 ctx,cancel:=context.WithCancel(context.Background());cancel()
 if _,err:=Audit(ctx,client(unprotected,"[]"));err==nil{t.Fatal("cancelled remote audit passed")}
}
