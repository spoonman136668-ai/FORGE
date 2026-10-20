package lcrm01

// O7 SOURCE-FREE mathematical feasibility: externally grounded semantic
// port mapping, query-blind binary causal law induction, two-hop composition.
// All evidence origin flags in these tests are SYNTHETIC; they do NOT
// attest an actual intervention source or independent scientific first use.

import "errors"

var (
 ErrO7Evidence=errors.New("LCRM_O7_UNTRUSTED_PHYSICAL_INTERVENTION")
 ErrO7Anchor=errors.New("LCRM_O7_UNTRUSTED_OR_MALFORMED_ROLE_ANCHOR")
 ErrO7Conflict=errors.New("LCRM_O7_PUBLIC_CAUSAL_EVIDENCE_CONFLICT")
 ErrO7Query=errors.New("LCRM_O7_UNSUPPORTED_SEMANTIC_DO_QUERY")
)

type O7PhysicalIntervention struct {
 P,Q,Output uint8
 InterventionAttested, IndependentlyAssigned bool
}
func (e O7PhysicalIntervention) valid()bool{
 return e.P<2&&e.Q<2&&e.Output<2&&
  e.InterventionAttested&&e.IndependentlyAssigned
}

// SemanticAPhysical: 0 means semantic A is physical P, 1 means A is Q.
// An observed output is never accepted as proof of this exogenous mapping.
type O7Grounding struct{
 SemanticAPhysical uint8
 IndependentlyWitnessed, AuthenticatedOutsideOperator bool
}
func(e O7Grounding)valid()bool{
 return e.SemanticAPhysical<2&&
  e.IndependentlyWitnessed&&e.AuthenticatedOutsideOperator
}

type O7AnchoredANF struct{
 laws [2]O6BinaryANFLearner // candidate semantic laws for both physical swaps
 hasGrounding bool
 grounding uint8
}
func(o *O7AnchoredANF)Ground(e O7Grounding)error{
 if !e.valid(){return ErrO7Anchor}
 if o.hasGrounding&&o.grounding!=e.SemanticAPhysical{return ErrO7Conflict}
 o.hasGrounding=true
 o.grounding=e.SemanticAPhysical
 return nil
}
func(o *O7AnchoredANF)Observe(e O7PhysicalIntervention)error{
 if !e.valid(){return ErrO7Evidence}
 // Update both orientation-conditioned GF(2) systems transactionally.
 // Thus an inconsistent row cannot mutate either legal hypothesis.
 next:=o.laws
 for orientation:=uint8(0);orientation<2;orientation++{
  a,c:=e.P,e.Q
  if orientation==1{a,c=c,a}
  x:=O6BinaryIntervention{A:a,B:c,Output:e.Output,
   InterventionAttested:true,IndependentlyAssigned:true}
  if err:=next[orientation].Learn(x);err!=nil{return ErrO7Conflict}
 }
 o.laws=next
 return nil
}
func(o *O7AnchoredANF)PossibleSemanticTables()uint16{
 var possible uint16
 for orientation:=uint8(0);orientation<2;orientation++{
  if o.hasGrounding&&o.grounding!=orientation{continue}
  for coeff:=uint8(0);coeff<16;coeff++{
   if o.laws[orientation].accepts(coeff){
    possible|=uint16(1)<<o6TruthTable(coeff)
   }
  }
 }
 return possible
}
func o7EvaluateTables(tables uint16,a,b uint8)(uint8,bool,error){
 if a>1||b>1{return 0,false,ErrO7Query}
 seen:=false
 var prediction uint8
 for law:=uint8(0);law<16;law++{
  if tables&(uint16(1)<<law)==0{continue}
  y:=o6TableValue(law,a,b)
  if seen&&prediction!=y{return 0,false,nil}
  seen=true;prediction=y
 }
 if !seen{return 0,false,ErrO7Conflict}
 return prediction,true,nil
}
func(o *O7AnchoredANF)PredictCanonical(a,b uint8)(uint8,bool,error){
 return o7EvaluateTables(o.PossibleSemanticTables(),a,b)
}

