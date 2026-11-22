package nativediscovery

import (
    "bytes"
    "encoding/json"
    "math"
    "reflect"
    "testing"
)

// The fully matched conventional portfolio, its negative controls, and actual
// selected-action consequences are independently recomputed from frozen source.
func TestF20FrozenNoisyInterventionsAndStrongestBaseline(t *testing.T) {
    v,err:=F20Development()
    if err!=nil {t.Fatal(err)}
    if F20Validate(v)!=nil {t.Fatal("F20 source report rejected")}
    prior,err:=F19Development()
    if err!=nil||F19Validate(prior)!=nil||prior.Classification!=F19NO_GO||
        v.ParentF19SHA256!=prior.DigestSHA256||!v.EarlierNegativesPreserved{
        t.Fatal("F19 and earlier negatives not preserved")
    }
    if v.Schema!=F20Schema||v.Seeds!=[2]uint32{113,127}||
        v.Schedules!=[2]string{"balanced","skewed"}||v.Actions!=18||
        v.Delay!=2||v.Milestones!=[4]int{4,7,10,14}||
        v.MaxScore!=32||v.MinStrongGain!=2||v.MinAblationGain!=3||
        len(v.Arms)!=4||!v.DevelopmentOnly||v.ScientificAccepted||
        v.OwnerEligible||v.DispatchAuthorized||v.ActiveResearchChanged||
        v.IndependentFirstUseConsumed||v.WholeProcessCostMeasured||
        v.AgentCalls!=0||v.PaidAPICalls!=0 {t.Fatal("preregistered source or authority drift")}
    passed,charged:=0,0
    for ai,a:=range v.Arms {
        if a.Seed!=v.Seeds[ai/2]||a.Schedule!=v.Schedules[ai%2]{
            t.Fatal("missing or reordered development arm")
        }
        best,bestName:=-1,""
        for pi,kind:=range f20Kinds(){
            p:=a.Policies[pi]
            again,e:=f20PolicyRun(a.Seed,a.Schedule,kind)
            if e!=nil||p.Name!=kind||!reflect.DeepEqual(p,again)||
                !p.ColdMatches||p.G1Credited!=8||p.G1Pending!=2||
                p.G2Credited!=16||p.G2Pending!=2||p.Delivered!=16||
                len(p.Actions)!=18||len(p.G1SnapshotSHA256)!=64||
                len(p.G2SnapshotSHA256)!=64||len(p.ObservationSHA256)!=64||
                p.Work<=0 {t.Fatalf("bad exact causal source %s: %v",kind,e)}
            sum:=0
            for _,s:=range p.Correct {
                if s<0||s>8 {t.Fatal("oracle probe score impossible")}
                sum+=s
            }
            if sum!=p.TotalCorrect||sum>32||p.Missing+p.Flipped>16{
                t.Fatal("scored consequence or noise accounting invalid")
            }
            for step,ch:=range p.Actions {
                cue,e:=f20Cue(a.Seed,a.Schedule,step)
                if e!=nil||ch!='0'&&ch!='1' {t.Fatal("invalid intervention")}
                if kind=="no-intervention"&&ch!='0'{t.Fatal("no-action ablation changed")}
                if kind=="cue-following"&&int(ch-'0')!=cue&1{
                    t.Fatal("passive conventional control changed")
                }
            }
            if pi>=1&&pi<=7&&p.TotalCorrect>best{
                best,bestName=p.TotalCorrect,kind
            }
            charged+=p.Work
        }
        noncue:=0
        for step,ch:=range a.Policies[0].Actions{
            cue,_:=f20Cue(a.Seed,a.Schedule,step)
            if int(ch-'0')!=cue&1{noncue++}
        }
        gain:=a.Policies[0].TotalCorrect-best
        noAction:=a.Policies[0].TotalCorrect-a.Policies[8].TotalCorrect
        wrong:=a.Policies[0].TotalCorrect-a.Policies[9].TotalCorrect
        success:=gain>=2&&noAction>=3&&wrong>=3&&noncue>=2&&best<32
        if a.StrongestScore!=best||a.StrongestName!=bestName||
            a.GainStrongest!=gain||a.GainNoIntervention!=noAction||
            a.GainWrongCredit!=wrong||a.NonCueActions!=noncue||a.Passes!=success{
            t.Fatal("strongest portfolio / ablations / frozen threshold altered")
        }
        if success {passed++}
        t.Logf("F20_DEV seed=%d schedule=%s candidate=%d strongest=%s/%d gain=%+d no_action=%+d wrong_credit=%+d noncue=%d pass=%v",
            a.Seed,a.Schedule,a.Policies[0].TotalCorrect,bestName,best,gain,noAction,wrong,noncue,success)
    }
    classification:=F20NoGo
    if passed==4 {classification=F20Signal}
    if v.PassingArms!=passed||v.Classification!=classification||
        v.TotalWork!=charged {t.Fatal("negative relabeled or model work omitted")}
    t.Logf("F20_FROZEN_DEV=%s passing=%d/4 work=%d science_unverified=true",classification,passed,charged)
}

