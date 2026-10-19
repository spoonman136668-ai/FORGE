package infogain

// Calibration is read-only and does NOT constitute scientific acceptance.
// It measures forecast quality and full resource deltas when the caller
// supplies a separately signed prospective cohort. Signatures establish
// integrity relative to a key, not independent first-use or scientific merit.
import (
    "crypto/ed25519"
    "crypto/sha256"
    "encoding/hex"
    "encoding/json"
    "math"
    "sort"
)

const CalibrationSchema = "forge.infogain.signed-prospective-calibration.v1"
const CalibrationReportSchema = "forge.infogain.calibration-advisory.v1"
const CalibrationDomain = "FORGE-INFOGAIN-PROSPECTIVE-CALIBRATION-V1\n"

type ProspectiveRecord struct {
    CandidateID string `json:"candidate_id"`
    SourceSHA string `json:"source_sha"`
    MechanismSHA256 string `json:"mechanism_sha256"`
    Observation string `json:"observation"`
    PreregistrationSHA256 string `json:"preregistration_sha256"`
    FirstUseWitnessSHA256 string `json:"first_use_witness_sha256"`
    OriginalEvidenceSHA256 string `json:"original_evidence_sha256"`
    CPUTimeMillis int64 `json:"cpu_time_millis"`
    PeakMemoryBytes int64 `json:"peak_memory_bytes"`
    MemoryByteMillis int64 `json:"memory_byte_millis"`
    ActualComputeUnits int64 `json:"actual_compute_units"`
    TransferClassification string `json:"transfer_classification"`
}

type ProspectiveCohort struct {
    Schema string `json:"schema"`
    Lane string `json:"lane"`
    FrozenSHA256 string `json:"frozen_sha256"`
    SourceSHA string `json:"source_sha"`
    Records []ProspectiveRecord `json:"records"`
}
type SignedProspective struct {
    Cohort ProspectiveCohort `json:"cohort"`
    IndependentSignerPublicKeyHex string `json:"independent_signer_public_key_hex"`
    SignatureHex string `json:"signature_hex"`
}
type ExternalCalibrationPin struct {
    FrozenSHA256 string `json:"frozen_sha256"`
    ExpectedCohortSHA256 string `json:"expected_cohort_sha256"`
    QualifiedSignerPublicKeyHex string `json:"qualified_signer_public_key_hex"`
}
type CalibrationItem struct {
    CandidateID string `json:"candidate_id"`
    Observation string `json:"observation"`
    PredictedProbabilityBP int64 `json:"predicted_probability_bp"`
    BrierScoreMicro int64 `json:"brier_score_micro"`
    LogLossMicrobits int64 `json:"log_loss_microbits"`
    EstimatedComputeUnits int64 `json:"estimated_compute_units"`
    ActualComputeUnits int64 `json:"actual_compute_units"`
    CostOverrunBP int64 `json:"cost_overrun_bp"`
    CPUTimeMillis int64 `json:"cpu_time_millis"`
    PeakMemoryBytes int64 `json:"peak_memory_bytes"`
    MemoryByteMillis int64 `json:"memory_byte_millis"`
    TransferClassification string `json:"transfer_classification"`
    OriginalEvidenceSHA256 string `json:"original_evidence_sha256"`
}
type CalibrationReport struct {
    Schema string `json:"schema"`
    Lane string `json:"lane"`
    FrozenSHA256 string `json:"frozen_sha256"`
    CohortSHA256 string `json:"cohort_sha256"`
    SignatureVerified bool `json:"signature_verified"`
    Observations int `json:"observations"`
    NegativeCount int `json:"negative_count"`
    LimitationCount int `json:"limitation_count"`
    TransferClaimCount int `json:"transfer_claim_count"`
    MeanBrierMicro int64 `json:"mean_brier_micro"`
    MeanLogLossMicrobits int64 `json:"mean_log_loss_microbits"`
    TotalActualComputeUnits int64 `json:"total_actual_compute_units"`
    TotalCPUTimeMillis int64 `json:"total_cpu_time_millis"`
    MaxPeakMemoryBytes int64 `json:"max_peak_memory_bytes"`
    Items []CalibrationItem `json:"items"`
    ScientificAccepted bool `json:"scientific_accepted"`
    GenuineTransferEstablished bool `json:"genuine_transfer_established"`
    IndependentlyWitnessedFirstUse bool `json:"independently_witnessed_first_use"`
    OptimizerPromotionAuthorized bool `json:"optimizer_promotion_authorized"`
    ExecutionAuthorized bool `json:"execution_authorized"`
    Status string `json:"status"`
}
func CohortDigest(c ProspectiveCohort)string{
    data,_:=json.Marshal(c)
    h:=sha256.Sum256(append([]byte(CalibrationDomain),data...))
    return hex.EncodeToString(h[:])
}
func calibrationOutcomeIndex(s string)int{
    switch s {
    case "SUPPORTED":return 0
    case "NEGATIVE":return 1
    case "LIMITATION":return 2
    case "INDETERMINATE":return 3
    }
    return -1
}

