package main

import (
 "math"
 "testing"
)
func TestAuthenticSourceDeterminismAndIndependentRank(t *testing.T){
 for _,c:=range cohorts{
  a,e:=makeMatrix(c,94101,3);if e!=nil{t.Fatal(e)}
  b,e:=makeMatrix(c,94101,3);if e!=nil{t.Fatal(e)}
  d,e:=makeMatrix(c,94103,3);if e!=nil{t.Fatal(e)}
  if len(a)!=dimension*dimension{t.Fatal("incorrect input shape")}
  distinct:=false
  for i:=range a{if a[i]!=b[i]{t.Fatal("nondeterministic matrix")};if a[i]!=d[i]{distinct=true};if !finite(a[i]){t.Fatal("nonfinite source")}}
  if !distinct{t.Fatal("reused independent seed")}
 }
}
func TestACAReconstructsActualRankEight(t *testing.T){
 m,e:=makeMatrix("RANK8",94101,1);if e!=nil{t.Fatal(e)}
 f,e:=decomposeACA(m);if e!=nil{t.Fatal(e)}
 if f.Rank<8||f.Rank>rankCap{t.Fatalf("unexpected factor rank %d",f.Rank)}
 p,e:=prepare("LOWRANK16",m);if e!=nil{t.Fatal(e)}
 x:=makeVector(94101,1,3)
 wanted:=denseMul(m,x);got,e:=p.Apply(x);if e!=nil{t.Fatal(e)}
 err2,signal:=0.0,0.0
 for i:=range got{z:=got[i]-wanted[i];err2+=z*z;signal+=wanted[i]*wanted[i]}
 if math.Sqrt(err2/signal)>1e-8{t.Fatal("true rank eight source not recovered")}
}
func TestExactOptimizedBaselines(t *testing.T){
 m,e:=makeMatrix("FULL_RANDOM",94101,2);if e!=nil{t.Fatal(e)}
 x:=makeVector(94101,2,7)
 exact:=denseMul(m,x)
 for _,mode:=range []string{"DENSE","TILED","CSR"}{
  p,e:=prepare(mode,m);if e!=nil{t.Fatal(e)}
  y,e:=p.Apply(x);if e!=nil{t.Fatal(e)}
  for i:=range y{if math.Abs(y[i]-exact[i])>1e-12{t.Fatalf("%s altered exact baseline",mode)}}
 }
}
func TestRankAndMemoryBudget(t *testing.T){
 m,e:=makeMatrix("RANK24",94101,0);if e!=nil{t.Fatal(e)}
 p,e:=prepare("LOWRANK16",m);if e!=nil{t.Fatal(e)}
 if p.Factor.Rank>16||p.Factor.Rank<=0{t.Fatal("invalid frozen factor bound")}
 if p.LogicalBytes()!=32768||p.LogicalBytes()>131072/2{t.Fatal("factor storage budget changed")}
 if _,e:=decomposeACA([]float64{1});e==nil{t.Fatal("accepted wrong dimension")}
}
func TestSourcePairedAndProcessOSRSS(t *testing.T){
 a,e:=work("LOWRANK16","RANK8",94101);if e!=nil{t.Fatal(e)}
 b,e:=work("DENSE","RANK8",94101);if e!=nil{t.Fatal(e)}
 if a.SourceSHA256!=b.SourceSHA256||a.TruthSHA256!=b.TruthSHA256{t.Fatal("candidate fitted from a different source")}
 if a.QueryVectors!=episodes*vectorsPerEpisode||a.PeakRSSBytes==0||a.MemoryMetric!="OS_PROCESS_PEAK_PHYSICAL_RSS_BYTES"{t.Fatal("resource or sample count corrupt")}
 if !finite(a.NormalizedRMSE)||a.NormalizedRMSE>1e-8{t.Fatal("unexpected lowrank accuracy loss")}
}
func TestFrozenNoCherryPickOrSourceMismatch(t *testing.T){
 var rows []trial
 for _,mode:=range modes{
  for _,seed:=range seeds{
   cpu:=1.0
   if mode=="LOWRANK16"{cpu=0.95}
   bytes:=131072
   if mode=="LOWRANK16"{bytes=32768}
   rows=append(rows,trial{Worker:workerResult{Mode:mode,Cohort:"RANK8",Seed:seed,
    SourceSHA256:"paired",TruthSHA256:"truth",LogicalBytes:bytes,PeakRSSBytes:15*1024*1024,NormalizedRMSE:0},CPUSeconds:cpu,WallSeconds:1})
  }
 }
 result,e:=compare(rows,"RANK8");if e!=nil{t.Fatal(e)}
 if result.Pass{t.Fatal("0.95 CPU cannot meet 0.90 accepted threshold")}
 rows[0].Worker.SourceSHA256="other"
 if _,e:=compare(rows,"RANK8");e==nil{t.Fatal("accepted mismatched public source")}
}