// No policy API takes the true law, seed, future outcome or oracle correctness.
func TestF20NoFutureOraclePartialObservationAndColdEvidence(t *testing.T){
    for _,seed:=range []uint32{0,17,31,59,83,107,109,112,128}{
        if _,e:=f20Law(seed);e==nil{t.Fatal("unapproved or first-use world admitted")}
    }
    for _,schedule:=range []string{"","oracle","confounded"}{
        if _,e:=f20Cue(113,schedule,0);e==nil{t.Fatal("unapproved schedule admitted")}
    }
    for _,kind:=range []string{"","oracle","future-observations"}{
        if _,_,e:=f20Select(kind,nil,nil,0,0,0);e==nil{
            t.Fatal("unknown selector admitted")
        }
    }
    if _,_,e:=f20Select("pending-coverage",nil,nil,0,1,1);e==nil{
        t.Fatal("missing past actions admitted")
    }
    if _,_,e:=f20Select("pending-coverage",nil,nil,4,1,0);e==nil{
        t.Fatal("unknown context admitted")
    }
    if _,_,e:=f20Select("pending-coverage",nil,
        []f20Probe{{Step:0,Cue:0,Action:2}},0,1,1);e==nil{
        t.Fatal("invalid pending action admitted")
    }
    prior,w,e:=f20Posterior(nil,false)
    if e!=nil||w!=256 {t.Fatal("invalid uniform prior")}
    for _,weight:=range prior{
        if math.Abs(weight-1.0/256)>1e-12{t.Fatal("prior biased")}
    }
    erased,_,e:=f20Posterior([]f20Credit{
        {Step:0,Cue:0,Action:1,WrongAction:0,Value:-1},
    },false)
    if e!=nil||!reflect.DeepEqual(erased,prior){
        t.Fatal("erased feedback leaked information")
    }
    after,_,e:=f20Posterior([]f20Credit{
        {Step:0,Cue:0,Action:1,WrongAction:0,Value:1},
    },false)
    p,_:=f20PredProb(after,0,1)
    if e!=nil||math.Abs(p-0.875)>1e-10{
        t.Fatal("noisy 7:1 posterior update not calibrated")
    }
    for _,seed:=range f20Seeds(){for _,schedule:=range f20Schedules(){
        for _,kind:=range f20Kinds(){
            trace,raw,e:=f20Simulate(seed,schedule,kind,true)
            if e!=nil{t.Fatal(e)}
            cold,e:=f20Load(raw,trace.G2SnapshotSHA256)
            if e!=nil||cold.Seen!=18||len(cold.Credits)!=16||
                len(cold.Pending)!=2||cold.Pending[0].Step!=16||
                cold.Pending[1].Step!=17{
                t.Fatal("missing pending custody / invalid cold resume")
            }
            bad:=append([]byte(nil),raw...)
            bad[len(bad)-2]^=1
            if _,e:=f20Load(bad,trace.G2SnapshotSHA256);e==nil{
                t.Fatal("modified cold bytes accepted")
            }
            misses,flips:=0,0
            for i,c:=range cold.Credits{
                cue,e:=f20Cue(seed,schedule,i)
                prev:=0
                if i>0{prev=int(trace.Actions[i-1]-'0')}
                if e!=nil||c.Step!=i||c.Cue!=cue||
                    c.Action!=int(trace.Actions[i]-'0')||
                    c.WrongAction!=prev{
                    t.Fatal("wrong intervention or shifted credit")
                }
                value,missing,flip,e:=f20Outcome(seed,i,c.Cue,c.Action)
                if e!=nil||value!=c.Value{t.Fatal("future/counterfactual feedback used")}
                if missing{misses++};if flip{flips++}
            }
            if misses!=trace.Missing||flips!=trace.Flipped{
                t.Fatal("observed channel evidence miscounted")
            }
        }
    }}
}

