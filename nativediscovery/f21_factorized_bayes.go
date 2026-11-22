// Eureka F21: exact four-factor alternative to F20 exhaustive Bayesian probing.
// Engineering DEV only. The equal-information 256-rule model and F20 are unchanged.
package nativediscovery

import (
    "errors"
    "math"
)

const F21Schema = "forge.native-discovery.factorized-bayes.dev.v1"
var errF21 = errors.New("FORGE_EUREKA_F21_SOURCE_OR_AUTHORITY_INVALID")

type f21Factors [4][4]float64

// Rule-mask bits c and c+4 encode independent two-bit response factors
// for cue c. The representation is exactly equivalent to F20's 256 masks.
func f21BitResponse(pair, action int) int {
    return (pair & 1) ^ (action & ((pair >> 1) & 1))
}

func f21Posterior(credits []f20Credit) (f21Factors, int, error) {
    var factors f21Factors
    if len(credits) > F20Actions-2 { return factors,0,errF21 }
    for cue := range factors { for pair := range factors[cue] { factors[cue][pair] = .25 } }
    work:=16
    for step, rec := range credits {
        if rec.Step!=step || rec.Cue<0 || rec.Cue>3 || rec.Action<0 || rec.Action>1 ||
            rec.WrongAction<0 || rec.WrongAction>1 || rec.Value< -1 || rec.Value>1 {
            return f21Factors{},0,errF21
        }
        if rec.Value == -1 { continue }
        mass:=0.0
        for pair := 0; pair<4; pair++ {
            if f21BitResponse(pair,rec.Action) == rec.Value {factors[rec.Cue][pair] *= 7}
            mass+=factors[rec.Cue][pair]
            work++
        }
        if mass<=0 || math.IsNaN(mass)||math.IsInf(mass,0){return f21Factors{},0,errF21}
        for pair:=0;pair<4;pair++ {factors[rec.Cue][pair]/=mass;work++}
    }
    return factors,work,nil
}

func f21Probe(f f21Factors, cue, action int) (float64, int, error) {
    if cue<0||cue>3||action<0||action>1 { return 0,0,errF21 }
    p:=0.0
    for pair,mass := range f[cue] {if f21BitResponse(pair,action)==1 {p+=mass}}
    return p,4,nil
}

// Returns all-eight-probe expected Bayes-correct score after observing the
// selected (cue,action) through the original 1/8 noisy channel. The 1/5
// erasure term is action-independent and so cannot change argmax.
func f21Risk(f f21Factors, cue, action int) (float64,int,error) {
    if cue<0||cue>3||action<0||action>1 {return 0,0,errF21}
    constant,work:=0.0,0
    for c:=0;c<4;c++ {
        if c==cue {continue}
        for a:=0;a<2;a++ {
            p,w,e:=f21Probe(f,c,a)
            if e!=nil{return 0,0,errF21}
            constant+=math.Max(p,1-p)
            work+=w
        }
    }
    total:=0.0
    for outcome:=0;outcome<2;outcome++ {
        var conditioned [4]float64
        normalizer:=0.0
        for pair,mass:=range f[cue] {
            if f21BitResponse(pair,action)==outcome {mass*=7}
            conditioned[pair]=mass
            normalizer+=mass
            work++
        }
        if normalizer<=0 {return 0,0,errF21}
        for pair:=range conditioned {conditioned[pair]/=normalizer;work++}
        score:=constant
        for probeAction:=0;probeAction<2;probeAction++ {
            prob:=0.0
            for pair,mass:=range conditioned {
                if f21BitResponse(pair,probeAction)==1 {prob+=mass}
                work++
            }
            score+=math.Max(prob,1-prob)
        }
        total+=(normalizer/8)*score
    }
    return total,work,nil
}

// Exactly the frozen F20 bayes-risk decision and tie-break, but without
// enumerating 256 causal masks, or accessing any hidden-world information.
func f21Select(credits []f20Credit, cue int) (int,int,error) {
    if cue<0||cue>3 {return 0,0,errF21}
    posterior,work,err:=f21Posterior(credits)
    if err!=nil{return 0,0,errF21}
    best:=-1.0
    selected:=0
    for action:=0;action<2;action++ {
        score,cost,e:=f21Risk(posterior,cue,action)
        if e!=nil{return 0,0,errF21}
        work+=cost
        if score>best+1e-12 {best=score;selected=action}
    }
    return selected,work,nil
}
