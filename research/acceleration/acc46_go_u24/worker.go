package main

import (
 "crypto/sha256"
 "encoding/hex"
 "errors"
 "math"
)

type workerResult struct {
 Schema string
 Mode string
 Regime string
 Seed uint64
 Episodes int
 FitStateCount int
 HeldoutStateCount int
 EvaluatedCells int
 CorrectCells int
 UnseenCells int
 CorrectUnseen int
 ErrorRate float64
 UnseenErrorRate float64
 LogicalBytes int
 NeighborMessageReads int64
 SourceSHA256 string
 FitSHA256 string
 TruthSHA256 string
 PredictionSHA256 string
 PeakRSSBytes uint64
 MemoryMetric string
}
func work(mode,regime string,seed uint64)(workerResult,error){
 var w workerResult
 if !eligible(modes,mode)||!eligible(regimes,regime){return w,errors.New("invalid mode/regime")}
 sourceHash,fitHash,truthHash,predHash:=sha256.New(),sha256.New(),sha256.New(),sha256.New()
 evaluated,correct,unseen,unseenCorrect:=0,0,0,0
 neighborReads:=int64(0)
 for episode:=0;episode<episodes;episode++{
  base:=episodeBase(seed,episode)
  ruleset:=makeRules(base)
  learner:=newLearner(mode)
  var seen [cells][neighborhoods]bool
  addHash(sourceHash,1,base)
  for g:=0;g<4;g++{
   addHash(sourceHash,2,uint64(ruleset.Old[g]))
   addHash(sourceHash,3,uint64(ruleset.New[g]))
  }
  for t:=0;t<fitStates;t++{
   state:=fitState(base,t)
   addHash(sourceHash,4,state)
   var truthMask uint64
   for cell:=0;cell<cells;cell++{
    pattern:=neighborhood(state,cell)
    result:=truth(ruleset,regime,t,cell,pattern)
    if result!=0{truthMask|=uint64(1)<<uint(cell)}
    seen[cell][pattern]=true
    learner.Learn(cell,pattern,result)
   }
   addHash(fitHash,5,truthMask)
   addHash(sourceHash,6,truthMask)
  }
  for t:=0;t<testStates;t++{
   state:=heldoutState(base,t)
   addHash(sourceHash,7,state)
   var truthMask,predictionMask uint64
   for cell:=0;cell<cells;cell++{
    pattern:=neighborhood(state,cell)
    prediction:=learner.Predict(cell,pattern)
    // Auditor computes the heldout label only after the candidate prediction.
    actual:=truth(ruleset,regime,fitStates+t,cell,pattern)
    if prediction!=0{predictionMask|=uint64(1)<<uint(cell)}
    if actual!=0{truthMask|=uint64(1)<<uint(cell)}
    evaluated++
    if prediction==actual{correct++}
    if !seen[cell][pattern]{
     unseen++
     if prediction==actual{unseenCorrect++}
    }
    neighborReads+=int64(learner.MessageReadsPerPrediction())
   }
   addHash(truthHash,8,truthMask)
   addHash(predHash,9,predictionMask)
  }
 }
 if evaluated!=episodes*testStates*cells||unseen<=0{return w,errors.New("heldout generation or unseen-pattern coverage invalid")}
 rss,err:=peakResidentBytes()
 if err!=nil{return w,err}
 if rss==0{return w,errors.New("missing real OS peak RSS")}
 allErr:=1-float64(correct)/float64(evaluated)
 unseenErr:=1-float64(unseenCorrect)/float64(unseen)
 if math.IsNaN(allErr)||math.IsNaN(unseenErr)||math.IsInf(allErr,0)||math.IsInf(unseenErr,0){return w,errors.New("nonfinite source accuracy")}
 learner:=newLearner(mode)
 w=workerResult{
  Schema:schema,Mode:mode,Regime:regime,Seed:seed,Episodes:episodes,
  FitStateCount:episodes*fitStates,HeldoutStateCount:episodes*testStates,
  EvaluatedCells:evaluated,CorrectCells:correct,UnseenCells:unseen,CorrectUnseen:unseenCorrect,
  ErrorRate:allErr,UnseenErrorRate:unseenErr,LogicalBytes:learner.LogicalBytes(),
  NeighborMessageReads:neighborReads,
  SourceSHA256:hex.EncodeToString(sourceHash.Sum(nil)),
  FitSHA256:hex.EncodeToString(fitHash.Sum(nil)),
  TruthSHA256:hex.EncodeToString(truthHash.Sum(nil)),
  PredictionSHA256:hex.EncodeToString(predHash.Sum(nil)),
  PeakRSSBytes:rss,MemoryMetric:"OS_PROCESS_PEAK_PHYSICAL_RSS_BYTES",
 }
 return w,nil
}
