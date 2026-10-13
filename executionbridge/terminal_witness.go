package executionbridge

import (
 "context"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "github.com/spoonman136668-ai/forge/workerreconcile"
)
// SignedTerminal binds an independently signed classification and source
// snapshot to the exact terminal worker evidence hash.
type SignedTerminal struct {
 Evidence TerminalEvidence `json:"evidence"`
 WorkerEvidenceSHA256 string `json:"worker_evidence_sha256"`
 OwnerEpoch uint64 `json:"owner_epoch"`
 SignatureHex string `json:"signature_hex"`
}
type AttestedTerminalWitness struct{PublicKey ed25519.PublicKey; Expected workerreconcile.Expected; Signed SignedTerminal}
func(w AttestedTerminalWitness)VerifyTerminal(_ context.Context,e TerminalEvidence)(bool,error){
 s:=w.Signed
 if len(w.PublicKey)!=ed25519.PublicKeySize||s.Evidence!=e||
  s.OwnerEpoch!=w.Expected.OwnerEpoch||s.OwnerEpoch==0||
  s.WorkerEvidenceSHA256!=e.EvidenceSHA256||!validDigest(s.WorkerEvidenceSHA256)||
  e.Lane!=w.Expected.Lane||e.OriginalRunID!=w.Expected.OriginalRunID||
  !e.IndependentlyAuthenticated{return false,ErrBlocked}
 raw,err:=json.Marshal(struct{
  Evidence TerminalEvidence `json:"evidence"`
  WorkerEvidenceSHA256 string `json:"worker_evidence_sha256"`
  OwnerEpoch uint64 `json:"owner_epoch"`
 }{s.Evidence,s.WorkerEvidenceSHA256,s.OwnerEpoch})
 if err!=nil{return false,ErrBlocked}
 sig,err:=hex.DecodeString(s.SignatureHex)
 if err!=nil||len(sig)!=ed25519.SignatureSize||
  !ed25519.Verify(w.PublicKey,append([]byte("FORGE-TERMINAL-SCIENCE-WITNESS-V1\n"),raw...),sig){return false,ErrBlocked}
 return true,nil
}
func TerminalWitnessFingerprint(s SignedTerminal)(string,error){
 b,err:=json.Marshal(s);if err!=nil{return "",err}
 h:=sha256.Sum256(append([]byte("FORGE-TERMINAL-WITNESS-FINGERPRINT-V1\n"),b...))
 return hex.EncodeToString(h[:]),nil
}
