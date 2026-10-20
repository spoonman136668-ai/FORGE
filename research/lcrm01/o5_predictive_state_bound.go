package lcrm01

// O5 source-free minimum-sufficient predictive causal memory.
// Pre-supplied Boolean unary vocabulary only: no new causal law learned.
// Query-blind state records interventions but never a future query.
// Ten *information* bits are necessary for all 729 partial public states;
// this uint16 implementation occupies 16 physical bits.
import "errors"

var ErrO5State = errors.New("LCRM_O5_INVALID_PREDICTIVE_STATE")

const (
 O5Coordinates = 6
 O5PublicStates = 729 // 3^6
 O5InformationBits = 10
)
type O5PredictiveMemory struct { code uint16 }
// Trit code: 0 = unobserved, 1 = observed output zero, 2 = observed output one.
func o5Pow3(k int) uint16 {
 p:=uint16(1)
 for i:=0;i<k;i++{p*=3}
 return p
}
func o5Trit(code uint16,k int) uint16 {
 return (code/o5Pow3(k))%3
}
func (m *O5PredictiveMemory) Code() uint16 {return m.code}
func (m *O5PredictiveMemory) Observe(e O4Intervention) error {
 if !o4ValidEvidence(e){return ErrO4Evidence}
 k:=int(e.Role)*2+int(e.Input)
 old:=o5Trit(m.code,k)
 newTrit:=uint16(e.Output)+1
 if old!=0 && old!=newTrit {return ErrO4Conflict}
 if old==0 {m.code+=newTrit*o5Pow3(k)}
 return nil
}
// Direct future do(role,input) forecast. Unknown is never a guessed answer.
// Bit0 indicates possible output 0; bit1 indicates possible output 1.
func (m *O5PredictiveMemory) FutureDoMask(role,input uint8)(uint8,error){
 if role>=O4Roles||input>1{return 0,ErrO5State}
 switch o5Trit(m.code,int(role)*2+int(input)){
 case 0:return 3,nil
 case 1:return 1,nil
 case 2:return 2,nil
 default:return 0,ErrO5State
 }
}
func (m *O5PredictiveMemory) Counterfactual(program [O4ProgramEdges]uint8,start uint8)(uint8,bool,error){
 if !o4ProgramValid(program,start){return 0,false,ErrO4Program}
 if m.code>=O5PublicStates {return 0,false,ErrO5State}
 var masks [O4Roles]uint8
 for role:=0;role<O4Roles;role++{
  for f:=O3Unary(0);f<4;f++{
   valid:=true
   for x:=uint8(0);x<2;x++{
    observed:=o5Trit(m.code,role*2+int(x))
    if observed!=0 && uint8(observed-1)!=o3ApplyExact(f,x) {valid=false}
   }
   if valid{masks[role]|=1<<f}
  }
 }
 return o4Certify(masks,program,start)
}
// Canonical lower bound. 2^9 < 3^6 <= 2^10; no learned encoding can
// distinguish all 729 predictions in fewer than ten information bits.
func O5MinimumExactBits() int {
 states:=O5PublicStates
 bits:=0;capacity:=1
 for capacity<states {capacity*=2;bits++}
 return bits
}
