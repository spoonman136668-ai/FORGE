package fsaidentity

import (
 "bytes"
 "context"
 "crypto"
 "crypto/rand"
 "crypto/rsa"
 "crypto/sha256"
 "encoding/base64"
 "encoding/json"
 "errors"
 "io"
 "math/big"
 "net/http"
 "net/url"
 "strings"
 "testing"
 "time"

 "github.com/spoonman136668-ai/forge/oidcaudit"
)

type signedFixture struct {
 jwt string
 keys oidcaudit.JWKS
 reg Registration
 pin string
 now time.Time
 private *rsa.PrivateKey
 claims oidcaudit.Claims
}
func fixture(t *testing.T) signedFixture{
 t.Helper()
 sk,e:=rsa.GenerateKey(rand.Reader,2048)
 if e!=nil{t.Fatal(e)}
 now:=time.Unix(1791720000,0)
 r:=Registration{
  Schema:Schema,Audience:"forge-fsa-issuer-authorization-v1",
  Repository:Repository,RepositoryID:RepositoryID,
  RepositoryOwnerID:OwnerID,WorkflowPath:".github/workflows/forge-fsa-original.yml",
  Ref:"refs/heads/main",Event:"workflow_dispatch",
  SourceSHA:strings.Repeat("a",40),GitHubRunID:"38190000421",
  RunAttempt:1,Lane:"Wingless",
  CohortSHA256:strings.Repeat("b",64),
  FrozenPrewakeSHA256:strings.Repeat("c",64),
  FrozenRunClaimSHA256:strings.Repeat("d",64),AuthorityEpoch:9,
 }
 pin,e:=RegistrationSHA(r)
 if e!=nil{t.Fatal(e)}
 aud,_:=json.Marshal(r.Audience)
 c:=oidcaudit.Claims{Issuer:Issuer,Audience:aud,
  Subject:"repo:"+Repository+":ref:"+r.Ref,
  Exp:now.Unix()+300,Iat:now.Unix()-30,Nbf:now.Unix()-30,
  Repository:Repository,RepositoryID:RepositoryID,
  RepositoryOwnerID:OwnerID,RepositoryVisibility:"public",
  RunnerEnvironment:"github-hosted",
  WorkflowRef:Repository+"/"+r.WorkflowPath+"@"+r.Ref,
  Ref:r.Ref,RefType:"branch",SHA:r.SourceSHA,
  RunID:r.GitHubRunID,RunAttempt:"1",EventName:r.Event,
 }
 exponent:=big.NewInt(int64(sk.E)).Bytes()
 keys:=oidcaudit.JWKS{Keys:[]oidcaudit.Key{{Kid:"github-fixture-rsa",
  Kty:"RSA",Alg:"RS256",Use:"sig",
  N:base64.RawURLEncoding.EncodeToString(sk.N.Bytes()),
  E:base64.RawURLEncoding.EncodeToString(exponent)}}}
 return signedFixture{
  jwt:sign(t,sk,c,"RS256","github-fixture-rsa"),
  keys:keys,reg:r,pin:pin,now:now,private:sk,claims:c}
}
func sign(t *testing.T,sk *rsa.PrivateKey,c oidcaudit.Claims,alg,kid string)string{
 t.Helper()
 head,_:=json.Marshal(oidcaudit.Header{Alg:alg,Kid:kid,Typ:"JWT"})
 body,_:=json.Marshal(c)
 encoded:=base64.RawURLEncoding.EncodeToString(head)+"."+base64.RawURLEncoding.EncodeToString(body)
 h:=sha256.Sum256([]byte(encoded))
 signature,e:=rsa.SignPKCS1v15(rand.Reader,sk,crypto.SHA256,h[:])
 if e!=nil{t.Fatal(e)}
 return encoded+"."+base64.RawURLEncoding.EncodeToString(signature)
}
func TestFSAServerSideSignatureWithProtectedRegistration(t *testing.T){
 f:=fixture(t)
 receipt,e:=Verify(f.jwt,f.keys,f.reg,f.pin,f.now)
 if e!=nil{t.Fatal(e)}
 if !receipt.GitHubOIDCVerified||receipt.Mode!="FSA_SIDE_CRYPTOGRAPHIC_REVIEW_ONLY"||
  receipt.FSAIndependentlyDeployed||receipt.FSAFirstUseConsumed||
  receipt.FSADispatchLeaseConsumed||receipt.ScienceDispatchAuthorized||
  receipt.ScientificOriginalExecuted||receipt.AcceptedScientificResult||
  receipt.ProtectedFSARegistrationObserved{
  t.Fatalf("server-side verification incorrectly grants authority: %+v",receipt)
 }
}
func TestRejectWorkerControlledPinnedPolicyChanges(t *testing.T){
 variations:=[]func(*Registration){
  func(r *Registration){r.GitHubRunID="38190000422"},
  func(r *Registration){r.SourceSHA=strings.Repeat("0",40)},
  func(r *Registration){r.Audience="forge-r11-provenance-audit-non-authorizing"},
  func(r *Registration){r.WorkflowPath=".github/workflows/attack.yml"},
  func(r *Registration){r.Ref="refs/heads/proposal/attacker"},
  func(r *Registration){r.RepositoryID="12"},
  func(r *Registration){r.RepositoryOwnerID="12"},
  func(r *Registration){r.Lane="KTRADE"},
  func(r *Registration){r.RunAttempt=2},
  func(r *Registration){r.Event="pull_request"},
  func(r *Registration){r.AuthorityEpoch=0},
  func(r *Registration){r.CohortSHA256=strings.Repeat("0",64)},
  func(r *Registration){r.FrozenPrewakeSHA256=strings.Repeat("0",64)},
 }
 f:=fixture(t)
 for i,change:=range variations{
  changed:=f.reg;change(&changed)
  if _,e:=Verify(f.jwt,f.keys,changed,f.pin,f.now);!errors.Is(e,ErrDenied){
   t.Fatalf("registration tamper %d accepted",i)
  }
 }
}
func TestRejectSignedWrongGitHubClaims(t *testing.T){
 f:=fixture(t)
 changes:=[]func(*oidcaudit.Claims){
  func(c *oidcaudit.Claims){c.Issuer="https://attacker.invalid"},
  func(c *oidcaudit.Claims){c.Subject="repo:attacker/FORGE:ref:refs/heads/main"},
  func(c *oidcaudit.Claims){c.Audience,_=json.Marshal("forge-r11-provenance-audit-non-authorizing")},
  func(c *oidcaudit.Claims){c.Repository="attacker/FORGE"},
  func(c *oidcaudit.Claims){c.RepositoryID="0"},
  func(c *oidcaudit.Claims){c.RepositoryOwnerID="0"},
  func(c *oidcaudit.Claims){c.RepositoryVisibility="private"},
  func(c *oidcaudit.Claims){c.WorkflowRef="foreign"},
  func(c *oidcaudit.Claims){c.RunnerEnvironment="self-hosted"},
  func(c *oidcaudit.Claims){c.Ref="refs/heads/attack"},
  func(c *oidcaudit.Claims){c.RefType="tag"},
  func(c *oidcaudit.Claims){c.SHA=strings.Repeat("0",40)},
  func(c *oidcaudit.Claims){c.RunID="38190000422"},
  func(c *oidcaudit.Claims){c.RunAttempt="2"},
  func(c *oidcaudit.Claims){c.EventName="pull_request"},
  func(c *oidcaudit.Claims){c.Exp=f.now.Unix()-1},
  func(c *oidcaudit.Claims){c.Exp=f.now.Unix()+999},
  func(c *oidcaudit.Claims){c.Iat=f.now.Unix()+100},
  func(c *oidcaudit.Claims){c.Nbf=f.now.Unix()+100},
 }
 for i,change:=range changes{
  c:=f.claims;change(&c)
  token:=sign(t,f.private,c,"RS256","github-fixture-rsa")
  if _,e:=Verify(token,f.keys,f.reg,f.pin,f.now);!errors.Is(e,ErrDenied){
   t.Fatalf("mutated GitHub claim %d admitted",i)
  }
 }
}
func TestRejectWrongSignatureAlgorithmAndKey(t *testing.T){
 f:=fixture(t)
 altered:=f.keys
 altered.Keys=append([]oidcaudit.Key{},f.keys.Keys...)
 altered.Keys[0].Kid="other"
 if _,e:=Verify(f.jwt,altered,f.reg,f.pin,f.now);e==nil{t.Fatal("wrong key ID")}
 altered=f.keys
 altered.Keys=append([]oidcaudit.Key{},f.keys.Keys...)
 altered.Keys[0].E=base64.RawURLEncoding.EncodeToString([]byte{2})
 if _,e:=Verify(f.jwt,altered,f.reg,f.pin,f.now);e==nil{t.Fatal("even exponent")}
 altered=f.keys
 altered.Keys=append([]oidcaudit.Key{},f.keys.Keys...)
 altered.Keys=append(altered.Keys,altered.Keys[0])
 if _,e:=Verify(f.jwt,altered,f.reg,f.pin,f.now);e==nil{t.Fatal("duplicate kid")}
 for _,token:=range []string{
  sign(t,f.private,f.claims,"none","github-fixture-rsa"),
  sign(t,f.private,f.claims,"HS256","github-fixture-rsa"),
  f.jwt+"x",f.jwt+".extra",strings.Repeat("a",MaxJWT+1),
 }{
  if _,e:=Verify(token,f.keys,f.reg,f.pin,f.now);e==nil{t.Fatal("invalid signature")}
 }
}
type fakeTransport struct{response []byte;status int;url string}
func (f fakeTransport)RoundTrip(req *http.Request)(*http.Response,error){
 if req.URL.String()!=JWKSURL{return nil,ErrDenied}
 u,e:=url.Parse(f.url)
 if e!=nil{return nil,e}
 cp:=req.Clone(req.Context());cp.URL=u
 return &http.Response{StatusCode:f.status,Body:io.NopCloser(bytes.NewReader(f.response)),
  Request:cp,Header:make(http.Header)},nil
}
func TestFSAFetchPinsGitHubJWKSAndRejectsRedirectAndPoison(t *testing.T){
 f:=fixture(t)
 raw,_:=json.Marshal(f.keys)
 makeClient:=func(body []byte,status int,url string)*http.Client{
  return &http.Client{Transport:fakeTransport{response:body,status:status,url:url},
   CheckRedirect:func(*http.Request,[]*http.Request)error{return http.ErrUseLastResponse}}
 }
 fetched,e:=FetchGitHubKeys(context.Background(),makeClient(raw,200,JWKSURL))
 if e!=nil||len(fetched.Keys)!=1{t.Fatal("trusted JWKS parse",e)}
 bads:=[]struct{body []byte;status int;url string}{
  {raw,302,JWKSURL},{raw,200,"https://attacker.invalid/jwks"},
  {raw,500,JWKSURL},{[]byte("{}"),200,JWKSURL},
  {bytes.Repeat([]byte("x"),MaxJWKS+1),200,JWKSURL},
 }
 for _,bad:=range bads{
  if _,e:=FetchGitHubKeys(context.Background(),makeClient(bad.body,bad.status,bad.url));e==nil{
   t.Fatal("untrusted/oversized remote keyset accepted")
  }
 }
 changed:=f.keys;changed.Keys=append(changed.Keys,changed.Keys[0])
 poisoned,_:=json.Marshal(changed)
 if _,e:=FetchGitHubKeys(context.Background(),makeClient(poisoned,200,JWKSURL));e==nil{
  t.Fatal("duplicate remote JWKS key accepted")
 }
}
func TestMissingProtectedRegistrationAndWrongRunDenies(t *testing.T){
 f:=fixture(t)
 if _,e:=Verify(f.jwt,f.keys,Registration{},f.pin,f.now);e==nil{t.Fatal("absent protected FSA registration accepted")}
 if _,e:=Verify(f.jwt,f.keys,f.reg,strings.Repeat("0",64),f.now);e==nil{t.Fatal("untrusted external registration SHA")}
 if _,e:=VerifyLive(context.Background(),"",f.reg,f.pin,f.now);e==nil{t.Fatal("absent live GitHub JWT authorized")}
}
