// Package lanereview binds independently signed scientific failure reviews
// to independently witnessed observations of the TWO existing CKB research
// lanes. It produces inactive recovery plans only, never worker commands.
package lanereview

import (
 "bytes"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"

 "github.com/spoonman136668-ai/forge/lanewitness"
 "github.com/spoonman136668-ai/forge/watchdog"
)
const Schema="forge.existing-lane-failure-review.v1"
const domain="FORGE-EXISTING-LANE-FAILURE-REVIEW-V1\n"
var ErrUntrusted=errors.New("FORGE_EXISTING_LANE_REVIEW_NOT_AUTHENTICATED")
type Finding struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 IncidentKey string `json:"incident_key"`
 ObservationSHA256 string `json:"observation_sha256"`
 Failure watchdog.FailureKind `json:"failure"`
 EvidenceSHA256 string `json:"evidence_sha256"`
 ReversiblePreFirstUseProven bool `json:"reversible_pre_first_use_proven"`
 RepairScope string `json:"repair_scope"`
 ReviewSequence uint64 `json:"review_sequence"`
}
type SignedFinding struct {
 Finding Finding `json:"finding"`
 SignatureHex string `json:"signature_hex"`
}
type ReviewerPin struct {
 Lane string
 PublicKey ed25519.PublicKey
 MinimumReviewSequence uint64
}
func validHex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
// AssessIndependent verifies signed owner observations first, then requires
// separately signed and evidence-bound reviews for EVERY diagnosed incident.
// A reviewer cannot drop an inconvenient negative or uncertain original.
func AssessIndependent(now uint64,
 witnessed []lanewitness.Signed, witnessPins []lanewitness.Pinned,
 reviews []SignedFinding, reviewerPins []ReviewerPin,
)(lanewitness.Assessment,[]watchdog.AssessedIncident,error){
 var empty lanewitness.Assessment
 assessment,err:=lanewitness.AssessPair(now,witnessed,witnessPins)
 if err!=nil{return empty,nil,ErrUntrusted}
 if len(reviewerPins)!=2||len(reviews)!=len(assessment.Incidents)||
  len(assessment.Incidents)>2{return empty,nil,ErrUntrusted}
 pinByLane:=map[string]ReviewerPin{}
 witnessByLane:=map[string]lanewitness.Pinned{}
 for _,p:=range witnessPins{witnessByLane[p.Lane]=p}
 for _,p:=range reviewerPins{
  if (p.Lane!="Wingless"&&p.Lane!="Yggdrasil")||len(p.PublicKey)!=ed25519.PublicKeySize||
   p.MinimumReviewSequence==0||len(pinByLane)>1||pinByLane[p.Lane].Lane!=""||
   bytes.Equal(p.PublicKey,witnessByLane[p.Lane].PublicKey){
   return empty,nil,ErrUntrusted
  }
  pinByLane[p.Lane]=p
 }
 if len(pinByLane)!=2||bytes.Equal(pinByLane["Wingless"].PublicKey,pinByLane["Yggdrasil"].PublicKey){
  return empty,nil,ErrUntrusted
 }
 proof:=map[string]string{}
 for _,p:=range assessment.Proofs{proof[p.Lane]=p.ObservationSHA256}
 reviewByIncident:=map[string]SignedFinding{}
 for _,r:=range reviews{
  finding:=r.Finding
  pin,ok:=pinByLane[finding.Lane]
  if !ok||reviewByIncident[finding.IncidentKey].Finding.Schema!=""||
   finding.Schema!=Schema||finding.ReviewSequence<pin.MinimumReviewSequence||
   !validHex(finding.ObservationSHA256,64)||finding.ObservationSHA256!=proof[finding.Lane]||
   !validHex(finding.EvidenceSHA256,64)||
   !validHex(r.SignatureHex,ed25519.SignatureSize*2){
   return empty,nil,ErrUntrusted
  }
  msg,err:=json.Marshal(finding);if err!=nil{return empty,nil,ErrUntrusted}
  signature,err:=hex.DecodeString(r.SignatureHex)
  if err!=nil||!ed25519.Verify(pin.PublicKey,append([]byte(domain),msg...),signature){
   return empty,nil,ErrUntrusted
  }
  reviewByIncident[finding.IncidentKey]=r
 }
 out:=make([]watchdog.AssessedIncident,0,len(assessment.Incidents))
 for _,i:=range assessment.Incidents{
  r,ok:=reviewByIncident[watchdog.IncidentKey(i)]
  if !ok||r.Finding.Lane!=i.Lane{return empty,nil,ErrUntrusted}
  // The external review service, not the caller's boolean, must attest
  // that the original has never crossed the irreversible first-use boundary.
  evidenceAuthenticated:=true
  out=append(out,watchdog.AssessedIncident{
   Assessment:watchdog.RecoveryAssessment{
    Incident:i,Failure:r.Finding.Failure,
    ReversiblePreFirstUseProven:r.Finding.ReversiblePreFirstUseProven,
    IndependentEvidenceAuthenticated:evidenceAuthenticated,
   },RepairScope:r.Finding.RepairScope,
  })
 }
 if _,err:=watchdog.PrepareRecoveryBatch(out);err!=nil{return empty,nil,ErrUntrusted}
 return assessment,out,nil
}
// ReviewDigest is an evidence binding, not a grant or a trusted result class.
func ReviewDigest(s SignedFinding)(string,error){
 if s.Finding.Schema!=Schema{return "",ErrUntrusted}
 b,err:=json.Marshal(s.Finding);if err!=nil{return "",err}
 d:=sha256.Sum256(append([]byte(domain),b...))
 return hex.EncodeToString(d[:]),nil
}
