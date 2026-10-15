package researcharchive

// R21 composes existing source-birth and worker receipt signatures for a
// complete historical cohort. It never creates independent trust or grants a
// research original, even when every signature is valid.
import (
    "bytes"
    "errors"
    "strconv"

    "github.com/spoonman136668-ai/forge/sourcebirth"
    "github.com/spoonman136668-ai/forge/workerreconcile"
)

var ErrR21Custody = errors.New("FORGE_R21_INDEPENDENT_FIRST_USE_CUSTODY_NOT_QUALIFIED")

type R21OriginalEvidence struct {
    Birth *sourcebirth.Signed
    BirthPins sourcebirth.Pins
    WorkerExpected workerreconcile.Expected
    Started *workerreconcile.Signed
    Terminal *workerreconcile.Signed
}
type R21CustodyReview struct {
    SignedOriginalsStructurallyVerified int
    IndependentPhysicalSignerCustody bool
    CompleteFirstUseHighWater bool
    HistoricalScientificAcceptance bool
    OptimizerTrainingAdmitted bool
    OptimizerDispatchAuthorized bool
    OriginalsExecuted int
}

// AuditR21SignedRecords requires complete, identity-bound source birth and
// STARTED/TERMINAL receipts, returning no report on any missing or forged
// claim. Offline role-separated signatures are NOT an operational FSA.
func AuditR21SignedRecords(manifestRaw []byte, supplied []R21OriginalEvidence) (R21CustodyReview,error) {
    var zero R21CustodyReview
    m,err:=LoadManifest(manifestRaw)
    if err!=nil || len(m.Entries)!=6 || len(supplied)!=6 {return zero,ErrR21Custody}
    seen:=make(map[string]bool,6)
    for i,e:=range m.Entries {
        item:=supplied[i]
        if item.Birth==nil || item.Started==nil || item.Terminal==nil {return zero,ErrR21Custody}
        p,w:=item.BirthPins,item.WorkerExpected
        if p.Lane!=e.Lane || p.OriginalID!=e.Experiment ||
            p.SourceCommitSHA!=e.HeadSHA || p.ArchiveSHA256!=e.ArchiveSHA256 ||
            w.Lane!=e.Lane || w.ExperimentID!=e.Experiment ||
            w.OriginalRunID!=strconv.FormatUint(e.RunID,10) ||
            w.OwnerEpoch==0 || w.OwnerEpoch!=p.AuthorityEpoch ||
            len(w.WorkerPublicKey)==0 ||
            bytes.Equal(w.WorkerPublicKey,p.IssuerPublicKey) ||
            bytes.Equal(w.WorkerPublicKey,p.WitnessPublicKey) ||
            seen[e.Lane+":"+e.Experiment] {return zero,ErrR21Custody}
        seen[e.Lane+":"+e.Experiment]=true
        b:=item.Birth.Statement
        if b.Repository!=e.Repository || b.SourceCommitSHA!=e.HeadSHA ||
            b.OriginalID!=e.Experiment || b.ArchiveSHA256!=e.ArchiveSHA256 {
            return zero,ErrR21Custody
        }
        if _,err:=sourcebirth.Verify(*item.Birth,p);err!=nil{return zero,ErrR21Custody}
        state,err:=workerreconcile.Reconcile(w,item.Started,item.Terminal)
        if err!=nil || state!=workerreconcile.Terminal {return zero,ErrR21Custody}
    }
    return R21CustodyReview{SignedOriginalsStructurallyVerified:6},nil
}
