package main

import (
 "crypto/sha256"
 "encoding/hex"
 "errors"
 "math"
 "time"
)
type workerResult struct {
 Schema string
 Mode string
 Cohort string
 Seed uint64
 Episodes int
 QueryVectors int
 MatrixRows int
 LogicalBytes int
 LastFactorRank int
 SourceSHA256 string
 TruthSHA256 string
 OutputSHA256 string
 NormalizedRMSE float64
 MaxAbsError float64
 InferenceNano int64
 PeakRSSBytes uint64
 MemoryMetric string
}
func work(mode,cohort string,seed uint64)(workerResult,error){
 var w workerResult
 if !oneOf(modes,mode)||!oneOf(cohorts,cohort){return w,errors.New("bad experiment identifiers")}
 sourceDigest:=sha256.New()
 truthDigest:=sha256.New()
 outputDigest:=sha256.New()
 errorSquared,signalSquared,maxAbsolute:=0.0,0.0,0.0
 inference:=int64(0);lastRank:=0;storage:=0
 for session:=0;session<episodes;session++{
  matrix,err:=makeMatrix(cohort,seed,session)
  if err!=nil{return w,err}
  digestArray(sourceDigest,matrix)
  repr,err:=prepare(mode,matrix)
  if err!=nil{return w,err}
  storage=repr.LogicalBytes()
  lastRank=repr.Factor.Rank
  for q:=0;q<vectorsPerEpisode;q++{
   x:=makeVector(seed,session,q)
   digestArray(sourceDigest,x)
   // The reference is always charged to all four arms; it is never used in factor fitting.
   truth:=denseMul(matrix,x)
   digestArray(truthDigest,truth)
   begin:=time.Now()
   predicted,err:=repr.Apply(x)
   inference+=time.Since(begin).Nanoseconds()
   if err!=nil{return w,err}
   for i,v:=range predicted{
    if math.IsNaN(v)||math.IsInf(v,0){return w,errors.New("nonfinite output")}
    delta:=v-truth[i]
    errorSquared+=delta*delta
    signalSquared+=truth[i]*truth[i]
    if math.Abs(delta)>maxAbsolute{maxAbsolute=math.Abs(delta)}
   }
   digestArray(outputDigest,predicted)
  }
 }
 if signalSquared<=0||math.IsNaN(signalSquared)||math.IsInf(signalSquared,0){return w,errors.New("invalid truth signal")}
 rss,err:=peakResidentBytes()
 if err!=nil{return w,err}
 if rss==0{return w,errors.New("missing process physical RSS")}
 normalized:=math.Sqrt(errorSquared/signalSquared)
 if math.IsNaN(normalized)||math.IsInf(normalized,0){return w,errors.New("nonfinite accuracy")}
 w=workerResult{
  Schema:schema,Mode:mode,Cohort:cohort,Seed:seed,
  Episodes:episodes,QueryVectors:episodes*vectorsPerEpisode,MatrixRows:dimension,
  LogicalBytes:storage,LastFactorRank:lastRank,
  SourceSHA256:hex.EncodeToString(sourceDigest.Sum(nil)),
  TruthSHA256:hex.EncodeToString(truthDigest.Sum(nil)),
  OutputSHA256:hex.EncodeToString(outputDigest.Sum(nil)),
  NormalizedRMSE:normalized,MaxAbsError:maxAbsolute,
  InferenceNano:inference,PeakRSSBytes:rss,MemoryMetric:"OS_PROCESS_PEAK_PHYSICAL_RSS_BYTES",
 }
 return w,nil
}
