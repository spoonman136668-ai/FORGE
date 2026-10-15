package researcharchive

import (
    "bytes"
    "crypto/ed25519"
    "encoding/hex"
    "encoding/json"
    "os"
    "strconv"
    "strings"
    "testing"

    "github.com/spoonman136668-ai/forge/sourcebirth"
    "github.com/spoonman136668-ai/forge/workerreconcile"
)
func r21Key(b byte)(ed25519.PublicKey,ed25519.PrivateKey){
    k:=ed25519.NewKeyFromSeed(bytes.Repeat([]byte{b},ed25519.SeedSize))
    return k.Public().(ed25519.PublicKey),k
}
func r21Fixture(t *testing.T)([]byte,[]R21OriginalEvidence){
    t.Helper()
    raw,err:=os.ReadFile("../reference/research-originals/20261013-six-recent-archive-cohort.json")
    if err!=nil {t.Fatal(err)}
    m,err:=LoadManifest(raw);if err!=nil{t.Fatal(err)}
    ip,ik:=r21Key(1);wp,wk:=r21Key(2);rp,rk:=r21Key(3)
    claims:=make([]R21OriginalEvidence,0,6)
    for i,e:=range m.Entries {
        pre,cohort,tree:=strings.Repeat("4",64),strings.Repeat("5",64),strings.Repeat("6",40)
        b:=sourcebirth.Statement{Schema:sourcebirth.Schema,Lane:e.Lane,
            Repository:e.Repository,OriginalID:e.Experiment,SourceCommitSHA:e.HeadSHA,
            SourceTreeSHA:tree,PreregSHA256:pre,CohortSHA256:cohort,
            ArchiveSHA256:e.ArchiveSHA256,AuthorityEpoch:1,BirthSequence:uint64(i+1),
            WitnessRevision:uint64(i+1),FrozenUnix:1,BirthUnix:2}
        bytesBirth,err:=json.Marshal(b);if err!=nil{t.Fatal(err)}
        signed:=&sourcebirth.Signed{Statement:b,
            IssuerSignatureHex:hex.EncodeToString(ed25519.Sign(ik,
                append([]byte(sourcebirth.IssuerDomain),bytesBirth...))),
            WitnessSignatureHex:hex.EncodeToString(ed25519.Sign(wk,
                append([]byte(sourcebirth.WitnessDomain),bytesBirth...)))}
        pins:=sourcebirth.Pins{Lane:e.Lane,OriginalID:e.Experiment,
            SourceCommitSHA:e.HeadSHA,SourceTreeSHA:tree,PreregSHA256:pre,
            CohortSHA256:cohort,ArchiveSHA256:e.ArchiveSHA256,
            AuthorityEpoch:1,MinBirthSequence:1,MinWitnessRevision:1,
            IssuerPublicKey:ip,WitnessPublicKey:wp}
        run:=strconv.FormatUint(e.RunID,10)
        expected:=workerreconcile.Expected{Lane:e.Lane,ExperimentID:e.Experiment,
            FrozenSHA256:pre,IntentSHA256:cohort,OriginalRunID:run,OwnerEpoch:1,
            WorkerID:"synthetic-test-worker",WorkerPublicKey:rp}
        receipt:=func(stage string)*workerreconcile.Signed{
            r:=workerreconcile.Receipt{Schema:workerreconcile.Schema,
                Lane:e.Lane,ExperimentID:e.Experiment,FrozenSHA256:pre,IntentSHA256:cohort,
                OriginalRunID:run,OwnerEpoch:1,WorkerID:"synthetic-test-worker",Stage:stage}
            if stage=="TERMINAL"{r.EvidenceSHA256=e.ArchiveSHA256}
            rb,err:=json.Marshal(r);if err!=nil{t.Fatal(err)}
            return &workerreconcile.Signed{Receipt:r,SignatureHex:hex.EncodeToString(
                ed25519.Sign(rk,append([]byte("FORGE-WORKER-ORIGINAL-RECEIPT-V1\n"),rb...)))}
        }
        claims=append(claims,R21OriginalEvidence{Birth:signed,BirthPins:pins,
            WorkerExpected:expected,Started:receipt("STARTED"),Terminal:receipt("TERMINAL")})
    }
    return raw,claims
}
func TestR21SignaturesNeverAuthorizeScientificUse(t *testing.T){
    raw,claims:=r21Fixture(t)
    r,err:=AuditR21SignedRecords(raw,claims)
    if err!=nil{t.Fatal(err)}
    if r.SignedOriginalsStructurallyVerified!=6 || r.IndependentPhysicalSignerCustody ||
        r.CompleteFirstUseHighWater || r.HistoricalScientificAcceptance ||
        r.OptimizerTrainingAdmitted || r.OptimizerDispatchAuthorized || r.OriginalsExecuted!=0 {
        t.Fatalf("historical synthetic signatures became live authority: %+v",r)
    }
}
func TestR21HistoricalClaimNegatives(t *testing.T){
    raw,base:=r21Fixture(t)
    cases:=map[string]func([]R21OriginalEvidence){
        "missing_birth":func(v []R21OriginalEvidence){v[0].Birth=nil},
        "missing_start":func(v []R21OriginalEvidence){v[0].Started=nil},
        "missing_terminal":func(v []R21OriginalEvidence){v[0].Terminal=nil},
        "cross_lane":func(v []R21OriginalEvidence){v[0],v[3]=v[3],v[0]},
        "run_drift":func(v []R21OriginalEvidence){v[0].WorkerExpected.OriginalRunID="99"},
        "source_drift":func(v []R21OriginalEvidence){v[0].BirthPins.SourceCommitSHA=strings.Repeat("a",40)},
        "digest_drift":func(v []R21OriginalEvidence){v[0].BirthPins.ArchiveSHA256=strings.Repeat("b",64)},
        "signer_reuse":func(v []R21OriginalEvidence){v[0].WorkerExpected.WorkerPublicKey=v[0].BirthPins.IssuerPublicKey},
        "signature_forgery":func(v []R21OriginalEvidence){
            z:=*v[0].Terminal;z.SignatureHex=strings.Repeat("0",128);v[0].Terminal=&z},
    }
    for name,fn:=range cases{t.Run(name,func(t *testing.T){
        clone:=append([]R21OriginalEvidence(nil),base...)
        fn(clone)
        if _,err:=AuditR21SignedRecords(raw,clone);err==nil{t.Fatal("untrusted evidence admitted")}
    })}
    if _,err:=AuditR21SignedRecords(raw,base[:5]);err==nil{t.Fatal("partial cohort admitted")}
}
