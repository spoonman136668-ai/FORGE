package lcrm01

import (
 "errors"
 "reflect"
 "testing"
)

func TestO3AllBooleanOperatorsAssocAndIdentity(t *testing.T){
 for before:=O3Unary(0);before<4;before++{
  if x,_:=O3Compose(O3Identity,before);x!=before {t.Fatalf("left identity %d: %d",before,x)}
  if x,_:=O3Compose(before,O3Identity);x!=before {t.Fatalf("right identity %d: %d",before,x)}
  for after:=O3Unary(0);after<4;after++{
   joined,_:=O3Compose(after,before)
   for bit:=uint8(0);bit<2;bit++{
    y1,_:=O3Apply(joined,bit)
    tmp,_:=O3Apply(before,bit)
    y2,_:=O3Apply(after,tmp)
    if y1!=y2 {t.Fatalf("composition mismatch %d %d %d",after,before,bit)}
   }
   for final:=O3Unary(0);final<4;final++ {
    ab,_:=O3Compose(after,before)
    lhs,_:=O3Compose(final,ab)
    bc,_:=O3Compose(final,after)
    rhs,_:=O3Compose(bc,before)
    if lhs!=rhs {t.Fatalf("not associative %d %d %d",final,after,before)}
   }
  }
 }
 if _,err:=O3Compose(4,O3Identity);!errors.Is(err,ErrInvalid){t.Fatal("unregistered operator accepted")}
 if _,err:=O3Apply(O3Not,2);!errors.Is(err,ErrInvalid){t.Fatal("nonboolean input accepted")}
}
func o3Construct(words [12]O3Unary,offset int)(*O3ComposedMemory,*O3LastEightControl,error){
 m:=NewO3ComposedMemory()
 raw:=&O3LastEightControl{}
 for i,op:=range words{
  e:=O3Edge{From:i+offset,To:i+offset+1,PublicOperator:op}
  if err:=m.Append(e);err!=nil {return nil,nil,err}
  if err:=raw.Append(e);err!=nil{return nil,nil,err}
  if m.PhysicalSlots()>O3SlotsCap {return nil,nil,ErrBudget}
 }
 return m,raw,nil
}
func o3Direct(words [12]O3Unary,input uint8) uint8 {
 y:=input
 for _,w:=range words {y=o3ApplyExact(w,y)}
 return y
}
func TestO3SourceFreeAllFourEdgeBlocks(t *testing.T){
 checked:=0
 // Exhaust every 4-edge public operator block (4^4=256), then vary
 // independently the next eight operators using four frozen transformations.
 // No scientific TRAIN/DEV sample, hidden label or learned rule is loaded.
 for encoded:=0;encoded<256;encoded++ {
  var a [12]O3Unary
  for i:=0;i<4;i++ {a[i]=O3Unary((encoded>>(2*i))&3)}
  for shift:=0;shift<4;shift++ {
   for i:=4;i<12;i++ {
    a[i]=O3Unary((encoded>>(2*((i+shift)%4)))&3)
   }
   for _,offset:=range []int{0,1500} {
    m,raw,err:=o3Construct(a,offset)
    if err!=nil{t.Fatal(err)}
    if m.Count()!=12||m.PhysicalSlots()!=3 {t.Fatalf("slot cap regression: %d",m.PhysicalSlots())}
    if raw.count!=12 {t.Fatal("raw control did not receive all events")}
    for input:=uint8(0);input<2;input++{
     got,err:=m.WholePathCounterfactual(offset,offset+12,input)
     if err!=nil||got!=o3Direct(a,input){
      t.Fatalf("unsound public composition block=%d shift=%d offset=%d bit=%d got=%d err=%v",
        encoded,shift,offset,input,got,err)
     }
     if _,err:=raw.WholePathCounterfactual(offset,offset+12,input);!errors.Is(err,ErrO3Query) {
       t.Fatal("raw 8-slot memory guessed missing-prefix outcome")
     }
     checked++
    }
   }
  }
 }
 if checked!=4096 {t.Fatalf("finite structural coverage: %d",checked)}
}
func TestO3PrefixIndistinguishableToFIFOButDistinctCounterfactual(t *testing.T){
 var a,b [12]O3Unary
 for i:=range a {a[i]=O3Identity;b[i]=O3Identity}
 b[0]=O3Not
 ma,ra,err:=o3Construct(a,0);if err!=nil{t.Fatal(err)}
 mb,rb,err:=o3Construct(b,0);if err!=nil{t.Fatal(err)}
 if !reflect.DeepEqual(ra.edges,rb.edges){t.Fatal("raw tails differ; counterexample invalid")}
 ya,ea:=ma.WholePathCounterfactual(0,12,0)
 yb,eb:=mb.WholePathCounterfactual(0,12,0)
 if ea!=nil||eb!=nil||ya==yb {t.Fatalf("prefix indistinguishability not witnessed %d %d %v %v",ya,yb,ea,eb)}
 // Best equally informed symbolic compiled control can store precisely the
 // same three segment functions, hence it ties; NO learned advantage.
 symbolicA:=NewO3ComposedMemory()
 for i,op:=range a {if err:=symbolicA.Append(O3Edge{i,i+1,op});err!=nil{t.Fatal(err)}}
 sy,err:=symbolicA.WholePathCounterfactual(0,12,0)
 if err!=nil||sy!=ya{t.Fatal("strong symbolic equal-slot control missed output")}
}
func TestO3FailClosedAndObservationalCausalAmbiguity(t *testing.T){
 m:=NewO3ComposedMemory()
 if _,err:=m.WholePathCounterfactual(0,12,0);!errors.Is(err,ErrO3Query){
  t.Fatal("incomplete chain certified")
 }
 if err:=m.Append(O3Edge{0,1,O3Identity});err!=nil{t.Fatal(err)}
 if err:=m.Append(O3Edge{19,20,O3Identity});!errors.Is(err,ErrO3Path){
  t.Fatal("disconnected relation admitted")
 }
 if m.Count()!=1 {t.Fatal("invalid edge mutated state")}
 if err:=m.Append(O3Edge{1,2,5});!errors.Is(err,ErrO3Path){t.Fatal("unknown function accepted")}
 if m.Count()!=1 {t.Fatal("unknown function mutated state")}
 if !O3SourceFreeIndistinguishability(){t.Fatal("confounded observation treated as identified intervention")}
}
