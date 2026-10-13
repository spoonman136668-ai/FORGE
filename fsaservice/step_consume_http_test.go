package fsaservice

import (
 "bytes"
 "context"
 "crypto/ed25519"
 "encoding/json"
 "encoding/hex"
 "net/http"
 "path/filepath"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/fsaepochstore"
 "github.com/spoonman136668-ai/forge/workerfence"
)

type testOriginalCustody struct{
 allowed bool
 checks int
}
func(o *testOriginalCustody)ConfirmEligible(_ context.Context,_ workerfence.StepClaim)(bool,error){
 o.checks++
 return o.allowed,nil
}
type stepHTTPFixture struct{
 f *gateFixture
 store *fsaepochstore.Store
 custody *testOriginalCustody
 client *http.Client
 reader *http.Client
 writer *http.Client
 address string
 claim workerfence.StepClaim
 adminKey ed25519.PrivateKey
 pin fsaepochstore.Pin
}
func newStepHTTPFixture(t *testing.T)*stepHTTPFixture{
 t.Helper()
 f:=newGateFixture(t,false)
 adminPub,adminKey:=testKey(t)
 receiptPub,receiptPrivate:=testKey(t)
 stamp:=epochClock{value:1000}
 pin:=fsaepochstore.Pin{ArchiveID:f.pin.ArchiveID,
  AuthoritySequence:f.anchor.Sequence,AuthorityHeadSHA256:f.anchor.HeadSHA256,
  OwnerID:"FORGE_SYNTHETIC_OWNER_A",OwnerEpoch:f.anchor.AuthorityEpoch,
  TransferPublicKey:adminPub,StepReceiptPublicKey:receiptPub}
 store,err:=fsaepochstore.Provision(filepath.Join(t.TempDir(),fsaepochstore.FolderName),
  pin,stamp,epochSigner{key:receiptPrivate})
 if err!=nil{t.Fatal(err)}
 workerCert,workerSPKI:=certFor(t,f.ca,f.caPrivate,true)
 checkpointCert,checkpointSPKI:=certFor(t,f.ca,f.caPrivate,true)
 serverCert,_:=certFor(t,f.ca,f.caPrivate,false)
 custody:=&testOriginalCustody{allowed:true}
 h,err:=StepConsumptionHandler(f.pin,f.readerSPKI,checkpointSPKI,workerSPKI,
  f.remote,store,custody,stamp,receiptPub)
 if err!=nil{t.Fatal(err)}
 server:=testService(t,h,serverCert,f.roots)
 claim:=workerfence.StepClaim{Schema:workerfence.StepSchema,
  ArchiveID:pin.ArchiveID,AuthoritySequence:pin.AuthoritySequence,
  AuthorityHeadSHA256:pin.AuthorityHeadSHA256,Lane:"Wingless",
  OriginalID:"original_http_w",IntentSHA256:strings.Repeat("b",64),
  OwnerID:pin.OwnerID,OwnerEpoch:pin.OwnerEpoch,WorkerID:"FORGE_WORKER_HTTP",
  WorkerBinarySHA256:strings.Repeat("c",64),LeaseSequence:1,
  ExpiresAtUnix:2000,StepSHA256:strings.Repeat("d",64)}
 return &stepHTTPFixture{f:f,store:store,custody:custody,
  client:testSignedWriterClient(t,f,workerCert),
  reader:testSignedWriterClient(t,f,f.readerCert),
  writer:testSignedWriterClient(t,f,checkpointCert),
  address:server.URL,claim:claim,adminKey:adminKey,pin:pin}
}
func requestStep(t *testing.T,c *http.Client,base string,claim workerfence.StepClaim)(int,[]byte){
 t.Helper()
 body,err:=json.Marshal(stepRequest{Schema:StepRequestSchema,Claim:claim})
 if err!=nil{t.Fatal(err)}
 return rawStepRequest(t,c,base,body)
}
func rawStepRequest(t *testing.T,c *http.Client,base string,body []byte)(int,[]byte){
 t.Helper()
 req,err:=http.NewRequest(http.MethodPost,base+"/v1/fsa/consume-step",bytes.NewReader(body))
 if err!=nil{t.Fatal(err)}
 req.Header.Set("Content-Type","application/json")
 reply,err:=c.Do(req)
 if err!=nil{t.Fatal(err)}
 defer reply.Body.Close()
 var payload bytes.Buffer
 if _,err:=payload.ReadFrom(reply.Body);err!=nil{t.Fatal(err)}
 return reply.StatusCode,payload.Bytes()
}
func TestStepEndpointEnforcesSeparateWorkerCertificateAndSignedConsumption(t *testing.T){
 x:=newStepHTTPFixture(t)
 if code,_:=requestStep(t,x.reader,x.address,x.claim);code!=http.StatusUnauthorized{
  t.Fatalf("reader performed step mutation: %d",code)
 }
 if code,_:=requestStep(t,x.writer,x.address,x.claim);code!=http.StatusUnauthorized{
  t.Fatalf("checkpoint writer performed step mutation: %d",code)
 }
 if n,err:=x.store.Read(context.Background());err!=nil||n.Ordinal!=0{t.Fatal(n,err)}
 status,body:=requestStep(t,x.client,x.address,x.claim)
 if status!=http.StatusOK{t.Fatalf("signed consumption denied %d %s",status,body)}
 var reply struct{
  Schema string `json:"schema"`
  Receipt workerfence.SignedStepReceipt `json:"receipt"`
  ExecutionAuthorized bool `json:"execution_authorized"`
 }
 if err:=json.Unmarshal(body,&reply);err!=nil||reply.Schema!=StepRequestSchema||
  reply.ExecutionAuthorized||
  !workerfence.VerifyStepReceipt(reply.Receipt,x.claim,x.pin.StepReceiptPublicKey){
  t.Fatal("step response lacked signed negative-only custody",string(body),err)
 }
 if x.custody.checks!=2{t.Fatal("independent original gate did not recheck")}
 if code,_:=requestStep(t,x.client,x.address,x.claim);code!=http.StatusConflict{
  t.Fatal("duplicate worker step accepted",code)
 }
 if state,err:=x.store.Read(context.Background());err!=nil||state.Ordinal!=1{
  t.Fatal("duplicate changed owner ledger",state,err)
 }
}
func TestStepEndpointDeniedMissingOriginalCustodyAndNoncanonicalRequests(t *testing.T){
 x:=newStepHTTPFixture(t)
 x.custody.allowed=false
 if code,_:=requestStep(t,x.client,x.address,x.claim);code!=http.StatusServiceUnavailable{
  t.Fatal("unverified original first-use admitted",code)
 }
 x.custody.allowed=true
 body,_:=json.Marshal(stepRequest{Schema:StepRequestSchema,Claim:x.claim})
 dup:=[]byte(strings.Replace(string(body),`"schema":`,`"schema":"untrusted","schema":`,1))
 if code,_:=rawStepRequest(t,x.client,x.address,dup);code!=http.StatusBadRequest{
  t.Fatal("duplicate JSON keys admitted",code)
 }
 forged:=x.claim;forged.AuthorityHeadSHA256=strings.Repeat("f",64)
 if code,_:=requestStep(t,x.client,x.address,forged);code==http.StatusOK{
  t.Fatal("unwitnessed archive head admitted")
 }
 forged=x.claim;forged.ExpiresAtUnix=999
 if code,_:=requestStep(t,x.client,x.address,forged);code==http.StatusOK{
  t.Fatal("expired step admitted")
 }
 if state,err:=x.store.Read(context.Background());err!=nil||state.Ordinal!=0{
  t.Fatal("invalid requests mutated durable step ledger",state,err)
 }
}
func TestStepEndpointRevocationCannotBypassIndependentRemoteEpoch(t *testing.T){
 x:=newStepHTTPFixture(t)
 tfer:=fsaepochstore.SignedTransfer{Schema:fsaepochstore.TransferSchema,
  ArchiveID:x.pin.ArchiveID,FromOwnerID:x.pin.OwnerID,FromEpoch:x.pin.OwnerEpoch,
  ToOwnerID:"FORGE_SYNTHETIC_OWNER_B",ToEpoch:x.pin.OwnerEpoch+1,
  NonceSHA256:strings.Repeat("e",64)}
 unsigned,err:=json.Marshal(tfer);if err!=nil{t.Fatal(err)}
 tfer.SignatureHex=fmtSign(t,x.adminKey,append([]byte(fsaepochstore.TransferDomain),unsigned...))
 if err:=x.store.TransferOwner(context.Background(),tfer);err!=nil{t.Fatal(err)}
 if code,_:=requestStep(t,x.client,x.address,x.claim);code==http.StatusOK{
  t.Fatal("revoked owner admitted through service")
 }
 shifted:=x.claim
 shifted.OwnerID="FORGE_SYNTHETIC_OWNER_B"
 shifted.OwnerEpoch++
 if code,_:=requestStep(t,x.client,x.address,shifted);code==http.StatusOK{
  t.Fatal("new owner bypassed independent signed remote epoch")
 }
 if state,err:=x.store.Read(context.Background());err!=nil||state.Ordinal!=1||
  state.OwnerID!=tfer.ToOwnerID{t.Fatal(state,err)}
}
func fmtSign(t *testing.T,key ed25519.PrivateKey,data []byte)string{
 t.Helper()
 return hex.EncodeToString(ed25519.Sign(key,data))
}
