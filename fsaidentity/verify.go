// Package fsaidentity is the FORGE Scientific Authority-side GitHub OIDC
// verification boundary. Protected registrations MUST be loaded from FSA
// custody, never from the hosted worker being verified. No issuer or dispatch.
package fsaidentity

import (
 "bytes"
 "context"
 "crypto"
 "crypto/rsa"
 "crypto/sha256"
 "crypto/tls"
 "encoding/base64"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "math/big"
 "net/http"
 "strconv"
 "strings"
 "time"

 "github.com/spoonman136668-ai/forge/oidcaudit"
)

const (
 Schema = "forge.fsa.protected-github-registration.v1"
 ReceiptSchema = "forge.fsa.oidc-identity-review.v1"
 Repository = "spoonman136668-ai/FORGE"
 RepositoryID = "1413298198"
 OwnerID = "253477821"
 Issuer = "https://token.actions.githubusercontent.com"
 JWKSURL = "https://token.actions.githubusercontent.com/.well-known/jwks"
 MaxJWT = 16384
 MaxJWKS = 65536
)
var ErrDenied=errors.New("FORGE_FSA_IDENTITY_DENIED_NO_SCIENTIFIC_DISPATCH")

// Registration is an FSA-owned frozen record. Its SHA-256 MUST be pinned in
// independently protected FSA state before any worker presents an OIDC JWT.
type Registration struct {
 Schema string
 Audience string
 Repository string
 RepositoryID string
 RepositoryOwnerID string
 WorkflowPath string
 Ref string
 Event string
 SourceSHA string
 GitHubRunID string
 RunAttempt int
 Lane string
 CohortSHA256 string
 FrozenPrewakeSHA256 string
 FrozenRunClaimSHA256 string
 AuthorityEpoch uint64
}
type Receipt struct {
 Schema string
 Mode string
 FrozenRegistrationSHA256 string
 SourceSHA string
 RunID string
 Lane string
 CohortSHA256 string
 GitHubOIDCVerified bool
 ProtectedFSARegistrationObserved bool
 FSAIndependentlyDeployed bool
 FSAFirstUseConsumed bool
 FSADispatchLeaseConsumed bool
 ScienceDispatchAuthorized bool
 ScientificOriginalExecuted bool
 AcceptedScientificResult bool
}

