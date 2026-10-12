package fsaintent

import (
    "errors"
    "strings"
    "testing"
)

func fakeIntent(lane,id,cohort string,run uint64) Intent {
    return Intent{
        Lane:lane,CandidateID:id,Generation:12,RunID:run,
        FrozenSHA256:strings.Repeat("1",64),CohortSHA256:cohort,
        SourceSHA:strings.Repeat("a",40),PreregSHA256:strings.Repeat("b",64),
        BudgetUnits:10,
    }
}
func next(t *testing.T,j Journal,i Intent,stage Stage,witness string)Journal{
    t.Helper()
    result,err:=Append(j,i,stage,witness)
    if err!=nil{t.Fatalf("append %s: %v",stage,err)}
    return result
}
func trusted(j Journal)TrustedHead{
    return TrustedHead{
        Sequence:uint64(len(j.Entries)),
        SHA256:j.Entries[len(j.Entries)-1].RecordSHA256,
        IndependentlyAuthenticated:true, // synthetic fixture, never live trust
    }
}
func classification(t *testing.T,j Journal,i Intent,want Decision){
    t.Helper()
    result,err:=Inspect(j,trusted(j),i.Lane,i.CandidateID)
    if err!=nil||result!=want{t.Fatalf("classification got=%q want=%q err=%v",result,want,err)}
}
func rejectAppend(t *testing.T,j Journal,i Intent,stage Stage,witness string){
    t.Helper()
    if next,err:=Append(j,i,stage,witness);err==nil||!errors.Is(err,ErrBlocked)||next.Schema!=""{
        t.Fatalf("unexpected append %s allowed: %v",stage,err)
    }
}
func TestOneShotCrashCutsAndEvidenceBasedReconciliation(t *testing.T){
    i:=fakeIntent("Wingless","wingless_001",strings.Repeat("c",64),8001)
    j:=next(t,New(),i,Prepared,"")
    classification(t,j,i,PreparedOnly)
    rejectAppend(t,j,i,StartObserved,strings.Repeat("d",64))
    j=next(t,j,i,DispatchRisk,"")
    classification(t,j,i,NoRedispatchUnknown)
    rejectAppend(t,j,i,DispatchRisk,"") // cannot request the same dispatch twice

    // Restart with a signed independently authenticated head still returns
    // NO RE-DISPATCH, not a permission to retry after a timeout.
    j=next(t,j,i,Indeterminate,"")
    classification(t,j,i,NoRedispatchUnknown)
    rejectAppend(t,j,i,DispatchRisk,"")
    rejectAppend(t,j,i,TerminalObserved,strings.Repeat("e",64))
    j=next(t,j,i,StartObserved,strings.Repeat("d",64))
    classification(t,j,i,NoRedispatchStarted)
    rejectAppend(t,j,i,DispatchRisk,"")
    j=next(t,j,i,TerminalObserved,strings.Repeat("e",64))
    classification(t,j,i,NoRedispatchTerminal)
    for _,s:=range []Stage{Prepared,DispatchRisk,Indeterminate,StartObserved,TerminalObserved}{
        rejectAppend(t,j,i,s,strings.Repeat("e",64))
    }
}
func TestOneShotNoUnattestedStartOrEmptyEvidence(t *testing.T){
    i:=fakeIntent("Yggdrasil","ygg_001",strings.Repeat("a",64),9001)
    j:=next(t,New(),i,Prepared,"")
    rejectAppend(t,j,i,Prepared,"")
    rejectAppend(t,j,i,DispatchRisk,strings.Repeat("d",64))
    rejectAppend(t,j,i,Indeterminate,"")
    j=next(t,j,i,DispatchRisk,"")
    rejectAppend(t,j,i,StartObserved,"")
    rejectAppend(t,j,i,StartObserved,"forged")
    j=next(t,j,i,StartObserved,strings.Repeat("a",64))
    rejectAppend(t,j,i,TerminalObserved,"")
    rejectAppend(t,j,i,TerminalObserved,"not_a_hash")
}
func TestCrossLaneCohortAndRunIDCollisionBlocked(t *testing.T){
    cohort:=strings.Repeat("c",64)
    i:=fakeIntent("Wingless","wingless_001",cohort,8001)
    j:=next(t,New(),i,Prepared,"")
    sameCohort:=fakeIntent("Yggdrasil","ygg_001",cohort,8002)
    rejectAppend(t,j,sameCohort,Prepared,"")
    sameRun:=fakeIntent("Yggdrasil","ygg_002",strings.Repeat("d",64),8001)
    rejectAppend(t,j,sameRun,Prepared,"")
    changed:=i;changed.BudgetUnits++
    rejectAppend(t,j,changed,DispatchRisk,"")
    changed=i;changed.SourceSHA=strings.Repeat("b",40)
    rejectAppend(t,j,changed,DispatchRisk,"")
    changed=i;changed.Generation++
    rejectAppend(t,j,changed,DispatchRisk,"")
    // Two independent lanes with disjoint cohorts/run IDs are valid static
    // records. The journal alone still grants neither lane admission.
    other:=fakeIntent("Yggdrasil","ygg_003",strings.Repeat("e",64),8003)
    j=next(t,j,other,Prepared,"")
    if err:=Verify(j);err!=nil{t.Fatal(err)}
    classification(t,j,other,PreparedOnly)
}
func TestTamperingTailRollbackAndMissingIndependentTrustBlock(t *testing.T){
    i:=fakeIntent("Wingless","wingless_001",strings.Repeat("c",64),8001)
    j:=next(t,New(),i,Prepared,"")
    head:=trusted(j)
    j=next(t,j,i,DispatchRisk,"")
    // A full valid rollback to the old head would pass an ordinary SHA256
    // chain check; comparison to a separately pinned highwater blocks it.
    if d,err:=Inspect(j,head,i.Lane,i.CandidateID);d!=""||!errors.Is(err,ErrBlocked){
        t.Fatalf("stale head passed: %q %v",d,err)
    }
    untrusted:=trusted(j);untrusted.IndependentlyAuthenticated=false
    if d,err:=Inspect(j,untrusted,i.Lane,i.CandidateID);d!=""||!errors.Is(err,ErrBlocked){
        t.Fatalf("untrusted head passed: %q %v",d,err)
    }
    changed:=Journal{Schema:j.Schema,Entries:append([]Record{},j.Entries...)}
    changed.Entries[0].Intent.RunID++
    if d,err:=Inspect(changed,trusted(j),i.Lane,i.CandidateID);d!=""||!errors.Is(err,ErrBlocked){
        t.Fatalf("forged early run ID passed: %q %v",d,err)
    }
    changed=Journal{Schema:j.Schema,Entries:append([]Record{},j.Entries[:1]...)}
    if d,err:=Inspect(changed,trusted(j),i.Lane,i.CandidateID);d!=""||!errors.Is(err,ErrBlocked){
        t.Fatalf("valid truncated prefix passed: %q %v",d,err)
    }
    if d,err:=Inspect(j,trusted(j),"Yggdrasil","missing_id");d!=""||!errors.Is(err,ErrBlocked){
        t.Fatalf("missing logical intent passed: %q %v",d,err)
    }
}
func TestInvalidNewIntentIdentityFailsClosed(t *testing.T){
    i:=fakeIntent("Wingless","wingless_001",strings.Repeat("c",64),8001)
    cases:=map[string]func(*Intent){
        "zero budget":func(x *Intent){x.BudgetUnits=0},
        "unbounded budget":func(x *Intent){x.BudgetUnits=1000001},
        "missing run":func(x *Intent){x.RunID=0},
        "missing frozen pin":func(x *Intent){x.FrozenSHA256=""},
        "foreign lane":func(x *Intent){x.Lane="KTRADE"},
        "missing source pin":func(x *Intent){x.SourceSHA=""},
        "zero generation":func(x *Intent){x.Generation=0},
    }
    for name,mutate:=range cases{t.Run(name,func(t *testing.T){
        current:=i;mutate(&current)
        rejectAppend(t,New(),current,Prepared,"")
    })}
}
