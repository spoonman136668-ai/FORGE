package nativediscovery

import (
    "bytes"
    "encoding/json"
    "math"
    "reflect"
    "testing"
)
func TestF29FrozenFourArmDevelopment(t *testing.T){
    r,e:=F29Development()
    if e!=nil||F29Validate(r)!=nil{t.Fatal("F29 frozen development invalid",e)}
    if r.Schema!=F29Schema||r.Parent!=F29Parent||r.TrainingWorlds!=[2]uint32{241,243}||
        r.TransferWorlds!=[4]uint32{271,277,281,283}||r.TrainSteps!=128||r.TransferSteps!=48||
        r.MinGain!=.05||r.MinAblationGain!=.10||r.MinNovelGain!=1||!r.DevelopmentOnly||
        !r.EarlierNegativesPreserved||r.FirstUseConsumed||r.ScientificAccepted||r.OwnerEligible||
        r.DispatchAuthorized||r.MatchedComputeProven||r.WholeProcessCostProven{
        t.Fatal("frozen threshold or authority drift")
    }
    passing:=0
    for i,a:=range r.Arms{
        if a.Seed!=r.TransferWorlds[i]||a.Schedule!=f29Worlds()[i].Schedule{t.Fatal("arm identity")}
        strongest:=math.Inf(1);bestReturn,bestNovel:=0,0
        for j,tr:=range a.Trials{
            if tr.Kind!=f29Kinds()[j]||tr.TrainingSeen!=128||tr.TransferSeen!=48||tr.Work<=0||
                tr.Accuracy<0||tr.Accuracy>48||math.IsNaN(tr.NLL)||math.IsInf(tr.NLL,0)||tr.NLL<0||
                tr.Parameters<=0||len(tr.CheckpointSHA256)!=64||len(tr.TerminalSHA256)!=64||
                len(tr.ActionsSHA256)!=64||len(tr.SensorsSHA256)!=64||len(tr.PredictionsSHA256)!=64||
                !tr.ColdMatches{t.Fatalf("trial custody world=%d model=%s",i,tr.Kind)}
            score:=0;for _,n:=range tr.PhaseAccuracy{if n<0||n>12{t.Fatal("phase score invalid")};score+=n}
            if score!=tr.Accuracy{t.Fatal("phase totals")}
            if tr.ActionsSHA256!=a.Trials[0].ActionsSHA256||tr.SensorsSHA256!=a.Trials[0].SensorsSHA256{
                t.Fatal("unequal action or observation exposure")
            }
            if j>=1&&j<=5{
                if tr.NLL<strongest{strongest=tr.NLL}
                if tr.PhaseAccuracy[2]>bestReturn{bestReturn=tr.PhaseAccuracy[2]}
                if tr.PhaseAccuracy[3]>bestNovel{bestNovel=tr.PhaseAccuracy[3]}
            }
        }
        valid:=strongest-a.Trials[0].NLL>=.05&&
            a.Trials[0].PhaseAccuracy[3]>=bestNovel+1&&
            a.Trials[0].PhaseAccuracy[2]>=bestReturn&&
            a.Trials[6].NLL-a.Trials[0].NLL>=.10&&
            a.Trials[7].NLL-a.Trials[0].NLL>=.10
        if valid!=a.Passes||math.Abs(strongest-a.BestConventionalNLL)>1e-9{t.Fatal("incorrect classification")}
        if valid{passing++}
        t.Logf("F29_DEV seed=%d %s candidate_nll=%.6f best_nll=%.6f gain=%+.6f return=%d/%d novel=%d/%d no_comp=%.6f wrong_action=%.6f pass=%v",
            a.Seed,a.Schedule,a.Trials[0].NLL,strongest,a.GainNLL,a.Trials[0].PhaseAccuracy[2],bestReturn,a.Trials[0].PhaseAccuracy[3],bestNovel,a.GainNoComposition,a.GainWrongAction,valid)
    }
    class:=F29NoGo;if passing==4{class=F29Signal}
    if r.Passing!=passing||r.Classification!=class{t.Fatal("frozen result relabeled")}
    t.Logf("F29_FROZEN_DEV=%s passing=%d/4 first_use=false science=false",class,passing)
}
func TestF29CausalCompositionHasCrossBankSupport(t *testing.T){
    m,e:=f29Candidate("composed-causal-filter");if e!=nil{t.Fatal(e)}
    for c:=0;c<4;c++{
        p,e:=f29Banks(m,c);if e!=nil{t.Fatal(e)}
        for k:=0;k<4;k++{
            sum:=0.0
            for _,v:=range p[k]{if v<0||v>1||math.IsNaN(v){t.Fatal("invalid causal probability")};sum+=v}
            if math.Abs(sum-1)>1e-8{t.Fatal("improper causal convolution")}
        }
    }
    if _,e=f29Banks(m,4);e==nil{t.Fatal("invalid cue accepted")}
    for _,s:=range []uint32{271,277,281,283}{
        w,e:=f29NewWorld(s,"balanced");if e!=nil{t.Fatal(e)}
        for step:=0;step<48;step++{
            cue,e:=f29Cue(s,"balanced",step);if e!=nil{t.Fatal(e)}
            a,e:=f29Action(s,step);if e!=nil{t.Fatal(e)}
            law,e:=f29Phase(s,step);if e!=nil{t.Fatal(e)}
            base,effect,e:=f28Law(law,cue);if e!=nil{t.Fatal(e)}
            before:=w.S;actual,_,e:=w.step(step,cue,a);if e!=nil{t.Fatal(e)}
            if w.S!=(before+base+a*effect)%4||actual!=(w.S+w.Offset)%4{t.Fatal("fake or nonpersistent transition")}
        }
    }
}
func TestF29NoHiddenLawFirstUseOrFuture(t *testing.T){
    for _,seed:=range []uint32{0,59,83,211,223,241,243,251,257,263,269,270,272,276,278,280,282,284}{
        if _,e:=f29NewWorld(seed,"balanced");e==nil{t.Fatal("unknown world admitted")}
        if _,e:=f29Cue(seed,"balanced",0);e==nil{t.Fatal("unknown cue admitted")}
        if _,e:=f29Phase(seed,0);e==nil{t.Fatal("unknown phase admitted")}
        if _,e:=f29Sensor(seed,0,0,0);e==nil{t.Fatal("unknown sensor admitted")}
    }
    for _,bad:=range []string{"oracle","", "hidden-law","replay"}{
        if _,e:=f29Candidate(bad);e==nil{t.Fatal("unauthorized model admitted")}
    }
    if _,e:=f29Cue(271,"balanced",48);e==nil{t.Fatal("future step")}
    if _,e:=f29Action(271,-1);e==nil{t.Fatal("negative step")}
    if _,e:=f29Sensor(271,0,4,0);e==nil{t.Fatal("invalid state")}
    if _,e:=f29Cue(271,"unknown",0);e==nil{t.Fatal("unknown schedule")}
}
func TestF29ColdRetentionAndNegativeAblations(t *testing.T){
    for _,seed:=range f29Worlds(){
        for _,kind:=range f29Kinds(){
            c,cb,e:=f29Trial(kind,seed.Seed,seed.Schedule,true)
            w,wb,e2:=f29Trial(kind,seed.Seed,seed.Schedule,false)
            if e!=nil||e2!=nil||!reflect.DeepEqual(c,w)||!bytes.Equal(cb,wb){
                t.Fatal("warm/cold mismatch",seed.Seed,kind,e,e2)
            }
        }
    }
    m,e:=f29Candidate("composed-causal-filter");if e!=nil{t.Fatal(e)}
    raw,e:=f29Save(m);if e!=nil{t.Fatal(e)}
    loaded,e:=f29Load(raw);if e!=nil||!reflect.DeepEqual(m,loaded){t.Fatal("learned banks lost on cold restore")}
    wrong:=append([]byte(" "),raw...)
    if _,e:=f29Load(wrong);e==nil{t.Fatal("noncanonical checkpoint admitted")}
    broken:=append([]byte(nil),raw...);broken[0]='['
    if _,e:=f29Load(broken);e==nil{t.Fatal("tampered checkpoint admitted")}
}
func TestF29NoScientificFlagOrEvidenceRehash(t *testing.T){
    orig,e:=F29Development();if e!=nil{t.Fatal(e)}
    cases:=[]struct{name string;change func(*F29Report)}{
        {"science",func(r *F29Report){r.ScientificAccepted=true}},
        {"firstuse",func(r *F29Report){r.FirstUseConsumed=true}},
        {"owner",func(r *F29Report){r.OwnerEligible=true}},
        {"dispatch",func(r *F29Report){r.DispatchAuthorized=true}},
        {"compute",func(r *F29Report){r.MatchedComputeProven=true}},
        {"cost",func(r *F29Report){r.WholeProcessCostProven=true}},
        {"seeds",func(r *F29Report){r.TransferWorlds[0]=59}},
        {"threshold",func(r *F29Report){r.MinGain=0}},
        {"baseline",func(r *F29Report){r.Arms[0].Trials[1].NLL=999}},
        {"candidate",func(r *F29Report){r.Arms[0].Trials[0].NLL=0}},
        {"negative",func(r *F29Report){r.EarlierNegativesPreserved=false}},
        {"relabel",func(r *F29Report){r.Classification=F29Signal}},
    }
    for _,tc:=range cases{
        t.Run(tc.name,func(t *testing.T){
            buf,_:=json.Marshal(orig);var copy F29Report
            if json.Unmarshal(buf,&copy)!=nil{t.Fatal("copy")}
            tc.change(&copy);copy.DigestSHA256=f29Digest(copy)
            if F29Validate(copy)==nil{t.Fatal("false scientific or custody claim admitted")}
        })
    }
}