func hexLower(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s {if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func validRun(s string)bool{
 if len(s)<1||len(s)>20||s[0]=='0'{return false}
 for _,c:=range s{if c<'0'||c>'9'{return false}}
 u,e:=strconv.ParseUint(s,10,64);return e==nil&&u!=0
}
func validRegistration(r Registration)bool{
 if r.Schema!=Schema||r.Repository!=Repository||
 r.RepositoryID!=RepositoryID||r.RepositoryOwnerID!=OwnerID||
 r.WorkflowPath!=".github/workflows/forge-fsa-original.yml"||
 r.Ref!="refs/heads/main"||
 (r.Event!="workflow_dispatch"&&r.Event!="repository_dispatch")||
 r.Audience!="forge-fsa-issuer-authorization-v1"||
 !hexLower(r.SourceSHA,40)||!validRun(r.GitHubRunID)||
 r.RunAttempt!=1||(r.Lane!="Wingless"&&r.Lane!="Yggdrasil")||
 !hexLower(r.CohortSHA256,64)||!hexLower(r.FrozenPrewakeSHA256,64)||
 !hexLower(r.FrozenRunClaimSHA256,64)||r.AuthorityEpoch==0{return false}
 return true
}
func RegistrationSHA(r Registration)(string,error){
 if !validRegistration(r){return "",ErrDenied}
 b,e:=json.Marshal(r);if e!=nil||len(b)>8192{return "",ErrDenied}
 h:=sha256.Sum256(b);return hex.EncodeToString(h[:]),nil
}
func rawDecode(s string,max int)([]byte,error){
 if len(s)>max*2{return nil,ErrDenied}
 v,e:=base64.RawURLEncoding.DecodeString(s)
 if e!=nil||len(v)==0||len(v)>max{return nil,ErrDenied}
 return v,nil
}
func audienceOK(raw json.RawMessage,expected string)bool{
 var s string
 if json.Unmarshal(raw,&s)==nil{return s==expected}
 var arr []string
 return json.Unmarshal(raw,&arr)==nil&&len(arr)==1&&arr[0]==expected
}
func keyRSA(k oidcaudit.Key)(*rsa.PublicKey,error){
 if k.Kty!="RSA"||k.Alg!="RS256"||k.Use!="sig"||k.Kid==""{return nil,ErrDenied}
 n,err:=rawDecode(k.N,1024);if err!=nil||len(n)<256{return nil,ErrDenied}
 exp,err:=rawDecode(k.E,4);if err!=nil{return nil,ErrDenied}
 e:=0
 for _,v:=range exp{e=e*256+int(v)}
 if e!=65537&&e!=3{return nil,ErrDenied}
 p:=&rsa.PublicKey{N:new(big.Int).SetBytes(n),E:e}
 if p.N.BitLen()<2048||p.N.BitLen()>8192{return nil,ErrDenied}
 return p,nil
}
// Verify never accepts a self-reported runner receipt. The registration and
// SHA pin are supplied by the FSA (protected out-of-band); the JWT is from
// the runner over a channel that an independent FSA must authenticate.
func Verify(jwt string,keys oidcaudit.JWKS,registration Registration,
 independentlyPinnedRegistrationSHA string,now time.Time)(Receipt,error){
 var empty Receipt
 actual,err:=RegistrationSHA(registration)
 if err!=nil||!hexLower(independentlyPinnedRegistrationSHA,64)||
 actual!=independentlyPinnedRegistrationSHA||len(jwt)<100||len(jwt)>MaxJWT||
 len(keys.Keys)==0||len(keys.Keys)>32{return empty,ErrDenied}
 parts:=strings.Split(jwt,".")
 if len(parts)!=3{return empty,ErrDenied}
 rawHeader,err:=rawDecode(parts[0],2048);if err!=nil{return empty,ErrDenied}
 rawClaims,err:=rawDecode(parts[1],8192);if err!=nil{return empty,ErrDenied}
 signature,err:=rawDecode(parts[2],1024);if err!=nil{return empty,ErrDenied}
 var h oidcaudit.Header
 if json.Unmarshal(rawHeader,&h)!=nil||h.Alg!="RS256"||h.Kid==""||
 (h.Typ!=""&&h.Typ!="JWT"){return empty,ErrDenied}
 var pub *rsa.PublicKey
 for _,k:=range keys.Keys {
  if k.Kid!=h.Kid{continue}
  if pub!=nil{return empty,ErrDenied}
  key,e:=keyRSA(k);if e!=nil{return empty,ErrDenied}
  pub=key
 }
 if pub==nil{return empty,ErrDenied}
 msg:=sha256.Sum256([]byte(parts[0]+"."+parts[1]))
 if rsa.VerifyPKCS1v15(pub,crypto.SHA256,msg[:],signature)!=nil{return empty,ErrDenied}
 var c oidcaudit.Claims
 if json.Unmarshal(rawClaims,&c)!=nil{return empty,ErrDenied}
 secs:=now.Unix()
 expectSub:="repo:"+Repository+":ref:"+registration.Ref
 if c.Issuer!=Issuer||!audienceOK(c.Audience,registration.Audience)||
 c.Subject!=expectSub||c.Exp<=secs||c.Exp>secs+600||
 c.Iat>secs+30||c.Iat<secs-600||c.Exp<=c.Iat||
 c.Nbf>secs+30||c.Nbf<secs-600||
 c.Repository!=Repository||c.RepositoryID!=RepositoryID||
 c.RepositoryOwnerID!=OwnerID||c.RepositoryVisibility!="public"||
 c.RunnerEnvironment!="github-hosted"||
 c.WorkflowRef!=Repository+"/"+registration.WorkflowPath+"@"+registration.Ref||
 c.Ref!=registration.Ref||c.RefType!="branch"||
 c.SHA!=registration.SourceSHA||c.RunID!=registration.GitHubRunID||
 c.RunAttempt!="1"||c.EventName!=registration.Event{return empty,ErrDenied}
 return Receipt{
  Schema:ReceiptSchema,Mode:"FSA_SIDE_CRYPTOGRAPHIC_REVIEW_ONLY",
  FrozenRegistrationSHA256:actual,SourceSHA:registration.SourceSHA,
  RunID:registration.GitHubRunID,Lane:registration.Lane,
  CohortSHA256:registration.CohortSHA256,GitHubOIDCVerified:true,
 },nil
}

// FetchGitHubKeys retrieves JWKS from the hardcoded GitHub endpoint with
// system TLS validation and NO redirects or caller-configurable remote URL.
// This never downloads a JWT or trusts keys supplied by a worker.
func FetchGitHubKeys(ctx context.Context,client *http.Client)(oidcaudit.JWKS,error){
 var zero oidcaudit.JWKS
 if ctx==nil||ctx.Err()!=nil||client==nil{return zero,ErrDenied}
 req,e:=http.NewRequestWithContext(ctx,http.MethodGet,JWKSURL,nil)
 if e!=nil{return zero,ErrDenied}
 req.Header.Set("Accept","application/json")
 response,e:=client.Do(req)
 if e!=nil{return zero,ErrDenied}
 defer response.Body.Close()
 if response.Request==nil||response.Request.URL.String()!=JWKSURL||
 response.StatusCode!=http.StatusOK{return zero,ErrDenied}
 b,e:=io.ReadAll(io.LimitReader(response.Body,MaxJWKS+1))
 if e!=nil||len(b)==0||len(b)>MaxJWKS{return zero,ErrDenied}
 d:=json.NewDecoder(bytes.NewReader(b));d.DisallowUnknownFields()
 var keys oidcaudit.JWKS
 if d.Decode(&keys)!=nil{return zero,ErrDenied}
 var extra any
 if d.Decode(&extra)!=io.EOF||len(keys.Keys)==0||len(keys.Keys)>32{return zero,ErrDenied}
 seen:=map[string]bool{}
 for _,k:=range keys.Keys {
  if seen[k.Kid]||k.Kid==""{return zero,ErrDenied}
  seen[k.Kid]=true
  if _,e:=keyRSA(k);e!=nil{return zero,ErrDenied}
 }
 return keys,nil
}
func NewGitHubClient()*http.Client{
 return &http.Client{
  Timeout:10*time.Second,
  Transport:&http.Transport{
   TLSClientConfig:&tls.Config{MinVersion:tls.VersionTLS12},
   DisableCompression:true,MaxIdleConnsPerHost:1,
   TLSHandshakeTimeout:5*time.Second},
  CheckRedirect:func(*http.Request,[]*http.Request)error{return http.ErrUseLastResponse},
 }
}

 // VerifyLive is the only production-oriented entrypoint. It obtains GitHub
 // keys over the hardcoded HTTPS endpoint; caller cannot substitute JWKS.
func VerifyLive(ctx context.Context,jwt string,registration Registration,
 pinnedRegistrationSHA string,now time.Time)(Receipt,error){
 var zero Receipt
 if ctx==nil||ctx.Err()!=nil{return zero,ErrDenied}
 client:=NewGitHubClient()
 defer client.CloseIdleConnections()
 keys,err:=FetchGitHubKeys(ctx,client)
 if err!=nil{return zero,ErrDenied}
 return Verify(jwt,keys,registration,pinnedRegistrationSHA,now)
}
