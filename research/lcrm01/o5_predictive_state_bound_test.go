package lcrm01

import (
 "errors"
 "testing"
)

func TestO5Exhaustive729DistinctPredictiveSignaturesAndExactSymbolicPeer(t *testing.T){
 signatures:=make(map[[O5Coordinates]uint8]uint16,O5PublicStates)
 programs:=o4Programs()
 futureChecks:=0
 counterfactualChecks:=0
 for code:=0;code<O5PublicStates;code++ {
  memory:=&O5PredictiveMemory{}
  symbolic:=NewO4SymbolicControl()
  learner:=&O4RuleLearner{}
  // Reconstruct the identical attested public evidence without supplying
  // a future query to any model during its append/learning phase.
  for k:=0;k<O5Coordinates;k++{
   trit:=o5Trit(uint16(code),k)
   if trit==0 {continue}
   e:=O4Intervention{Role:uint8(k/2),Input:uint8(k%2),
     Output:uint8(trit-1),InterventionAttested:true,
     IndependentlyAssigned:true}
   if err:=memory.Observe(e);err!=nil{t.Fatal(err)}
   if err:=symbolic.Observe(e);err!=nil{t.Fatal(err)}
   if err:=learner.Learn(e);err!=nil{t.Fatal(err)}
  }
  if memory.Code()!=uint16(code) {t.Fatalf("canonical code mismatch %d %d",code,memory.Code())}
  var signature [O5Coordinates]uint8
  for k:=0;k<O5Coordinates;k++{
   role,input:=uint8(k/2),uint8(k%2)
   got,err:=memory.FutureDoMask(role,input)
   if err!=nil{t.Fatal(err)}
   possible:=uint8(0)
   for f:=O3Unary(0);f<4;f++{
    if symbolic.masks[role]&(1<<f)!=0 {
     possible |= 1<<o3ApplyExact(f,input)
    }
   }
   if got!=possible{t.Fatalf("future do mismatch code=%d query=%d got=%d peer=%d",code,k,got,possible)}
   signature[k]=got
   futureChecks++
  }
  if prev,exists:=signatures[signature];exists {
   t.Fatalf("loss of predictive distinguishability state=%d collided=%d",code,prev)
  }
  signatures[signature]=uint16(code)
  for _,program:=range programs{
   for start:=uint8(0);start<2;start++{
    got,ok,err:=memory.Counterfactual(program,start)
    peer,peerOK,peerErr:=symbolic.Counterfactual(program,start)
    fitted,fittedOK,fittedErr:=learner.Counterfactual(program,start)
    if err!=nil||peerErr!=nil||fittedErr!=nil ||
       ok!=peerOK||ok!=fittedOK||(ok&&(got!=peer||got!=fitted)) {
      t.Fatalf("exact partial counterfactual mismatch state=%d start=%d",code,start)
    }
    counterfactualChecks++
   }
  }
 }
 if len(signatures)!=729||O5MinimumExactBits()!=10{
  t.Fatalf("theoretical sufficient-memory lower bound failed states=%d bits=%d",len(signatures),O5MinimumExactBits())
 }
 if futureChecks!=729*6||counterfactualChecks!=729*12{
  t.Fatalf("incomplete property %d %d",futureChecks,counterfactualChecks)
 }
 t.Logf("O5_EXACT_DISTINCT_PREDICTIVE_STATES=%d O5_LOWER_BOUND_BITS=%d O5_FUTURE_DO_CHECKS=%d O5_COUNTERFACTUAL_PARITY=%d",len(signatures),O5MinimumExactBits(),futureChecks,counterfactualChecks)
}

func TestO5CausalSourceAuthenticationAndContradictionFailClosed(t *testing.T){
 m:=&O5PredictiveMemory{}
 for _,e:=range []O4Intervention{
  {Role:0,Input:0,Output:1,InterventionAttested:false,IndependentlyAssigned:true},
  {Role:0,Input:0,Output:1,InterventionAttested:true,IndependentlyAssigned:false},
  {Role:5,Input:0,Output:1,InterventionAttested:true,IndependentlyAssigned:true},
 }{
  if !errors.Is(m.Observe(e),ErrO4Evidence) || m.Code()!=0{
   t.Fatal("unqualified causal evidence mutated state")
  }
 }
 v,err:=m.FutureDoMask(0,0)
 if err!=nil||v!=3{t.Fatal("unknown intervention output was guessed")}
 good:=O4Intervention{Role:0,Input:0,Output:1,InterventionAttested:true,IndependentlyAssigned:true}
 if err:=m.Observe(good);err!=nil{t.Fatal(err)}
 previous:=m.Code()
 if err:=m.Observe(good);err!=nil||m.Code()!=previous{t.Fatal("repeat public observation changed state")}
 bad:=good;bad.Output=0
 if !errors.Is(m.Observe(bad),ErrO4Conflict)||m.Code()!=previous{
  t.Fatal("contradictory evidence admitted or changed state")
 }
 if _,err:=m.FutureDoMask(4,0);!errors.Is(err,ErrO5State){t.Fatal("invalid role allowed")}
 if _,err:=m.FutureDoMask(0,2);!errors.Is(err,ErrO5State){t.Fatal("invalid input allowed")}
 var program [O4ProgramEdges]uint8
 if _,known,err:=m.Counterfactual(program,2);!errors.Is(err,ErrO4Program)||known{
  t.Fatal("unsupported future query was certified")
 }
 corrupted:=&O5PredictiveMemory{code:729}
 if _,known,err:=corrupted.Counterfactual(program,0);!errors.Is(err,ErrO5State)||known{
  t.Fatal("out-of-range predictive state was accepted")
 }
}

func TestO5PredictiveMemoryEquivariantUnderAllRoleRenamings(t *testing.T){
 perms:=[6][3]uint8{{0,1,2},{0,2,1},{1,0,2},{1,2,0},{2,0,1},{2,1,0}}
 programs:=o4Programs()
 checks:=0
 for code:=0;code<O5PublicStates;code++{
  base:=&O5PredictiveMemory{code:uint16(code)}
  for _,renaming:=range perms{
   renamed:=&O5PredictiveMemory{}
   for k:=0;k<O5Coordinates;k++{
    trit:=o5Trit(base.Code(),k)
    if trit==0{continue}
    e:=O4Intervention{Role:renaming[k/2],Input:uint8(k%2),Output:uint8(trit-1),
      InterventionAttested:true,IndependentlyAssigned:true}
    if err:=renamed.Observe(e);err!=nil{t.Fatal(err)}
   }
   for _,program:=range programs{
    var mapped [O4ProgramEdges]uint8
    for i,role:=range program{mapped[i]=renaming[role]}
    for start:=uint8(0);start<2;start++{
     want,cert,err:=base.Counterfactual(program,start)
     got,newCert,newErr:=renamed.Counterfactual(mapped,start)
     if err!=nil||newErr!=nil||cert!=newCert||(cert&&got!=want){
      t.Fatalf("role renaming changed certificate state=%d",code)
     }
     checks++
    }
   }
  }
 }
 if checks!=729*6*6*2 {t.Fatalf("role-equivariance coverage incomplete %d",checks)}
 t.Logf("O5_ROLE_EQUIVARIANCE_EXACT_CHECKS=%d",checks)
}
