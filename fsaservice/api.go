// Package fsaservice contains inactive, source-only HTTP handlers for the
// FORGE FSA trust protocol. It does not create a listener, signer, credential,
// storage backend, scheduler, or scientific execution authority.
package fsaservice

import (
 "bytes"
 "context"
 "crypto/ed25519"
 "crypto/sha256"
 "crypto/tls"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "net/http"
 "net/url"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsaremote"
 "github.com/spoonman136668-ai/forge/fsatrust"
 "github.com/spoonman136668-ai/forge/researchlog"
)

// Admission MUST be supplied by a separately governed, fail-closed verifier.
// A "true" from a local development stub does not constitute provisioning,
// a physical archive-instance proof or signed scientific-source admission.
type Admission interface {
 VerifyPhysicalBinding(context.Context, string, string) (bool, error)
 VerifySignedTransition(context.Context, fsahead.Anchor, fsahead.Anchor) (bool, error)
}
type AuthorityConfig struct {
 Backend fsatrust.Authority
 Admission Admission
 Genesis fsahead.Anchor
 BindingSHA256 string
 ClientSPKISHA256 string
}
type WitnessReader interface {
 ReadHighWater(context.Context, string) (fsaremote.SignedWitness, error)
}
type WitnessConfig struct {
 Reader WitnessReader
 Pin fsaremote.Pin
 ClientSPKISHA256 string
}
type anchorEnvelope struct {
 Schema string `json:"schema"`
 Anchor fsaremote.AnchorWire `json:"anchor"`
}
type bindingEnvelope struct {
 Schema string `json:"schema"`
 ArchiveID string `json:"archive_id"`
 BindingSHA256 string `json:"binding_sha256"`
 Bound bool `json:"bound"`
}
type casEnvelope struct {
 Schema string `json:"schema"`
 Previous fsaremote.AnchorWire `json:"previous"`
 Next fsaremote.AnchorWire `json:"next"`
}
type casResult struct {
 Schema string `json:"schema"`
 Committed bool `json:"committed"`
}
type witnessEnvelope struct {
 Schema string `json:"schema"`
 Witness fsaremote.SignedWitness `json:"witness"`
}
func hex64(v string) bool {
 if len(v)!=64{return false}
 for _,r:=range v {if !(r>='0'&&r<='9'||r>='a'&&r<='f'){return false}}
 return true
}
func validID(v string) bool {
 if len(v)<3||len(v)>80{return false}
 for _,r:=range v {
  if !(r>='a'&&r<='z'||r>='A'&&r<='Z'||r>='0'&&r<='9'||r=='_'||r=='-'){return false}
 }
 return true
}
func genesisValid(a fsahead.Anchor) bool {
 return hex64(a.ArchiveID)&&validID(a.KeyID)&&len(a.PublicKey)==ed25519.PublicKeySize&&a.AuthorityEpoch>0&&
  a.Sequence==0&&a.HeadSHA256==researchlog.Genesis
}
func sameIdentity(a,b fsahead.Anchor) bool {
 return a.ArchiveID==b.ArchiveID&&a.KeyID==b.KeyID&&
  bytes.Equal(a.PublicKey,b.PublicKey)&&a.AuthorityEpoch==b.AuthorityEpoch
}
func sameAnchor(a,b fsahead.Anchor) bool {
 return sameIdentity(a,b)&&a.Sequence==b.Sequence&&a.HeadSHA256==b.HeadSHA256
}
func wire(a fsahead.Anchor) fsaremote.AnchorWire {
 return fsaremote.AnchorWire{ArchiveID:a.ArchiveID,KeyID:a.KeyID,PublicKeyHex:hex.EncodeToString(a.PublicKey),
  AuthorityEpoch:a.AuthorityEpoch,Sequence:a.Sequence,HeadSHA256:a.HeadSHA256}
}
func parse(w fsaremote.AnchorWire,identity fsahead.Anchor)(fsahead.Anchor,bool) {
 key,err:=hex.DecodeString(w.PublicKeyHex)
 if err!=nil||len(key)!=ed25519.PublicKeySize||!hex64(w.ArchiveID)||!validID(w.KeyID)||
  !hex64(w.HeadSHA256)||w.AuthorityEpoch==0||w.Sequence>researchlog.MaxEntries||
  (w.Sequence==0&&w.HeadSHA256!=researchlog.Genesis)||
  (w.Sequence>0&&w.HeadSHA256==researchlog.Genesis){return fsahead.Anchor{},false}
 a:=fsahead.Anchor{ArchiveID:w.ArchiveID,KeyID:w.KeyID,PublicKey:ed25519.PublicKey(key),
  AuthorityEpoch:w.AuthorityEpoch,Sequence:w.Sequence,HeadSHA256:w.HeadSHA256}
 return a,sameIdentity(a,identity)
}
func authenticated(r *http.Request,clientPin string)bool {
 if r==nil||r.TLS==nil||r.TLS.Version<tls.VersionTLS13||
  len(r.TLS.VerifiedChains)==0||len(r.TLS.PeerCertificates)==0{return false}
 sum:=sha256.Sum256(r.TLS.PeerCertificates[0].RawSubjectPublicKeyInfo)
 return hex.EncodeToString(sum[:])==clientPin
}
func noBody(r *http.Request)bool{return r.Body==nil||r.Body==http.NoBody}
func archiveQuery(r *http.Request,archiveID string)bool {
 q,err:=url.ParseQuery(r.URL.RawQuery)
 if err!=nil||len(q)!=1||len(q["archive_id"])!=1{return false}
 return q.Get("archive_id")==archiveID
}
func respond(w http.ResponseWriter,v any){
 b,err:=json.Marshal(v)
 if err!=nil{http.Error(w,"unavailable",http.StatusServiceUnavailable);return}
 w.Header().Set("Content-Type","application/json")
 w.Header().Set("Cache-Control","no-store")
 w.Header().Set("X-Content-Type-Options","nosniff")
 w.WriteHeader(http.StatusOK)
 _,_=w.Write(append(b,'\n'))
}
func decodeCAS(r *http.Request)(casEnvelope,bool){
 var out casEnvelope
 if r.Header.Get("Content-Type")!="application/json"||r.Body==nil||r.ContentLength>fsaremote.MaxResponseBytes{
  return out,false
 }
 d:=json.NewDecoder(io.LimitReader(r.Body,fsaremote.MaxResponseBytes+1));d.DisallowUnknownFields()
 if d.Decode(&out)!=nil{return out,false}
 var trailing any
 if d.Decode(&trailing)!=io.EOF{return out,false}
 return out,out.Schema==fsaremote.WireSchema
}
func binding(ctx context.Context,admission Admission,id,hash string)bool {
 ok,err:=admission.VerifyPhysicalBinding(ctx,id,hash)
 return err==nil&&ok&&ctx.Err()==nil
}
func NewAuthorityHandler(c AuthorityConfig)(http.Handler,error){
 if c.Backend==nil||c.Admission==nil||!genesisValid(c.Genesis)||
  !hex64(c.BindingSHA256)||!hex64(c.ClientSPKISHA256){
  return nil,errors.New("FORGE_FSA_SERVICE_AUTHORITY_NOT_INDEPENDENTLY_CONFIGURED")
 }
 return http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){
  if !authenticated(r,c.ClientSPKISHA256){http.Error(w,"forbidden",http.StatusForbidden);return}
  w.Header().Set("Cache-Control","no-store")
  if r.URL.Path=="/v1/fsa/anchor"&&r.Method==http.MethodGet&&r.URL.RawQuery==""&&noBody(r){
   if !binding(r.Context(),c.Admission,c.Genesis.ArchiveID,c.BindingSHA256){
    http.Error(w,"unavailable",http.StatusServiceUnavailable);return
   }
   a,err:=c.Backend.ReadAnchor(r.Context())
   if err!=nil||!sameIdentity(a,c.Genesis)||!hex64(a.HeadSHA256){
    http.Error(w,"unavailable",http.StatusServiceUnavailable);return
   }
   respond(w,anchorEnvelope{fsaremote.WireSchema,wire(a)});return
  }
  if r.URL.Path=="/v1/fsa/binding"&&r.Method==http.MethodGet&&noBody(r)&&archiveQuery(r,c.Genesis.ArchiveID){
   if !binding(r.Context(),c.Admission,c.Genesis.ArchiveID,c.BindingSHA256){
    http.Error(w,"unavailable",http.StatusServiceUnavailable);return
   }
   respond(w,bindingEnvelope{fsaremote.WireSchema,c.Genesis.ArchiveID,c.BindingSHA256,true});return
  }
  if r.URL.Path=="/v1/fsa/cas"&&r.Method==http.MethodPost&&r.URL.RawQuery==""{
   req,ok:=decodeCAS(r)
   if !ok{http.Error(w,"bad request",http.StatusBadRequest);return}
   prev,pok:=parse(req.Previous,c.Genesis)
   next,nok:=parse(req.Next,c.Genesis)
   if !pok||!nok||next.Sequence<=prev.Sequence||next.HeadSHA256==prev.HeadSHA256{
    http.Error(w,"bad request",http.StatusBadRequest);return
   }
   if !binding(r.Context(),c.Admission,c.Genesis.ArchiveID,c.BindingSHA256){
    http.Error(w,"unavailable",http.StatusServiceUnavailable);return
   }
   verified,err:=c.Admission.VerifySignedTransition(r.Context(),prev,next)
   if err!=nil||!verified||r.Context().Err()!=nil{
    http.Error(w,"unavailable",http.StatusServiceUnavailable);return
   }
   committed,err:=c.Backend.CompareAndSwap(r.Context(),prev,next)
   if err!=nil{ // May have committed: never retry or manufacture a success.
    http.Error(w,"indeterminate",http.StatusServiceUnavailable);return
   }
   if !committed{http.Error(w,"conflict",http.StatusConflict);return}
   respond(w,casResult{fsaremote.WireSchema,true});return
  }
  http.Error(w,"not found",http.StatusNotFound)
 }),nil
}
func NewWitnessHandler(c WitnessConfig)(http.Handler,error){
 if c.Reader==nil||!hex64(c.ClientSPKISHA256)||
  !hex64(c.Pin.ArchiveID)||!hex64(c.Pin.BindingSHA256)||
  !validID(c.Pin.KeyID)||c.Pin.AuthorityEpoch==0||c.Pin.MinimumRevision==0||
  len(c.Pin.PublicKey)!=ed25519.PublicKeySize||
  len(c.Pin.WitnessPublicKey)!=ed25519.PublicKeySize||
  bytes.Equal(c.Pin.PublicKey,c.Pin.WitnessPublicKey){
  return nil,errors.New("FORGE_FSA_SERVICE_WITNESS_NOT_INDEPENDENTLY_CONFIGURED")
 }
 return http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){
  if !authenticated(r,c.ClientSPKISHA256){http.Error(w,"forbidden",http.StatusForbidden);return}
  if r.URL.Path!="/v1/fsa/highwater"||r.Method!=http.MethodGet||
   !noBody(r)||!archiveQuery(r,c.Pin.ArchiveID){
   http.Error(w,"not found",http.StatusNotFound);return
  }
  statement,err:=c.Reader.ReadHighWater(r.Context(),c.Pin.ArchiveID)
  if err!=nil||r.Context().Err()!=nil{
   http.Error(w,"unavailable",http.StatusServiceUnavailable);return
  }
  h:=statement.Head
  a:=fsahead.Anchor{ArchiveID:h.ArchiveID,KeyID:h.KeyID,
   PublicKey:c.Pin.PublicKey,AuthorityEpoch:h.AuthorityEpoch,
   Sequence:h.Sequence,HeadSHA256:h.HeadSHA256}
  if fsaremote.VerifyWitness(c.Pin,statement,a)!=nil{
   http.Error(w,"unavailable",http.StatusServiceUnavailable);return
  }
  respond(w,witnessEnvelope{fsaremote.WireSchema,statement})
 }),nil
}
