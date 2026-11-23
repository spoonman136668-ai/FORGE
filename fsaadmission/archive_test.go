package fsaadmission

import (
    "context"
    "crypto/ed25519"
    "crypto/sha256"
    "errors"
    "os"
    "path/filepath"
    "strings"
    "testing"

    "github.com/spoonman136668-ai/forge/eligibility"
    "github.com/spoonman136668-ai/forge/fsahead"
    "github.com/spoonman136668-ai/forge/fsatrust"
    "github.com/spoonman136668-ai/forge/privatearchive"
    "github.com/spoonman136668-ai/forge/researchlog"
    "github.com/spoonman136668-ai/forge/startrecovery"
)

// archiveTestBackend is deliberately a non-durable in-process test double.
// Only a separately authenticated, witnessed remote service may be used for
// live acceptance, and AssessArchived has no dispatch or acceptance ability.
type archiveTestBackend struct {
    anchor fsahead.Anchor
    bound bool
    offline bool
    reads int
    casCalls int
    onRead func(int)
}
func (b *archiveTestBackend) ReadAnchor(context.Context) (fsahead.Anchor,error) {
    b.reads++
    if b.onRead!=nil{b.onRead(b.reads)}
    if b.offline { return fsahead.Anchor{}, errors.New("synthetic outage") }
    result := b.anchor
    result.PublicKey = append(ed25519.PublicKey(nil), b.anchor.PublicKey...)
    return result, nil
}
func (b *archiveTestBackend) ConfirmArchiveBinding(_ context.Context, archiveID string) (bool,error) {
    return b.bound && b.anchor.ArchiveID == archiveID,nil
}
func (b *archiveTestBackend) CompareAndSwap(context.Context,fsahead.Anchor,fsahead.Anchor)(bool,error){
    b.casCalls++
    return false,errors.New("read-only preflight must never call CAS")
}
func setupArchivedPreflight(t *testing.T)(Evidence,*privatearchive.Store,*archiveTestBackend,fsatrust.Identity) {
    t.Helper()
    e:=testEvidence(t)
    root:=filepath.Join(t.TempDir(),privatearchive.FolderName)
    archive,err:=privatearchive.Initialize(root)
    if err!=nil{t.Fatal(err)}
    for _,row:=range e.Journal.Entries {
        saved,err:=archive.AppendEvent(row.Event)
        if err!=nil{t.Fatal(err)}
        if saved.RecordSHA256!=row.RecordSHA256 {t.Fatal("source archive hash divergence")}
    }
    sum:=sha256.Sum256([]byte("FORGE ONLY synthetic archive preflight test identity"))
    pub:=ed25519.NewKeyFromSeed(sum[:]).Public().(ed25519.PublicKey)
    anchor:=fsahead.Anchor{
        ArchiveID: strings.Repeat("a",64),
        KeyID:"FORGE_SYNTHETIC_ONLY",PublicKey:append(ed25519.PublicKey(nil),pub...),
        AuthorityEpoch:1,Sequence:e.JournalHead.Sequence,HeadSHA256:e.JournalHead.SHA256,
    }
    identity:=fsatrust.Identity{
        ArchiveID:anchor.ArchiveID,KeyID:anchor.KeyID,
        PublicKey:append(ed25519.PublicKey(nil),pub...),AuthorityEpoch:anchor.AuthorityEpoch,
    }
    // Intentionally spoof the caller head and journal. AssessArchived must
    // read the real verified archive and derive its head from authority.
    e.Journal=researchlog.New()
    e.JournalHead=startrecovery.TrustedHead{
        Sequence:999,SHA256:strings.Repeat("f",64),IndependentlyAuthenticated:false,
    }
    return e,archive,&archiveTestBackend{anchor:anchor,bound:true},identity
}
func archivedBlocked(t *testing.T,e Evidence,a *privatearchive.Store,b *archiveTestBackend,id fsatrust.Identity){
    t.Helper()
    d,err:=AssessArchived(context.Background(),b,a,id,e)
    if d!="" || !errors.Is(err,ErrBlocked) {
        t.Fatalf("fail closed required: %q %v",d,err)
    }
    if b.casCalls!=0 { t.Fatal("read-only method called authority CAS") }
}
func TestArchivedPreflightDerivesAuthenticatedHeadAndRemainsNonAuthorizing(t *testing.T){
    e,a,b,id:=setupArchivedPreflight(t)
    d,err:=AssessArchived(context.Background(),b,a,id,e)
    if err!=nil||d!=PreflightOnly {t.Fatalf("archived preflight: %q %v",d,err)}
    if b.reads<2||b.casCalls!=0{t.Fatal("missing double authority witness or unexpected CAS")}
    actual,err:=a.Load();if err!=nil{t.Fatal(err)}
    if len(actual.Entries)!=3{t.Fatal("unexpected archive mutation")}
}
func TestArchivedPreflightRejectsAuthorityAndArchiveDrift(t *testing.T){
    t.Run("missing backend",func(t *testing.T){
        e,a,_,id:=setupArchivedPreflight(t)
        d,err:=AssessArchived(context.Background(),nil,a,id,e)
        if d!=""||!errors.Is(err,ErrBlocked){t.Fatalf("nil authority accepted: %q %v",d,err)}
    })
    t.Run("missing archive",func(t *testing.T){
        e,_,b,id:=setupArchivedPreflight(t)
        d,err:=AssessArchived(context.Background(),b,nil,id,e)
        if d!=""||!errors.Is(err,ErrBlocked){t.Fatalf("nil archive accepted: %q %v",d,err)}
    })
    t.Run("unavailable authority",func(t *testing.T){
        e,a,b,id:=setupArchivedPreflight(t);b.offline=true;archivedBlocked(t,e,a,b,id)
    })
    t.Run("foreign identity",func(t *testing.T){
        e,a,b,id:=setupArchivedPreflight(t);id.KeyID="FORGED_KEY";archivedBlocked(t,e,a,b,id)
    })
    t.Run("unbound archive",func(t *testing.T){
        e,a,b,id:=setupArchivedPreflight(t);b.bound=false;archivedBlocked(t,e,a,b,id)
    })
    t.Run("stale authority head",func(t *testing.T){
        e,a,b,id:=setupArchivedPreflight(t);b.anchor.Sequence--;archivedBlocked(t,e,a,b,id)
    })
    t.Run("wrong authority head",func(t *testing.T){
        e,a,b,id:=setupArchivedPreflight(t);b.anchor.HeadSHA256=strings.Repeat("e",64);archivedBlocked(t,e,a,b,id)
    })
    t.Run("cancelled context",func(t *testing.T){
        e,a,b,id:=setupArchivedPreflight(t)
        ctx,cancel:=context.WithCancel(context.Background());cancel()
        d,err:=AssessArchived(ctx,b,a,id,e)
        if d!=""||!errors.Is(err,ErrBlocked){t.Fatalf("cancel accepted: %q %v",d,err)}
    })
    t.Run("repinned budget drift",func(t *testing.T){
        e,a,b,id:=setupArchivedPreflight(t)
        e.Frozen.BudgetUnits++
        pin,err:=eligibility.Fingerprint(e.Frozen)
        if err!=nil{t.Fatal(err)}
        e.FrozenPinSHA256=pin
        archivedBlocked(t,e,a,b,id)
    })
}

