// Package classification verifies externally signed classification attestations.
// It cannot create reviewer authority or grant scientific execution rights.
package classification
import("crypto/ed25519";"crypto/sha256";"encoding/hex";"encoding/json";"errors")
const Schema="forge.science.independent-classification.v1"
const domain="FORGE-INDEPENDENT-CLASSIFICATION-V1\n"
var ErrBlocked=errors.New("FORGE_CLASSIFICATION_NOT_AUTHENTICATED")
type Statement struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 ExperimentID string `json:"experiment_id"`
 FrozenSHA256 string `json:"frozen_sha256"`
 OriginalEvidenceSHA256 string `json:"original_evidence_sha256"`
 Outcome string `json:"outcome"`
 ReviewerID string `json:"reviewer_id"`
}
type Attestation struct{Statement Statement `json:"statement"`; SignatureHex string `json:"signature_hex"`}
type Expected struct{
 Lane,ExperimentID,FrozenSHA256,OriginalEvidenceSHA256,ReviewerID string
 TrustedKey ed25519.PublicKey
}
func hex64(s string)bool{if len(s)!=64{return false};for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}};return true}
func Verify(a Attestation,e Expected)(string,error){
 s:=a.Statement
 if len(e.TrustedKey)!=ed25519.PublicKeySize||s.Schema!=Schema||
 (s.Lane!="Wingless"&&s.Lane!="Yggdrasil")||s.Lane!=e.Lane||
 s.ExperimentID==""||s.ExperimentID!=e.ExperimentID||
 s.FrozenSHA256!=e.FrozenSHA256||!hex64(s.FrozenSHA256)||
 s.OriginalEvidenceSHA256!=e.OriginalEvidenceSHA256||!hex64(s.OriginalEvidenceSHA256)||
 s.ReviewerID==""||s.ReviewerID!=e.ReviewerID||
 (s.Outcome!="POSITIVE"&&s.Outcome!="NEGATIVE"&&s.Outcome!="INCONCLUSIVE"&&s.Outcome!="INVALID"){return "",ErrBlocked}
 body,err:=json.Marshal(s);if err!=nil{return "",ErrBlocked}
 sig,err:=hex.DecodeString(a.SignatureHex)
 if err!=nil||len(sig)!=ed25519.SignatureSize||!ed25519.Verify(e.TrustedKey,append([]byte(domain),body...),sig){return "",ErrBlocked}
 hash:=sha256.Sum256(append([]byte(domain),body...))
 return hex.EncodeToString(hash[:]),nil
}
