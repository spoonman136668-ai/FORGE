package lcrm01

// O4 source-free, query-blind intervention-grounded law learning.
// This does not assert authenticated evidence or unseen scientific transfer.
import "errors"

var (
 ErrO4Evidence = errors.New("LCRM_O4_UNTRUSTED_OR_INVALID_INTERVENTION")
 ErrO4Conflict = errors.New("LCRM_O4_CONTRADICTORY_INTERVENTION")
 ErrO4Program = errors.New("LCRM_O4_UNSUPPORTED_CAUSAL_PROGRAM")
)
const O4Roles=3
const O4Parameters=6
const O4ProgramEdges=12

type O4Intervention struct {
 Role, Input, Output uint8
 InterventionAttested, IndependentlyAssigned bool
}
// Synthetic flags are not independent provider authentication.
func o4ValidEvidence(e O4Intervention) bool {
 return e.Role<O4Roles && e.Input<2 && e.Output<2 && e.InterventionAttested && e.IndependentlyAssigned
}
// Online six-coordinate learner; outcome signs are fitted from input/output
// evidence without knowing the future query or the underlying operator.
type O4RuleLearner struct { coord [O4Roles][2]int8; updates uint8 }
func (m *O4RuleLearner) Learn(e O4Intervention) error {
 if !o4ValidEvidence(e) {return ErrO4Evidence}
 next:=int8(-1);if e.Output==1 {next=1}
 prev:=m.coord[e.Role][e.Input]
 if prev!=0 && prev!=next {return ErrO4Conflict}
 if prev==0 {m.coord[e.Role][e.Input]=next;m.updates++}
 return nil
}
func (m *O4RuleLearner) LearnedCoordinates()int {return O4Parameters}
func (m *O4RuleLearner) SuccessfulUpdates()int{return int(m.updates)}
func o4ProgramValid(program [O4ProgramEdges]uint8,start uint8) bool {
 if start>1 {return false}
 for _,r:=range program {if r>=O4Roles{return false}}
 return true
}
func o4Certify(masks [O4Roles]uint8,program [O4ProgramEdges]uint8,start uint8)(uint8,bool,error){
 if !o4ProgramValid(program,start){return 0,false,ErrO4Program}
 for _,mask:=range masks {if mask==0{return 0,false,ErrO4Conflict}}
 found:=false;var answer uint8
 for f0:=O3Unary(0);f0<4;f0++ {if masks[0]&(1<<f0)==0{continue}
  for f1:=O3Unary(0);f1<4;f1++ {if masks[1]&(1<<f1)==0{continue}
   for f2:=O3Unary(0);f2<4;f2++ {if masks[2]&(1<<f2)==0{continue}
    ops:=[O4Roles]O3Unary{f0,f1,f2}
    y:=start
    for _,role:=range program {y=o3ApplyExact(ops[role],y)}
    if found && answer!=y{return 0,false,nil}
    answer=y;found=true
   }
  }
 }
 if !found{return 0,false,ErrO4Conflict}
 return answer,true,nil
}
// Learned coordinates are NOT a certificate; enumerate every
// globally consistent recurrent-role causal law before answering.
func (m *O4RuleLearner) Counterfactual(program [O4ProgramEdges]uint8,start uint8)(uint8,bool,error){
 var masks [O4Roles]uint8
 for r:=0;r<O4Roles;r++ {for f:=O3Unary(0);f<4;f++{
  compatible:=true
  for x:=uint8(0);x<2;x++{
   observed:=m.coord[r][x]
   if observed!=0 && (observed==1)!=(o3ApplyExact(f,x)==1){compatible=false}
  }
  if compatible {masks[r]|=1<<f}
 }}
 return o4Certify(masks,program,start)
}
// Equal-information full symbolic version-space competitor.
type O4SymbolicControl struct { masks [O4Roles]uint8 }
func NewO4SymbolicControl()*O4SymbolicControl{
 return &O4SymbolicControl{masks:[O4Roles]uint8{15,15,15}}
}
func (s *O4SymbolicControl) Observe(e O4Intervention)error{
 if !o4ValidEvidence(e){return ErrO4Evidence}
 keep:=uint8(0)
 for op:=O3Unary(0);op<4;op++{
  if s.masks[e.Role]&(1<<op)!=0 && o3ApplyExact(op,e.Input)==e.Output {keep|=1<<op}
 }
 if keep==0{return ErrO4Conflict}
 s.masks[e.Role]=keep
 return nil
}
func (s *O4SymbolicControl) Counterfactual(program [O4ProgramEdges]uint8,start uint8)(uint8,bool,error){
 return o4Certify(s.masks,program,start)
}
