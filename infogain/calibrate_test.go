package infogain

import (
    "crypto/ed25519"
    "encoding/hex"
    "reflect"
    "strings"
    "testing"
)

func calibrationFixture()(Frozen,string,SignedProspective,ExternalCalibrationPin) {
    f:=fixture()
    frozen:=Digest(f)
    rows:=[]ProspectiveRecord{
        {
            CandidateID:f.Candidates[0].ID,
            SourceSHA:f.Candidates[0].SourceSHA,
            MechanismSHA256:f.Candidates[0].MechanismSHA256,
            Observation:"NEGATIVE",PreregistrationSHA256:strings.Repeat("1",64),
            FirstUseWitnessSHA256:strings.Repeat("2",64),
            OriginalEvidenceSHA256:strings.Repeat("3",64),
            CPUTimeMillis:400,PeakMemoryBytes:4096,MemoryByteMillis:204800,
            ActualComputeUnits:12,TransferClassification:"REGRESSION",
        },
        {
            CandidateID:f.Candidates[1].ID,
            SourceSHA:f.Candidates[1].SourceSHA,
            MechanismSHA256:f.Candidates[1].MechanismSHA256,
            Observation:"LIMITATION",PreregistrationSHA256:strings.Repeat("4",64),
            FirstUseWitnessSHA256:strings.Repeat("5",64),
            OriginalEvidenceSHA256:strings.Repeat("6",64),
            CPUTimeMillis:900,PeakMemoryBytes:8192,MemoryByteMillis:900000,
            ActualComputeUnits:120,TransferClassification:"NOT_MEASURED",
        },
    }
    cohort:=ProspectiveCohort{
        Schema:CalibrationSchema,Lane:f.Lane,FrozenSHA256:frozen,
        SourceSHA:f.SourceSHA,Records:rows,
    }
    var seed [32]byte
    copy(seed[:],[]byte("SOURCE_TEST_ONLY_NOT_INDEPENDENT_"))
    private:=ed25519.NewKeyFromSeed(seed[:])
    pub:=private.Public().(ed25519.PublicKey)
    digest:=CohortDigest(cohort)
    signature:=ed25519.Sign(private,[]byte(CalibrationDomain+digest+"\n"))
    signed:=SignedProspective{
        Cohort:cohort,IndependentSignerPublicKeyHex:hex.EncodeToString(pub),
        SignatureHex:hex.EncodeToString(signature),
    }
    pin:=ExternalCalibrationPin{
        FrozenSHA256:frozen,ExpectedCohortSHA256:digest,
        QualifiedSignerPublicKeyHex:hex.EncodeToString(pub),
    }
    return f,frozen,signed,pin
}
func TestSignedProspectiveCalibrationPreservesNegativeAndActualResources(t *testing.T){
    f,freeze,signed,pin:=calibrationFixture()
    a,err:=Calibrate(f,freeze,signed,pin)
    if err!=nil{t.Fatal(err)}
    b,err:=Calibrate(f,freeze,signed,pin)
    if err!=nil||!reflect.DeepEqual(a,b){t.Fatal("nondeterministic calibration",err)}
    if a.Observations!=2||a.NegativeCount!=1||a.LimitationCount!=1||
       a.TotalActualComputeUnits!=132||a.TotalCPUTimeMillis!=1300||
       a.MaxPeakMemoryBytes!=8192||a.MeanBrierMicro!=500000||
       a.MeanLogLossMicrobits!=1000000||!a.SignatureVerified{
       t.Fatalf("wrong calibration or negative retention: %+v",a)
    }
    for _,item:=range a.Items{
        if item.CostOverrunBP!=12000||item.PredictedProbabilityBP!=5000{
            t.Fatalf("cost/forecast mismatch: %+v",item)
        }
    }
    if a.ScientificAccepted||a.GenuineTransferEstablished||
       a.IndependentlyWitnessedFirstUse||a.OptimizerPromotionAuthorized||
       a.ExecutionAuthorized{t.Fatalf("signed claim improperly promoted: %+v",a)}
}
func TestProspectiveTamperingFailsClosed(t *testing.T){
    f,freeze,signed,pin:=calibrationFixture()
    mutate:=[]struct{
        name string
        change func(*SignedProspective,*ExternalCalibrationPin)
    }{
        {"changed-observation",func(s *SignedProspective,p *ExternalCalibrationPin){s.Cohort.Records[0].Observation="SUPPORTED"}},
        {"reused-evidence",func(s *SignedProspective,p *ExternalCalibrationPin){s.Cohort.Records[1].OriginalEvidenceSHA256=s.Cohort.Records[0].OriginalEvidenceSHA256}},
        {"changed-cost",func(s *SignedProspective,p *ExternalCalibrationPin){s.Cohort.Records[0].ActualComputeUnits=1}},
        {"zero-CPU",func(s *SignedProspective,p *ExternalCalibrationPin){s.Cohort.Records[0].CPUTimeMillis=0}},
        {"untrusted-key",func(s *SignedProspective,p *ExternalCalibrationPin){p.QualifiedSignerPublicKeyHex=strings.Repeat("f",64)}},
        {"changed-source",func(s *SignedProspective,p *ExternalCalibrationPin){s.Cohort.Records[0].SourceSHA=strings.Repeat("e",40)}},
        {"reversed-records",func(s *SignedProspective,p *ExternalCalibrationPin){s.Cohort.Records[0],s.Cohort.Records[1]=s.Cohort.Records[1],s.Cohort.Records[0]}},
        {"wrong-lane",func(s *SignedProspective,p *ExternalCalibrationPin){s.Cohort.Lane="Yggdrasil"}},
        {"wrong-frozen",func(s *SignedProspective,p *ExternalCalibrationPin){s.Cohort.FrozenSHA256=strings.Repeat("e",64)}},
        {"bad-signature",func(s *SignedProspective,p *ExternalCalibrationPin){s.SignatureHex=strings.Repeat("0",128)}},
        {"unqualified-source",func(s *SignedProspective,p *ExternalCalibrationPin){s.Cohort.Records[0].PreregistrationSHA256=""}},
        {"invalid-transfer-claim",func(s *SignedProspective,p *ExternalCalibrationPin){s.Cohort.Records[0].TransferClassification="ACCEPTED_TRANSFER"}},
    }
    for _,tc:=range mutate{
        t.Run(tc.name,func(t *testing.T){
            copy:=signed
            copy.Cohort.Records=append([]ProspectiveRecord(nil),signed.Cohort.Records...)
            trust:=pin
            tc.change(&copy,&trust)
            if _,err:=Calibrate(f,freeze,copy,trust);err!=ErrFrozen{
                t.Fatalf("invalid or altered cohort accepted: %v",err)
            }
        })
    }
}
func TestSignedDataCannotPromoteRejectedCheapSuccess(t *testing.T){
    f,freeze,signed,pin:=calibrationFixture()
    signed.Cohort.Records=append(signed.Cohort.Records,ProspectiveRecord{
        CandidateID:f.Candidates[2].ID,
        SourceSHA:f.Candidates[2].SourceSHA,
        MechanismSHA256:f.Candidates[2].MechanismSHA256,
        Observation:"SUPPORTED",
        PreregistrationSHA256:strings.Repeat("7",64),
        FirstUseWitnessSHA256:strings.Repeat("8",64),
        OriginalEvidenceSHA256:strings.Repeat("9",64),
        ActualComputeUnits:1,CPUTimeMillis:1,PeakMemoryBytes:1,
        MemoryByteMillis:1,TransferClassification:"TRANSFER_CLAIM",
    })
    // Caller could always generate a new signature over a changed cohort.
    // A new signature does not prove that an excluded candidate was selected.
    var seed [32]byte
    copy(seed[:],[]byte("SOURCE_TEST_ONLY_NOT_INDEPENDENT_"))
    private:=ed25519.NewKeyFromSeed(seed[:])
    newSHA:=CohortDigest(signed.Cohort)
    signed.SignatureHex=hex.EncodeToString(ed25519.Sign(private,[]byte(CalibrationDomain+newSHA+"\n")))
    pin.ExpectedCohortSHA256=newSHA
    if _,err:=Calibrate(f,freeze,signed,pin);err!=ErrFrozen{
        t.Fatalf("signed rejected cheap success was admitted: %v",err)
    }
}
