package fsaremote

import (
 "context"
 "crypto/rand"
 "crypto/sha256"
 "crypto/tls"
 "crypto/x509"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "math/big"
 "net/http"
 "strings"
 "testing"
 "time"
)

func testWriter(t *testing.T)(*SignedCheckpointWriter,*Client){
 t.Helper()
 observer,_,_:=fixture(t)
 pub,key:=kpair("signed-checkpoint-writer-fixture")
 certTemplate:=&x509.Certificate{
  SerialNumber:big.NewInt(17),
  NotBefore:time.Now().Add(-time.Hour),
  NotAfter:time.Now().Add(time.Hour),
  KeyUsage:x509.KeyUsageDigitalSignature,
  ExtKeyUsage:[]x509.ExtKeyUsage{x509.ExtKeyUsageClientAuth},
  BasicConstraintsValid:true,
 }
 der,err:=x509.CreateCertificate(rand.Reader,certTemplate,certTemplate,pub,key)
 if err!=nil{t.Fatal(err)}
 leaf,err:=x509.ParseCertificate(der)
 if err!=nil{t.Fatal(err)}
 sum:=sha256.Sum256(leaf.RawSubjectPublicKeyInfo)
 writerID:=hex.EncodeToString(sum[:])
 server:=Peer{
  BaseURL:"https://authority.forge.test",
  Roots:x509.NewCertPool(),
  Certificate:tls.Certificate{Certificate:[][]byte{der},PrivateKey:key},
  ServerSPKISHA256:hx("f",64),
 }
 if _,err:=NewSignedCheckpointWriter(server,observer.pin,writerID,writerID);err==nil{
  t.Fatal("reader identity reused for writer")
 }
 if _,err:=NewSignedCheckpointWriter(server,observer.pin,hx("e",64),hx("1",64));err==nil{
  t.Fatal("unmatched writer certificate SPKI accepted")
 }
 unsafe:=server;unsafe.BaseURL="http://authority.forge.test"
 if _,err:=NewSignedCheckpointWriter(unsafe,observer.pin,hx("e",64),writerID);err==nil{
  t.Fatal("plaintext FSA checkpoint transport accepted")
 }
 unsafe=server;unsafe.Roots=nil
 if _,err:=NewSignedCheckpointWriter(unsafe,observer.pin,hx("e",64),writerID);err==nil{
  t.Fatal("missing authority TLS roots accepted")
 }
 w,err:=NewSignedCheckpointWriter(server,observer.pin,hx("e",64),writerID)
 if err!=nil{t.Fatal(err)}
 return w,observer
}

func testSignedWriteInput(t *testing.T,c *Client)(context.Context,func() (SignedCheckpointReceipt,error),SignedCheckpointReceipt){
 t.Helper()
 anchor,err:=c.ReadAnchor(context.Background())
 if err!=nil{t.Fatal(err)}
 _,_,private:=fixture(t)
 signed:=signHead(t,anchor,private,1,hx("d",64))
 // The private key above uses the exact deterministic test-only FSA
 // identity from fixture(); no production issuer is created.
 expected:=SignedCheckpointReceipt{Schema:SignedCheckpointRequestSchema,
  WitnessedSequence:1,WitnessedHeadSHA256:signed.Payload.HeadSHA256,
  ExecutionAuthorized:false}
 ctx:=context.Background()
 return ctx,func()(SignedCheckpointReceipt,error){
  w,_:=testWriter(t)
  return w.Submit(ctx,anchor,signed)
 },expected
}

func TestSignedCheckpointWriterUsesExactlyOneAuthenticatedSignedRequest(t *testing.T){
 w,observer:=testWriter(t)
 anchor,err:=observer.ReadAnchor(context.Background())
 if err!=nil{t.Fatal(err)}
 _,_,signer:=fixture(t)
 signed:=signHead(t,anchor,signer,1,hx("d",64))
 expected:=SignedCheckpointReceipt{Schema:SignedCheckpointRequestSchema,
  WitnessedSequence:signed.Payload.Sequence,WitnessedHeadSHA256:signed.Payload.HeadSHA256}
 n:=0
 w.client.Transport=roundTripFunc(func(req *http.Request)(*http.Response,error){
  n++
  if req.Method!=http.MethodPost||req.URL.String()!="https://authority.forge.test/v1/fsa/signed-checkpoint"||
   req.Header.Get("Content-Type")!="application/json"{
   t.Fatal("unexpected FSA writer route or content type")
  }
  data,err:=io.ReadAll(req.Body);if err!=nil{t.Fatal(err)}
  var received signedCheckpointRequest
  if err=json.Unmarshal(data,&received);err!=nil||
   received.Schema!=SignedCheckpointRequestSchema||
   received.SignedCheckpoint.SignatureHex!=signed.SignatureHex{
   t.Fatal("unsigned or modified request")
  }
  response:=jsonResponse(http.StatusOK,expected)
  response.Header.Set("Content-Type","application/json")
  return response,nil
 })
 got,err:=w.Submit(context.Background(),anchor,signed)
 if err!=nil||got!=expected||n!=1{t.Fatalf("signed checkpoint not acknowledged: %+v %v calls=%d",got,err,n)}
 if _,err:=w.Submit(context.Background(),anchor,signed);!errors.Is(err,ErrSignedWriterAlreadyAttempted)||n!=1{
  t.Fatal("signed checkpoint replay attempt")
 }
}

