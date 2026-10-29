package main

import (
 "testing"
)

func TestACC37FrozenDimensionsAndSourceOnlyWorkload(t *testing.T){
 if N!=128||K!=256||Batches!=64||Sessions!=8||Trials!=5{
  t.Fatal("ACC37 original prereg dimensions drift")
 }
 for _,scene:=range []string{"dense","sparse"}{
  b:=data(scene,0,0)
  zero,nonzero:=0,0
  for n:=0;n<N;n++{for k:=0;k<K;k++{
   if b.W[n][k]<-1||b.W[n][k]>1{t.Fatal("non-ternary source weight")}
   if b.W[n][k]==0{zero++}else{nonzero++}
  }}
  if zero+nonzero!=N*K||nonzero==0{t.Fatal("incomplete kernel")}
  if scene=="dense"&&!(zero>2500&&zero<7000){t.Fatal("dense weight distribution drift")}
  if scene=="sparse"&&!(zero>24000&&zero<29000){t.Fatal("sparse weight distribution drift")}
 }
}
func TestACC37FourArmsExactBitwiseOutputs(t *testing.T){
 for _,scene:=range []string{"dense","sparse"}{
  b:=data(scene,3,12)
  base:=evaluate(&b,"base")
  for _,mode:=range []string{"ternary","fused","both"}{
   got:=evaluate(&b,mode)
   for i:=0;i<N;i++{if (*base)[i]!=(*got)[i]{
    t.Fatalf("ACC37 %s %s differs at output %d",scene,mode,i)
   }}
  }
 }
}
func TestACC37AllActualSourceFreeWorkerSHAAndCost(t *testing.T){
 for _,scene:=range []string{"dense","sparse"}{
  base,e:=worker("base",scene);if e!=nil{t.Fatal(e)}
  if base.Rows!=N*Batches*Sessions||base.SHA256==""||
   base.GoRuntimeSysBytes==0||base.TotalAllocBytes==0{t.Fatal("real CPU/allocator evidence malformed")}
  for _,mode:=range []string{"ternary","fused","both"}{
   w,e:=worker(mode,scene)
   if e!=nil||w.SHA256!=base.SHA256||w.Rows!=base.Rows{
    t.Fatalf("full original source bitwise parity failed %s %s %v",scene,mode,e)
   }
  }
 }
}
func TestACC37InvalidSourceOrModeFailClosed(t *testing.T){
 if _,e:=worker("oracle","dense");e==nil{t.Fatal("unregistered oracle accepted")}
 if _,e:=worker("base","new_unregistered_source_family");e==nil{t.Fatal("unregistered scene accepted")}
 if Schema!="forge.acc37.u11-u15.actual-go-kernel.v1"{t.Fatal("scope changed")}
}
func TestACC37BiasClampDoesNotChangeKernelResults(t *testing.T){
 b:=data("dense",4,31)
 for n:=0;n<N;n++{b.Bias[n]=32767}
 baseline:=evaluate(&b,"base")
 for _,mode:=range []string{"ternary","fused","both"}{
  result:=evaluate(&b,mode)
  for i:=range baseline{if (*baseline)[i]!=(*result)[i]{
   t.Fatal("overflow/saturation changed actual source result")
  }}
 }
}
