package fsaremote

// This optional client submits an already-signed FORGE archive checkpoint to
// the separate, unregistered FSA signed-checkpoint writer endpoint. Neither
// construction nor acknowledgement supplies scientific execution authority.
import (
 "bytes"
 "context"
 "crypto/sha256"
 "crypto/x509"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "net/http"
 "sync"

 "github.com/spoonman136668-ai/forge/fsahead"
)

const SignedCheckpointRequestSchema = "forge.fsa.signed-checkpoint-request.v1"
const signedCheckpointMaxBytes = 4096

var (
 ErrSignedWriterBlocked = errors.New("FORGE_FSA_SIGNED_WRITER_UNPROVISIONED_OR_INVALID")
 ErrSignedWriterIndeterminate = errors.New("FORGE_FSA_SIGNED_CHECKPOINT_POSSIBLY_COMMITTED_NO_RETRY")
 ErrSignedWriterAlreadyAttempted = errors.New("FORGE_FSA_SIGNED_CHECKPOINT_ONESHOT_REUSE_DENIED")
)

type SignedCheckpointReceipt struct {
 Schema string `json:"schema"`
 WitnessedSequence uint64 `json:"witnessed_sequence"`
 WitnessedHeadSHA256 string `json:"witnessed_head_sha256"`
 ExecutionAuthorized bool `json:"execution_authorized"`
}

type signedCheckpointRequest struct {
 Schema string `json:"schema"`
 SignedCheckpoint fsahead.SignedHead `json:"signed_checkpoint"`
}

// SignedCheckpointWriter is a one-attempt authenticated transport. Its one-shot
// latch is process-local and is NOT durable first-use or archive CAS protection.
type SignedCheckpointWriter struct {
 mu sync.Mutex
 endpoint string
 client *http.Client
 pin Pin
 attempted bool
}

// NewSignedCheckpointWriter requires an externally pinned writer identity,
// distinct from the reader certificate. Its HTTPS transport pins the authority
// server public key and does not follow redirects. It creates no credentials.
func NewSignedCheckpointWriter(server Peer,pin Pin,readerSPKI,writerSPKI string)(*SignedCheckpointWriter,error){
 if !pin.valid()||!validHex(readerSPKI,64)||!validHex(writerSPKI,64)||
  readerSPKI==writerSPKI||len(server.Certificate.Certificate)==0{
  return nil,ErrSignedWriterBlocked
 }
 leaf,err:=x509.ParseCertificate(server.Certificate.Certificate[0])
 if err!=nil||leaf.IsCA{return nil,ErrSignedWriterBlocked}
 sum:=sha256.Sum256(leaf.RawSubjectPublicKeyInfo)
 if hex.EncodeToString(sum[:])!=writerSPKI{return nil,ErrSignedWriterBlocked}
 endpoint,client,err:=peerClient(server)
 if err!=nil{return nil,ErrSignedWriterBlocked}
 return &SignedCheckpointWriter{endpoint:endpoint,client:client,pin:pin},nil
}

// Submit posts one pre-signed, predecessor-bound checkpoint. A successful
// return only reports the writer's witnessed acknowledgement. It is NOT an
// original STARTED receipt, D1 reservation, worker permit, or science PASS.
//
// An independently recovered current anchor must be passed in; signature
// checking here is not a substitute for the server's full archive verification
// and separate durable monotonic CAS+witness. Any request that might reach the
// server consumes this instance forever, including transport errors, 409/503,
// malformed acknowledgements and unknown commit outcomes. Never auto-retry.
func (w *SignedCheckpointWriter)Submit(ctx context.Context,current fsahead.Anchor,
 signed fsahead.SignedHead)(SignedCheckpointReceipt,error){
 var zero SignedCheckpointReceipt
 if w==nil||ctx==nil||ctx.Err()!=nil{return zero,ErrSignedWriterBlocked}
 w.mu.Lock()
 defer w.mu.Unlock()
 if w.attempted{return zero,ErrSignedWriterAlreadyAttempted}
 if w.client==nil||w.endpoint==""||!w.pin.valid()||
  !w.pin.accepts(current){return zero,ErrSignedWriterBlocked}
 if _,err:=fsahead.VerifySignature(current,signed);err!=nil{
  return zero,ErrSignedWriterBlocked
 }
 body,err:=json.Marshal(signedCheckpointRequest{
  Schema:SignedCheckpointRequestSchema,SignedCheckpoint:signed,
 })
 if err!=nil||len(body)==0||len(body)>signedCheckpointMaxBytes{
  return zero,ErrSignedWriterBlocked
 }
 request,err:=http.NewRequestWithContext(ctx,http.MethodPost,
  w.endpoint+"/v1/fsa/signed-checkpoint",bytes.NewReader(body))
 if err!=nil||ctx.Err()!=nil{return zero,ErrSignedWriterBlocked}
 request.Header.Set("Accept","application/json")
 request.Header.Set("Content-Type","application/json")
 w.attempted=true // BEFORE network: every possible start is permanently risky.
 response,err:=w.client.Do(request)
 if err!=nil{return zero,ErrSignedWriterIndeterminate}
 defer response.Body.Close()
 if response.StatusCode!=http.StatusOK||
  response.Header.Get("Content-Type")!="application/json"{
  return zero,ErrSignedWriterIndeterminate
 }
 raw,err:=io.ReadAll(io.LimitReader(response.Body,signedCheckpointMaxBytes+1))
 if err!=nil||len(raw)==0||len(raw)>signedCheckpointMaxBytes{
  return zero,ErrSignedWriterIndeterminate
 }
 decoder:=json.NewDecoder(bytes.NewReader(raw))
 decoder.DisallowUnknownFields()
 var receipt SignedCheckpointReceipt
 if decoder.Decode(&receipt)!=nil||decoder.Decode(new(any))!=io.EOF{
  return zero,ErrSignedWriterIndeterminate
 }
 canonical,err:=json.Marshal(receipt)
 if err!=nil||( !bytes.Equal(raw,canonical)&&
  !bytes.Equal(raw,append(append([]byte{},canonical...), '\n')) )||
  receipt.Schema!=SignedCheckpointRequestSchema||
  receipt.WitnessedSequence!=signed.Payload.Sequence||
  receipt.WitnessedHeadSHA256!=signed.Payload.HeadSHA256||
  receipt.ExecutionAuthorized{
  return zero,ErrSignedWriterIndeterminate
 }
 return receipt,nil
}
