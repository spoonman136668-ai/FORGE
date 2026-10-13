package fsaservice

import (
 "bytes"
 "crypto/tls"
 "encoding/json"
 "io"
 "net/http"
 "strings"
 "testing"
)

func testSignedWriterClient(t *testing.T,f *gateFixture,cert tls.Certificate)*http.Client{
 t.Helper()
 return &http.Client{Transport:&http.Transport{TLSClientConfig:&tls.Config{
  MinVersion:tls.VersionTLS13,RootCAs:f.roots,
  Certificates:[]tls.Certificate{cert},
 }}}
}
func postSignedCheckpoint(t *testing.T,client *http.Client,url string,body []byte)(int,[]byte,error){
 t.Helper()
 request,err:=http.NewRequest(http.MethodPost,url+"/v1/fsa/signed-checkpoint",bytes.NewReader(body))
 if err!=nil{t.Fatal(err)}
 request.Header.Set("Content-Type","application/json")
 response,err:=client.Do(request)
 if err!=nil{return 0,nil,err}
 defer response.Body.Close()
 result,err:=io.ReadAll(io.LimitReader(response.Body,8192))
 return response.StatusCode,result,err
}
func signedWriterPayload(t *testing.T,f *gateFixture)[]byte{
 t.Helper()
 b,err:=json.Marshal(signedCheckpointRequest{Schema:SignedCheckpointSchema,SignedCheckpoint:f.signed})
 if err!=nil{t.Fatal(err)}
 return b
}

func TestSignedCheckpointWriteRequiresDistinctWriterMTLSAndWitness(t *testing.T){
 f:=newGateFixture(t,true)
 writerCert,writerSPKI:=certFor(t,f.ca,f.caPrivate,true)
 serverCert,_:=certFor(t,f.ca,f.caPrivate,false)
 if _,err:=SignedCheckpointHandler(f.pin,f.readerSPKI,f.readerSPKI,f.gate);err==nil{
  t.Fatal("read-only client granted writer identity")
 }
 handler,err:=SignedCheckpointHandler(f.pin,f.readerSPKI,writerSPKI,f.gate)
 if err!=nil{t.Fatal(err)}
 service:=testService(t,handler,serverCert,f.roots)
 writer:=testSignedWriterClient(t,f,writerCert)
 reader:=testSignedWriterClient(t,f,f.readerCert)
 body:=signedWriterPayload(t,f)
 status,_,err:=postSignedCheckpoint(t,reader,service.URL,body)
 if err!=nil||status!=http.StatusUnauthorized{t.Fatal("reader gained write authority",status,err)}
 if f.checkpoint.commits!=0{t.Fatal("reader mutated durable checkpoint")}
 status,data,err:=postSignedCheckpoint(t,writer,service.URL,body)
 if err!=nil||status!=http.StatusOK{t.Fatal("signed writer denied",status,string(data),err)}
 var reply struct{
  Schema string `json:"schema"`
  WitnessedSequence uint64 `json:"witnessed_sequence"`
  WitnessedHeadSHA256 string `json:"witnessed_head_sha256"`
  ExecutionAuthorized bool `json:"execution_authorized"`
 }
 if err=json.Unmarshal(data,&reply);err!=nil||reply.Schema!=SignedCheckpointSchema||
  reply.WitnessedSequence!=1||reply.WitnessedHeadSHA256!=f.signed.Payload.HeadSHA256||
  reply.ExecutionAuthorized||f.checkpoint.commits!=1{
  t.Fatal("unwitnessed or execution-authorizing acknowledgement",string(data),err)
 }
 status,_,err=postSignedCheckpoint(t,writer,service.URL,body)
 if err!=nil||status==http.StatusOK||f.checkpoint.commits!=1{
  t.Fatal("duplicate signed primary checkpoint replay",status,err)
 }
 resp,err:=writer.Get(service.URL+"/v1/fsa/signed-checkpoint")
 if err!=nil{t.Fatal(err)}
 resp.Body.Close()
 if resp.StatusCode!=http.StatusMethodNotAllowed{t.Fatal("unexpected GET writer surface")}
 status,_,err=postSignedCheckpoint(t,writer,service.URL+"/wrong-route",body)
 if err!=nil||status!=http.StatusNotFound{t.Fatal("wrong writer endpoint admitted",status,err)}
}

func TestSignedCheckpointHTTPRejectsMalformedForgedAndUnwitnessedWrites(t *testing.T){
 setup:=func(t *testing.T,ack bool)(*gateFixture,*http.Client,string){
  t.Helper()
  f:=newGateFixture(t,ack)
  writerCert,writerSPKI:=certFor(t,f.ca,f.caPrivate,true)
  serverCert,_:=certFor(t,f.ca,f.caPrivate,false)
  h,err:=SignedCheckpointHandler(f.pin,f.readerSPKI,writerSPKI,f.gate);if err!=nil{t.Fatal(err)}
  service:=testService(t,h,serverCert,f.roots)
  return f,testSignedWriterClient(t,f,writerCert),service.URL
 }
 t.Run("noncanonical duplicate fields",func(t *testing.T){
  f,writer,url:=setup(t,true)
  good:=signedWriterPayload(t,f)
  malformed:=[]byte(strings.Replace(string(good),`"schema":`,`"schema":"duplicated","schema":`,1))
  status,_,err:=postSignedCheckpoint(t,writer,url,malformed)
  if err!=nil||status!=http.StatusBadRequest||f.checkpoint.commits!=0{
   t.Fatal("duplicate JSON fields accepted",status,err)
  }
 })
 t.Run("forged signature",func(t *testing.T){
  f,writer,url:=setup(t,true)
  f.signed.SignatureHex=strings.Repeat("0",128)
  status,_,err:=postSignedCheckpoint(t,writer,url,signedWriterPayload(t,f))
  if err!=nil||status==http.StatusOK||f.checkpoint.commits!=0{
   t.Fatal("forged checkpoint committed",status,err)
  }
 })
 t.Run("missing independent witness after committed CAS",func(t *testing.T){
  f,writer,url:=setup(t,false)
  status,_,err:=postSignedCheckpoint(t,writer,url,signedWriterPayload(t,f))
  if err!=nil||status!=http.StatusServiceUnavailable||f.checkpoint.commits!=1||
   !f.gate.Indeterminate(){
   t.Fatal("unwitnessed CAS acknowledged or silently retried",status,err)
  }
  status,_,err=postSignedCheckpoint(t,writer,url,signedWriterPayload(t,f))
  if err!=nil||status!=http.StatusServiceUnavailable||f.checkpoint.commits!=1{
   t.Fatal("uncertain CAS replayed",status,err)
  }
 })
}
