package nativediscovery

import (
    "fmt"
    "math"
    "testing"
)

// Reconstruct only the actually delivered F20 Bayesian-risk trajectory.
func f21Fixture(seed uint32, schedule string, stop int) ([]f20Credit, []f20Probe, int, int, error) {
    trace,err:=f20PolicyRun(seed,schedule,"bayes-risk")
    if err!=nil||stop<0||stop>=F20Actions{return nil,nil,0,0,errF21}
    credits:=make([]f20Credit,0,F20Actions)
    pending:=make([]f20Probe,0,2)
    for t:=0;t<=stop;t++ {
        if t>=2 {
            due:=pending[0]
            v,_,_,e:=f20Outcome(seed,due.Step,due.Cue,due.Action)
            if e!=nil {return nil,nil,0,0,errF21}
            credits=append(credits,f20Credit{Step:due.Step,Cue:due.Cue,
                Action:due.Action,WrongAction:due.WrongAction,Value:v})
            pending=pending[1:]
        }
        if t==stop {
            cue,e:=f20Cue(seed,schedule,t)
            if e!=nil{return nil,nil,0,0,errF21}
            next,e:=f20Cue(seed,schedule,t+1)
            if e!=nil{return nil,nil,0,0,errF21}
            return credits,pending,cue,next,nil
        }
        cue,e:=f20Cue(seed,schedule,t)
        if e!=nil {return nil,nil,0,0,errF21}
        prev:=0
        if t>0 {prev=int(trace.Actions[t-1]-'0')}
        pending=append(pending,f20Probe{Step:t,Cue:cue,Action:int(trace.Actions[t]-'0'),WrongAction:prev})
    }
    return nil,nil,0,0,errF21
}

func TestF21ExactPosteriorRiskAndSeventyTwoDecisions(t *testing.T) {
    prev,e:=F20Development()
    if e!=nil||F20Validate(prev)!=nil||prev.Classification!=F20NoGo||prev.PassingArms!=0||
        prev.ScientificAccepted||prev.OwnerEligible||prev.DispatchAuthorized {
        t.Fatal("frozen negative parent changed")
    }
    decisions,probes,risks:=0,0,0
    for _,seed:=range f20Seeds(){for _,schedule:=range f20Schedules(){
        trace,e:=f20PolicyRun(seed,schedule,"bayes-risk")
        if e!=nil||!trace.ColdMatches||len(trace.Actions)!=F20Actions{t.Fatal("invalid original replay")}
        for step:=0;step<F20Actions;step++ {
            credits,pending,cue,next,e:=f21Fixture(seed,schedule,step)
            if e!=nil||len(credits)!=max(0,step-1)||len(pending)!=min(step,1){t.Fatal("wrong delayed credits")}
            full,_,e:=f20Posterior(credits,false)
            if e!=nil{t.Fatal(e)}
            fact,_,e:=f21Posterior(credits)
            if e!=nil{t.Fatal(e)}
            for c:=0;c<4;c++ {
                normalization:=0.0
                for _,x:=range fact[c]{normalization+=x}
                if math.Abs(normalization-1)>1e-12 {t.Fatal("factor not normalized")}
                for a:=0;a<2;a++ {
                    expected,_:=f20PredProb(full,c,a)
                    actual,_,e:=f21Probe(fact,c,a)
                    if e!=nil||math.Abs(expected-actual)>1e-10 {t.Fatalf("posterior mismatch seed=%d schedule=%s step=%d cue=%d action=%d full=%.16g fact=%.16g",seed,schedule,step,c,a,expected,actual)}
                    probes++
                }
            }
            for action:=0;action<2;action++ {
                expected,_:=f20ExpectedRisk(full,cue,action)
                actual,_,e:=f21Risk(fact,cue,action)
                if e!=nil||math.Abs(expected-actual)>1e-10 {t.Fatalf("risk mismatch seed=%d schedule=%s step=%d action=%d full=%.16g fact=%.16g",seed,schedule,step,action,expected,actual)}
                risks++
            }
            old,_,e:=f20Select("bayes-risk",credits,pending,cue,next,step)
            if e!=nil {t.Fatal(e)}
            newChoice,_,e:=f21Select(credits,cue)
            if e!=nil||old!=newChoice||newChoice!=int(trace.Actions[step]-'0') {
                t.Fatalf("changed real intervention seed=%d schedule=%s step=%d old=%d factor=%d expected=%c",seed,schedule,step,old,newChoice,trace.Actions[step])
            }
            decisions++
        }
    }}
    if decisions!=72||probes!=576||risks!=144{t.Fatal("missing comparison")}
    t.Logf("F21_EXACT_PARITY=PASS decisions=%d posterior_probes=%d risk_comparisons=%d; science_unverified=true",decisions,probes,risks)
}

