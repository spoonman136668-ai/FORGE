package main

import (
	"crypto/sha256"
	"encoding/hex"
	"os"
	"path/filepath"
	"testing"
)
func TestSourceReproducibilityAndShortFile(t *testing.T){
	dir:=t.TempDir();a:=filepath.Join(dir,"a");b:=filepath.Join(dir,"b")
	ah,e:=makeSource(a,8*blockSize);if e!=nil{t.Fatal(e)}
	bh,e:=makeSource(b,8*blockSize);if e!=nil{t.Fatal(e)}
	if ah!=bh{t.Fatal("source changed")}
	bb,e:=os.ReadFile(a);if e!=nil{t.Fatal(e)}
	x:=sha256.Sum256(bb);if hex.EncodeToString(x[:])!=ah{t.Fatal("source hash mismatch")}
	if _,e:=makeSource(filepath.Join(dir,"bad"),3);e==nil{t.Fatal("unaligned file accepted")}
	if e:=os.Truncate(b,7*blockSize);e!=nil{t.Fatal(e)}
	f,e:=os.Open(b);if e!=nil{t.Fatal(e)}
	r,e:=newBlockReader(f,"SYNC",8*blockSize);if e!=nil{t.Fatal(e)}
	if _,e=r.Read(7*blockSize);e==nil{t.Fatal("silent truncated read")}
	r.Close();f.Close()
}
func TestAllArmsParityAndBounds(t *testing.T){
	file:=filepath.Join(t.TempDir(),"test")
	if _,e:=makeSource(file,8*blockSize);e!=nil{t.Fatal(e)}
	for _,schedule:=range schedules{
		for _,seed:=range []uint64{49101,49107}{
			var prior workerResult
			for i,mode:=range modes{
				w,e:=work(file,mode,schedule,seed);if e!=nil{t.Fatalf("%s %s: %v",schedule,mode,e)}
				if w.PeakRSSBytes==0 || w.RequestedBytes!=16*blockSize{t.Fatalf("invalid accounting: %+v",w)}
				if mode=="PREDICTIVE" && w.PrefetchedBytes>0 && w.PrefetchedBytes>w.UserReadBytes {t.Fatal("prefetch accounting exceeds read bytes")}
				if i>0 && (w.TraceDigest!=prior.TraceDigest || w.ArithmeticChecksum!=prior.ArithmeticChecksum){t.Fatalf("wrong output in %s %s",mode,schedule)}
				prior=w
			}
		}
	}
}
func TestPredictorUsesOnlyObservedAddresses(t *testing.T){
	fpath:=filepath.Join(t.TempDir(),"history")
	if _,e:=makeSource(fpath,8*blockSize);e!=nil{t.Fatal(e)}
	f,e:=os.Open(fpath);if e!=nil{t.Fatal(e)};defer f.Close()
	r,e:=newBlockReader(f,"PREDICTIVE",8*blockSize);if e!=nil{t.Fatal(e)}
	if r.pending!=nil{t.Fatal("prefetch before first request")}
	for _,i:=range []int64{0,2,4}{
		if _,e:=r.Read(i*blockSize);e!=nil{t.Fatal(e)}
		if i<4 && r.pending!=nil{t.Fatal("speculated before repeated observed stride")}
	}
	if r.pending==nil || r.pending.offset!=6*blockSize{t.Fatal("did not infer observed stride")}
	if _,e:=r.Read(7*blockSize);e!=nil{t.Fatal(e)}
	if _,e:=r.settle(-1,false);e!=nil{t.Fatal(e)}
	if r.wastedBytes==0{t.Fatal("misprediction not charged")}
	if e:=r.Close();e!=nil{t.Fatal(e)}
	if bufferBudget<2*blockSize{t.Fatal("buffer cap too small")}
}
func TestScheduleIsPermutation(t *testing.T){
	for _,sched:=range schedules{
		s,e:=scheduleFor(sched,16,49101);if e!=nil{t.Fatal(e)}
		seen:=map[int]bool{}
		for _,x:=range s{if x<0||x>=16||seen[x]{t.Fatal("not a permutation")};seen[x]=true}
		if len(seen)!=16{t.Fatal("incomplete schedule")}
	}
}
func TestConservativeThresholdAndParity(t *testing.T){
	var rows []record
	for _,mode:=range modes{
		for trial,seed:=range trialSeeds{
			w:=workerResult{Mode:mode,Schedule:"SEQUENTIAL",Seed:seed,SourceBytes:192*1024*1024,
				RequestedBytes:2*192*1024*1024,TraceDigest:"same",ArithmeticChecksum:"same",PeakRSSBytes:32*1024*1024}
			wall:=1.0
			if mode=="PREDICTIVE"{wall=0.95}
			rows=append(rows,record{Worker:w,CPUSeconds:1,WallSeconds:wall,Trial:trial})
		}
	}
	c,e:=cellFor(rows,192*1024*1024,"SEQUENTIAL","sha");if e!=nil{t.Fatal(e)}
	if c.Pass{t.Fatal("unearned 0.95 time speedup classified positive")}
	rows[0].Worker.TraceDigest="bad"
	if _,e:=cellFor(rows,192*1024*1024,"SEQUENTIAL","sha");e==nil{t.Fatal("mismatch admitted")}
}