func TestArchivedPreflightRejectsOriginalLostAfterFirstRecovery(t *testing.T){
    e,_,backend,id:=setupArchivedPreflight(t)
    root:=filepath.Join(t.TempDir(),privatearchive.FolderName)
    archive,err:=privatearchive.Initialize(root)
    if err!=nil{t.Fatal(err)}
    for _,row:=range testEvidence(t).Journal.Entries {
        saved,err:=archive.AppendEvent(row.Event)
        if err!=nil||saved.RecordSHA256!=row.RecordSHA256{t.Fatal("fixture journal divergence",err)}
    }
    raw,err:=archive.SaveOriginal([]byte("synthetic independent original negative outcome"))
    if err!=nil{t.Fatal(err)}
    other:=researchlog.Event{
        Lane:"Yggdrasil",Generation:7,ExperimentID:"ygg_other_01",
        SourceCommitSHA:strings.Repeat("f",40),
    }
    stages:=[]researchlog.Kind{
        researchlog.Hypothesis,researchlog.Preregister,
        researchlog.SourceQualified,researchlog.PrimaryStarted,
        researchlog.PrimaryTerminal,
    }
    for _,kind:=range stages {
        other.Kind=kind
        if kind==researchlog.Preregister{
            other.PreregSHA256=strings.Repeat("a",64)
            other.CohortSHA256=strings.Repeat("b",64)
        }
        if kind==researchlog.SourceQualified{other.WitnessSHA256=strings.Repeat("d",64)}
        if kind==researchlog.PrimaryStarted{
            other.WitnessSHA256=strings.Repeat("e",64)
            other.RunID=901
        }
        if kind==researchlog.PrimaryTerminal{
            other.WitnessSHA256=strings.Repeat("e",64)
            other.OriginalEvidenceSHA256=raw
            other.Outcome="NEGATIVE"
        }
        if _,err:=archive.AppendEvent(other);err!=nil{t.Fatalf("synthetic %s: %v",kind,err)}
    }
    complete,err:=archive.Load()
    if err!=nil{t.Fatal(err)}
    backend.anchor.Sequence=uint64(len(complete.Entries))
    backend.anchor.HeadSHA256=complete.Entries[len(complete.Entries)-1].RecordSHA256
    if decision,err:=AssessArchived(context.Background(),backend,archive,id,e);decision!=PreflightOnly||err!=nil{
        t.Fatalf("valid archive with another lane's original must pass static preflight: %q %v",decision,err)
    }
    backend.reads=0
    backend.onRead=func(count int){
        if count==3{
            if err:=os.Remove(filepath.Join(root,"originals",raw+".raw"));err!=nil{t.Fatal(err)}
        }
    }
    // Read #3 happens after the first full recovery and local journal/head
    // load. The second full recovery MUST observe the missing original.
    archivedBlocked(t,e,archive,backend,id)
    if backend.reads<3{t.Fatal("did not exercise the post-recovery deletion interval")}
}
