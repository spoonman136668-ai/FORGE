package main
import("math";"testing")
func TestFrozenStreamReproducibleAndDisjoint(t *testing.T){
 a:=stream(73101,3,false);b:=stream(73101,3,false);c:=stream(73101,3,true)
 if len(a)!=seriesLength||len(c)!=seriesLength{t.Fatal("source size")}
 for i:=range a{if a[i]!=b[i]{t.Fatal("nondeterministic")}}
 if string(a)==string(c){t.Fatal("train/test stream reused")}
}
func TestHistoryTargetsNoFutureInput(t *testing.T){
 bits:=make([]byte,seriesLength);bits[11]=1;bits[9]=1
 y,e:=label(bits,12,"PREVIOUS_BIT");if e!=nil||y!=1{t.Fatal(y,e)}
 y,e=label(bits,12,"DELAY_3");if e!=nil||y!=1{t.Fatal(y,e)}
 y,e=label(bits,12,"XOR_1_3");if e!=nil||y!=0{t.Fatal(y,e)}
 if _,e:=label(bits,3,"DELAY_3");e==nil{t.Fatal("premature evaluation")}
}
func TestLagRegisterAndFixedReservoir(t *testing.T){
 for _,mode:=range modes{
  m,e:=newModel(mode,73101);if e!=nil{t.Fatal(e)}
  m.observe(1);m.observe(0);m.observe(1)
  if mode=="LAG12"&&(m.state[0]!=1||m.state[1]!=0||m.state[2]!=1){t.Fatal("lag broken")}
  if mode=="RESERVOIR12"{for _,v:=range m.state{if !finite(v)||math.Abs(v)>1{t.Fatal("unstable reservoir")}}}
 }
}
func TestNoTestLabelsUsedForFit(t *testing.T){
 x:=stream(73101,0,false);y:=stream(73101,0,true)
 rows,e:=samples(x,"LAG12","PREVIOUS_BIT",73101);if e!=nil{t.Fatal(e)}
 c,e:=fitted(rows,"LAG12");if e!=nil{t.Fatal(e)}
 yRows,e:=samples(y,"LAG12","PREVIOUS_BIT",73101);if e!=nil{t.Fatal(e)}
 orig:=c;for i:=range yRows{yRows[i].y=1-yRows[i].y}
 if c!=orig{t.Fatal("test labels changed training")}
}
func TestWorkerCompleteFiniteResourceAndStrongControls(t *testing.T){
 for _,scenario:=range scenarios{
  var prev workerResult
  for i,mode:=range modes{
   w,e:=work(mode,scenario,73101);if e!=nil{t.Fatal(mode,e)}
   if w.TrainSamples!=sessions*(seriesLength-memoryLength)||w.PeakRSSBytes==0||!finite(w.HeldoutMSE){t.Fatal("invalid metric")}
   if i>0&&(w.TrainSourceSHA256!=prev.TrainSourceSHA256||w.HeldoutSourceSHA256!=prev.HeldoutSourceSHA256){t.Fatal("input mismatch")}
   prev=w
  }
 }
}
func TestNoUnearnedAcceleration(t *testing.T){
 records:=[]record{}
 for _,mode:=range modes{for i,seed:=range trialSeeds{
  w:=workerResult{Mode:mode,Scenario:"PREVIOUS_BIT",Seed:seed,TrainSourceSHA256:"train",HeldoutSourceSHA256:"test",HeldoutMSE:0.02,PeakRSSBytes:30*1024*1024}
  cpu:=1.0;if mode=="RESERVOIR12"{cpu=0.95}
  records=append(records,record{Worker:w,CPUSeconds:cpu,WallSeconds:2,Trial:i})
 }}
 c,e:=compare(records,"PREVIOUS_BIT");if e!=nil{t.Fatal(e)}
 if c.Pass{t.Fatal("0.95 CPU ratio should not qualify")}
 records[0].Worker.TrainSourceSHA256="leak"
 if _,e:=compare(records,"PREVIOUS_BIT");e==nil{t.Fatal("accepted unmatched source")}
}
