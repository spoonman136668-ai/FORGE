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
  if err:=m.Observe(observed(i));err!=nil {t.Fatal(err)}
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
 for i:=0;i<30;i++ {if err:=original.Observe(observed(i));err!=nil {t.Fatal(err)}}
 if err:=original.Feedback(1);err!=nil {t.Fatal(err)}
 snap,err:=original.Snapshot()
 if err!=nil {t.Fatal(err)}
 restored,err:=Restore(snap)
 if err!=nil {t.Fatal(err)}
 for i:=30;i<70;i++ {
  if err:=original.Observe(observed(i));err!=nil {t.Fatal(err)}
  if err:=restored.Observe(observed(i));err!=nil {t.Fatal(err)}
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
