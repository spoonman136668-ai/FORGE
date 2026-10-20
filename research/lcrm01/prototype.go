// Package lcrm01 contains a bounded SOURCE-FREE development prototype for
// relational-state, query-blind retention, interventional action-value, and
// counterfactual composition. It grants no scientific or dispatch authority.
package lcrm01

import ("errors"; "fmt")

const (
    FeatureCount=8
    MaxSlots=8
    MaxAbsWeight=64
    MaxTrainingUpdates=4096
    MaxActions=16
    MaxSamplesPerAction=128
)
var (
    ErrInvalid=errors.New("LCRM01_INVALID_OR_UNAUTHORIZED_INPUT")
    ErrBudget=errors.New("LCRM01_RESOURCE_BUDGET_EXCEEDED")
)
type Features [FeatureCount]int8
type Family string
const (
    EncoderOnly Family="encoder-only"
    FutureRetention Family="future-task-retention"
    InterventionalValue Family="interventional-action-value"
    LearnedComposition Family="counterfactual-composition"
    Joint Family="lcrm-full"
)
type Spec struct {
    Family Family
    MemorySlots int
    ParameterCap int
    MaxUpdates int
    Encoder,Retention,ActionValue,Composition bool
    TrainingOnly bool
    SourceFirstUse bool
    ProductionEnabled bool
}
func ForFamily(f Family) Spec {
    s:=Spec{Family:f,MemorySlots:MaxSlots,ParameterCap:24,
        MaxUpdates:MaxTrainingUpdates,TrainingOnly:true}
    switch f {
    case EncoderOnly:s.Encoder=true
    case FutureRetention:s.Retention=true
    case InterventionalValue:s.ActionValue=true
    case LearnedComposition:s.Composition=true
    case Joint:s.Encoder=true;s.Retention=true;s.ActionValue=true;s.Composition=true
    default:return Spec{} // fail closed on unregistered mechanism families
    }
    return s
}
func (s Spec) Validate()error{
    expected:=ForFamily(s.Family)
    if expected.Family=="" || s!=expected || s.MemorySlots>MaxSlots ||
       s.ParameterCap>3*FeatureCount || s.MaxUpdates>MaxTrainingUpdates ||
       !s.TrainingOnly || s.SourceFirstUse || s.ProductionEnabled {
       return ErrInvalid
    }
    return nil
}
type Relation struct {
    Subject, Object int
    Predicate uint8
    Features Features
}
type Slot struct {
    Relation Relation
    RetentionScore int
    Arrival uint64
}
type ActionEvidence struct {
    Action uint8
    Outcome int8
    AssignedRandomly bool
    Intervention bool
    MatchedControls bool
    TrainingOnly bool
}
type CompositionEvidence struct {
    Left Features
    Right Features
    Target int8
    TrainingOnly bool
}
type ActionStats struct{ Count, Total int }
type Model struct {
    spec Spec
    encoder,retention,composition [FeatureCount]int16
    slots []Slot
    action map[uint8]ActionStats
    ticks uint64
    updates int
}
type Snapshot struct{
    Family Family
    Stored int
    TrainingUpdates int
    ActionClasses int
    Parameters int
    ScientificAccepted bool
    DispatchAuthorized bool
    IndependentlyReplicated bool
}
type Counterfactual struct{
    EstimateSign int
    ActionValueNumerator int
    ActionValueDenominator int
    LearnedCompositionScore int
    Certified bool
    ScientificEvidence bool
}
func New(spec Spec)(*Model,error){
    if err:=spec.Validate();err!=nil{return nil,err}
    return &Model{spec:spec,action:make(map[uint8]ActionStats)},nil
}
func validFeatures(f Features)bool{
    for _,x:=range f{if x < -1 || x > 1{return false}}
    return true
}
func dot(w [FeatureCount]int16,f Features)int{
    total:=0
    for i,x:=range f{total+=int(w[i])*int(x)}
    return total
}
func update(w *[FeatureCount]int16,f Features,target int8)bool{
    goal:= -1
    if target==1{goal=1}
    predicted:= -1
    if dot(*w,f)>0{predicted=1}
    if predicted==goal{return false}
    for i,x:=range f{
        next:=int(w[i])+goal*int(x)
        if next>MaxAbsWeight{next=MaxAbsWeight}
        if next< -MaxAbsWeight{next= -MaxAbsWeight}
        w[i]=int16(next)
    }
    return true
}
func (m *Model) train(w *[FeatureCount]int16,f Features,target int8)error{
    if !validFeatures(f)||(target!=0 && target!=1){return ErrInvalid}
    if m.updates>=m.spec.MaxUpdates{return ErrBudget}
    update(w,f,target)
    m.updates++
    return nil
}
func (m *Model) LearnEncoder(f Features,target int8,training bool)error{
    if !m.spec.Encoder||!training{return ErrInvalid}
    return m.train(&m.encoder,f,target)
}
func (m *Model) LearnFutureTaskValue(f Features,useful int8,training bool)error{
    if !m.spec.Retention||!training{return ErrInvalid}
    return m.train(&m.retention,f,useful)
}
// Observe has no future query argument or query-dependent access. Retention
// is determined at *event arrival*, before any later recall.
func (m *Model) Observe(r Relation)error{
    if !validFeatures(r.Features)||r.Subject<0||r.Object<0||
       r.Subject==r.Object{return ErrInvalid}
    m.ticks++
    score:=0
    if m.spec.Retention{score=dot(m.retention,r.Features)}
    // One key denotes a single bounded slot, irrespective of repeated events.
    for i:=range m.slots {
        prior:=m.slots[i].Relation
        if prior.Subject==r.Subject && prior.Object==r.Object &&
           prior.Predicate==r.Predicate{
            m.slots[i]=Slot{Relation:r,RetentionScore:score,Arrival:m.ticks}
            return nil
        }
    }
    candidate:=Slot{Relation:r,RetentionScore:score,Arrival:m.ticks}
    if len(m.slots)<m.spec.MemorySlots{
        m.slots=append(m.slots,candidate)
        return nil
    }
    lowest:=0
    for i:=1;i<len(m.slots);i++{
        if m.slots[i].RetentionScore<m.slots[lowest].RetentionScore ||
          (m.slots[i].RetentionScore==m.slots[lowest].RetentionScore &&
           m.slots[i].Arrival<m.slots[lowest].Arrival){lowest=i}
    }
    if candidate.RetentionScore<m.slots[lowest].RetentionScore{return nil}
    m.slots[lowest]=candidate
    return nil
}
// Recall never changes retention weights, slot rank, or future-task scores.
func (m *Model) Recall(subject,object int,predicate uint8)(Slot,bool){
    for _,s:=range m.slots {
        r:=s.Relation
        if r.Subject==subject&&r.Object==object&&r.Predicate==predicate{
            return s,true
        }
    }
    return Slot{},false
}
func (m *Model) LearnAction(e ActionEvidence)error{
    if !m.spec.ActionValue || !e.TrainingOnly || !e.Intervention ||
       !e.AssignedRandomly || !e.MatchedControls ||
       (e.Outcome!= -1 && e.Outcome!=0 && e.Outcome!=1){return ErrInvalid}
    if m.updates>=m.spec.MaxUpdates{return ErrBudget}
    a:=m.action[e.Action]
    if a.Count==0&&len(m.action)==MaxActions{return ErrBudget}
    if a.Count==MaxSamplesPerAction{return ErrBudget}
    m.action[e.Action]=ActionStats{Count:a.Count+1,Total:a.Total+int(e.Outcome)}
    m.updates++
    return nil
}
func (m *Model) LearnComposition(e CompositionEvidence)error{
    if !m.spec.Composition||!e.TrainingOnly||
       !validFeatures(e.Left)||!validFeatures(e.Right){return ErrInvalid}
    var joined Features
    for i:=range joined {
        joined[i]=e.Left[i]*e.Right[i]
    }
    return m.train(&m.composition,joined,e.Target)
}
// EstimateCounterfactual combines two *retained* relations and training-only
// randomized action statistics. It is an estimate, NEVER a sound certificate.
func (m *Model) EstimateCounterfactual(a,b Relation,action uint8)(Counterfactual,error){
    if !m.spec.Composition||!m.spec.ActionValue||
       a.Object!=b.Subject||a.Subject==b.Object{return Counterfactual{},ErrInvalid}
    _,hasA:=m.Recall(a.Subject,a.Object,a.Predicate)
    _,hasB:=m.Recall(b.Subject,b.Object,b.Predicate)
    stats,hasAction:=m.action[action]
    if !hasA||!hasB||!hasAction||stats.Count==0{return Counterfactual{},ErrInvalid}
    var joint Features
    for i:=range joint{joint[i]=a.Features[i]*b.Features[i]}
    value:=dot(m.composition,joint)
    predicted:=0
    if value*stats.Total>0{predicted=1}
    if value*stats.Total<0{predicted= -1}
    return Counterfactual{EstimateSign:predicted,
       ActionValueNumerator:stats.Total,ActionValueDenominator:stats.Count,
       LearnedCompositionScore:value,Certified:false,
       ScientificEvidence:false},nil
}
func (m *Model) Snapshot()Snapshot{
    return Snapshot{Family:m.spec.Family,Stored:len(m.slots),
       TrainingUpdates:m.updates,ActionClasses:len(m.action),
       Parameters:m.spec.ParameterCap,
       ScientificAccepted:false,DispatchAuthorized:false,
       IndependentlyReplicated:false}
}
func (m *Model) CheckBounded()error{
    if len(m.slots)>m.spec.MemorySlots || len(m.action)>MaxActions ||
       m.updates>m.spec.MaxUpdates{return fmt.Errorf("%w:model",ErrBudget)}
    for _,w:=range [...][FeatureCount]int16{m.encoder,m.retention,m.composition}{
        for _,x:=range w{if x>MaxAbsWeight||x< -MaxAbsWeight{return ErrBudget}}
    }
    return nil
}
