// Package fsaremoteissuer is a client-only, fail-closed mutual-TLS boundary
// to a separately provisioned FORGE FSA first-use issuance service.
// It creates NO server, key, authority, scheduler, or scientific experiment.
package fsaremoteissuer

import (
 "bytes"
 "context"
 "crypto/ed25519"
 "crypto/rand"
 "crypto/sha256"
 "crypto/tls"
 "crypto/x509"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "net/http"
 "net/url"
 "strings"
 "time"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsaissuance"
)

const (
 WireSchema="forge.fsa.remote-first-use-issuer.v1"
 ApprovalSchema="forge.fsa.independent-first-use-approval.v1"
 ApprovalDomain="FORGE-FSA-FIRST-USE-INDEPENDENT-APPROVAL-V1\n"
 MaxBytes=16384
)
var (
 ErrConfiguration=errors.New("FORGE_FSA_REMOTE_ISSUER_INDEPENDENT_PINS_REQUIRED")
 ErrUncertain=errors.New("FORGE_FSA_REMOTE_ISSUER_UNCERTAIN_NO_RETRY")
 ErrUnauthorized=errors.New("FORGE_FSA_REMOTE_ISSUER_APPROVAL_UNTRUSTED")
)

type Config struct {
 BaseURL string
 // These two destinations are independently supplied, NOT discovered from
 // the remote issuer. Endpoint equality is forbidden; physical independence
 // still requires separately measured provisioning/fault evidence.
 AuthorityURL string
 WitnessURL string
 Roots *x509.CertPool
 ClientCertificate tls.Certificate
 ServerSPKISHA256 string
 ApprovalPublicKey ed25519.PublicKey
 FSAHeadPublicKey ed25519.PublicKey
 ApprovalKeyID string
}
type Request struct{
 Schema string `json:"schema"`
 Intent fsaissuance.IssuanceRequest `json:"intent"`
 ChallengeHex string `json:"challenge_hex"`
}
type Approval struct {
 Schema string `json:"schema"`
 ArchiveID string `json:"archive_id"`
 AuthorityEpoch uint64 `json:"authority_epoch"`
 Lane string `json:"lane"`
 CohortSHA256 string `json:"cohort_sha256"`
 RequestSHA256 string `json:"request_sha256"`
 CheckpointSHA256 string `json:"checkpoint_sha256"`
 ChallengeHex string `json:"challenge_hex"`
 ApproverKeyID string `json:"approver_key_id"`
 Verdict string `json:"verdict"`
}
type Reply struct {
 Schema string `json:"schema"`
 Approval Approval `json:"approval"`
 ApprovalSignatureHex string `json:"approval_signature_hex"`
 Checkpoint fsahead.SignedHead `json:"checkpoint"`
}
type Client struct {
 endpoint string
 httpClient *http.Client
 approvalKey ed25519.PublicKey
 headKey ed25519.PublicKey
 approverKeyID string
}
func validHex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !((c>='0'&&c<='9')||(c>='a'&&c<='f')){return false}}
 return true
}
func validID(s string)bool{
 if len(s)<3||len(s)>80{return false}
 for _,c:=range s{if !((c>='A'&&c<='Z')||(c>='a'&&c<='z')||(c>='0'&&c<='9')||(c=='_')||(c=='-')){return false}}
 return true
}
func endpoint(s string)(string,error){
 u,err:=url.Parse(s)
 if err!=nil||u.Scheme!="https"||u.Host==""||u.Hostname()==""||
  u.User!=nil||u.Path!=""&&u.Path!="/"||u.RawQuery!=""||u.Fragment!=""||
  strings.ContainsAny(u.Host,"@\\\r\n\x00"){return "",ErrConfiguration}
 return "https://"+u.Host,nil
}
func digest(v any)(string,error){
 b,err:=json.Marshal(v)
 if err!=nil||len(b)==0||len(b)>MaxBytes{return "",ErrUnauthorized}
 sum:=sha256.Sum256(b)
 return hex.EncodeToString(sum[:]),nil
}
func New(cfg Config)(*Client,error){
 issuer,err:=endpoint(cfg.BaseURL);if err!=nil{return nil,err}
 authority,err:=endpoint(cfg.AuthorityURL);if err!=nil{return nil,err}
 witness,err:=endpoint(cfg.WitnessURL);if err!=nil{return nil,err}
 if issuer==authority||issuer==witness||authority==witness||
  cfg.Roots==nil||len(cfg.ClientCertificate.Certificate)==0||
  cfg.ClientCertificate.PrivateKey==nil||!validHex(cfg.ServerSPKISHA256,64)||
  len(cfg.ApprovalPublicKey)!=ed25519.PublicKeySize||
  len(cfg.FSAHeadPublicKey)!=ed25519.PublicKeySize||
  bytes.Equal(cfg.ApprovalPublicKey,cfg.FSAHeadPublicKey)||
  !validID(cfg.ApprovalKeyID){return nil,ErrConfiguration}
 pin:=cfg.ServerSPKISHA256
 tlsConfig:=&tls.Config{
  MinVersion:tls.VersionTLS13,RootCAs:cfg.Roots.Clone(),
  Certificates:[]tls.Certificate{cfg.ClientCertificate},
  VerifyConnection:func(cs tls.ConnectionState)error{
   if len(cs.VerifiedChains)==0||len(cs.PeerCertificates)==0{return ErrUnauthorized}
   sum:=sha256.Sum256(cs.PeerCertificates[0].RawSubjectPublicKeyInfo)
   if hex.EncodeToString(sum[:])!=pin{return ErrUnauthorized}
   return nil
  },
 }
 transport:=&http.Transport{TLSClientConfig:tlsConfig,
  DisableCompression:true,MaxIdleConnsPerHost:1,
  TLSHandshakeTimeout:5*time.Second,IdleConnTimeout:5*time.Second}
 client:=&http.Client{Transport:transport,Timeout:10*time.Second,
  CheckRedirect:func(*http.Request,[]*http.Request)error{return http.ErrUseLastResponse}}
 return &Client{endpoint:issuer+"/v1/fsa/issue-first-use",
  httpClient:client,
  approvalKey:append(ed25519.PublicKey(nil),cfg.ApprovalPublicKey...),
  headKey:append(ed25519.PublicKey(nil),cfg.FSAHeadPublicKey...),
  approverKeyID:cfg.ApprovalKeyID},nil
}
func (c *Client)Close(){
 if c!=nil&&c.httpClient!=nil{c.httpClient.CloseIdleConnections()}
}
func validIntent(r fsaissuance.IssuanceRequest)bool{
 return validHex(r.PlanSHA256,64)&&validHex(r.ArchiveID,64)&&
  validHex(r.PreviousHeadSHA256,64)&&validHex(r.ProposedHeadSHA256,64)&&
  validHex(r.CohortSHA256,64)&&validHex(r.SourceQualificationWitnessSHA256,64)&&
  validID(r.ExperimentID)&&len(r.Lane)>0&&
  (r.Lane=="Wingless"||r.Lane=="Yggdrasil")&&
  r.AuthorityEpoch>0&&r.ProposedSequence==r.PreviousSequence+1
}
// IssueFirstUse is an FSA-side transport, not an optimizer operation. An
// I/O error after the request leaves issuance uncertain; never retry here.
// A returned checkpoint still requires the separate R6 journal/CAS checks.
func (c *Client)IssueFirstUse(ctx context.Context,r fsaissuance.IssuanceRequest)(fsahead.SignedHead,error){
 var zero fsahead.SignedHead
 if c==nil||c.httpClient==nil||ctx==nil||ctx.Err()!=nil||!validIntent(r){
  return zero,ErrConfiguration
 }
 challenge:=make([]byte,32)
 if _,err:=rand.Read(challenge);err!=nil{return zero,ErrUncertain}
 challengeHex:=hex.EncodeToString(challenge)
 msg:=Request{Schema:WireSchema,Intent:r,ChallengeHex:challengeHex}
 body,err:=json.Marshal(msg)
 if err!=nil||len(body)>MaxBytes{return zero,ErrConfiguration}
 req,err:=http.NewRequestWithContext(ctx,http.MethodPost,c.endpoint,bytes.NewReader(body))
 if err!=nil{return zero,ErrConfiguration}
 req.Header.Set("Content-Type","application/json")
 req.Header.Set("Accept","application/json")
 response,err:=c.httpClient.Do(req)
 if err!=nil{return zero,ErrUncertain}
 defer response.Body.Close()
 if response.StatusCode==http.StatusForbidden||response.StatusCode==http.StatusUnauthorized||
  response.StatusCode==http.StatusConflict{return zero,ErrUnauthorized}
 if response.StatusCode!=http.StatusOK{return zero,ErrUncertain}
 raw,err:=io.ReadAll(io.LimitReader(response.Body,MaxBytes+1))
 if err!=nil||len(raw)==0||len(raw)>MaxBytes{return zero,ErrUncertain}
 d:=json.NewDecoder(bytes.NewReader(raw));d.DisallowUnknownFields()
 var reply Reply
 if err=d.Decode(&reply);err!=nil{return zero,ErrUnauthorized}
 var extra any
 if err=d.Decode(&extra);err!=io.EOF{return zero,ErrUnauthorized}
 if reply.Schema!=WireSchema||reply.Approval.Schema!=ApprovalSchema||
  reply.Approval.Verdict!="FSA_INDEPENDENT_FIRST_USE_APPROVED"||
  reply.Approval.ArchiveID!=r.ArchiveID||
  reply.Approval.AuthorityEpoch!=r.AuthorityEpoch||
  reply.Approval.Lane!=r.Lane||
  reply.Approval.CohortSHA256!=r.CohortSHA256||
  reply.Approval.ChallengeHex!=challengeHex||
  reply.Approval.ApproverKeyID!=c.approverKeyID||
  !validHex(reply.ApprovalSignatureHex,128){return zero,ErrUnauthorized}
 reqSHA,err:=digest(msg);if err!=nil||reply.Approval.RequestSHA256!=reqSHA{return zero,ErrUnauthorized}
 headSHA,err:=digest(reply.Checkpoint);if err!=nil||reply.Approval.CheckpointSHA256!=headSHA{return zero,ErrUnauthorized}
 aRaw,err:=json.Marshal(reply.Approval);if err!=nil{return zero,ErrUnauthorized}
 sig,_:=hex.DecodeString(reply.ApprovalSignatureHex)
 if !ed25519.Verify(c.approvalKey,append([]byte(ApprovalDomain),aRaw...),sig){
  return zero,ErrUnauthorized
 }
 h:=reply.Checkpoint.Payload
 if h.Schema!=fsahead.Schema||h.Domain!=fsahead.Domain||
  h.ArchiveID!=r.ArchiveID||h.AuthorityEpoch!=r.AuthorityEpoch||
  h.ParentSequence!=r.PreviousSequence||
  h.ParentHeadSHA256!=r.PreviousHeadSHA256||
  h.Sequence!=r.ProposedSequence||h.HeadSHA256!=r.ProposedHeadSHA256||
  !validHex(reply.Checkpoint.SignatureHex,128){return zero,ErrUnauthorized}
 hb,err:=json.Marshal(h);if err!=nil{return zero,ErrUnauthorized}
 hs,_:=hex.DecodeString(reply.Checkpoint.SignatureHex)
 if !ed25519.Verify(c.headKey,append([]byte("FORGE-FSA-ARCHIVE-HEAD-SIGNATURE-V1\n"),hb...),hs){
  return zero,ErrUnauthorized
 }
 return reply.Checkpoint,nil
}
var _ fsaissuance.Issuer=(*Client)(nil)
