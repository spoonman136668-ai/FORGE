// Package nrm1j screens action disagreement using an already-observed,
// explicitly source-free public history. It never runs an environment.
package nrm1j

import (
    "crypto/sha256"
    "encoding/hex"
    "encoding/json"
    "errors"
    "math"
    "math/rand"

    nrm1e "github.com/spoonman136668-ai/forge/research/nr-m1e"
)

const SourceFreeRole = "SOURCE_FREE_ENGINEERING_ONLY"
const MaxEvents = 128
const MemorySlots = 2

// Input contains only historical public actions and their recorded public
// consequences. Neither a future hidden correct action nor a source step is
// provided. An actual source owner must separately admit a future experiment.
type Input struct {
    Role string
    CandidateCheckpoint []byte
    History []nrm1e.Event
    NextPublicGrid nrm1e.NativePublicGrid
    ReservoirSeed int64
}

// Recommendation uses the SAME simple, non-trainable reward/context readout
// for all three memory arms. This is not the native Wingless action policy.
type Recommendation struct {
    Action int
    HasEvidence bool
    Score float64
}

// Result intentionally omits any correctness or episode-return claim.
type Result struct {
    Candidate Recommendation
    FIFO Recommendation
    Reservoir Recommendation
    DifferentFromFIFO bool
    DifferentFromReservoir bool
    DecisionDiscriminating bool
    SourceFreeOnly bool
    CheckpointSHA256 string
    HistorySHA256 string
    Events int
    MaxMemorySlots int
}

func safeHistory(events []nrm1e.Event) error {
    if len(events)<3 || len(events)>MaxEvents {
        return errors.New("NRM1J_UNQUALIFIED_EVENT_COUNT")
    }
    for _,e:=range events {
        if e.Terminal || e.Truncated {
            return errors.New("NRM1J_NOT_AT_PRETERMINAL_DECISION")
        }
        if _,_,_,err:=nrm1e.DecodeObservedPublic(e);err!=nil {
            return errors.New("NRM1J_INVALID_PUBLIC_TRANSITION")
        }
    }
    return nil
}

func memoryFIFO(events []nrm1e.Event) []nrm1e.Event {
    return append([]nrm1e.Event(nil),events[len(events)-MemorySlots:]...)
}
func memoryReservoir(events []nrm1e.Event,seed int64) []nrm1e.Event {
    random:=rand.New(rand.NewSource(seed))
    slots:=append([]nrm1e.Event(nil),events[:MemorySlots]...)
    for t:=MemorySlots;t<len(events);t++ {
        i:=random.Intn(t+1)
        if i<MemorySlots {slots[i]=events[t]}
    }
    return slots
}

func distance(a,b [6]float64) float64 {
    var d float64
    for i:=0;i<6;i++ {d+=math.Abs(a[i]-b[i])}
    return math.Min(d,60)
}

// Recommend calculates a deterministic, equal-information public consequence
// heuristic. Unsampled actions cannot receive fabricated expected returns.
// All-zero observed rewards yield abstention, not a guessed legal action.
func Recommend(events []nrm1e.Event,current nrm1e.NativePublicGrid) (Recommendation,error) {
    if len(events)>MemorySlots {return Recommendation{},errors.New("NRM1J_MEMORY_CAPACITY_EXCEEDED")}
    query,err:=nrm1e.EncodeNativeGrid(current)
    if err!=nil {return Recommendation{},err}
    var sum,weight [3]float64
    for _,e:=range events {
        if e.Terminal||e.Truncated {return Recommendation{},errors.New("NRM1J_TERMINAL_EVENT")}
        if _,_,_,err:=nrm1e.DecodeObservedPublic(e);err!=nil {return Recommendation{},err}
        if e.Reward==0 {continue}
        a:=int(e.Action)
        w:=math.Exp(-distance(e.Before,query)/6.)
        sum[a]+=e.Reward*w
        weight[a]+=w
    }
    chosen:=-1
    best:=math.Inf(-1)
    for a:=0;a<3;a++ {
        if weight[a]==0 {continue}
        score:=sum[a]/weight[a]
        if chosen<0 || score>best {chosen=a;best=score}
    }
    if chosen<0 {return Recommendation{Action:-1},nil}
    return Recommendation{Action:chosen,HasEvidence:true,Score:best},nil
}

// Screen clones the frozen, previously trained candidate checkpoint, so
// screening cannot alter source-owned learner or checkpoint state.
func Screen(in Input) (Result,error) {
    if in.Role!=SourceFreeRole {
        return Result{},errors.New("NRM1J_SOURCE_NOT_ADMITTED")
    }
    if in.ReservoirSeed==0 {return Result{},errors.New("NRM1J_SEED_REQUIRED")}
    if err:=safeHistory(in.History);err!=nil {return Result{},err}
    if _,err:=nrm1e.EncodeNativeGrid(in.NextPublicGrid);err!=nil {return Result{},err}
    learner,err:=nrm1e.Restore(in.CandidateCheckpoint)
    if err!=nil {return Result{},errors.New("NRM1J_CANDIDATE_CHECKPOINT_INVALID")}
    if learner.Episodes==0 || len(learner.Slots)!=0 || learner.AwaitingFeedback {
        return Result{},errors.New("NRM1J_NOT_AT_FROZEN_TRAINED_BOUNDARY")
    }
    for _,e:=range in.History {
        if err:=learner.Observe(e);err!=nil {return Result{},err}
    }
    if len(learner.Slots)!=MemorySlots {
        return Result{},errors.New("NRM1J_CANDIDATE_MEMORY_CAPACITY_DRIFT")
    }
    candidate,err:=Recommend(learner.Slots,in.NextPublicGrid)
    if err!=nil {return Result{},err}
    fifo,err:=Recommend(memoryFIFO(in.History),in.NextPublicGrid)
    if err!=nil {return Result{},err}
    reservoir,err:=Recommend(memoryReservoir(in.History,in.ReservoirSeed),in.NextPublicGrid)
    if err!=nil {return Result{},err}
    historyBytes,err:=json.Marshal(in.History)
    if err!=nil {return Result{},err}
    checkpointDigest:=sha256.Sum256(in.CandidateCheckpoint)
    historyDigest:=sha256.Sum256(historyBytes)
    // A different action is diagnostic ONLY if both arms have actual public
    // reward evidence. Missing evidence is recorded as abstention.
    fromFIFO:=candidate.HasEvidence&&fifo.HasEvidence&&candidate.Action!=fifo.Action
    fromReservoir:=candidate.HasEvidence&&reservoir.HasEvidence&&candidate.Action!=reservoir.Action
    return Result{
        Candidate:candidate,FIFO:fifo,Reservoir:reservoir,
        DifferentFromFIFO:fromFIFO,DifferentFromReservoir:fromReservoir,
        DecisionDiscriminating:fromFIFO||fromReservoir,
        SourceFreeOnly:true,CheckpointSHA256:hex.EncodeToString(checkpointDigest[:]),
        HistorySHA256:hex.EncodeToString(historyDigest[:]),
        Events:len(in.History),MaxMemorySlots:MemorySlots,
    },nil
}
