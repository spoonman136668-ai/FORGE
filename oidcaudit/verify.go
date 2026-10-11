// Package oidcaudit verifies real GitHub Actions RS256 OIDC provenance.
// It is read-only and cannot authorize FSA science, consume leases or dispatch.
package oidcaudit

import (
 "crypto"
 "crypto/rsa"
 "crypto/sha256"
 "encoding/base64"
 "encoding/json"
 "errors"
 "math/big"
 "strings"
 "time"
)

const (
 Issuer="https://token.actions.githubusercontent.com"
 JWKSURL="https://token.actions.githubusercontent.com/.well-known/jwks"
 Audience="forge-r11-provenance-audit-non-authorizing"
 Repository="spoonman136668-ai/FORGE"
 RepositoryID="1413298198"
 OwnerID="253477821"
 Branch="refs/heads/proposal/dreamrsi-r11-oidc-20261011"
 WorkflowRef=Repository+"/.github/workflows/qualify-dreamrsi-r11-oidc.yml@"+Branch
 Schema="forge.oidc.provenance-audit.v1"
)
var ErrDenied=errors.New("FORGE_R11_GITHUB_OIDC_UNTRUSTED_NO_SCIENCE")
type Context struct{
 SourceSHA string
 RunID string
 Attempt string
 Repository string
 RepositoryID string
 Ref string
 Event string
}
type Header struct{
 Alg string `json:"alg"`
 Kid string `json:"kid"`
 Typ string `json:"typ"`
}
type Claims struct{
 Issuer string `json:"iss"`
 Audience json.RawMessage `json:"aud"`
 Subject string `json:"sub"`
 Exp int64 `json:"exp"`
 Iat int64 `json:"iat"`
 Nbf int64 `json:"nbf"`
 Repository string `json:"repository"`
 RepositoryID string `json:"repository_id"`
 RepositoryOwnerID string `json:"repository_owner_id"`
 RepositoryVisibility string `json:"repository_visibility"`
 RunnerEnvironment string `json:"runner_environment"`
 WorkflowRef string `json:"workflow_ref"`
 Ref string `json:"ref"`
 RefType string `json:"ref_type"`
 SHA string `json:"sha"`
 RunID string `json:"run_id"`
 RunAttempt string `json:"run_attempt"`
 EventName string `json:"event_name"`
}
type Key struct {
 Kty string `json:"kty"`
 Kid string `json:"kid"`
 Alg string `json:"alg"`
 Use string `json:"use"`
 N string `json:"n"`
 E string `json:"e"`
}
type JWKS struct{Keys []Key `json:"keys"`}
type Receipt struct {
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Repository string `json:"repository"`
 RepositoryID string `json:"repository_id"`
 SourceSHA string `json:"source_sha"`
 RunID string `json:"run_id"`
 FirstAttempt bool `json:"first_attempt"`
 GitHubRS256SignatureVerified bool `json:"github_rs256_signature_verified"`
 ExactWorkflowAndRepositoryVerified bool `json:"exact_workflow_and_repository_verified"`
 GitHubHostedEnvironmentVerified bool `json:"github_hosted_environment_verified"`
 IndependentlyWitnessedByFSA bool `json:"independently_witnessed_by_fsa"`
 PhysicalCustodyVerified bool `json:"physical_custody_verified"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 ScientificOriginalExecuted bool `json:"scientific_original_executed"`
 AcceptedScience bool `json:"accepted_science"`
}
func lowerSHA(s string)bool{
 if len(s)!=40{return false}
 for _,b:=range s{if !(b>='0'&&b<='9'||b>='a'&&b<='f'){return false}}
 return true
}
func auditAudience(raw json.RawMessage)bool{
 var s string
 if json.Unmarshal(raw,&s)==nil{return s==Audience}
 var arr []string
 if json.Unmarshal(raw,&arr)==nil&&len(arr)==1{return arr[0]==Audience}
 return false
}
func validateContext(c Context)bool{
 return c.Repository==Repository&&c.RepositoryID==RepositoryID&&
  c.Ref==Branch&&c.Event=="push"&&c.Attempt=="1"&&
  lowerSHA(c.SourceSHA)&&len(c.RunID)>0&&len(c.RunID)<20&&c.RunID[0]!='0'&&
  allDigits(c.RunID)
}
func allDigits(s string)bool{for _,b:=range s{if b<'0'||b>'9'{return false}};return len(s)>0}
func ValidateClaims(c Claims,expected Context,now time.Time)error{
 secs:=now.Unix()
 if !validateContext(expected)||c.Issuer!=Issuer||
  !auditAudience(c.Audience)||len(c.Subject)<3||
  c.Exp<=secs||c.Exp>secs+900||c.Iat>secs+30||
  c.Iat<secs-900||c.Exp<=c.Iat||c.Nbf>secs+30||
  c.Repository!=expected.Repository||c.RepositoryID!=expected.RepositoryID||
  c.RepositoryOwnerID!=OwnerID||
  c.RepositoryVisibility!="public"||c.RunnerEnvironment!="github-hosted"||
  c.WorkflowRef!=WorkflowRef||c.Ref!=expected.Ref||c.RefType!="branch"||
  c.SHA!=expected.SourceSHA||c.RunID!=expected.RunID||
  c.RunAttempt!=expected.Attempt||c.EventName!=expected.Event{
  return ErrDenied
 }
 return nil
}
func keyRSA(k Key)(*rsa.PublicKey,error){
 if k.Kty!="RSA"||(k.Alg!=""&&k.Alg!="RS256")||
  (k.Use!=""&&k.Use!="sig")||k.Kid==""{
  return nil,ErrDenied
 }
 n,e:=decode(k.N),decode(k.E)
 if len(n)<256||len(n)>1024||len(e)==0||len(e)>4{return nil,ErrDenied}
 exponent:=0
 for _,v:=range e{exponent=exponent*256+int(v)}
 if exponent<3||exponent%2==0{return nil,ErrDenied}
 key:=&rsa.PublicKey{N:new(big.Int).SetBytes(n),E:exponent}
 if key.N.BitLen()<2048{return nil,ErrDenied}
 return key,nil
}
func decode(s string)[]byte{v,e:=base64.RawURLEncoding.DecodeString(s);if e!=nil{return nil};return v}
// VerifySignedToken validates the JWT signature with a key independently
// retrieved over HTTPS from GitHub, then checks ALL exact source/run claims.
// The raw bearer JWT is NEVER returned or written to the public artifacts.
func VerifySignedToken(jwt string,jwks JWKS,ctx Context,now time.Time)(Receipt,error){
 var zero Receipt
 if len(jwt)<100||len(jwt)>16384||len(jwks.Keys)==0||len(jwks.Keys)>32{
  return zero,ErrDenied
 }
 parts:=strings.Split(jwt,".")
 if len(parts)!=3{return zero,ErrDenied}
 h:=decode(parts[0]);p:=decode(parts[1]);sig:=decode(parts[2])
 if len(h)==0||len(h)>2048||len(p)==0||len(p)>8192||len(sig)<256{
  return zero,ErrDenied
 }
 var header Header
 if json.Unmarshal(h,&header)!=nil||header.Alg!="RS256"||header.Kid==""||
  (header.Typ!=""&&header.Typ!="JWT"){return zero,ErrDenied}
 var selected *rsa.PublicKey
 for _,k:=range jwks.Keys{
  if k.Kid!=header.Kid{continue}
  if selected!=nil{return zero,ErrDenied}
  key,err:=keyRSA(k);if err!=nil{return zero,ErrDenied}
  selected=key
 }
 if selected==nil{return zero,ErrDenied}
 hash:=sha256.Sum256([]byte(parts[0]+"."+parts[1]))
 if rsa.VerifyPKCS1v15(selected,crypto.SHA256,hash[:],sig)!=nil{return zero,ErrDenied}
 var claims Claims
 if json.Unmarshal(p,&claims)!=nil||ValidateClaims(claims,ctx,now)!=nil{return zero,ErrDenied}
 return Receipt{
  Schema:Schema,Mode:"GITHUB_OIDC_SIGNATURE_VERIFIED_SHADOW_ONLY",
  Repository:Repository,RepositoryID:RepositoryID,
  SourceSHA:ctx.SourceSHA,RunID:ctx.RunID,FirstAttempt:true,
  GitHubRS256SignatureVerified:true,
  ExactWorkflowAndRepositoryVerified:true,
  GitHubHostedEnvironmentVerified:true,
 },nil
}
