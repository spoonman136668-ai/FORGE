package lcrm01

// O2 is a SOURCE-FREE same-information structural screen. It does not
// evaluate novel scientific sources, identify causal interventions, or
// authorize learned cognition admission.
import ("errors"; "time")

type O2Arm string
const (
    O2Learned O2Arm="learned-value"
    O2TrainedPeer O2Arm="trained-predictive-peer"
    O2Untrained O2Arm="untrained-same-representation"
    O2Recency O2Arm="recency"
)
type O2Report struct {
    Arm O2Arm
    Episodes int
    OldImportantRetained int
    OtherRecallCorrect int
    QueryBlind bool
    MaxPhysicalSlots int
    TrainUpdates int
    CompleteScreenCPUTimeNS int64
    ScientificAccepted bool
    IndependentFirstUse bool
    OptimizerAdmitted bool
}
type o2Peer struct{
    trained [FeatureCount]int16
    slots []Slot
    tick uint64
}
// A separately instantiated equally TRAIN-informed peer. It has the same
// 8 coefficients, labels, 8 stored relations and online retention budget.
func (p *o2Peer) learn(f Features,value int8){
    update(&p.trained,f,value)
}
func (p *o2Peer) observe(r Relation,arm O2Arm) {
    p.tick++
    score:=0
    if arm==O2TrainedPeer{score=dot(p.trained,r.Features)}
    candidate:=Slot{Relation:r,RetentionScore:score,Arrival:p.tick}
    for i:=range p.slots{
        x:=p.slots[i].Relation
        if x.Subject==r.Subject&&x.Object==r.Object&&x.Predicate==r.Predicate{
            p.slots[i]=candidate
            return
        }
    }
    if len(p.slots)<MaxSlots{
        p.slots=append(p.slots,candidate)
        return
    }
    oldest:=0
    for i:=1;i<len(p.slots);i++{
        if p.slots[i].RetentionScore<p.slots[oldest].RetentionScore ||
           (p.slots[i].RetentionScore==p.slots[oldest].RetentionScore &&
            p.slots[i].Arrival<p.slots[oldest].Arrival){oldest=i}
    }
    if candidate.RetentionScore>=p.slots[oldest].RetentionScore{
        p.slots[oldest]=candidate
    }
}
func (p *o2Peer) recall(r Relation)bool{
    for _,s:=range p.slots{
        x:=s.Relation
        if x.Subject==r.Subject&&x.Object==r.Object&&x.Predicate==r.Predicate{
            return true
        }
    }
    return false
}
func o2PublicTraining()[][2]interface{}{
    return [][2]interface{}{
        {Features{1,0,0,0,0,0,0,0},int8(1)},
        {Features{0,1,0,0,0,0,0,0},int8(0)},
        {Features{-1,0,0,0,0,0,0,0},int8(0)},
        {Features{0,-1,0,0,0,0,0,0},int8(1)},
        {Features{1,0,0,0,0,0,0,0},int8(1)},
        {Features{0,1,0,0,0,0,0,0},int8(0)},
        {Features{-1,0,0,0,0,0,0,0},int8(0)},
        {Features{0,-1,0,0,0,0,0,0},int8(1)},
    }
}
// O2Screen trains on public structural constants and screens deterministic
// intentionally non-novel event streams, with the eventual recall query
// withheld until every event has already been observed.
func O2Screen(arm O2Arm)(O2Report,error){
    start:=time.Now()
    switch arm{case O2Learned,O2TrainedPeer,O2Untrained,O2Recency:
    default:return O2Report{},ErrInvalid}
    report:=O2Report{Arm:arm,QueryBlind:true}
    for episode:=0;episode<6;episode++{
        model,err:=New(ForFamily(FutureRetention))
        if err!=nil{return O2Report{},err}
        peer:=&o2Peer{}
        for _,pair:=range o2PublicTraining(){
            features:=pair[0].(Features)
            label:=pair[1].(int8)
            if arm==O2Learned{
                if err:=model.LearnFutureTaskValue(features,label,true);err!=nil{return O2Report{},err}
                report.TrainUpdates++
            }
            if arm==O2TrainedPeer{
                peer.learn(features,label)
                report.TrainUpdates++
            }
        }
        offset:=episode*1000
        important:=Relation{Subject:1+offset,Object:2+offset,Predicate:1,
                             Features:Features{1,0,0,0,0,0,0,0}}
        after:=Relation{Subject:30+offset,Object:31+offset,Predicate:2,
                             Features:Features{0,1,0,0,0,0,0,0}}
        // Public case generator has no information about a future query.
        events:=[]Relation{important}
        for i:=0;i<20;i++{
            r:=after
            r.Subject+=i*3
            r.Object+=i*3
            events=append(events,r)
        }
        for _,r:=range events{
            if arm==O2Learned||arm==O2Untrained{
                if err:=model.Observe(r);err!=nil{return O2Report{},err}
            }else{peer.observe(r,arm)}
        }
        var before Snapshot
        if arm==O2Learned||arm==O2Untrained{
            before=model.Snapshot()
            if before.Stored>MaxSlots{return O2Report{},ErrBudget}
            if _,ok:=model.Recall(important.Subject,important.Object,important.Predicate);ok{
                report.OldImportantRetained++
            }
            if _,ok:=model.Recall(events[len(events)-1].Subject,
                        events[len(events)-1].Object,events[len(events)-1].Predicate);ok{
                report.OtherRecallCorrect++
            }
            for k:=0;k<30;k++{
                model.Recall(90000+k,90001+k,1)
            }
            if model.Snapshot()!=before{return O2Report{},errors.New("O2_RECALL_MUTATED_STATE")}
            if err:=model.CheckBounded();err!=nil{return O2Report{},err}
            if before.Stored>report.MaxPhysicalSlots{report.MaxPhysicalSlots=before.Stored}
        }else{
            if len(peer.slots)>MaxSlots{return O2Report{},ErrBudget}
            if peer.recall(important){report.OldImportantRetained++}
            if peer.recall(events[len(events)-1]){report.OtherRecallCorrect++}
            if len(peer.slots)>report.MaxPhysicalSlots{report.MaxPhysicalSlots=len(peer.slots)}
        }
        report.Episodes++
    }
    report.CompleteScreenCPUTimeNS=time.Since(start).Nanoseconds() // wall-time proxy, not process CPU
    return report,nil
}
