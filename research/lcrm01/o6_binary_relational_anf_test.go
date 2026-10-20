package lcrm01

import (
 "errors"
 "testing"
)

func o6Fixture(a,b,out uint8)O6BinaryIntervention {
 return O6BinaryIntervention{A:a,B:b,Output:out,
   InterventionAttested:true,IndependentlyAssigned:true}
}
func TestO6CompleteBinaryLawANFAndExactSymbolicParity(t *testing.T){
 truthFunctions:=map[uint8]bool{}
 checks:=0
 for c:=uint8(0);c<16;c++{
  table:=o6TruthTable(c)
  if truthFunctions[table]{t.Fatalf("O6_ANF_MAP_NONINJECTIVE coeff=%d",c)}
  truthFunctions[table]=true
  for subset:=uint8(0);subset<16;subset++{
   learned:=&O6BinaryANFLearner{}
   peer:=NewO6BinarySymbolicControl()
   for cell:=uint8(0);cell<4;cell++{
    if subset&(1<<cell)==0{continue}
    a,b:=cell>>1,cell&1
    evidence:=o6Fixture(a,b,o6TableValue(table,a,b))
    if err:=learned.Learn(evidence);err!=nil{t.Fatal(err)}
    if err:=peer.Observe(evidence);err!=nil{t.Fatal(err)}
   }
   if learned.ConsistentCount()!=peer.ConsistentCount() {
    t.Fatalf("O6_VERSION_SPACE_MISMATCH true=%d subset=%d",c,subset)
   }
   if subset==15 && (learned.Rank()!=4 || learned.ConsistentCount()!=1) {
    t.Fatalf("O6_COMPLETE_OBSERVATION_DID_NOT_IDENTIFY true=%d",c)
   }
   for cell:=uint8(0);cell<4;cell++{
    a,b:=cell>>1,cell&1
    actual,cert,err:=learned.Predict(a,b)
    baseline,peerCert,peerErr:=peer.Predict(a,b)
    if err!=nil||peerErr!=nil||cert!=peerCert||
       (cert&&(actual!=baseline||actual!=o6TableValue(table,a,b))) {
      t.Fatalf("O6_CERTIFICATION_DISAGREEMENT law=%d subset=%d query=%d",c,subset,cell)
    }
    if subset&(1<<cell)!=0 && !cert {
      t.Fatalf("O6_PUBLIC_INTERVENTION_NOT_PREDICTABLE")
    }
    checks++
   }
  }
 }
 if len(truthFunctions)!=16||checks!=1024{
  t.Fatalf("O6_INCOMPLETE_BINARY_LAW_TEST functions=%d checks=%d",len(truthFunctions),checks)
 }
 t.Logf("O6_OUT_OF_UNARY_TRUE_LAWS=%d O6_COMPLETE_SOURCEFREE_CERTIFICATE_COMPARISONS=%d O6_ERRORS=0",len(truthFunctions),checks)
}
func TestO6AllEightyOnePartialPublicBeliefStates(t *testing.T){
 signatures:=map[[4]uint8]bool{}
 futureChecks:=0
 for code:=0;code<81;code++{
  learner:=&O6BinaryANFLearner{}
  peer:=NewO6BinarySymbolicControl()
  state:=code
  var expected [4]uint8
  for cell:=uint8(0);cell<4;cell++ {
   ternary:=uint8(state%3);state/=3
   expected[cell]=ternary
   if ternary==0{continue}
   e:=o6Fixture(cell>>1,cell&1,ternary-1)
   if err:=learner.Learn(e);err!=nil{t.Fatal(err)}
   if err:=peer.Observe(e);err!=nil{t.Fatal(err)}
  }
  var signature [4]uint8
  for cell:=uint8(0);cell<4;cell++{
   got,cert,err:=learner.Predict(cell>>1,cell&1)
   sym,symOK,symErr:=peer.Predict(cell>>1,cell&1)
   if err!=nil||symErr!=nil||cert!=symOK||(cert&&got!=sym){
    t.Fatalf("O6_PUBLIC_BELIEF_CERTIFICATE_DISAGREEMENT state=%d",code)
   }
   if cert{signature[cell]=got+1}
   futureChecks++
  }
  if signature!=expected{
   t.Fatalf("O6_QUERY_BLIND_FUTURE_SIGNATURE_LOSS state=%d expected=%v got=%v",code,expected,signature)
  }
  if signatures[signature]{t.Fatalf("O6_PREDICTIVE_STATE_COLLISION state=%d",code)}
  signatures[signature]=true
 }
 if len(signatures)!=81||futureChecks!=324{
  t.Fatalf("O6_PARTIAL_BELIEF_COVERAGE short count=%d checks=%d",len(signatures),futureChecks)
 }
 t.Logf("O6_QUERY_BLIND_DISTINCT_PUBLIC_PREDICTIVE_STATES=%d O6_PARTIAL_QUERY_CHECKS=%d O6_INFORMATION_FLOOR_BITS=7",len(signatures),futureChecks)
}
func TestO6LatentEntityPortBindingGaugeIsUnidentifiable(t *testing.T){
 explanations:=[16]int{}
 symmetric:=0
 checks:=0
 for law:=uint8(0);law<16;law++{
  if o6SwapPorts(law)==law{symmetric++}
  for swapped:=0;swapped<2;swapped++{
   observed:=law
   if swapped==1{observed=o6SwapPorts(law)}
   explanations[observed]++
   for cell:=uint8(0);cell<4;cell++{
    a,b:=cell>>1,cell&1
    y:=o6TableValue(observed,a,b)
    modelA:=o6TableValue(law,a,b)
    modelB:=o6TableValue(law,b,a)
    if swapped==0 && y!=modelA{t.Fatal("O6_LATENT_MAP_IDENTITY_FAILED")}
    if swapped==1 && y!=modelB{t.Fatal("O6_LATENT_MAP_SWAP_FAILED")}
    checks++
   }
  }
 }
 for table,n:=range explanations{
  if n!=2{t.Fatalf("O6_FALSE_BINDING_IDENTIFICATION table=%d explanations=%d",table,n)}
 }
 if symmetric!=8||checks!=128{
  t.Fatalf("O6_LATENT_GAUGE_COVERAGE_FAILED symmetric=%d checks=%d",symmetric,checks)
 }
 t.Logf("O6_LATENT_PORT_EXPLANATIONS_PER_FUNCTION=2 O6_DISTINCT_OBSERVABLE_LAWS=16 O6_SYMMETRIC_BINARY_LAWS=%d O6_PORT_MAP_CHECKS=%d",symmetric,checks)
}
func TestO6InteractionTermRequiredAndUntrustedEvidenceFailClosed(t *testing.T){
 affine:=0;nonlinear:=0
 for coeff:=uint8(0);coeff<16;coeff++{
  if coeff&8==0 {affine++}else{nonlinear++}
  table:=o6TruthTable(coeff)
  foundAffine:=false
  for a:=uint8(0);a<8;a++{
   if o6TruthTable(a)==table{foundAffine=true}
  }
  if foundAffine!=(coeff&8==0){t.Fatalf("O6_INTERACTION_ABLATION_INVALID %d",coeff)}
 }
 if affine!=8||nonlinear!=8{t.Fatal("O6_NONLINEAR_OPERATOR_HEADROOM_WRONG")}
 m:=&O6BinaryANFLearner{}
 s:=NewO6BinarySymbolicControl()
 for _,e:=range []O6BinaryIntervention{
  {A:0,B:0,Output:1,InterventionAttested:false,IndependentlyAssigned:true},
  {A:0,B:0,Output:1,InterventionAttested:true,IndependentlyAssigned:false},
  {A:2,B:0,Output:1,InterventionAttested:true,IndependentlyAssigned:true},
  {A:0,B:0,Output:2,InterventionAttested:true,IndependentlyAssigned:true},
 }{
  if !errors.Is(m.Learn(e),ErrO6Evidence)||!errors.Is(s.Observe(e),ErrO6Evidence){
   t.Fatal("O6_UNAUTHENTICATED_OR_MALFORMED_SOURCE_ADMITTED")
  }
 }
 if m.Rank()!=0||m.ConsistentCount()!=16||s.ConsistentCount()!=16{
  t.Fatal("O6_UNTRUSTED_DATA_MUTATED_STATE")
 }
 good:=o6Fixture(1,1,1)
 if err:=m.Learn(good);err!=nil{t.Fatal(err)}
 if err:=s.Observe(good);err!=nil{t.Fatal(err)}
 oldRank,oldCount:=m.Rank(),s.ConsistentCount()
 if err:=m.Learn(good);err!=nil{t.Fatal(err)}
 if err:=s.Observe(good);err!=nil{t.Fatal(err)}
 bad:=good;bad.Output=0
 if !errors.Is(m.Learn(bad),ErrO6Conflict)||
    !errors.Is(s.Observe(bad),ErrO6Conflict)||
    m.Rank()!=oldRank||s.ConsistentCount()!=oldCount{
  t.Fatal("O6_CONTRADICTORY_INTERVENTION_WAS_ADMITTED")
 }
 if _,cert,err:=m.Predict(2,1);!errors.Is(err,ErrO6Query)||cert{
  t.Fatal("O6_INVALID_QUERY_DID_NOT_FAIL_CLOSED")
 }
 t.Logf("O6_NONLINEAR_INTERACTION_REQUIRED_FOR=%d_OF_16_LAWS O6_PUBLIC_CAUSAL_ATTESTATION_SYNTHETIC_ONLY=PASS O6_CONFLICT_DEFAULT_DENY=PASS",nonlinear)
}
