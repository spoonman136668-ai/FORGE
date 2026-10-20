// O9 new source-free deterministic native benchmark, not scientific first use.
// Three distinct exact causal solvers receive identical public mathematical
// evidence; simulated intervention provenance is never called authentic.
package main

import (
  "encoding/json"
  "flag"
  "fmt"
  "hash/fnv"
  "os"
  "time"

  lcrm "github.com/spoonman136668-ai/forge/research/lcrm01"
)
const cases=60
const loops=256

type Sample struct{
  Schema string `json:"schema"`
  Arm string `json:"arm"`
  Rep int `json:"rep"`
  Episodes int `json:"episodes"`
  DoQueries int `json:"do_queries"`
  HardCertified int `json:"hard_certified"`
  SafeAbstentions int `json:"safe_abstentions"`
  HardFalsePositives int `json:"hard_false_positives"`
  Digest string `json:"digest"`
  ProcessCPUNs int64 `json:"process_cpu_ns"`
  WallElapsedNs int64 `json:"wall_elapsed_ns"`
  PeakRSSBytes int64 `json:"peak_rss_bytes"`
  NativeCPUClockCensored bool `json:"native_cpu_clock_censored"`
  SourceFirstUse bool `json:"source_first_use"`
  ScientificAccepted bool `json:"scientific_accepted"`
  OptimizerAdmitted bool `json:"optimizer_admitted"`
}
func op(law,a,b uint8)uint8{return (law>>((a<<1)|b))&1}
func observation(law,swap,p,q uint8)lcrm.O7PhysicalIntervention{
  a,b:=p,q
  if swap==1 {a,b=q,p}
  return lcrm.O7PhysicalIntervention{P:p,Q:q,Output:op(law,a,b),
    InterventionAttested:true,IndependentlyAssigned:true}
}
func require(ok bool,message string){if !ok{panic(message)}}

func main(){
  arm:=flag.String("arm","","compiled-version-space|independent-symbolic|original-anf")
  rep:=flag.Int("rep",-1,"separate whole-process replicate 0..4")
  flag.Parse()
  if(*arm!="compiled-version-space"&&*arm!="independent-symbolic"&&*arm!="original-anf")||
    *rep<0||*rep>=5{
    fmt.Fprintln(os.Stderr,"O9_INVALID_ARM_OR_REP");os.Exit(2)
  }
  startWall:=time.Now()
  startCPU,_,err:=lcrm.O2ProcessMetrics()
  if err!=nil{panic(err)}
  hash:=fnv.New64a()
  queries,hard,abstain:=0,0,0
  for round:=0;round<loops;round++{
    for i:=0;i<cases;i++{
      // New source-free mathematical generator; do not use the O8 schedule.
      law1:=uint8((i*11+round*3+7)%16)
      law2:=uint8((i*13+round*5+9)%16)
      swap1:=uint8((i/2+round)%2)
      swap2:=uint8((i/7+round/2)%2)
      known1:=uint8(1+(i+2*round)%4)
      known2:=uint8(1+(i/3+round*3)%4)
      exogenousGrounding:=((i+round)%5)!=0
      g1:=lcrm.O7Grounding{SemanticAPhysical:swap1,
        IndependentlyWitnessed:true,AuthenticatedOutsideOperator:true}
      g2:=lcrm.O7Grounding{SemanticAPhysical:swap2,
        IndependentlyWitnessed:true,AuthenticatedOutsideOperator:true}
      var one,two func(lcrm.O7PhysicalIntervention)error
      var ground1,ground2 func(lcrm.O7Grounding)error
      var predict func(a,b,c uint8)(uint8,bool,error)
      if *arm=="compiled-version-space"{
        x,y:=lcrm.NewO9CompiledPhysicalMemory(),lcrm.NewO9CompiledPhysicalMemory()
        one,two=x.Observe,y.Observe
        ground1,ground2=x.Ground,y.Ground
        predict=func(a,b,c uint8)(uint8,bool,error){
          return lcrm.O9ComposeTwoHopCompiled(x,y,a,b,c)
        }
      }else if *arm=="independent-symbolic"{
        x,y:=lcrm.NewO7PhysicalSymbolicControl(),lcrm.NewO7PhysicalSymbolicControl()
        one,two=x.Observe,y.Observe
        ground1,ground2=x.Ground,y.Ground
        predict=func(a,b,c uint8)(uint8,bool,error){
          return lcrm.O7ComposeTwoHopSymbolic(x,y,a,b,c)
        }
      }else{
        x,y:=&lcrm.O7AnchoredANF{},&lcrm.O7AnchoredANF{}
        one,two=x.Observe,y.Observe
        ground1,ground2=x.Ground,y.Ground
        predict=func(a,b,c uint8)(uint8,bool,error){
          return lcrm.O7ComposeTwoHopExact(x,y,a,b,c)
        }
      }
      if exogenousGrounding{
        require(ground1(g1)==nil&&ground2(g2)==nil,"O9_SYNTHETIC_ANCHOR_REJECTED")
      }
      for cell:=uint8(0);cell<known1;cell++{
        require(one(observation(law1,swap1,cell>>1,cell&1))==nil,
          "O9_FIRST_CONSISTENT_EVIDENCE_REJECTED")
      }
      for cell:=uint8(0);cell<known2;cell++{
        require(two(observation(law2,swap2,cell>>1,cell&1))==nil,
          "O9_SECOND_CONSISTENT_EVIDENCE_REJECTED")
      }
      for q:=uint8(0);q<8;q++{
        a,b,c:=(q>>2)&1,(q>>1)&1,q&1
        answer,certified,predErr:=predict(a,b,c)
        if predErr!=nil{panic(predErr)}
        truth:=op(law2,op(law1,a,b),c)
        code:=uint8(0)
        if certified{
          require(answer==truth,"O9_FALSE_HARD_CAUSAL_CERTIFICATE")
          hard++;code=1
        }else{abstain++}
        queries++
        out:=uint8(0)
        if certified{out=answer}
        if _,err:=hash.Write([]byte{uint8(i),uint8(round%256),q,code,out});err!=nil{
          panic(err)
        }
      }
    }
  }
  endCPU,peak,err:=lcrm.O2ProcessMetrics()
  if err!=nil{panic(err)}
  result:=Sample{Schema:"forge.lcrm01.o9.sourcefree-native-process.v1",
    Arm:*arm,Rep:*rep,Episodes:cases*loops,DoQueries:queries,
    HardCertified:hard,SafeAbstentions:abstain,HardFalsePositives:0,
    Digest:fmt.Sprintf("%016x",hash.Sum64()),
    ProcessCPUNs:endCPU-startCPU,WallElapsedNs:time.Since(startWall).Nanoseconds(),
    PeakRSSBytes:peak,NativeCPUClockCensored:endCPU-startCPU==0,
    SourceFirstUse:false,ScientificAccepted:false,OptimizerAdmitted:false}
  if result.PeakRSSBytes<=0||result.ProcessCPUNs<0||result.WallElapsedNs<=0||
    result.Episodes!=15360||result.DoQueries!=122880||
    result.HardCertified+result.SafeAbstentions!=result.DoQueries{
    panic("O9_NATIVE_RESOURCE_OR_COVERAGE_INVALID")
  }
  if err:=json.NewEncoder(os.Stdout).Encode(result);err!=nil{panic(err)}
}
