package optimizerbridge

// AuditedSelection is a read-only, independent cross-check of existing logged
// randomization claims. A signature and matching hashes never alone establish
// genuine random assignment, unbiased propensities, or causal improvement.
import (
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "errors"

 "github.com/spoonman136668-ai/forge/dreamrsi"
)

const SelectionAuditSchema="forge.optimizer.selection-audit.v1"
const SelectionAuditDomain="FORGE-OPTIMIZER-SELECTION-AUDIT-V1\x00"
var ErrSelectionAudit=errors.New("FORGE_OPTIMIZER_INDEPENDENT_SELECTION_AUDIT_REQUIRED")

type SelectionAuditEntry struct {
 Tick uint64 `json:"tick"`
 ReceiptSHA256 string `json:"receipt_sha256"`
 ChosenID string `json:"chosen_id"`
 CohortSHA256 string `json:"cohort_sha256"`
 ProbabilityBP int `json:"probability_bp"`
 RandomizationProofSHA256 string `json:"randomization_proof_sha256"`
 AssignmentEventSHA256 string `json:"assignment_event_sha256"`
}
type SelectionAudit struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 TrainHistorySHA256 string `json:"train_history_sha256"`
 ValidationHistorySHA256 string `json:"validation_history_sha256"`
 Entries []SelectionAuditEntry `json:"entries"`
}
type SignedSelectionAudit struct {
 Audit SelectionAudit `json:"audit"`
 SignatureHex string `json:"signature_hex"`
}
type SelectionAuditPin struct {
 AuditSHA256 string `json:"audit_sha256"`
 IndependentAuditorPublicKeyHex string `json:"independent_auditor_public_key_hex"`
}
// SelectionAuditReview is *not* certification of operational independence,
// randomization, or policy improvement. An actual independent reviewer must
// verify each source assignment event and logging design separately.
type SelectionAuditReview struct {
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 Lane string `json:"lane"`
 EntriesCrossChecked int `json:"entries_cross_checked"`
 SignedClaimsConsistent bool `json:"signed_claims_consistent"`
 ActualRandomizationIndependentlyDemonstrated bool `json:"actual_randomization_independently_demonstrated"`
 ProspectiveScienceAuthorized bool `json:"prospective_science_authorized"`
 ScientificImprovementEstablished bool `json:"scientific_improvement_established"`
}
func VerifySelectionAudit(e LaneEvidence,p LanePins,a SignedSelectionAudit,ap SelectionAuditPin,custodianKey string)(SelectionAuditReview,error){
 var zero SelectionAuditReview
 if !checkLane(e.Lane)||p.Lane!=e.Lane||a.Audit.Schema!=SelectionAuditSchema||
  a.Audit.Lane!=e.Lane||a.Audit.TrainHistorySHA256!=p.DreamTrainSHA256||
  a.Audit.ValidationHistorySHA256!=p.DreamValidationSHA256||
  !digestOK(ap.AuditSHA256,64)||!digestOK(ap.IndependentAuditorPublicKeyHex,64)||
  !digestOK(a.SignatureHex,128)||
  ap.IndependentAuditorPublicKeyHex==p.IndependentEd25519PublicKeyHex||
  ap.IndependentAuditorPublicKeyHex==custodianKey||
  custodianKey==""{
  return zero,ErrSelectionAudit
 }
 payload,err:=json.Marshal(a.Audit)
 if err!=nil||shaHex(payload)!=ap.AuditSHA256{return zero,ErrSelectionAudit}
 pub,_:=hex.DecodeString(ap.IndependentAuditorPublicKeyHex)
 sig,_:=hex.DecodeString(a.SignatureHex)
 if !ed25519.Verify(ed25519.PublicKey(pub),append([]byte(SelectionAuditDomain),payload...),sig){
  return zero,ErrSelectionAudit
 }
 // Independently reauthenticate the frozen training/validation histories;
 // audit records must correspond *exactly* to those signed source histories.
 train,err:=dreamrsi.VerifyEnvelope(e.DreamTrain,dreamrsi.TrustPin{
  ExpectedHistorySHA256:p.DreamTrainSHA256,
  IndependentEd25519PublicKeyHex:p.IndependentEd25519PublicKeyHex})
 if err!=nil{return zero,ErrSelectionAudit}
 validation,err:=dreamrsi.VerifyEnvelope(e.DreamValidation,dreamrsi.TrustPin{
  ExpectedHistorySHA256:p.DreamValidationSHA256,
  IndependentEd25519PublicKeyHex:p.IndependentEd25519PublicKeyHex})
 if err!=nil||train.Epoch!=validation.Epoch||train.Lane!=validation.Lane{return zero,ErrSelectionAudit}
 histories:=[]dreamrsi.Verified{train,validation}
 count:=len(train.Decisions)+len(validation.Decisions)
 if len(a.Audit.Entries)!=count||count==0{return zero,ErrSelectionAudit}
 usedEvents:=map[string]bool{}
 index:=0
 for _,h:=range histories{
  for _,d:=range h.Decisions{
   record:=a.Audit.Entries[index]
   if d.LoggingMode!=dreamrsi.Randomized||
    record.Tick!=d.Tick||record.ReceiptSHA256!=d.ReceiptSHA256||
    record.ChosenID!=d.ChosenID||record.CohortSHA256!=d.ChosenCohortSHA256||
    record.ProbabilityBP!=d.LoggedActionProbabilityBP||
    record.RandomizationProofSHA256!=d.RandomizationProofSHA256||
    !digestOK(record.AssignmentEventSHA256,64)||
    usedEvents[record.AssignmentEventSHA256] {
    return zero,ErrSelectionAudit
   }
   usedEvents[record.AssignmentEventSHA256]=true
   index++
  }
 }
 return SelectionAuditReview{
  Schema:"forge.optimizer.signed-selection-audit-review.v1",
  Mode:"SIGNED_ASSIGNMENT_CLAIMS_MATCH_NOT_INDEPENDENT_RANDOMIZATION_PROOF",
  Lane:e.Lane,EntriesCrossChecked:count,SignedClaimsConsistent:true,
 },nil
}
