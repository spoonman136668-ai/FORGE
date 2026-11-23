// Package fsaservice exposes a read-only, mTLS-protected service boundary
// for TWO separately hosted FORGE Scientific Authority (FSA) peers.
// No service is launched, no signer is provisioned, and no archive is written.
package fsaservice

import (
 "bytes"
 "context"
 "crypto/ed25519"
 "crypto/sha256"
 "crypto/subtle"
 "encoding/hex"
 "encoding/json"
 "errors"
 "net/http"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsaremote"
 "github.com/spoonman136668-ai/forge/researchlog"
)

var ErrUnprovisioned=errors.New("FORGE_FSA_INDEPENDENT_READONLY_SERVICE_UNPROVISIONED")
const maxJSON=fsaremote.MaxResponseBytes

// AuthorityStore MUST be separately authenticated monotonic storage in its
// own failure domain. Implementations are supplied by a qualified operator,
// never a research worker or this package.
type AuthorityStore interface{
 ReadAnchor(context.Context)(fsahead.Anchor,error)
 ReadBinding(context.Context,string)(bindingSHA256 string, bound bool, err error)
}
// WitnessStore MUST be in a different protected failure domain than
// AuthorityStore. It returns ALREADY signed, independently persisted
// checkpoints, never signs a worker-provided value here.
type WitnessStore interface{
 ReadWitness(context.Context,string)(fsaremote.SignedWitness,error)
}

type bound struct{
 pin fsaremote.Pin
 allowedClientSPKISHA256 string
}
func validHex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func validID(s string)bool{
 if len(s)<3||len(s)>80{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='z'||c>='A'&&c<='Z'||c=='-'||c=='_'){return false}}
 return true
}
func newBound(p fsaremote.Pin,clientSPKI string)(bound,error){
 if !validHex(p.ArchiveID,64)||!validID(p.KeyID)||p.AuthorityEpoch==0||
  !validHex(p.BindingSHA256,64)||p.MinimumRevision==0||
  len(p.PublicKey)!=ed25519.PublicKeySize||
  len(p.WitnessPublicKey)!=ed25519.PublicKeySize||
  bytes.Equal(p.PublicKey,p.WitnessPublicKey)||
  !validHex(clientSPKI,64){return bound{},ErrUnprovisioned}
 return bound{pin:p,allowedClientSPKISHA256:clientSPKI},nil
}
func(b bound)authenticated(r *http.Request)bool{
 if r==nil||r.TLS==nil||len(r.TLS.VerifiedChains)==0||
  len(r.TLS.PeerCertificates)==0{return false}
 sum:=sha256.Sum256(r.TLS.PeerCertificates[0].RawSubjectPublicKeyInfo)
 expected,_:=hex.DecodeString(b.allowedClientSPKISHA256)
 return subtle.ConstantTimeCompare(sum[:],expected)==1
}
func(s bound) anchorMatches(a fsahead.Anchor)bool{
 return a.ArchiveID==s.pin.ArchiveID&&a.KeyID==s.pin.KeyID&&
  bytes.Equal(a.PublicKey,s.pin.PublicKey)&&
  a.AuthorityEpoch==s.pin.AuthorityEpoch&&
  a.Sequence<=researchlog.MaxEntries&&validHex(a.HeadSHA256,64)&&
  ((a.Sequence==0&&a.HeadSHA256==researchlog.Genesis)||
   (a.Sequence>0&&a.HeadSHA256!=researchlog.Genesis))
}
func respond(w http.ResponseWriter,value any){
 raw,err:=json.Marshal(value)
 if err!=nil||len(raw)>maxJSON{
  http.Error(w,"FORGE_FSA_RESPONSE_UNAVAILABLE",http.StatusServiceUnavailable)
  return
 }
 w.Header().Set("Content-Type","application/json")
 w.Header().Set("Cache-Control","no-store")
 w.Header().Set("X-Content-Type-Options","nosniff")
 w.WriteHeader(http.StatusOK)
 _,_=w.Write(append(raw,'\n'))
}
func deny(w http.ResponseWriter,code int){
 http.Error(w,"FORGE_FSA_READONLY_DENIED",code)
}
func authenticatedRequest(w http.ResponseWriter,r *http.Request,b bound)bool{
 if !b.authenticated(r){deny(w,http.StatusUnauthorized);return false}
 if r.ContentLength>0||r.URL==nil||r.URL.Fragment!=""{
  deny(w,http.StatusBadRequest);return false
 }
 return true
}