func TestF21NegativeInvalidAndMissingNeutral(t *testing.T) {
    prior,_,e:=f21Posterior(nil)
    if e!=nil {t.Fatal(e)}
    for cue:=0;cue<4;cue++ {for pair:=0;pair<4;pair++ {
        if prior[cue][pair]!=.25 {t.Fatal("non-uniform prior")}
    }}
    missing,_,e:=f21Posterior([]f20Credit{{Step:0,Cue:1,Action:1,Value:-1}})
    if e!=nil||missing!=prior {t.Fatal("erasure gave illicit information")}
    after,_,e:=f21Posterior([]f20Credit{{Step:0,Cue:2,Action:1,Value:1}})
    if e!=nil{t.Fatal(e)}
    p,_,e:=f21Probe(after,2,1)
    if e!=nil||math.Abs(p-.875)>1e-12 {t.Fatal("incorrect 7:1 noisy response calibration")}
    for _,credits:=range [][]f20Credit{
        {{Step:1,Cue:1,Action:0,Value:1}},
        {{Step:0,Cue:5,Action:0,Value:1}},
        {{Step:0,Cue:1,Action:2,Value:0}},
        {{Step:0,Cue:1,Action:0,Value:2}},
        {{Step:0,Cue:1,Action:0,WrongAction:-1,Value:0}},
    } {
        if _,_,e:=f21Posterior(credits);e==nil {t.Fatal("forged action/credit admitted")}
        if _,_,e:=f21Select(credits,0);e==nil {t.Fatal("forged selector admitted")}
    }
    if _,_,e:=f21Select(nil,-1);e==nil{t.Fatal("invalid cue")}
    if _,_,e:=f21Select(nil,4);e==nil{t.Fatal("future/invalid cue")}
    if _,_,e:=f21Probe(prior,0,2);e==nil{t.Fatal("unavailable action")}
    if _,_,e:=f21Risk(prior,4,0);e==nil{t.Fatal("unavailable risk cue")}
}

var f21BenchSink int
func benchmarkF21(b *testing.B, factorized bool) {
    for _,seed:=range f20Seeds(){for _,schedule:=range f20Schedules(){
        b.Run(fmt.Sprintf("seed%d/%s",seed,schedule),func(b *testing.B){
            credits,pending,cue,next,e:=f21Fixture(seed,schedule,14)
            if e!=nil {b.Fatal(e)}
            b.ReportAllocs()
            b.ResetTimer()
            result:=0
            for i:=0;i<b.N;i++ {
                var choice int
                if factorized {choice,_,e=f21Select(credits,cue)} else {
                    choice,_,e=f20Select("bayes-risk",credits,pending,cue,next,14)
                }
                if e!=nil {b.Fatal(e)}
                result+=choice
            }
            f21BenchSink=result
        })
    }}
}
func BenchmarkF21OriginalExhaustive(b *testing.B){benchmarkF21(b,false)}
func BenchmarkF21ExactFactorized(b *testing.B){benchmarkF21(b,true)}
