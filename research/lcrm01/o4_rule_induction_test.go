package lcrm01

import ("errors";"testing")
func o4Programs()[6][O4ProgramEdges]uint8{
 perms:=[6][O4Roles]uint8{{0,1,2},{0,2,1},{1,0,2},{1,2,0},{2,0,1},{2,1,0}}
 var programs [6][O4ProgramEdges]uint8
 for i,p:=range perms {for j:=0;j<O4ProgramEdges;j++ {programs[i][j]=p[j%O4Roles]}}
 return programs
}
func o4Direct(ops [O4Roles]O3Unary,program [O4ProgramEdges]uint8,start uint8)uint8{
 y:=start;for _,r:=range program {y=o3ApplyExact(ops[r],y)}
 return y
}
func TestO4AllRoleOperatorWorldsInterventionMasksAndStrongControl(t *testing.T){
 programs:=o4Programs()
 cases:=0;checks:=0;partialAbstentions:=0
 for a:=O3Unary(0);a<4;a++ {for b:=O3Unary(0);b<4;b++ {for c:=O3Unary(0);c<4;c++{
  ops:=[O4Roles]O3Unary{a,b,c}
  for seed:=uint8(0);seed<8;seed++{
   learned:=&O4RuleLearner{};symbolic:=NewO4SymbolicControl()
   inputs:=[O4Roles]uint8{}
   for r:=0;r<O4Roles;r++{
    x:=(seed>>r)&1; inputs[r]=x
    e:=O4Intervention{uint8(r),x,o3ApplyExact(ops[r],x),true,true}
    if err:=learned.Learn(e);err!=nil{t.Fatal(err)}
    if err:=symbolic.Observe(e);err!=nil{t.Fatal(err)}
   }
   if learned.SuccessfulUpdates()!=3||learned.LearnedCoordinates()!=6{t.Fatal("parameter bound violated")}
   for _,program:=range programs{for input:=uint8(0);input<2;input++{
    want:=o4Direct(ops,program,input)
    got,cert,err:=learned.Counterfactual(program,input)
    peer,peerCert,peerErr:=symbolic.Counterfactual(program,input)
    if err!=nil||peerErr!=nil||cert!=peerCert||(cert&&(got!=peer||got!=want)){
     t.Fatalf("partial public law mismatch ops=%v seed=%d",ops,seed)
    }
    if !cert{partialAbstentions++}
    checks++
   }}
   for r:=0;r<O4Roles;r++{
    x:=1-inputs[r]
    e:=O4Intervention{uint8(r),x,o3ApplyExact(ops[r],x),true,true}
    if err:=learned.Learn(e);err!=nil{t.Fatal(err)}
    if err:=symbolic.Observe(e);err!=nil{t.Fatal(err)}
   }
   if learned.SuccessfulUpdates()!=6{t.Fatal("not all six online coordinates fitted")}
   for _,program:=range programs{for input:=uint8(0);input<2;input++{
    want:=o4Direct(ops,program,input)
    got,cert,err:=learned.Counterfactual(program,input)
    peer,peerCert,peerErr:=symbolic.Counterfactual(program,input)
    if err!=nil||peerErr!=nil||!cert||!peerCert||got!=want||peer!=want{
     t.Fatalf("identified law failed ops=%v want=%d",ops,want)
    }
    checks++
   }}
   cases++
  }
 }}}
 if cases!=512||checks!=12288||partialAbstentions==0{t.Fatalf("coverage %d %d %d",cases,checks,partialAbstentions)}
 t.Logf("O4_SOURCEFREE_CASES=%d O4_CERTIFICATE_CHECKS=%d O4_PARTIAL_ABSTENTIONS=%d",cases,checks,partialAbstentions)
}
func TestO4FailClosedObservationalClaimsContradictionsAndUnseen(t *testing.T){
 m:=&O4RuleLearner{};s:=NewO4SymbolicControl()
 for _,e:=range []O4Intervention{
  {Role:0,Input:0,Output:0,InterventionAttested:false,IndependentlyAssigned:true},
  {Role:0,Input:0,Output:0,InterventionAttested:true,IndependentlyAssigned:false},
  {Role:4,Input:0,Output:0,InterventionAttested:true,IndependentlyAssigned:true},
  {Role:1,Input:2,Output:0,InterventionAttested:true,IndependentlyAssigned:true},
  {Role:1,Input:0,Output:2,InterventionAttested:true,IndependentlyAssigned:true},
 }{
  if !errors.Is(m.Learn(e),ErrO4Evidence)||!errors.Is(s.Observe(e),ErrO4Evidence){t.Fatal("bad causal evidence admitted")}
 }
 if m.SuccessfulUpdates()!=0{t.Fatal("invalid intervention changed model")}
 var program [O4ProgramEdges]uint8
 for i:=range program{program[i]=0}
 if _,known,err:=m.Counterfactual(program,0);err!=nil||known{t.Fatal("untrained unknown law guessed")}
 e:=O4Intervention{0,0,0,true,true}
 if err:=m.Learn(e);err!=nil{t.Fatal(err)}
 if err:=s.Observe(e);err!=nil{t.Fatal(err)}
 contrad:=O4Intervention{0,0,1,true,true}
 if !errors.Is(m.Learn(contrad),ErrO4Conflict)||!errors.Is(s.Observe(contrad),ErrO4Conflict){t.Fatal("contradictory evidence accepted")}
 if m.SuccessfulUpdates()!=1{t.Fatal("contradiction mutated trained state")}
 if _,_,err:=m.Counterfactual(program,2);!errors.Is(err,ErrO4Program){t.Fatal("invalid start certified")}
 program[4]=8
 if _,_,err:=m.Counterfactual(program,0);!errors.Is(err,ErrO4Program){t.Fatal("unknown role certified")}
 if !O3SourceFreeIndistinguishability(){t.Fatal("observational confounder check lost")}
}
func TestO4RoleRenamingAndQueryBlindLearning(t *testing.T){
 ops:=[O4Roles]O3Unary{O3Not,O3False,O3Identity}
 m:=&O4RuleLearner{};renamed:=&O4RuleLearner{}
 rename:=[O4Roles]uint8{2,0,1}
 for r:=0;r<O4Roles;r++ {for x:=uint8(0);x<2;x++{
  e:=O4Intervention{uint8(r),x,o3ApplyExact(ops[r],x),true,true}
  ep:=e;ep.Role=rename[r]
  if err:=m.Learn(e);err!=nil{t.Fatal(err)}
  if err:=renamed.Learn(ep);err!=nil{t.Fatal(err)}
 }}
 for _,word:=range o4Programs(){var rer [O4ProgramEdges]uint8
  for i,r:=range word{rer[i]=rename[r]}
  for v:=uint8(0);v<2;v++{
   a,ac,ae:=m.Counterfactual(word,v)
   b,bc,be:=renamed.Counterfactual(rer,v)
   if ae!=nil||be!=nil||!ac||!bc||a!=b||a!=o4Direct(ops,word,v){t.Fatal("role renaming equivariance loss")}
  }
 }
}