// AuthorityHandler provides authenticated, pinned GETs only.
// POST /v1/fsa/cas is deliberately not implemented: an anchor-only CAS
// without a verified signed scientific checkpoint is unsafe. The existing
// fsaremote client fails closed until a separately qualified authority
// server and atomic evidence-verified CAS backend are deployed.
func AuthorityHandler(pin fsaremote.Pin,clientSPKI string,store AuthorityStore)(http.Handler,error){
 b,err:=newBound(pin,clientSPKI)
 if err!=nil||store==nil{return nil,ErrUnprovisioned}
 return http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){
  if !authenticatedRequest(w,r,b){return}
  if r.Method!=http.MethodGet{deny(w,http.StatusMethodNotAllowed);return}
  switch r.URL.Path{
  case "/v1/fsa/anchor":
   if r.URL.RawQuery!=""{deny(w,http.StatusBadRequest);return}
   a,err:=store.ReadAnchor(r.Context())
   if err!=nil||!b.anchorMatches(a){deny(w,http.StatusServiceUnavailable);return}
   respond(w,struct{
    Schema string `json:"schema"`
    Anchor fsaremote.AnchorWire `json:"anchor"`
   }{Schema:fsaremote.WireSchema,Anchor:fsaremote.AnchorWire{
    ArchiveID:a.ArchiveID,KeyID:a.KeyID,PublicKeyHex:hex.EncodeToString(a.PublicKey),
    AuthorityEpoch:a.AuthorityEpoch,Sequence:a.Sequence,HeadSHA256:a.HeadSHA256}})
  case "/v1/fsa/binding":
   args:=r.URL.Query()
   if len(args)!=1||len(args["archive_id"])!=1||
    args.Get("archive_id")!=pin.ArchiveID{
    deny(w,http.StatusBadRequest);return
   }
   digest,bound,err:=store.ReadBinding(r.Context(),pin.ArchiveID)
   if err!=nil||digest!=pin.BindingSHA256{deny(w,http.StatusServiceUnavailable);return}
   respond(w,struct{
    Schema string `json:"schema"`
    ArchiveID string `json:"archive_id"`
    BindingSHA256 string `json:"binding_sha256"`
    Bound bool `json:"bound"`
   }{Schema:fsaremote.WireSchema,ArchiveID:pin.ArchiveID,
    BindingSHA256:digest,Bound:bound})
  default: deny(w,http.StatusNotFound)
  }
 }),nil
}

// WitnessHandler independently verifies the pre-signed persisted highwater
// before serving it. A fresh authority read must match at the CLIENT.
// The witness cannot issue or update a checkpoint through this handler.
func WitnessHandler(pin fsaremote.Pin,clientSPKI string,store WitnessStore)(http.Handler,error){
 b,err:=newBound(pin,clientSPKI)
 if err!=nil||store==nil{return nil,ErrUnprovisioned}
 return http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){
  if !authenticatedRequest(w,r,b){return}
  if r.Method!=http.MethodGet{deny(w,http.StatusMethodNotAllowed);return}
  if r.URL.Path!="/v1/fsa/highwater"{deny(w,http.StatusNotFound);return}
  args:=r.URL.Query()
  if len(args)!=1||len(args["archive_id"])!=1||
   args.Get("archive_id")!=pin.ArchiveID{
   deny(w,http.StatusBadRequest);return
  }
  signed,err:=store.ReadWitness(r.Context(),pin.ArchiveID)
  if err!=nil{deny(w,http.StatusServiceUnavailable);return}
  h:=signed.Head
  a:=fsahead.Anchor{ArchiveID:h.ArchiveID,KeyID:h.KeyID,
   PublicKey:pin.PublicKey,AuthorityEpoch:h.AuthorityEpoch,
   Sequence:h.Sequence,HeadSHA256:h.HeadSHA256}
  if !b.anchorMatches(a)||fsaremote.VerifyWitness(pin,signed,a)!=nil{
   deny(w,http.StatusServiceUnavailable);return
  }
  respond(w,struct{
   Schema string `json:"schema"`
   Witness fsaremote.SignedWitness `json:"witness"`
  }{Schema:fsaremote.WireSchema,Witness:signed})
 }),nil
}
