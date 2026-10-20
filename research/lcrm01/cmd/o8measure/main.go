// LCRM O8: SOURCE-FREE resource screen only, NOT independently sourced science.
// One invocation is one standalone Go OS process; no original DEV replay.
package main

import (
 "encoding/json"
 "flag"
 "fmt"
 "hash/fnv"
 "os"

 lcrm "github.com/spoonman136668-ai/forge/research/lcrm01"
)

const cases = 48
const loops = 128

type Result struct {
 Schema string `json:"schema"`
 Arm string `json:"arm"`
 Rep int `json:"rep"`
 Cases int `json:"cases"`
 DoQueries int `json:"do_queries"`
 HardCertified int `json:"hard_certified"`
 Abstentions int `json:"abstentions"`
 HardFalsePositives int `json:"hard_false_positives"`
 OutputDigest string `json:"output_digest"`
 CompleteProcessCPU_NS int64 `json:"complete_process_cpu_ns"`
 PeakRSSBytes int64 `json:"peak_rss_bytes"`
 SourceFirstUse bool `json:"source_first_use"`
 ScientificAccepted bool `json:"scientific_accepted"`
 OptimizerAdmitted bool `json:"optimizer_admitted"`
}

func tableVal(law, a, b uint8)uint8 {
 return (law >> ((a<<1)|b)) & 1
}

func syntheticObservation(law, swap, p, q uint8)lcrm.O7PhysicalIntervention {
 a,b:=p,q
 if swap==1 { a,b=q,p }
 return lcrm.O7PhysicalIntervention{
  P:p,Q:q,Output:tableVal(law,a,b),
  InterventionAttested:true,IndependentlyAssigned:true,
 }
}

func assert(ok bool, message string){
 if !ok { panic(message) }
}

func main(){
 arm:=flag.String("arm","","learned-anf or exact-symbolic")
 rep:=flag.Int("rep",-1,"0..4 independent process repetition")
 flag.Parse()
 if (*arm!="learned-anf" && *arm!="exact-symbolic") || *rep<0 || *rep>=5{
  fmt.Fprintln(os.Stderr,"O8_INVALID_ARM_OR_REPETITION")
  os.Exit(2)
 }
 // Unmodified O2ProcessMetrics is OS-native process CPU and peak RSS.
 start,_,err:=lcrm.O2ProcessMetrics()
 if err!=nil{panic(err)}
 digest:=fnv.New64a()
 totalQueries, certified, abstentions:=0,0,0
 for round:=0;round<loops;round++{
  for i:=0;i<cases;i++{
   firstLaw:=uint8((i*7+3*round+11)%16)
   secondLaw:=uint8((i*5+round*9+3)%16)
   firstSwap:=uint8((i+round)%2)
   secondSwap:=uint8((i/3+round)%2)
   firstKnown:=uint8(1+(i%4))
   secondKnown:=uint8(1+((i/3)%4))
   grounding1:=lcrm.O7Grounding{SemanticAPhysical:firstSwap,
    IndependentlyWitnessed:true,AuthenticatedOutsideOperator:true}
   grounding2:=lcrm.O7Grounding{SemanticAPhysical:secondSwap,
    IndependentlyWitnessed:true,AuthenticatedOutsideOperator:true}
   var observed [2]func(lcrm.O7PhysicalIntervention)error
   var grounded [2]func(lcrm.O7Grounding)error
   var predict func(a,b,c uint8)(uint8,bool,error)
   if *arm=="learned-anf"{
    first,second:=&lcrm.O7AnchoredANF{},&lcrm.O7AnchoredANF{}
    observed=[2]func(lcrm.O7PhysicalIntervention)error{first.Observe,second.Observe}
    grounded=[2]func(lcrm.O7Grounding)error{first.Ground,second.Ground}
    predict=func(a,b,c uint8)(uint8,bool,error){
     return lcrm.O7ComposeTwoHopExact(first,second,a,b,c)
    }
   }else{
    first,second:=lcrm.NewO7PhysicalSymbolicControl(),lcrm.NewO7PhysicalSymbolicControl()
    observed=[2]func(lcrm.O7PhysicalIntervention)error{first.Observe,second.Observe}
    grounded=[2]func(lcrm.O7Grounding)error{first.Ground,second.Ground}
    predict=func(a,b,c uint8)(uint8,bool,error){
     return lcrm.O7ComposeTwoHopSymbolic(first,second,a,b,c)
    }
   }
   assert(grounded[0](grounding1)==nil&&grounded[1](grounding2)==nil,
    "O8_SYNTHETIC_GROUNDING_REJECTED")
   for cell:=uint8(0);cell<firstKnown;cell++{
    assert(observed[0](syntheticObservation(firstLaw,firstSwap,cell>>1,cell&1))==nil,
     "O8_FIRST_PUBLIC_EVIDENCE_REJECTED")
   }
   for cell:=uint8(0);cell<secondKnown;cell++{
    assert(observed[1](syntheticObservation(secondLaw,secondSwap,cell>>1,cell&1))==nil,
     "O8_SECOND_PUBLIC_EVIDENCE_REJECTED")
   }
   for x:=uint8(0);x<8;x++{
    a,b,c:=(x>>2)&1,(x>>1)&1,x&1
    answer,ok,predErr:=predict(a,b,c)
    if predErr!=nil{panic(predErr)}
    truth:=tableVal(secondLaw,tableVal(firstLaw,a,b),c)
    outcome:=uint8(0)
    if ok{
     assert(answer==truth,"O8_FALSE_HARD_CAUSAL_CERTIFICATION")
     certified++
     outcome=answer
    }else{abstentions++}
    totalQueries++
    bit:=uint8(0)
    if ok{bit=1}
    if _,err:=digest.Write([]byte{uint8(i),uint8(round%256),x,bit,outcome});err!=nil{panic(err)}
   }
  }
 }
 done,peak,err:=lcrm.O2ProcessMetrics()
 if err!=nil{panic(err)}
 result:=Result{
  Schema:"forge.lcrm01.o8.sourcefree-native-matched-process.v1",
  Arm:*arm,Rep:*rep,Cases:cases*loops,DoQueries:totalQueries,
  HardCertified:certified,Abstentions:abstentions,HardFalsePositives:0,
  OutputDigest:fmt.Sprintf("%016x",digest.Sum64()),
  CompleteProcessCPU_NS:done-start,PeakRSSBytes:peak,
  SourceFirstUse:false,ScientificAccepted:false,OptimizerAdmitted:false,
 }
 if result.CompleteProcessCPU_NS<=0 || result.PeakRSSBytes<=0 ||
   result.DoQueries!=49152 || result.HardCertified+result.Abstentions!=result.DoQueries {
  panic("O8_NATIVE_RESOURCE_OR_COVERAGE_INVALID")
 }
 if err:=json.NewEncoder(os.Stdout).Encode(result);err!=nil{panic(err)}
}
