package nativediscovery

import (
 "math"
 "reflect"
 "testing"
)

func g188Fixture() f36Model {
 m := f36Model{Have:true, Kind:"compositional-issued-memory"}
 m.Weights = [4]float64{.70,.20,.08,.02}
 for k:=0;k<4;k++ { m.Beliefs[k][k]=1 }
 return m
}

func g188SameModelIncludingNaN(a,b f36Model) bool {
 // DeepEqual considers NaN != NaN even when source is bit-for-bit untouched.
 for k:=0;k<4;k++ {
  if math.IsNaN(a.Weights[k]) && math.IsNaN(b.Weights[k]) {
   if math.Float64bits(a.Weights[k]) != math.Float64bits(b.Weights[k]) {return false}
   a.Weights[k],b.Weights[k]=0,0
  }
  for s:=0;s<16;s++ {
   if math.IsNaN(a.Beliefs[k][s]) && math.IsNaN(b.Beliefs[k][s]) {
    if math.Float64bits(a.Beliefs[k][s]) != math.Float64bits(b.Beliefs[k][s]) {return false}
    a.Beliefs[k][s],b.Beliefs[k][s]=0,0
   }
  }
 }
 return reflect.DeepEqual(a,b)
}

func TestG188VersionedHazardPredictiveParityAndImmutability(t *testing.T) {
 m:=g188Fixture()
 initial:=m
 observed:=[2]int{0,0}
 different:=false
 for _,eps:=range []float64{0,F37Epsilon} {
  got,err:=g188SensorProbabilityV2(m,0,0,0,observed,eps)
  if err!=nil {t.Fatal(err)}
  cleanGot,err:=g188CleanProbabilityScorerOnlyV2(m,0,0,0,0,eps)
  if err!=nil {t.Fatal(err)}
  prior,err:=f37NextPrior(m,0,0,0,eps)
  if err!=nil {t.Fatal(err)}
  want,wantClean:=0.0,0.0
  for k:=0;k<4;k++ {
   z:=0.0
   for s:=0;s<16;s++ {z+=prior[k][s]*f36Likelihood(observed,s)}
   mixed:=.95*m.Weights[k]+.05/4
   want+=mixed*z
   wantClean+=mixed*prior[k][0]
  }
  if math.Abs(got-want)>1e-12 || math.Abs(cleanGot-wantClean)>1e-12 {
   t.Fatalf("G188 frozen hazard formula mismatch eps=%g actual=%g want=%g clean=%g want_clean=%g",eps,got,want,cleanGot,wantClean)
  }
  _,_,old,err:=f37Evidence(m,0,0,0,observed,eps)
  if err!=nil {t.Fatal(err)}
  if math.Abs(got-old)>1e-12 {different=true}
  if !g188SameModelIncludingNaN(initial,m) {t.Fatal("G188 scorer mutated trained model memory")}
 }
 if !different {t.Fatal("G188 skewed weights failed to expose original unadjusted likelihood mismatch")}
 uniform:=g188Fixture()
 uniform.Weights=[4]float64{.25,.25,.25,.25}
 for _,eps:=range []float64{0,F37Epsilon} {
  got,err:=g188SensorProbabilityV2(uniform,0,0,0,observed,eps)
  if err!=nil {t.Fatal(err)}
  _,_,old,err:=f37Evidence(uniform,0,0,0,observed,eps)
  if err!=nil || math.Abs(got-old)>1e-12 {t.Fatal("G188 uniform prior must match historical scorer",err)}
 }
 t.Log("G188_HAZARD_PREDICTIVE_V2=FORMULA_PARITY_AND_SOURCE_IMMUTABILITY_PASS")
}

func TestG188VersionedHazardPredictiveNegativeControls(t *testing.T) {
 observed:=[2]int{0,0}
 cases:=[]struct{name string; mutate func(*f36Model); t int; cue int; action int; obs [2]int; eps float64}{
  {"missing-state",func(m *f36Model){m.Have=false},0,0,0,observed,0},
  {"wrong-kind",func(m *f36Model){m.Kind="history-logistic"},0,0,0,observed,0},
  {"unnormalized-weights",func(m *f36Model){m.Weights[0]+=.1},0,0,0,observed,0},
  {"negative-weight",func(m *f36Model){m.Weights[0]=-.1},0,0,0,observed,0},
  {"nan-weight",func(m *f36Model){m.Weights[0]=math.NaN()},0,0,0,observed,0},
  {"inf-weight",func(m *f36Model){m.Weights[0]=math.Inf(1)},0,0,0,observed,0},
  {"unnormalized-belief",func(m *f36Model){m.Beliefs[0][0]=.5},0,0,0,observed,0},
  {"nan-belief",func(m *f36Model){m.Beliefs[0][0]=math.NaN()},0,0,0,observed,0},
  {"negative-belief",func(m *f36Model){m.Beliefs[0][0]=-.1},0,0,0,observed,0},
  {"bad-time",func(m *f36Model){},96,0,0,observed,0},
  {"bad-cue",func(m *f36Model){},0,4,0,observed,0},
  {"bad-action",func(m *f36Model){},0,0,3,observed,0},
  {"bad-epsilon",func(m *f36Model){},0,0,0,observed,.026},
  {"bad-observation-low",func(m *f36Model){},0,0,0,[2]int{-1,0},0},
  {"bad-observation-high",func(m *f36Model){},0,0,0,[2]int{0,16},0},
  {"expired-event",func(m *f36Model){m.Events[0]=[]f36Event{{Due:-1,Mask:1}}},0,0,0,observed,0},
 }
 for _,tc:=range cases {
  t.Run(tc.name,func(t *testing.T){
   m:=g188Fixture()
   tc.mutate(&m)
   original:=m
   _,err:=g188SensorProbabilityV2(m,tc.t,tc.cue,tc.action,tc.obs,tc.eps)
   if err==nil {t.Fatal("G188 invalid scorer input accepted")}
   if !g188SameModelIncludingNaN(m,original) {t.Fatal("G188 negative control changed source model")}
  })
 }
 for _,clean:=range []int{-1,16} {
  if _,err:=g188CleanProbabilityScorerOnlyV2(g188Fixture(),0,0,0,clean,0);err==nil {
   t.Fatal("G188 out-of-range scorer-only truth accepted")
  }
 }
 m:=g188Fixture()
 before:=m
 if _,err:=g188CleanProbabilityScorerOnlyV2(m,0,0,0,0,F37Epsilon);err!=nil || !g188SameModelIncludingNaN(before,m) {
  t.Fatal("G188 clean scorer corrupted online model or rejected valid input",err)
 }
 t.Log("G188_HAZARD_PREDICTIVE_V2=FAIL_CLOSED_NEGATIVE_CONTROLS_PASS")
}