// Even a forged and freshly rehashed report cannot promote first-use, owner,
// scientific acceptance, a false score, missing loser or altered threshold.
func TestF20RehashedForgeryAndAuthorityDenied(t *testing.T){
    good,e:=F20Development()
    if e!=nil{t.Fatal(e)}
    clone:=func()F20Report{
        b,e:=json.Marshal(good);if e!=nil{t.Fatal(e)}
        var x F20Report
        if json.Unmarshal(b,&x)!=nil{t.Fatal("copy failed")}
        return x
    }
    bad:=[]struct{name string;change func(*F20Report)}{
        {"parent",func(x *F20Report){x.ParentF19SHA256="forged"}},
        {"negative",func(x *F20Report){x.EarlierNegativesPreserved=false}},
        {"first-use-seed",func(x *F20Report){x.Seeds[0]=59}},
        {"schedule",func(x *F20Report){x.Schedules[0]="oracle"}},
        {"budget",func(x *F20Report){x.Actions=19}},
        {"delay",func(x *F20Report){x.Delay=0}},
        {"milestone",func(x *F20Report){x.Milestones[2]=9}},
        {"threshold",func(x *F20Report){x.MinStrongGain=0}},
        {"control",func(x *F20Report){x.Arms[0].Policies[1].Name="missing"}},
        {"score",func(x *F20Report){x.Arms[0].Policies[0].TotalCorrect=32}},
        {"omitted-loser",func(x *F20Report){x.Arms=x.Arms[:3]}},
        {"reordered",func(x *F20Report){x.Arms[0],x.Arms[1]=x.Arms[1],x.Arms[0]}},
        {"cold",func(x *F20Report){x.Arms[0].Policies[0].G1SnapshotSHA256="bad"}},
        {"pending",func(x *F20Report){x.Arms[0].Policies[0].G2Pending=0}},
        {"science",func(x *F20Report){x.ScientificAccepted=true}},
        {"first-use",func(x *F20Report){x.IndependentFirstUseConsumed=true}},
        {"owner",func(x *F20Report){x.OwnerEligible=true}},
        {"dispatch",func(x *F20Report){x.DispatchAuthorized=true}},
        {"active",func(x *F20Report){x.ActiveResearchChanged=true}},
        {"paid",func(x *F20Report){x.PaidAPICalls=1}},
        {"cost",func(x *F20Report){x.WholeProcessCostMeasured=true}},
    }
    for _,tc:=range bad{t.Run(tc.name,func(t *testing.T){
        x:=clone()
        tc.change(&x)
        x.DigestSHA256=f20Digest(x)
        if F20Validate(x)==nil{t.Fatal("rehashed false authority or evidence accepted")}
    })}
    packed,e:=json.Marshal(good)
    if e!=nil||bytes.Contains(packed,[]byte("\"scientific_accepted\":true")){
        t.Fatal("development evidence claimed independent science")
    }
}
