// Package nrm1e contains a source-neutral, developmental memory-retention candidate.
// It receives only PUBLIC action/consequence events. It is NOT a learned action
// planner, native Wingless/Yggdrasil integration, or eligible original-world runner.
package nrm1e

import (
 "encoding/json"
 "errors"
 "math"
)

// Event contains only an already observed transition and its actual public
// reward. It excludes future queries, protected labels, and latent world state.
// The six coordinates retain every field of Wingless R1's public grid through
// an audited conversion; no active Wingless runtime imports this candidate.
type Event struct {
 Before [6]float64 `json:"before"`
 After [6]float64 `json:"after"`
 Action uint8 `json:"action"`
 Reward float64 `json:"reward"`
 Terminal bool `json:"terminal"`
 Truncated bool `json:"truncated"`
}

// Learner uses a fixed two-transition memory and four learned, role-neutral
// score weights. Weights change ONLY on externally supplied terminal feedback.
// A public action/outcome cannot be rewritten or hallucinated by this policy.
type Learner struct {
 Slots []Event `json:"slots"`
 Weights [4]float64 `json:"weights"`
 Trace [4]float64 `json:"trace"`
 Baseline float64 `json:"baseline"`
 RNG uint64 `json:"rng"`
 Episodes uint64 `json:"episodes"`
 AwaitingFeedback bool `json:"awaiting_feedback"`
 Version int `json:"version"`
}

func New(seed uint64) *Learner {
 if seed == 0 { seed = 1 }
 return &Learner{Baseline:0.5,RNG:seed,Version:1}
}
func finite(v float64) bool { return !math.IsNaN(v) && !math.IsInf(v,0) }
func valid(e Event) bool {
 if e.Action > 2 || !finite(e.Reward) || e.Reward < -1 || e.Reward > 1 { return false }
 for i:=0;i<6;i++ {
  if !finite(e.Before[i]) || !finite(e.After[i]) { return false }
  if math.Abs(e.Before[i]) > 1e6 || math.Abs(e.After[i]) > 1e6 { return false }
 }
 return true
}
func absSum(a,b [6]float64) float64 {
 var z float64
 for i:=0;i<6;i++ { z += math.Abs(a[i]-b[i]) }
 return z
}

// features use only relationships between public state changes and the current
// public consequence. No categorical feature identifier, future query, or
// target-label index appears in the selection policy.
func features(e,now Event) [4]float64 {
 change:=math.Min(absSum(e.Before,e.After),20.)/20.
 match:=0.
 if e.Action==now.Action { match=1. }
 return [4]float64{change,math.Exp(-math.Min(absSum(e.After,now.After),20.)),match,e.Reward}
}
func dot(w,f [4]float64) float64 {
 var z float64
 for i:=range w { z+=w[i]*f[i] }
 return z
}
func (l *Learner) uniform() float64 {
 // Fixed-seed xorshift64*, reproducible without a shared/global RNG.
 x:=l.RNG
 x ^= x>>12; x ^= x<<25; x ^= x>>27
 l.RNG=x
 return float64((x*2685821657736338717)>>11) / float64(uint64(1)<<53)
}

// Observe is query-blind. Call ONLY after a source owner has returned the
// observed consequence of its already-selected action.
func (l *Learner) Observe(e Event) error {
 if l==nil || l.Version!=1 || len(l.Slots)>2 { return errors.New("INVALID_MEMORY_STATE") }
 if !valid(e) { return errors.New("INVALID_PUBLIC_TRANSITION") }
 if l.AwaitingFeedback { return errors.New("EPISODE_AWAITING_TERMINAL_FEEDBACK") }
 if len(l.Slots)<2 { l.Slots=append(l.Slots,e);l.AwaitingFeedback=e.Terminal||e.Truncated;return nil }
 candidates:=[3]Event{l.Slots[0],l.Slots[1],e}
 var fs [3][4]float64
 var scores [3]float64
 for i:=0;i<3;i++ { fs[i]=features(candidates[i],e);scores[i]=dot(l.Weights,fs[i]) }
 indices:=[3]int{0,1,2}
 var selected [2]int
 for n:=0;n<2;n++ {
  remaining:=3-n
  maxScore:=scores[indices[0]]
  for k:=1;k<remaining;k++ { maxScore=math.Max(maxScore,scores[indices[k]]) }
  var probs [3]float64
  var denom float64
  for k:=0;k<remaining;k++ {
   probs[k]=math.Exp(scores[indices[k]]-maxScore);denom+=probs[k]
  }
  r:=l.uniform()*denom
  chosen:=remaining-1
  for k:=0;k<remaining;k++ {
   r-=probs[k]
   if r<0 { chosen=k;break }
  }
  pick:=indices[chosen]
  selected[n]=pick
  for j:=0;j<4;j++ {
   expectation:=0.
   for k:=0;k<remaining;k++ { expectation+=probs[k]/denom*fs[indices[k]][j] }
   l.Trace[j]+=fs[pick][j]-expectation
  }
  indices[chosen],indices[remaining-1]=indices[remaining-1],indices[chosen]
 }
 l.Slots=[]Event{candidates[selected[0]],candidates[selected[1]]}
 l.AwaitingFeedback=e.Terminal||e.Truncated
 return nil
}

// Feedback accepts delayed outcome reward only. It deliberately does not
// receive correct actions, queries, desired memories or an oracle ranking.
func (l *Learner) Feedback(reward float64) error {
 if l==nil || l.Version!=1 || !l.AwaitingFeedback || !finite(reward) || reward<0 || reward>1 || len(l.Slots)==0 {
  return errors.New("INVALID_TERMINAL_FEEDBACK")
 }
 advantage:=reward-l.Baseline
 for j:=0;j<4;j++ {
  l.Weights[j]+=0.05*advantage*l.Trace[j]
  if l.Weights[j]>8 { l.Weights[j]=8 }
  if l.Weights[j] < -8 { l.Weights[j]=-8 }
 }
 l.Baseline=0.975*l.Baseline+0.025*reward
 l.Episodes++
 l.Slots=nil
 l.AwaitingFeedback=false
 l.Trace=[4]float64{}
 return nil
}
func (l *Learner) Snapshot() ([]byte,error) {
 if l==nil || l.Version!=1 || len(l.Slots)>2 { return nil,errors.New("INVALID_MEMORY_STATE") }
 return json.Marshal(l)
}
func Restore(blob []byte) (*Learner,error) {
 var m Learner
 if err:=json.Unmarshal(blob,&m);err!=nil {return nil,err}
 if m.Version!=1 || m.RNG==0 || len(m.Slots)>2 || !finite(m.Baseline) ||
   m.Baseline<0 || m.Baseline>1 {return nil,errors.New("INVALID_CHECKPOINT")}
 for _,e:=range m.Slots {if !valid(e){return nil,errors.New("INVALID_CHECKPOINT")}}
 for j:=0;j<4;j++ {if !finite(m.Weights[j]) || !finite(m.Trace[j]) || math.Abs(m.Weights[j])>8 {return nil,errors.New("INVALID_CHECKPOINT")}}
 return &m,nil
}