func TestSignedCheckpointWriterIndeterminateTransportAndReplyNeverReplay(t *testing.T){
 for _,kind:=range []string{"transport","conflict","unwitnessed","wrong_seq","wrong_head",
  "authorization_claim","wrong_schema","unknown_field","duplicate_field","redirect"}{
  t.Run(kind,func(t *testing.T){
   w,observer:=testWriter(t)
   anchor,err:=observer.ReadAnchor(context.Background());if err!=nil{t.Fatal(err)}
   _,_,signer:=fixture(t)
   signed:=signHead(t,anchor,signer,1,hx("d",64))
   calls:=0
   w.client.Transport=roundTripFunc(func(req *http.Request)(*http.Response,error){
    calls++
    if kind=="transport"{return nil,errors.New("lost response after possible CAS")}
    if kind=="conflict"{return jsonResponse(http.StatusConflict,map[string]string{"error":"conflict"}),nil}
    if kind=="unwitnessed"{return jsonResponse(http.StatusServiceUnavailable,map[string]string{"error":"witness unknown"}),nil}
    if kind=="redirect"{return jsonResponse(http.StatusTemporaryRedirect,map[string]string{"error":"redirect"}),nil}
    reply:=SignedCheckpointReceipt{Schema:SignedCheckpointRequestSchema,
     WitnessedSequence:1,WitnessedHeadSHA256:signed.Payload.HeadSHA256}
    switch kind{
    case "wrong_seq":reply.WitnessedSequence=2
    case "wrong_head":reply.WitnessedHeadSHA256=hx("a",64)
    case "authorization_claim":reply.ExecutionAuthorized=true
    case "wrong_schema":reply.Schema="forged"
    }
    response:=jsonResponse(http.StatusOK,reply)
    response.Header.Set("Content-Type","application/json")
    if kind=="unknown_field"{
     response.Body=io.NopCloser(strings.NewReader(`{"schema":"forge.fsa.signed-checkpoint-request.v1","witnessed_sequence":1,"witnessed_head_sha256":"`+
      signed.Payload.HeadSHA256+`","execution_authorized":false,"override":true}`))
    }
    if kind=="duplicate_field"{
     response.Body=io.NopCloser(strings.NewReader(`{"schema":"forge.fsa.signed-checkpoint-request.v1","schema":"forge.fsa.signed-checkpoint-request.v1","witnessed_sequence":1,"witnessed_head_sha256":"`+
      signed.Payload.HeadSHA256+`","execution_authorized":false}`))
    }
    return response,nil
   })
   if _,err:=w.Submit(context.Background(),anchor,signed);!errors.Is(err,ErrSignedWriterIndeterminate){
    t.Fatal("uncertain checkpoint accepted",kind,err)
   }
   if _,err:=w.Submit(context.Background(),anchor,signed);!errors.Is(err,ErrSignedWriterAlreadyAttempted)||calls!=1{
    t.Fatal("uncertain checkpoint retried",kind,err,calls)
   }
  })
 }
}

func TestSignedCheckpointWriterRejectsForgedPayloadWithoutRequest(t *testing.T){
 w,observer:=testWriter(t)
 anchor,err:=observer.ReadAnchor(context.Background());if err!=nil{t.Fatal(err)}
 _,_,signer:=fixture(t)
 signed:=signHead(t,anchor,signer,1,hx("d",64))
 signed.SignatureHex=hx("0",128)
 calls:=0
 w.client.Transport=roundTripFunc(func(*http.Request)(*http.Response,error){
  calls++;return nil,errors.New("should not send")
 })
 if _,err:=w.Submit(context.Background(),anchor,signed);!errors.Is(err,ErrSignedWriterBlocked)||calls!=0{
  t.Fatal("forged signed checkpoint was transmitted",err,calls)
 }
}
