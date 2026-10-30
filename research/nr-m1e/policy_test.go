package nrm1e

import (
 "bytes"
 "math"
 "testing"
)

func observed(i int) Event {
 return Event{
  Before:[6]float64{float64(i%4),float64((i+1)%5),float64(i%3),float64(i%3),float64((i+1)%4),float64(i%2)},
  After:[6]float64{float64((i+1)%4),float64((i+3)%5),float64((i+2)%3),float64((i+2)%5),float64(i%4),float64((i+1)%2)},
  Action:uint8(i%3),Reward:float64((i%3)-1)/2,
 }
}
func rotate(e Event) Event {
 return Event{
  Before:[6]float64{e.Before[2],e.Before[0],e.Before[1],e.Before[5],e.Before[3],e.Before[4]},
  After:[6]float64{e.After[2],e.After[0],e.After[1],e.After[5],e.After[3],e.After[4]},
  Action:e.Action,Reward:e.Reward,
 }
}
func TestBoundedAndRewardOnly(t *testing.T) {
 m:=New(17)
 for i:=0;i<30;i++ {
  e:=observed(i)
  if i==29 { e.Terminal=true }
  if err:=m.Observe(e);err!=nil {t.Fatal(err)}
  if len(m.Slots)>2 {t.Fatalf("unbounded slots: %d",len(m.Slots))}
 }
 before:=m.Weights
 if err:=m.Feedback(1);err!=nil {t.Fatal(err)}
 if m.Weights==before {t.Fatal("no terminal reward update despite distinct transitions")}
 if len(m.Slots)!=0 || m.Episodes!=1 {t.Fatal("episode boundary drift")}
}
func TestPublicCoordinateRelabelingIsEquivariant(t *testing.T) {
 a,b:=New(31),New(31)
 for i:=0;i<50;i++ {
  e:=observed(i)
  if i==49 {e.Truncated=true}
  if err:=a.Observe(e);err!=nil {t.Fatal(err)}
  if err:=b.Observe(rotate(e));err!=nil {t.Fatal(err)}
 }
 for i:=0;i<4;i++ {
  if math.Abs(a.Trace[i]-b.Trace[i])>1e-12 {
   t.Fatalf("role-neutral trace differs at %d: %.16f %.16f",i,a.Trace[i],b.Trace[i])
  }
 }
 if err:=a.Feedback(1);err!=nil {t.Fatal(err)}
 if err:=b.Feedback(1);err!=nil {t.Fatal(err)}
 for i:=0;i<4;i++ {
  if math.Abs(a.Weights[i]-b.Weights[i])>1e-12 {t.Fatal("weight update depended on role index")}
 }
}
func TestColdRestartProducesSameNextEpisode(t *testing.T) {
 original:=New(47)
 for i:=0;i<30;i++ {e:=observed(i);if i==29 {e.Terminal=true};if err:=original.Observe(e);err!=nil {t.Fatal(err)}}
 if err:=original.Feedback(1);err!=nil {t.Fatal(err)}
 snap,err:=original.Snapshot()
 if err!=nil {t.Fatal(err)}
 restored,err:=Restore(snap)
 if err!=nil {t.Fatal(err)}
 for i:=30;i<70;i++ {
  e:=observed(i)
  if i==69 {e.Terminal=true}
  if err:=original.Observe(e);err!=nil {t.Fatal(err)}
  if err:=restored.Observe(e);err!=nil {t.Fatal(err)}
 }
 if err:=original.Feedback(0);err!=nil {t.Fatal(err)}
 if err:=restored.Feedback(0);err!=nil {t.Fatal(err)}
 one,err:=original.Snapshot();if err!=nil {t.Fatal(err)}
 two,err:=restored.Snapshot();if err!=nil {t.Fatal(err)}
 if !bytes.Equal(one,two) {t.Fatal("cold restart diverged")}
}
func TestFailClosedOnInvalidConsequenceOrFeedback(t *testing.T) {
 m:=New(61)
 if err:=m.Observe(observed(0));err!=nil {t.Fatal(err)}
 before,err:=m.Snapshot();if err!=nil {t.Fatal(err)}
 e:=observed(1);e.Reward=math.NaN()
 if err:=m.Observe(e);err==nil {t.Fatal("accepted NaN public reward")}
 if err:=m.Feedback(math.Inf(1));err==nil {t.Fatal("accepted infinite terminal reward")}
 after,err:=m.Snapshot();if err!=nil {t.Fatal(err)}
 if !bytes.Equal(before,after) {t.Fatal("invalid input mutated state")}
 if _,err:=Restore([]byte(`{"version":1,"rng":0}`));err==nil {t.Fatal("accepted corrupt RNG")}
}
func TestContextAndActionActuallyAffectScore(t *testing.T) {
 e:=observed(0)
 now:=e
 now.Action=(e.Action+1)%3
 now.After=[6]float64{100,100,100,100,100,100}
 same:=features(e,e)
 shifted:=features(e,now)
 if same==shifted {t.Fatal("candidate ignores public action/context change")}
}

func TestObservedTerminalRequiredAndNoFurtherSteps(t *testing.T) {
 m:=New(113)
 before,err:=m.Snapshot();if err!=nil {t.Fatal(err)}
 if err:=m.Feedback(1);err==nil {t.Fatal("accepted terminal reward before any source event")}
 if err:=m.Observe(observed(0));err!=nil {t.Fatal(err)}
 if err:=m.Feedback(1);err==nil {t.Fatal("accepted terminal reward before source termination")}
 last:=observed(1);last.Truncated=true
 if err:=m.Observe(last);err!=nil {t.Fatal(err)}
 raw,err:=m.Snapshot();if err!=nil {t.Fatal(err)}
 recovered,err:=Restore(raw);if err!=nil {t.Fatal(err)}
 if err:=recovered.Observe(observed(2));err==nil {t.Fatal("accepted source step after termination before feedback")}
 after,err:=recovered.Snapshot();if err!=nil {t.Fatal(err)}
 if !bytes.Equal(raw,after) {t.Fatal("rejected step mutated retained state")}
 if err:=recovered.Feedback(1);err!=nil {t.Fatal(err)}
 if recovered.AwaitingFeedback || len(recovered.Slots)!=0 {t.Fatal("did not close episode")}
 if err:=recovered.Feedback(1);err==nil {t.Fatal("accepted duplicate terminal reward")}
 if bytes.Equal(raw,before) {t.Fatal("terminal state not retained before feedback")}
}
