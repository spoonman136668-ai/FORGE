// Eureka F29: independent causal baseline/effect compositional transfer (synthetic DEV only).
package nativediscovery

import (
    "bytes"
    "encoding/json"
    "errors"
    "math"
    "reflect"
    "sync"
)
const (
    F29Schema = "forge.native-discovery.compositional-causal-transfer.dev.v1"
    F29NoGo = "F29_DEV_NO_GO"
    F29Signal = "F29_DEV_SIGNAL_UNVERIFIED"
    F29Parent = "7e822cd873848a4e9ac06274bf6e82ec8de937aa"
)
var errF29 = errors.New("FORGE_EUREKA_F29_SOURCE_OR_AUTHORITY_INVALID")

func f29Kinds() [8]string { return [8]string{"composed-causal-filter", "stationary-delta", "factorized-bayes", "switch-bayes", "markov-bayes", "online-softmax", "no-composition", "wrong-action-attribution"} }
func f29Worlds() [4]struct{ Seed uint32; Schedule string } {
    return [4]struct{ Seed uint32; Schedule string }{{271,"balanced"},{277,"skewed"},{281,"balanced"},{283,"skewed"}}
}
func f29Known(seed uint32) bool { for _, v := range f29Worlds(){ if v.Seed==seed {return true} }; return false }
func f29Cue(seed uint32, schedule string, t int) (int,error) {
    if !f29Known(seed)||t<0||t>=48 {return 0,errF29}
    switch schedule {
    case "balanced": return int(f27Mix(seed^uint32(t+1)*0x27d4eb2d)&3),nil
    case "skewed": if t%5==4 {return (t/5+int(seed%4))%4,nil}; return (t/5+int(seed%2))%2,nil
    }
    return 0,errF29
}
func f29Action(seed uint32,t int)(int,error){
    if !f29Known(seed)||t<0||t>=48{return 0,errF29}
    return int(f27Mix(seed^uint32(t+1)*0x165667b1)&1),nil
}
func f29Phase(seed uint32, t int)(byte,error){
    if !f29Known(seed)||t<0||t>=48{return 0,errF29}
    startA := seed==271||seed==281
    switch t/12 {
    case 0,2: if startA{return 'A',nil};return 'B',nil
    case 1: if startA{return 'B',nil};return 'A',nil
    case 3: if seed==271||seed==283{return 'C',nil};return 'D',nil
    }
    return 0,errF29
}
func f29Sensor(seed uint32,t,clean,sensor int)(int,error){
    if !f29Known(seed)||t<0||t>48||clean<0||clean>3||sensor<0||sensor>1{return 0,errF29}
    u:=f27Mix(seed^uint32(t+1)*0x9e3779b9^uint32(sensor+1)*0x85ebca6b^0x6a09e667)%100
    if sensor==0 {if u<90{return clean,nil};if u<96{return (clean+1)%4,nil};return (clean+3)%4,nil}
    if u<80{return clean,nil};if u<90{return (clean+1)%4,nil};return (clean+3)%4,nil
}
type f29World struct { Seed uint32; Schedule string; S,Offset,Seen int; Sensors [2]int }
func f29NewWorld(seed uint32,schedule string)(f29World,error){
    if _,e:=f29Cue(seed,schedule,0);e!=nil{return f29World{},e}
    w:=f29World{Seed:seed,Schedule:schedule,S:int(f27Mix(seed^0x4cf5ad43)&3),Offset:int(f27Mix(seed^0x6d2b79f5)&3)}
    for i:=0;i<2;i++ {v,e:=f29Sensor(seed,0,(w.S+w.Offset)%4,i);if e!=nil{return f29World{},e};w.Sensors[i]=v}
    return w,nil
}
// The hidden physical law is used only by the simulator and scorer, never by model functions.
func (w *f29World) step(t,c,a int)(int,[2]int,error){
    if t!=w.Seen||c<0||c>3||a<0||a>1{return 0,[2]int{},errF29}
    law,e:=f29Phase(w.Seed,t);if e!=nil{return 0,[2]int{},e}
    base,effect,e:=f28Law(law,c);if e!=nil{return 0,[2]int{},e}
    w.S=(w.S+base+a*effect)%4;w.Seen++
    actual:=(w.S+w.Offset)%4
    var next [2]int
    for i:=0;i<2;i++{v,e:=f29Sensor(w.Seed,w.Seen,actual,i);if e!=nil{return 0,[2]int{},e};next[i]=v}
    w.Sensors=next
    return actual,next,nil
}
// Two source archives encode causal factors independently of the online state.
type f29Model struct{
    Mode string `json:"mode"`
    A [4][2][4]float64 `json:"archive_a"`
    B [4][2][4]float64 `json:"archive_b"`
    W [4][4]float64 `json:"pair_weights"`
    Belief [4]float64 `json:"state_belief"`
    Prev [2]int `json:"previous_observation"`
    HasWorld bool `json:"has_world"`
    TrainingSeen int `json:"training_seen"`
    TransferSeen int `json:"transfer_seen"`
    Work int `json:"work"`
}
func f29Candidate(kind string)(f29Model,error){
    if kind!="composed-causal-filter"&&kind!="no-composition"&&kind!="wrong-action-attribution" {return f29Model{},errF29}
    // Exactly the same 128 real original A/B transitions as the independently trained controls.
    trained,e:=f28Train("factorized-bayes");if e!=nil||trained.TrainingSeen!=128{return f29Model{},errF29}
    return f29Model{Mode:kind,A:trained.A,B:trained.B,TrainingSeen:128},nil
}
func (m *f29Model) beginWorld(obs [2]int)error{
    p,e:=f27Posterior(obs);if e!=nil{return errF29}
    m.Belief=p;m.Prev=obs;m.HasWorld=true;m.TransferSeen=0
    for c:=0;c<4;c++ {if m.Mode=="no-composition"{m.W[c]=[4]float64{.5,0,0,.5}}else{m.W[c]=[4]float64{.25,.25,.25,.25}}}
    return nil
}
func f29Banks(m f29Model,c int)([4][4]float64,error){
    var pairs [4][4]float64
    if c<0||c>3{return pairs,errF29}
    qa0:=f28DeltaProb(m.A,c,0);qa1:=f28DeltaProb(m.A,c,1)
    qb0:=f28DeltaProb(m.B,c,0);qb1:=f28DeltaProb(m.B,c,1)
    bases:=[2][4]float64{qa0,qb0}
    // Effect posterior is the modular difference of the observed action1 and action0 posteriors.
    var effects [2][4]float64
    for i,act:=range [2][4]float64{qa1,qb1} {
        for d1:=0;d1<4;d1++ {for d0:=0;d0<4;d0++ {
            effects[i][(d1-d0+4)%4]+=act[d1]*bases[i][d0]
        }}
    }
    for bi:=0;bi<2;bi++{for ei:=0;ei<2;ei++{
        k:=bi*2+ei
        for d0:=0;d0<4;d0++ {for e:=0;e<4;e++{ pairs[k][(d0+e)%4]+=bases[bi][d0]*effects[ei][e] }}
    }}
    return pairs,nil
}
func (m *f29Model) delta(c,a int)([4]float64,error){
    var out [4]float64
    if !m.HasWorld||c<0||c>3||a<0||a>1{return out,errF29}
    if a==0{
        pa:=f28DeltaProb(m.A,c,0);pb:=f28DeltaProb(m.B,c,0)
        for d:=0;d<4;d++{out[d]=(m.W[c][0]+m.W[c][1])*pa[d]+(m.W[c][2]+m.W[c][3])*pb[d]}
        return out,nil
    }
    pairs,e:=f29Banks(*m,c);if e!=nil{return out,e}
    for k:=0;k<4;k++{for d:=0;d<4;d++{out[d]+=m.W[c][k]*pairs[k][d]}}
    return out,nil
}
func (m *f29Model) forecast(c,a int)([4]float64,error){
    var out [4]float64
    q,e:=m.delta(c,a);if e!=nil{return out,e}
    for s:=0;s<4;s++{for d:=0;d<4;d++{out[(s+d)%4]+=m.Belief[s]*q[d]}}
    m.Work+=96
    return out,nil
}
func (m *f29Model) observe(c,a int,next [2]int)error{
    if !m.HasWorld||c<0||c>3||a<0||a>1{return errF29}
    obs,e:=f27Posterior(next);if e!=nil{return errF29};_ = obs
    q,e:=m.delta(c,a);if e!=nil{return e}
    // Joint hidden-state transition filtering using actual action, not scorer truth.
    var posterior [4]float64
    z:=0.0
    for s:=0;s<4;s++{for d:=0;d<4;d++{
        at:=(s+d)%4;mass:=m.Belief[s]*q[d]*f27Likelihood(next,at)
        posterior[at]+=mass;z+=mass
    }}
    if z<=0{return errF29}
    for i:=range posterior{posterior[i]/=z}
    evidence,e:=f28ObservedDelta(m.Prev,next);if e!=nil{return e}
    creditedAction:=a
    if m.Mode=="wrong-action-attribution"{creditedAction=1-a}
    // Per-cue Bayesian bank-pair hypothesis update, with fixed 0.02 hazard.
    var weight [4]float64
    zp:=0.0
    var pairL [4][4]float64
    if creditedAction==1{pairL,e=f29Banks(*m,c);if e!=nil{return e}}
    for k:=0;k<4;k++ {
        var likelihood float64
        if creditedAction==0{
            if k<2 {likelihood=f28Agreement(evidence,f28DeltaProb(m.A,c,0))} else {likelihood=f28Agreement(evidence,f28DeltaProb(m.B,c,0))}
        }else{likelihood=f28Agreement(evidence,pairL[k])}
        prior:=m.W[c][k]
        if m.Mode=="no-composition"{
            if k==1||k==2{weight[k]=0;continue}
            prior=.98*prior+.02/2
        } else {prior=.98*prior+.02/4}
        weight[k]=prior*likelihood;zp+=weight[k]
    }
    if zp<=0{return errF29}
    for k:=range weight{weight[k]/=zp}
    m.W[c]=weight;m.Belief=posterior;m.Prev=next;m.TransferSeen++;m.Work+=224
    return nil
}
func f29Valid(m f29Model)bool{
    if m.Mode!="composed-causal-filter"&&m.Mode!="no-composition"&&m.Mode!="wrong-action-attribution"{return false}
    if m.TrainingSeen!=128||m.TransferSeen<0||m.TransferSeen>48||m.Work<0{return false}
    for _,v:=range m.Prev{if v<0||v>3{return false}}
    if m.HasWorld {
        total:=0.0
        for _,v:=range m.Belief{if math.IsNaN(v)||math.IsInf(v,0)||v<0||v>1{return false};total+=v}
        if math.Abs(total-1)>1e-7{return false}
        for c:=0;c<4;c++{sum:=0.0;for k,x:=range m.W[c] {
            if math.IsNaN(x)||math.IsInf(x,0)||x<0||x>1{return false}
            if m.Mode=="no-composition"&&(k==1||k==2)&&x!=0{return false}
            sum+=x
        };if math.Abs(sum-1)>1e-7{return false}}
    }
    return true
}
func f29Save(m f29Model)([]byte,error){
    if !f29Valid(m){return nil,errF29};return json.Marshal(m)
}
func f29Load(raw []byte)(f29Model,error){
    var m f29Model
    if json.Unmarshal(raw,&m)!=nil||!f29Valid(m){return f29Model{},errF29}
    canon,_:=json.Marshal(m);if !bytes.Equal(canon,raw){return f29Model{},errF29}
    return m,nil
}
type F29Trial struct{
    Kind string `json:"kind"`
    NLL float64 `json:"mean_nll"`
    Accuracy int `json:"accuracy"`
    PhaseAccuracy [4]int `json:"phase_accuracy"`
    TrainingSeen,TransferSeen,Work,Parameters int
    ActionsSHA256,SensorsSHA256,PredictionsSHA256,CheckpointSHA256,TerminalSHA256 string
    ColdMatches bool `json:"cold_matches"`
}
func f29Trial(kind string,seed uint32,sched string,cold bool)(F29Trial,[]byte,error){
    if !f29Known(seed){return F29Trial{},nil,errF29}
    isCandidate:=kind=="composed-causal-filter"||kind=="no-composition"||kind=="wrong-action-attribution"
    var cm f29Model;var base f28Model;var e error;var ck []byte
    if isCandidate{cm,e=f29Candidate(kind);if e!=nil{return F29Trial{},nil,e};ck,e=f29Save(cm);if e!=nil{return F29Trial{},nil,e};if cold {cm,e=f29Load(ck);if e!=nil{return F29Trial{},nil,e}}} else {base,e=f28Train(kind);if e!=nil{return F29Trial{},nil,e};ck,e=f28Save(base);if e!=nil{return F29Trial{},nil,e};if cold {base,e=f28Load(ck);if e!=nil{return F29Trial{},nil,e}}}
    world,e:=f29NewWorld(seed,sched);if e!=nil{return F29Trial{},nil,e}
    if isCandidate{e=cm.beginWorld(world.Sensors)}else{e=base.beginWorld(world.Sensors)}
    if e!=nil{return F29Trial{},nil,e}
    startWork:=0;if isCandidate{startWork=cm.Work}else{startWork=base.Work;if f28BaseMode(kind)!=""{startWork=base.Base.Work}}
    tr:=F29Trial{Kind:kind,TrainingSeen:128,CheckpointSHA256:f27Hash(ck),ColdMatches:true}
    var acts []int;var sensors [][2]int;var preds [][4]float64
    sensors=append(sensors,world.Sensors)
    loss:=0.0
    for t:=0;t<48;t++ {
        cue,e:=f29Cue(seed,sched,t);if e!=nil{return F29Trial{},nil,e}
        action,e:=f29Action(seed,t);if e!=nil{return F29Trial{},nil,e}
        var p [4]float64
        if isCandidate{p,e=cm.forecast(cue,action)}else{p,e=base.forecast(cue,action)}
        if e!=nil{return F29Trial{},nil,e}
        predicted:=f27ArgMax(p)
        actual,next,e:=world.step(t,cue,action);if e!=nil{return F29Trial{},nil,e}
        if predicted==actual{tr.Accuracy++;tr.PhaseAccuracy[t/12]++}
        loss-=math.Log(math.Max(p[actual],1e-9))
        acts=append(acts,action);sensors=append(sensors,next);preds=append(preds,p)
        if isCandidate{e=cm.observe(cue,action,next)}else{e=base.observe(cue,action,next,false)}
        if e!=nil{return F29Trial{},nil,e}
    }
    tr.NLL=loss/48;tr.TransferSeen=48
    var terminal []byte
    if isCandidate{
        terminal,e=f29Save(cm);tr.Work=cm.Work-startWork;tr.Parameters=2*4*2*4+4*4+4
    }else{
        terminal,e=f28Save(base);tr.Work=base.Work-startWork;tr.Parameters=f28ParameterCount(kind)
        if f28BaseMode(kind)!=""{tr.Work=base.Base.Work-startWork}
    }
    if e!=nil{return F29Trial{},nil,e}
    b,_:=json.Marshal(acts);tr.ActionsSHA256=f27Hash(b)
    b,_=json.Marshal(sensors);tr.SensorsSHA256=f27Hash(b)
    b,_=json.Marshal(preds);tr.PredictionsSHA256=f27Hash(b)
    tr.TerminalSHA256=f27Hash(terminal)
    return tr,terminal,nil
}
type F29Arm struct{
    Seed uint32 `json:"seed"`
    Schedule string `json:"schedule"`
    Trials [8]F29Trial `json:"trials"`
    BestConventionalNLL,GainNLL,GainNoComposition,GainWrongAction float64
    BestConventionalReturn,BestConventionalNovel int
    Passes bool `json:"passes"`
}
type F29Report struct{
    Schema,Parent,Classification string
    TrainingWorlds [2]uint32
    TransferWorlds [4]uint32
    TrainSteps,TransferSteps int
    MinGain,MinAblationGain float64
    MinNovelGain int
    Arms [4]F29Arm
    Passing int
    DevelopmentOnly,EarlierNegativesPreserved bool
    FirstUseConsumed,ScientificAccepted,OwnerEligible,DispatchAuthorized,MatchedComputeProven,WholeProcessCostProven bool
    DigestSHA256 string
}
func f29Digest(r F29Report)string{r.DigestSHA256="";b,_:=json.Marshal(r);return f27Hash(b)}
func f29Calculate()(F29Report,error){
    r:=F29Report{Schema:F29Schema,Parent:F29Parent,TrainingWorlds:[2]uint32{241,243},TransferWorlds:[4]uint32{271,277,281,283},TrainSteps:128,TransferSteps:48,MinGain:.05,MinAblationGain:.10,MinNovelGain:1,DevelopmentOnly:true,EarlierNegativesPreserved:true}
    for i,w:=range f29Worlds(){
        arm:=F29Arm{Seed:w.Seed,Schedule:w.Schedule}
        for j,kind:=range f29Kinds(){
            cold,cb,e:=f29Trial(kind,w.Seed,w.Schedule,true);if e!=nil{return F29Report{},e}
            warm,wb,e:=f29Trial(kind,w.Seed,w.Schedule,false)
            if e!=nil||!reflect.DeepEqual(cold,warm)||!bytes.Equal(cb,wb){return F29Report{},errF29}
            arm.Trials[j]=cold
        }
        best:=math.Inf(1)
        refAct,refSensor:=arm.Trials[0].ActionsSHA256,arm.Trials[0].SensorsSHA256
        for j,tr:=range arm.Trials{
            if tr.TrainingSeen!=128||tr.TransferSeen!=48||tr.ActionsSHA256!=refAct||tr.SensorsSHA256!=refSensor||tr.Accuracy<0||tr.Accuracy>48||math.IsNaN(tr.NLL){return F29Report{},errF29}
            if j>=1&&j<=5 {
                if tr.NLL<best{best=tr.NLL}
                if tr.PhaseAccuracy[2]>arm.BestConventionalReturn{arm.BestConventionalReturn=tr.PhaseAccuracy[2]}
                if tr.PhaseAccuracy[3]>arm.BestConventionalNovel{arm.BestConventionalNovel=tr.PhaseAccuracy[3]}
            }
        }
        arm.BestConventionalNLL=best
        arm.GainNLL=best-arm.Trials[0].NLL
        arm.GainNoComposition=arm.Trials[6].NLL-arm.Trials[0].NLL
        arm.GainWrongAction=arm.Trials[7].NLL-arm.Trials[0].NLL
        arm.Passes=arm.GainNLL>=.05 && arm.Trials[0].PhaseAccuracy[3]>=arm.BestConventionalNovel+1 && arm.Trials[0].PhaseAccuracy[2]>=arm.BestConventionalReturn && arm.GainNoComposition>=.10 && arm.GainWrongAction>=.10
        if arm.Passes{r.Passing++}
        r.Arms[i]=arm
    }
    r.Classification=F29NoGo;if r.Passing==4{r.Classification=F29Signal}
    r.DigestSHA256=f29Digest(r)
    return r,nil
}
// This exact-source frozen development has no runtime inputs. Cache only immutable value data.
var f29Once sync.Once
var f29Cached F29Report
var f29CacheErr error
func F29Development()(F29Report,error){
    f29Once.Do(func(){f29Cached,f29CacheErr=f29Calculate()})
    return f29Cached,f29CacheErr
}
func F29Validate(r F29Report)error{
    if r.DigestSHA256==""||r.DigestSHA256!=f29Digest(r)||!r.DevelopmentOnly||!r.EarlierNegativesPreserved||r.FirstUseConsumed||r.ScientificAccepted||r.OwnerEligible||r.DispatchAuthorized||r.MatchedComputeProven||r.WholeProcessCostProven{return errF29}
    expected,e:=F29Development();if e!=nil||!reflect.DeepEqual(expected,r){return errF29};return nil
}
