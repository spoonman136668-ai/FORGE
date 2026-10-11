package oidcaudit

import (
 "crypto"
 "crypto/rand"
 "crypto/rsa"
 "crypto/sha256"
 "encoding/base64"
 "encoding/json"
 "math/big"
 "strings"
 "testing"
 "time"
)
func newTestData(t *testing.T)(string,JWKS,Context,Claims,time.Time,*rsa.PrivateKey){
 t.Helper()
 sk,err:=rsa.GenerateKey(rand.Reader,2048);if err!=nil{t.Fatal(err)}
 now:=time.Unix(1791720000,0)
 ctx:=Context{SourceSHA:strings.Repeat("a",40),RunID:"38149001234",Attempt:"1",
  Repository:Repository,RepositoryID:RepositoryID,Ref:Branch,Event:"push"}
 aud,_:=json.Marshal(Audience)
 claims:=Claims{Issuer:Issuer,Audience:aud,Subject:"repo:trusted:ref:branch",
  Exp:now.Unix()+240,Iat:now.Unix()-10,Nbf:now.Unix()-10,
  Repository:Repository,RepositoryID:RepositoryID,RepositoryOwnerID:OwnerID,
  RepositoryVisibility:"public",RunnerEnvironment:"github-hosted",
  WorkflowRef:WorkflowRef,Ref:Branch,RefType:"branch",
  SHA:ctx.SourceSHA,RunID:ctx.RunID,RunAttempt:"1",EventName:"push"}
 exponent:=big.NewInt(int64(sk.PublicKey.E)).Bytes()
 jwks:=JWKS{Keys:[]Key{{Kid:"test-github-kid",Kty:"RSA",Alg:"RS256",Use:"sig",
  N:base64.RawURLEncoding.EncodeToString(sk.PublicKey.N.Bytes()),
  E:base64.RawURLEncoding.EncodeToString(exponent)}}}
 token:=signTestToken(t,sk,claims,"RS256","test-github-kid")
 return token,jwks,ctx,claims,now,sk
}
func signTestToken(t *testing.T,sk *rsa.PrivateKey,c Claims,alg,kid string)string{
 t.Helper()
 header,_:=json.Marshal(Header{Alg:alg,Kid:kid,Typ:"JWT"})
 payload,_:=json.Marshal(c)
 body:=base64.RawURLEncoding.EncodeToString(header)+"."+base64.RawURLEncoding.EncodeToString(payload)
 h:=sha256.Sum256([]byte(body))
 signature,err:=rsa.SignPKCS1v15(rand.Reader,sk,crypto.SHA256,h[:])
 if err!=nil{t.Fatal(err)}
 return body+"."+base64.RawURLEncoding.EncodeToString(signature)
}
func TestRealRS256SignatureAndExactRepositoryIdentity(t *testing.T){
 tok,jwks,ctx,_,now,_:=newTestData(t)
 result,err:=VerifySignedToken(tok,jwks,ctx,now)
 if err!=nil{t.Fatal(err)}
 if !result.GitHubRS256SignatureVerified||!result.ExactWorkflowAndRepositoryVerified||
  !result.GitHubHostedEnvironmentVerified||!result.FirstAttempt||
  result.DispatchAuthorized||result.IndependentWitnessed()||
  result.PhysicalCustodyVerified||result.ScientificOriginalExecuted||result.AcceptedScience{
  t.Fatal("shadow OIDC promoted to FSA authority",result)
 }
}
func (r Receipt)IndependentWitnessed()bool{return r.IndependentlyWitnessedByFSA}
func TestRejectWrongTokenKeyAndAlgorithm(t *testing.T){
 tok,jwks,ctx,claims,now,key:=newTestData(t)
 for _,alter:=range []func(*JWKS){
  func(j *JWKS){j.Keys[0].Kid="unknown"},
  func(j *JWKS){j.Keys[0].Use="enc"},
  func(j *JWKS){j.Keys[0].Alg="HS256"},
  func(j *JWKS){j.Keys[0].N="broken"},
  func(j *JWKS){j.Keys=append(j.Keys,j.Keys[0])},
  func(j *JWKS){j.Keys[0].E=base64.RawURLEncoding.EncodeToString([]byte{2})},
 }{
  tmp:=JWKS{Keys:append([]Key(nil),jwks.Keys...)}
  alter(&tmp)
  if _,err:=VerifySignedToken(tok,tmp,ctx,now);err==nil{t.Fatal("malformed JWKS accepted")}
 }
 for _,invalid:=range []string{
  signTestToken(t,key,claims,"none","test-github-kid"),
  signTestToken(t,key,claims,"HS256","test-github-kid"),
  signTestToken(t,key,claims,"RS256","wrong-kid"),
  tok+"x",tok+".extra", "garbage", strings.Repeat("x",17000),
 }{
  if _,err:=VerifySignedToken(invalid,jwks,ctx,now);err==nil{t.Fatal("untrusted JWT accepted")}
 }
}
func TestRejectClaimTamperingEvenWhenTestSignerControlsSignature(t *testing.T){
 _,jwks,ctx,claims,now,key:=newTestData(t)
 changes:=[]func(*Claims){
  func(c *Claims){c.Issuer="https://attacker.invalid"},
  func(c *Claims){c.Audience,_=json.Marshal("wrong-audience")},
  func(c *Claims){c.Repository="attacker/FORGE"},
  func(c *Claims){c.RepositoryID="1"},
  func(c *Claims){c.RepositoryOwnerID="1"},
  func(c *Claims){c.RepositoryVisibility="private"},
  func(c *Claims){c.RunnerEnvironment="self-hosted"},
  func(c *Claims){c.WorkflowRef="spoonman136668-ai/FORGE/.github/workflows/attack.yml@"+Branch},
  func(c *Claims){c.Ref="refs/heads/main"},
  func(c *Claims){c.RefType="tag"},
  func(c *Claims){c.SHA=strings.Repeat("0",40)},
  func(c *Claims){c.RunID="100"},
  func(c *Claims){c.RunAttempt="2"},
  func(c *Claims){c.EventName="pull_request"},
  func(c *Claims){c.Exp=now.Unix()-1},
  func(c *Claims){c.Exp=now.Unix()+3600},
  func(c *Claims){c.Iat=now.Unix()+200},
  func(c *Claims){c.Nbf=now.Unix()+200},
  func(c *Claims){c.Subject=""},
 }
 for i,change:=range changes{
  c:=claims;change(&c)
  tok:=signTestToken(t,key,c,"RS256","test-github-kid")
  if _,err:=VerifySignedToken(tok,jwks,ctx,now);err==nil{
   t.Fatalf("mutated claim %d was trusted",i)
  }
 }
}
func TestRejectWrongExpectedContextWithoutAnyMutation(t *testing.T){
 tok,jwks,ctx,_,now,_:=newTestData(t)
 changes:=[]func(*Context){
  func(c *Context){c.Attempt="2"},
  func(c *Context){c.RepositoryID="123"},
  func(c *Context){c.Repository="attacker/FORGE"},
  func(c *Context){c.Event="pull_request"},
  func(c *Context){c.RunID="001"},
  func(c *Context){c.Ref="refs/heads/main"},
  func(c *Context){c.SourceSHA=strings.Repeat("0",40)},
 }
 for i,change:=range changes{
  c:=ctx;change(&c)
  if _,err:=VerifySignedToken(tok,jwks,c,now);err==nil{
   t.Fatalf("context drift %d admitted",i)
  }
 }
}
func TestOnlyBoundedCanonicalSingleAudience(t *testing.T){
 tok,jwks,ctx,claims,now,key:=newTestData(t)
 aud,_:=json.Marshal([]string{Audience})
 claims.Audience=aud
 if _,err:=VerifySignedToken(signTestToken(t,key,claims,"RS256","test-github-kid"),jwks,ctx,now);err!=nil{
  t.Fatal("single-entry aud array incorrectly denied",err)
 }
 aud,_=json.Marshal([]string{Audience,"attacker-audience"})
 claims.Audience=aud
 if _,err:=VerifySignedToken(signTestToken(t,key,claims,"RS256","test-github-kid"),jwks,ctx,now);err==nil{
  t.Fatal("mixed-audience token admitted")
 }
 _=tok
}
