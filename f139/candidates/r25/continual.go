// Package cognition provides candidate-only native predictive state.
// This package neither dispatches work nor grants scientific acceptance.
package cognition

import (
 "bytes"
 "encoding/json"
 "errors"
 "io"
 "math"
)

type State struct {
 Weights [4]float64 `json:"weights"`
 Updates uint64 `json:"updates"`
}
func features(action,prior int)([4]float64,error) {
 if (action!=0&&action!=1)||(prior!=0&&prior!=1){return [4]float64{},errors.New("nonbinary action/prior")}
 a,p:=float64(2*action-1),float64(2*prior-1)
 return [4]float64{1,a,p,a*p},nil
}
func sigmoid(z float64)float64 {
 if z>=0 {v:=math.Exp(-z);return 1/(1+v)}
 v:=math.Exp(z);return v/(1+v)
}
func (s *State) Predict(action,prior int)(float64,error) {
 if s==nil {return 0,errors.New("nil predictor")}
 f,err:=features(action,prior);if err!=nil{return 0,err}
 z:=0.0
 for i,x:=range f {
  w:=s.Weights[i]
  if math.IsNaN(w)||math.IsInf(w,0){return 0,errors.New("invalid learned weight")}
  z+=w*x
  if math.IsNaN(z)||math.IsInf(z,0){return 0,errors.New("nonfinite prediction")}
 }
 return sigmoid(z),nil
}
// Observe learns only after observing a consequence, without a task ID.
func (s *State) Observe(action,prior,outcome int,rate float64)error {
 if s==nil || s.Updates==^uint64(0){return errors.New("learner unavailable or update budget exhausted")}
 if (outcome!=0&&outcome!=1)||!(rate>0&&rate<=1)||math.IsNaN(rate)||math.IsInf(rate,0){return errors.New("invalid observation")}
 f,err:=features(action,prior);if err!=nil{return err}
 p,err:=s.Predict(action,prior);if err!=nil{return err}
 next:=s.Weights
 for i,v:=range f {next[i]+=rate*(float64(outcome)-p)*v;if math.IsNaN(next[i])||math.IsInf(next[i],0){return errors.New("nonfinite state")}}
 s.Weights=next;s.Updates++;return nil
}
// ForecastTwo marginalizes the first, unobserved consequence.
func (s *State) ForecastTwo(prior,first,second int)(float64,error) {
 p,err:=s.Predict(first,prior);if err!=nil{return 0,err}
 p0,err:=s.Predict(second,0);if err!=nil{return 0,err}
 p1,err:=s.Predict(second,1);if err!=nil{return 0,err}
 return (1-p)*p0+p*p1,nil
}
func (s State) Snapshot()([]byte,error){return json.Marshal(s)}
func (s *State) Restore(blob []byte)error{
 if s==nil{return errors.New("nil restore target")}
 if len(blob)==0||len(blob)>4096{return errors.New("invalid snapshot size")}
 var wire struct{Weights []float64 `json:"weights"`;Updates uint64 `json:"updates"`}
 decoder:=json.NewDecoder(bytes.NewReader(blob))
 decoder.DisallowUnknownFields()
 if err:=decoder.Decode(&wire);err!=nil{return err}
 var trailing any
 if err:=decoder.Decode(&trailing);err!=io.EOF{return errors.New("trailing snapshot bytes")}
 if len(wire.Weights)!=4{return errors.New("invalid weight count")}
 var next State
 for i,v:=range wire.Weights{if math.IsNaN(v)||math.IsInf(v,0){return errors.New("invalid weight")};next.Weights[i]=v}
 next.Updates=wire.Updates;*s=next;return nil
}
