package nrm1j

import (
    "bytes"
    "math"
    "reflect"
    "testing"

    nrm1e "github.com/spoonman136668-ai/forge/research/nr-m1e"
)

func sampleGrid() nrm1e.NativePublicGrid {
    return nrm1e.NativePublicGrid{X:1,Y:2,GoalX:5,GoalY:5,Direction:2,FrontBlocked:false}
}
func sampleEvent(t *testing.T,action int,reward float64) nrm1e.Event {
    t.Helper()
    before:=sampleGrid()
    after:=before;after.Direction=(after.Direction+1)%4
    e,err:=nrm1e.ConvertObservedPublic(before,action,nrm1e.NativePublicConsequence{
        After:after,Reward:reward,
    })
    if err!=nil {t.Fatal(err)}
    return e
}
func checkpoint(t *testing.T,override bool) []byte {
    t.Helper()
    learner:=nrm1e.New(17)
    first:=sampleEvent(t,0,0)
    last:=sampleEvent(t,1,1)
    last.Terminal=true
    if err:=learner.Observe(first);err!=nil {t.Fatal(err)}
    if err:=learner.Observe(last);err!=nil {t.Fatal(err)}
    if err:=learner.Feedback(1);err!=nil {t.Fatal(err)}
    // This test-only coefficient override creates a deterministic contrast.
    // It is an engineered fixture, NOT learned superiority or a fitted model.
    if override {learner.Weights=[4]float64{0,0,0,8}}
    raw,err:=learner.Snapshot()
    if err!=nil {t.Fatal(err)}
    return raw
}
func fixture(t *testing.T,override bool) Input {
    t.Helper()
    return Input{
        Role:SourceFreeRole,ReservoirSeed:17,
        CandidateCheckpoint:checkpoint(t,override),
        NextPublicGrid:sampleGrid(),
        History:[]nrm1e.Event{
            sampleEvent(t,0,0.8),
            sampleEvent(t,1,0.2),
            sampleEvent(t,2,-0.7),
        },
    }
}

func TestSourceFreeCandidateFIFOActionDifferenceIsDetected(t *testing.T) {
    in:=fixture(t,true)
    before:=append([]byte(nil),in.CandidateCheckpoint...)
    result,err:=Screen(in)
    if err!=nil {t.Fatal(err)}
    if result.Candidate.Action!=0 || result.FIFO.Action!=1 {
        t.Fatalf("expected engineered candidate/FIFO disagreement; got %+v",result)
    }
    if !result.DifferentFromFIFO || !result.DecisionDiscriminating || !result.SourceFreeOnly {
        t.Fatalf("wrong decision-discrimination status: %+v",result)
    }
    if result.MaxMemorySlots!=2 || result.Events!=3 {t.Fatal("memory/input budget drift")}
    if !bytes.Equal(before,in.CandidateCheckpoint) {t.Fatal("mutated caller checkpoint")}
}

func TestIdenticalCheckpointAndEventsAreDeterministic(t *testing.T) {
    in:=fixture(t,false)
    original:=append([]nrm1e.Event(nil),in.History...)
    a,err:=Screen(in);if err!=nil {t.Fatal(err)}
    b,err:=Screen(in);if err!=nil {t.Fatal(err)}
    if !reflect.DeepEqual(a,b) {t.Fatalf("replay diverged: %+v != %+v",a,b)}
    if !reflect.DeepEqual(in.History,original) {t.Fatal("mutated source history")}
}

func TestAllNullRewardHistoryAbstainsWithoutInventedAction(t *testing.T) {
    in:=fixture(t,true)
    for i:=range in.History {in.History[i].Reward=0}
    result,err:=Screen(in);if err!=nil {t.Fatal(err)}
    for _,r:=range []Recommendation{result.Candidate,result.FIFO,result.Reservoir} {
        if r.HasEvidence || r.Action!=-1 {t.Fatalf("invented reward evidence: %+v",r)}
    }
    if result.DecisionDiscriminating {t.Fatal("claimed a decision shift without any reward evidence")}
}

func TestProtectedRoleRejectedEvenWithValidPublicShape(t *testing.T) {
    in:=fixture(t,true)
    for _,name:=range []string{"","MiniGrid","PUBLIC_CHECK","HELD","original", "SOURCE_FREE_ENGINEERING_ONLY_EXTRA"} {
        in.Role=name
        if _,err:=Screen(in);err==nil {t.Fatalf("accepted unadmitted role %q",name)}
    }
}
func TestRejectTerminalHistoryAndUnqualifiedReward(t *testing.T) {
    in:=fixture(t,true)
    in.History[1].Terminal=true
    if _,err:=Screen(in);err==nil {t.Fatal("admitted a completed event in preterminal decision history")}
    in.History[1].Terminal=false
    in.History[1].Reward=math.NaN()
    if _,err:=Screen(in);err==nil {t.Fatal("accepted NaN source reward")}
    in.History[1]=sampleEvent(t,1,0.2)
    in.NextPublicGrid.Direction=5
    if _,err:=Screen(in);err==nil {t.Fatal("accepted noncanonical public decision context")}
}
func TestRejectUntrainedOrOpenEpisodeCheckpoint(t *testing.T) {
    in:=fixture(t,true)
    raw,err:=nrm1e.New(19).Snapshot();if err!=nil {t.Fatal(err)}
    in.CandidateCheckpoint=raw
    if _,err:=Screen(in);err==nil {t.Fatal("screened untrained memory")}
    trained,err:=nrm1e.Restore(checkpoint(t,false));if err!=nil {t.Fatal(err)}
    e:=sampleEvent(t,0,1);e.Truncated=true
    if err:=trained.Observe(e);err!=nil {t.Fatal(err)}
    in.CandidateCheckpoint,err=trained.Snapshot();if err!=nil {t.Fatal(err)}
    if _,err:=Screen(in);err==nil {t.Fatal("screened unfinished terminal feedback")}
}
func TestBoundedInputAndComparatorCapacity(t *testing.T) {
    in:=fixture(t,false)
    in.History=append([]nrm1e.Event(nil),in.History[:2]...)
    if _,err:=Screen(in);err==nil {t.Fatal("accepted below declared minimum screen history")}
    in=fixture(t,false)
    in.History=make([]nrm1e.Event,MaxEvents+1)
    if _,err:=Screen(in);err==nil {t.Fatal("accepted over-budget source history")}
    in=fixture(t,false)
    in.ReservoirSeed=0
    if _,err:=Screen(in);err==nil {t.Fatal("accepted unstable reservoir seed")}
    in=fixture(t,false)
    if len(memoryFIFO(in.History))!=MemorySlots || len(memoryReservoir(in.History,17))!=MemorySlots {
        t.Fatal("comparator memory not equal-capacity")
    }
}