// Calibrate has NO signing keys and NO external fetch capability. A pin MUST
// originate from an external trust boundary. A valid signature alone is
// insufficient for accepting original scientific evidence or transferable
// cognition. Forecasts and source identities remain frozen.
func Calibrate(f Frozen, frozenPin string, signed SignedProspective, pin ExternalCalibrationPin)(CalibrationReport,error){
    var zero CalibrationReport
    if err:=validate(f,frozenPin);err!=nil{return zero,ErrFrozen}
    if pin.FrozenSHA256!=frozenPin||signed.Cohort.FrozenSHA256!=frozenPin||
       signed.Cohort.Schema!=CalibrationSchema||signed.Cohort.Lane!=f.Lane||
       signed.Cohort.SourceSHA!=f.SourceSHA||
       !validHex(pin.ExpectedCohortSHA256,64)||
       CohortDigest(signed.Cohort)!=pin.ExpectedCohortSHA256||
       pin.QualifiedSignerPublicKeyHex!=signed.IndependentSignerPublicKeyHex||
       !validHex(pin.QualifiedSignerPublicKeyHex,64)||
       !validHex(signed.SignatureHex,128) {
        return zero,ErrFrozen
    }
    key,err:=hex.DecodeString(pin.QualifiedSignerPublicKeyHex)
    if err!=nil||len(key)!=ed25519.PublicKeySize{return zero,ErrFrozen}
    sig,err:=hex.DecodeString(signed.SignatureHex)
    if err!=nil||!ed25519.Verify(ed25519.PublicKey(key),
         []byte(CalibrationDomain+pin.ExpectedCohortSHA256+"
"),sig){
         return zero,ErrFrozen
    }
    records:=signed.Cohort.Records
    if len(records)<1||len(records)>40{return zero,ErrFrozen}
    advisory,err:=Recommend(f,frozenPin)
    if err!=nil{return zero,ErrFrozen}
    selected:=make(map[string]Candidate,len(advisory.Selected))
    for _,r:=range advisory.Selected{
        for _,candidate:=range f.Candidates{
            if r.ID==candidate.ID{selected[r.ID]=candidate;break}
        }
    }
    seenCandidates:=map[string]bool{}
    seenEvidence:=map[string]bool{}
    seenWitness:=map[string]bool{}
    out:=CalibrationReport{
       Schema:CalibrationReportSchema,Lane:f.Lane,
       FrozenSHA256:frozenPin,CohortSHA256:pin.ExpectedCohortSHA256,
       SignatureVerified:true,Status:"EXTERNAL_SIGNATURE_VALID_PROSPECTIVE_CLAIM_NOT_SCIENTIFIC_ACCEPTANCE",
       Items:[]CalibrationItem{},
    }
    var brierSum,logSum int64
    previous:=""
    for _,r:=range records{
       candidate,found:=selected[r.CandidateID]
       idx:=calibrationOutcomeIndex(r.Observation)
       if !found||!validID(r.CandidateID)||seenCandidates[r.CandidateID]||
          (previous!=""&&r.CandidateID<=previous)||
          candidate.SourceSHA!=r.SourceSHA||candidate.MechanismSHA256!=r.MechanismSHA256||
          idx<0||!validHex(r.PreregistrationSHA256,64)||
          !validHex(r.FirstUseWitnessSHA256,64)||
          !validHex(r.OriginalEvidenceSHA256,64)||
          r.FirstUseWitnessSHA256==r.OriginalEvidenceSHA256||
          seenEvidence[r.OriginalEvidenceSHA256]||
          seenWitness[r.FirstUseWitnessSHA256]||
          r.ActualComputeUnits<1||r.ActualComputeUnits>1_000_000_000||
          r.CPUTimeMillis<1||r.CPUTimeMillis>1_000_000_000||
          r.PeakMemoryBytes<1||r.PeakMemoryBytes>1_000_000_000_000||
          r.MemoryByteMillis<1||r.MemoryByteMillis>1_000_000_000_000_000||
          (r.TransferClassification!="NOT_MEASURED"&&
           r.TransferClassification!="TRANSFER_CLAIM"&&
           r.TransferClassification!="NO_TRANSFER"&&
           r.TransferClassification!="REGRESSION"){
          return zero,ErrFrozen
       }
       seenCandidates[r.CandidateID]=true
       seenEvidence[r.OriginalEvidenceSHA256]=true
       seenWitness[r.FirstUseWitnessSHA256]=true
       previous=r.CandidateID
       var marginal [4]float64
       for h,p:=range f.Hypotheses{
           weight:=float64(p.PriorBP)/10000
           for outcome,mass:=range candidate.OutcomeGivenHypothesis[h]{
               marginal[outcome]+=weight*float64(mass)/10000
           }
       }
       loss:=0.0
       for o,pred:=range marginal{
           label:=0.0
           if o==idx{label=1}
           delta:=pred-label
           loss+=delta*delta
       }
       brier:=int64(math.Round(loss*1_000_000))
       bits:=int64(-1)
       if marginal[idx]>0{bits=int64(math.Round(-math.Log2(marginal[idx])*1_000_000))}
       // -1 denotes a zero-probability, infinitely surprising observation.
       item:=CalibrationItem{
           CandidateID:r.CandidateID,Observation:r.Observation,
           PredictedProbabilityBP:int64(math.Round(marginal[idx]*10000)),
           BrierScoreMicro:brier,LogLossMicrobits:bits,
           EstimatedComputeUnits:candidate.ComputeUnits,
           ActualComputeUnits:r.ActualComputeUnits,
           CostOverrunBP:r.ActualComputeUnits*10000/candidate.ComputeUnits,
           CPUTimeMillis:r.CPUTimeMillis,PeakMemoryBytes:r.PeakMemoryBytes,
           MemoryByteMillis:r.MemoryByteMillis,TransferClassification:r.TransferClassification,
           OriginalEvidenceSHA256:r.OriginalEvidenceSHA256,
       }
       out.Items=append(out.Items,item)
       out.TotalActualComputeUnits+=r.ActualComputeUnits
       out.TotalCPUTimeMillis+=r.CPUTimeMillis
       if r.PeakMemoryBytes>out.MaxPeakMemoryBytes{out.MaxPeakMemoryBytes=r.PeakMemoryBytes}
       if idx==1{out.NegativeCount++}
       if idx==2{out.LimitationCount++}
       if r.TransferClassification=="TRANSFER_CLAIM"{out.TransferClaimCount++}
       brierSum+=brier
       if bits==-1{logSum=-1}else if logSum>=0{logSum+=bits}
    }
    out.Observations=len(records)
    out.MeanBrierMicro=brierSum/int64(len(records))
    if logSum==-1{out.MeanLogLossMicrobits=-1}else{out.MeanLogLossMicrobits=logSum/int64(len(records))}
    sort.Slice(out.Items,func(i,j int)bool{return out.Items[i].CandidateID<out.Items[j].CandidateID})
    return out,nil
}
