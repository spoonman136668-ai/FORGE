package quarantine

import (
    "context"
    "crypto/sha256"
    "encoding/hex"
    "encoding/json"
    "errors"
    "reflect"
    "strings"
    "sync"
    "testing"

    "github.com/spoonman136668-ai/forge/contracts"
    "github.com/spoonman136668-ai/forge/evidence"
    "github.com/spoonman136668-ai/forge/planner"
)

func hex64(s string) string { return strings.Repeat(s,64) }
func candidate(l contracts.Lane,gen uint64,seed,cohort string) contracts.CandidateDraft {
    return contracts.CandidateDraft{
        Schema:contracts.CandidateSchema,Lane:l,Generation:gen,CandidateID:string(l)+"-proposal",
        SourceCommitSHA:strings.Repeat("a",40),CandidateSHA256:hex64("b"),PreregistrationSHA256:hex64("c"),CohortSHA256:hex64(cohort),
        EvidenceClass:contracts.Synthetic,SeedIdentities:[]string{string(l)+":"+seed},AllowedPaths:[]string{"research/proposal.go"},
        Budget:contracts.Budget{TimeoutSeconds:120,MemoryMiB:512,ComputeUnits:10},
    }
}
func TestShadowReplayConflictAndDeterministicSnapshot(t *testing.T) {
    ctx:=context.Background()
    q,e:=New(3);if e!=nil{t.Fatal(e)}
    wing:=candidate(contracts.Wingless,2,"s1","d")
    ygg:=candidate(contracts.Yggdrasil,2,"s2","e")
    a,e:=q.SubmitDraft(ctx,wing);if e!=nil{t.Fatal(e)}
    b,e:=q.SubmitDraft(ctx,wing)
    if e!=nil||!reflect.DeepEqual(a,b)||a.Status!="QUARANTINE_ONLY"||a.ScientificAdmitted||a.DispatchAuthorized||a.AcceptedRefMutation {
        t.Fatal("shadow replay or privilege drift",e)
    }
    changed:=candidate(contracts.Wingless,2,"s3","f")
    if _,e=q.SubmitDraft(ctx,changed);e==nil{t.Fatal("conflicting generation accepted")}
    changed.Generation=3;changed.CohortSHA256=wing.CohortSHA256
    if _,e=q.SubmitDraft(ctx,changed);e==nil{t.Fatal("reused cohort accepted")}
    changed.CohortSHA256=hex64("f");changed.SeedIdentities=append([]string(nil),wing.SeedIdentities...)
    if _,e=q.SubmitDraft(ctx,changed);e==nil{t.Fatal("reused seed accepted")}
    if _,e=q.SubmitDraft(ctx,ygg);e!=nil{t.Fatal(e)}
    s1,e:=q.Inspect(ctx);if e!=nil||len(s1.Records)!=2{t.Fatal("dual-lane snapshot",e)}
    if s1.Records[0].Draft.Lane!=contracts.Wingless||s1.Records[1].Draft.Lane!=contracts.Yggdrasil{t.Fatal("unstable lane order")}
    s1.Records[0].Draft.SeedIdentities[0]="FORGED"
    s2,e:=q.Inspect(ctx);if e!=nil||s2.Records[0].Draft.SeedIdentities[0]=="FORGED"||s1.SHA256!=s2.SHA256{t.Fatal("snapshot alias or hash drift",e)}
}
func TestConcurrentIdempotenceBoundsAndAuthorityDenial(t *testing.T) {
    ctx:=context.Background()
    q,e:=New(1);if e!=nil{t.Fatal(e)}
    d:=candidate(contracts.Wingless,2,"one","d")
    var wg sync.WaitGroup; fail:=make(chan error,32)
    for n:=0;n<32;n++{wg.Add(1);go func(){defer wg.Done();_,err:=q.SubmitDraft(ctx,d);fail<-err}()}
    wg.Wait();close(fail)
    for err:=range fail{if err!=nil{t.Fatal(err)}}
    s,_:=q.Inspect(ctx);if len(s.Records)!=1{t.Fatal("race duplicated proposal")}
    if _,e=q.SubmitDraft(ctx,candidate(contracts.Yggdrasil,2,"two","e"));e==nil{t.Fatal("cap bypass")}
    if _,e=New(0);e==nil{t.Fatal("zero cap")}
    if _,e=New(65);e==nil{t.Fatal("oversized cap")}
    invalid:=d;invalid.DispatchAuthorized=true
    if _,e=q.SubmitDraft(ctx,invalid);e==nil{t.Fatal("forged authority accepted")}
    canceled,cancel:=context.WithCancel(ctx);cancel()
    if _,e=q.SubmitDraft(canceled,d);!errors.Is(e,context.Canceled){t.Fatal("canceled submission",e)}
    if _,e=q.Inspect(canceled);!errors.Is(e,context.Canceled){t.Fatal("canceled inspection",e)}
}
type testSource struct{ docs map[contracts.Lane][]byte }
func(s testSource)ReadReceipt(_ context.Context,l contracts.Lane)([]byte,error){return append([]byte(nil),s.docs[l]...),nil}
type testAuth struct{ denied bool }
func(a *testAuth)Authenticate(_ context.Context,_ contracts.Lane,_ []byte,_ evidence.Witness)error {
    if a.denied{return errors.New("source not independently authenticated")}
    return nil
}
func testEvidence(t *testing.T)(testSource,map[contracts.Lane]evidence.Witness,[]contracts.Observation){
    t.Helper();src:=testSource{docs:map[contracts.Lane][]byte{}}
    pins:=map[contracts.Lane]evidence.Witness{}
    observations:=[]contracts.Observation{}
    for _,lane:=range []contracts.Lane{contracts.Wingless,contracts.Yggdrasil}{
        o:=contracts.Observation{Schema:contracts.ObservationSchema,Lane:lane,AuthorityEpoch:4,SourceWitnessSHA256:hex64("1"),LedgerWitnessSHA256:hex64("2"),LatestOutcome:"SUPPORTED"}
        r:=evidence.Receipt{Schema:evidence.ReceiptSchema,Observation:o,SourceClass:contracts.Synthetic,OriginalStartedSHA256:hex64("3"),OriginalTerminalSHA256:hex64("4"),OriginalArchiveSHA256:hex64("5"),OriginalRawEvidenceSHA256:hex64("6"),OriginalRunConsumed:true}
        b,err:=json.Marshal(r);if err!=nil{t.Fatal(err)}
        src.docs[lane]=b
        sum:=sha256.Sum256(b)
        pins[lane]=evidence.Witness{AuthorityEpoch:4,SourceWitnessSHA256:o.SourceWitnessSHA256,LedgerWitnessSHA256:o.LedgerWitnessSHA256,ReceiptSHA256:hex.EncodeToString(sum[:])}
        observations=append(observations,o)
    }
    return src,pins,observations
}
func TestFixtureEndToEndEvidencePortfolioAndQuarantine(t *testing.T){
    ctx:=context.Background();src,pins,observations:=testEvidence(t)
    reader,e:=evidence.NewReader(src,&testAuth{},pins);if e!=nil{t.Fatal(e)}
    q,_:=New(4)
    frozen:=planner.FrozenPortfolio{Schema:planner.InputSchema,AuthorityEpoch:4,Observations:observations,ConsumedSeedIdentities:[]string{},Candidates:[]planner.Candidate{
        {Draft:candidate(contracts.Wingless,2,"fresh-w","d"),MechanismFamily:"W-mechanism",ParentReceiptSHA256:hex64("7"),Impact:6,Novelty:8,Robustness:7,Cost:2},
        {Draft:candidate(contracts.Yggdrasil,2,"fresh-y","e"),MechanismFamily:"Y-mechanism",ParentReceiptSHA256:hex64("8"),Impact:7,Novelty:8,Robustness:9,Cost:3},
    }}
    // This test self-pin is not sufficient independent authority in production.
    pin,e:=planner.FreezeSHA256(frozen);if e!=nil{t.Fatal(e)}
    plan,acks,e:=planner.ReviewOnly(ctx,reader,q,frozen,pin)
    if e!=nil||len(acks)!=2||len(plan.Lanes)!=2||plan.ScientificAdmitted||plan.DispatchAuthorized||plan.ExternalSourceVerified||plan.AcceptedRefMutation{t.Fatal("fixture dual-lane authority drift",e)}
    for _,ack:=range acks{if ack.Status!="QUARANTINE_ONLY"||ack.ScientificAdmitted||ack.DispatchAuthorized||ack.AcceptedRefMutation{t.Fatal("forged review acknowledgment")}}
    if _,again,e:=planner.ReviewOnly(ctx,reader,q,frozen,pin);e!=nil||!reflect.DeepEqual(acks,again){t.Fatal("non-idempotent planner replay",e)}
    snapshot,_:=q.Inspect(ctx);if len(snapshot.Records)!=2{t.Fatal("expected 2 quarantined drafts")}
    // Authentication failure must block before any proposal submission.
    denied,_:=evidence.NewReader(src,&testAuth{denied:true},pins)
    unused,_:=New(4)
    if _,_,e=planner.ReviewOnly(ctx,denied,unused,frozen,pin);e==nil{t.Fatal("untrusted evidence accepted")}
    empty,_:=unused.Inspect(ctx);if len(empty.Records)!=0{t.Fatal("untrusted evidence mutated quarantine")}
    // One consumed-indeterminate lane must not block a clean other lane.
    src,pins,observations=testEvidence(t)
    observations[0].LatestOutcome="CONSUMED_INDETERMINATE"
    var changed evidence.Receipt
    if e=json.Unmarshal(src.docs[contracts.Wingless],&changed);e!=nil{t.Fatal(e)}
    changed.Observation=observations[0]
    raw,e:=json.Marshal(changed);if e!=nil{t.Fatal(e)}
    src.docs[contracts.Wingless]=raw
    sum:=sha256.Sum256(raw);w:=pins[contracts.Wingless];w.ReceiptSHA256=hex.EncodeToString(sum[:]);pins[contracts.Wingless]=w
    reader,e=evidence.NewReader(src,&testAuth{},pins);if e!=nil{t.Fatal(e)}
    frozen.Observations=observations
    pin,e=planner.FreezeSHA256(frozen);if e!=nil{t.Fatal(e)}
    isolated,_:=New(4)
    plan,acks,e=planner.ReviewOnly(ctx,reader,isolated,frozen,pin)
    if e!=nil||len(acks)!=1||!strings.Contains(plan.Lanes[0].Disposition,"REQUIRES_CKB_RECONCILIATION")||plan.Lanes[1].Draft==nil {
        t.Fatal("blocked lane violated independence",e)
    }
}
