package lcrm01

// O6: source-free online causal induction for all sixteen Boolean
// two-input operators. The binary interaction A*B did not exist in O4.
// Evidence flags are synthetic feasibility fixtures, NOT origin attestations.
// Physical entity-port orientation is not inferred from an unknown law.

import "errors"

var (
 ErrO6Evidence = errors.New("LCRM_O6_UNTRUSTED_OR_INVALID_INTERVENTION")
 ErrO6Conflict = errors.New("LCRM_O6_CONTRADICTORY_INTERVENTION")
 ErrO6Query = errors.New("LCRM_O6_UNSUPPORTED_QUERY")
)

type O6BinaryIntervention struct {
 A, B, Output uint8
 InterventionAttested, IndependentlyAssigned bool
}
func o6ValidEvidence(e O6BinaryIntervention)bool{
 return e.A<2 && e.B<2 && e.Output<2 &&
  e.InterventionAttested && e.IndependentlyAssigned
}
func o6Cell(a,b uint8)uint8{return (a<<1)|b}
func o6ApplyANF(coeff,a,b uint8)uint8{
 return (coeff&1)^((coeff>>1)&1&a)^((coeff>>2)&1&b)^((coeff>>3)&1&a&b)
}
func o6TableValue(table,a,b uint8)uint8{
 return (table>>o6Cell(a,b))&1
}
func o6TruthTable(coeff uint8)uint8{
 var table uint8
 for a:=uint8(0);a<2;a++{
  for b:=uint8(0);b<2;b++{
   table|=o6ApplyANF(coeff,a,b)<<o6Cell(a,b)
  }
 }
 return table
}
// An incoming do(A,B) observation is a GF(2) equation in ANF
// coefficients c0,cA,cB,cAB. The learned mechanism stores a compact
// pivoted linear basis, not the hidden true coefficient vector.
func o6Equation(e O6BinaryIntervention)uint8{
 row:=uint8(1)|(e.A<<1)|(e.B<<2)|((e.A&e.B)<<3)
 return row|(e.Output<<4)
}
type O6BinaryANFLearner struct {basis [4]uint8; rank uint8}
func(m *O6BinaryANFLearner) Rank()int{return int(m.rank)}
func(m *O6BinaryANFLearner) Learn(e O6BinaryIntervention)error{
 if !o6ValidEvidence(e){return ErrO6Evidence}
 row:=o6Equation(e)
 for pivot:=3;pivot>=0;pivot--{
  if row&(1<<pivot)!=0 && m.basis[pivot]!=0 {row^=m.basis[pivot]}
 }
 if row&15==0{
  if row&16!=0{return ErrO6Conflict}
  return nil
 }
 for pivot:=3;pivot>=0;pivot--{
  if row&(1<<pivot)!=0{
   if m.basis[pivot]!=0 {panic("O6_GF2_PIVOT_INVARIANT")}
   m.basis[pivot]=row
   m.rank++
   return nil
  }
 }
 panic("O6_GF2_IMPOSSIBLE")
}
func(m *O6BinaryANFLearner) accepts(coeff uint8)bool{
 for _,r:=range m.basis{
  if r==0{continue}
  var parity uint8
  for k:=uint(0);k<4;k++{
   parity^=((r>>k)&1)*((coeff>>k)&1)
  }
  if parity!=(r>>4)&1{return false}
 }
 return true
}
func(m *O6BinaryANFLearner) ConsistentCount()int{
 count:=0
 for c:=uint8(0);c<16;c++{if m.accepts(c){count++}}
 return count
}
// Predict is exact and fail-closed: a learned coefficient estimate alone
// is never treated as a certificate. All legal coefficients must agree.
func(m *O6BinaryANFLearner) Predict(a,b uint8)(uint8,bool,error){
 if a>=2||b>=2{return 0,false,ErrO6Query}
 var answer uint8
 found:=false
 for c:=uint8(0);c<16;c++{
  if !m.accepts(c){continue}
  y:=o6ApplyANF(c,a,b)
  if found && y!=answer{return 0,false,nil}
  answer=y;found=true
 }
 if !found{return 0,false,ErrO6Conflict}
 return answer,true,nil
}
// Fully informed, equally evidenced independent symbolic comparator,
// storing a version space over raw four-cell truth tables, not ANF rows.
type O6BinarySymbolicControl struct {allowed uint16}
func NewO6BinarySymbolicControl()*O6BinarySymbolicControl{
 return &O6BinarySymbolicControl{allowed:0xffff}
}
func(s *O6BinarySymbolicControl) Observe(e O6BinaryIntervention)error{
 if !o6ValidEvidence(e){return ErrO6Evidence}
 var survivors uint16
 for table:=uint8(0);table<16;table++{
  if s.allowed&(1<<table)!=0 &&
     o6TableValue(table,e.A,e.B)==e.Output {survivors|=1<<table}
 }
 if survivors==0{return ErrO6Conflict}
 s.allowed=survivors
 return nil
}
func(s *O6BinarySymbolicControl) ConsistentCount()int{
 n:=0
 for k:=0;k<16;k++{if s.allowed&(1<<k)!=0{n++}}
 return n
}
func(s *O6BinarySymbolicControl) Predict(a,b uint8)(uint8,bool,error){
 if a>=2||b>=2{return 0,false,ErrO6Query}
 var answer uint8
 found:=false
 for table:=uint8(0);table<16;table++{
  if s.allowed&(1<<table)==0{continue}
  v:=o6TableValue(table,a,b)
  if found&&v!=answer{return 0,false,nil}
  found=true;answer=v
 }
 if !found{return 0,false,ErrO6Conflict}
 return answer,true,nil
}
// Swap the two UNGROUNDED physical entity ports. Under unrestricted
// unknown laws, every observed table admits two distinct descriptions:
// (f,identity) and (swap(f),swapped); no public output can distinguish.
func o6SwapPorts(table uint8)uint8{
 var swapped uint8
 for a:=uint8(0);a<2;a++{for b:=uint8(0);b<2;b++{
  swapped|=o6TableValue(table,b,a)<<o6Cell(a,b)
 }}
 return swapped
}