// Independent full symbolic control: 32 separate physical hypotheses.
// Unlike the learner it never uses ANF coefficients or pivot reduction.
type O7PhysicalSymbolicControl struct{
 hypotheses uint32 // (orientation<<4)|canonical 4-cell truth-table
 hasGrounding bool
 grounding uint8
}
func NewO7PhysicalSymbolicControl()*O7PhysicalSymbolicControl{
 return &O7PhysicalSymbolicControl{hypotheses:0xffffffff}
}
func(s *O7PhysicalSymbolicControl)Ground(e O7Grounding)error{
 if !e.valid(){return ErrO7Anchor}
 if s.hasGrounding&&s.grounding!=e.SemanticAPhysical{return ErrO7Conflict}
 var retained uint32
 for k:=uint(0);k<32;k++{
  if (s.hypotheses&(uint32(1)<<k))!=0 && uint8(k>>4)==e.SemanticAPhysical{
   retained|=uint32(1)<<k
  }
 }
 if retained==0{return ErrO7Conflict}
 s.hypotheses=retained
 s.hasGrounding=true;s.grounding=e.SemanticAPhysical
 return nil
}
func(s *O7PhysicalSymbolicControl)Observe(e O7PhysicalIntervention)error{
 if !e.valid(){return ErrO7Evidence}
 var retained uint32
 for k:=uint(0);k<32;k++{
  if s.hypotheses&(uint32(1)<<k)==0{continue}
  a,b:=e.P,e.Q
  if k>=16{a,b=b,a}
  if o6TableValue(uint8(k&15),a,b)==e.Output{
   retained|=uint32(1)<<k
  }
 }
 if retained==0{return ErrO7Conflict}
 s.hypotheses=retained
 return nil
}
func(s *O7PhysicalSymbolicControl)PossibleSemanticTables()uint16{
 var possible uint16
 for k:=uint(0);k<32;k++{
  if s.hypotheses&(uint32(1)<<k)!=0{
   possible|=uint16(1)<<(k&15)
  }
 }
 return possible
}
func(s *O7PhysicalSymbolicControl)PredictCanonical(a,b uint8)(uint8,bool,error){
 return o7EvaluateTables(s.PossibleSemanticTables(),a,b)
}
func o7TwoHopExact(firstTables,secondTables uint16,a,b,c uint8)(uint8,bool,error){
 if a>1||b>1||c>1{return 0,false,ErrO7Query}
 if firstTables==0||secondTables==0{return 0,false,ErrO7Conflict}
 seen:=false
 var answer uint8
 for first:=uint8(0);first<16;first++{
  if firstTables&(uint16(1)<<first)==0{continue}
  middle:=o6TableValue(first,a,b)
  for second:=uint8(0);second<16;second++{
   if secondTables&(uint16(1)<<second)==0{continue}
   y:=o6TableValue(second,middle,c)
   if seen&&answer!=y{return 0,false,nil}
   answer=y;seen=true
  }
 }
 if !seen{return 0,false,ErrO7Conflict}
 return answer,true,nil
}
func O7ComposeTwoHopExact(first,second *O7AnchoredANF,a,b,c uint8)(uint8,bool,error){
 if first==nil||second==nil{return 0,false,ErrO7Query}
 return o7TwoHopExact(first.PossibleSemanticTables(),second.PossibleSemanticTables(),a,b,c)
}
func O7ComposeTwoHopSymbolic(first,second *O7PhysicalSymbolicControl,a,b,c uint8)(uint8,bool,error){
 if first==nil||second==nil{return 0,false,ErrO7Query}
 return o7TwoHopExact(first.PossibleSemanticTables(),second.PossibleSemanticTables(),a,b,c)
}
