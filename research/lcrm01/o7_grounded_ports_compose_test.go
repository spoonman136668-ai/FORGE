package lcrm01

import(
 "errors"
 "testing"
)

func o7ObservedFixture(law,swap,p,q uint8)O7PhysicalIntervention{
 a,b:=p,q
 if swap==1{a,b=q,p}
 return O7PhysicalIntervention{P:p,Q:q,Output:o6TableValue(law,a,b),
  InterventionAttested:true,IndependentlyAssigned:true}
}
func o7PublicAnchor(swap uint8)O7Grounding{
 return O7Grounding{SemanticAPhysical:swap,
  IndependentlyWitnessed:true,AuthenticatedOutsideOperator:true}
}
func o7ObserveAll(t *testing.T,law,swap uint8,learn *O7AnchoredANF,peer *O7PhysicalSymbolicControl){
 t.Helper()
 for cell:=uint8(0);cell<4;cell++{
  e:=o7ObservedFixture(law,swap,cell>>1,cell&1)
  if err:=learn.Observe(e);err!=nil{t.Fatal(err)}
  if err:=peer.Observe(e);err!=nil{t.Fatal(err)}
 }
}
func TestO7EveryPublicBinaryLawPartialEvidenceAnchorAndSemanticDoParity(t *testing.T){
 total:=0;fullAnchored:=0;fullUnanchoredAmbiguous:=0
 for law:=uint8(0);law<16;law++{
  for swap:=uint8(0);swap<2;swap++{
   for subset:=uint8(0);subset<16;subset++{
    for anchorMode:=uint8(0);anchorMode<2;anchorMode++{
     learn:=&O7AnchoredANF{}
     control:=NewO7PhysicalSymbolicControl()
     if anchorMode==1{
      e:=o7PublicAnchor(swap)
      if err:=learn.Ground(e);err!=nil{t.Fatal(err)}
      if err:=control.Ground(e);err!=nil{t.Fatal(err)}
     }
     for cell:=uint8(0);cell<4;cell++{
      if subset&(1<<cell)==0{continue}
      e:=o7ObservedFixture(law,swap,cell>>1,cell&1)
      if err:=learn.Observe(e);err!=nil{t.Fatal(err)}
      if err:=control.Observe(e);err!=nil{t.Fatal(err)}
     }
     if learn.PossibleSemanticTables()!=control.PossibleSemanticTables(){
      t.Fatalf("O7_EXACT_LATENT_WORLD_PARITY law=%d swap=%d subset=%d anchor=%d",law,swap,subset,anchorMode)
     }
     for query:=uint8(0);query<4;query++{
      a,b:=query>>1,query&1
      got,ok,err:=learn.PredictCanonical(a,b)
      expected,peerOK,peerErr:=control.PredictCanonical(a,b)
      if err!=nil||peerErr!=nil||ok!=peerOK||(ok&&(got!=expected||got!=o6TableValue(law,a,b))){
       t.Fatalf("O7_FALSE_SEMANTIC_CAUSAL_CERT law=%d swap=%d subset=%d anchor=%d query=%d",law,swap,subset,anchorMode,query)
      }
      total++
      if subset==15&&anchorMode==1{
       if !ok{t.Fatal("O7_FULL_PUBLIC_ANCHORED_LAW_NOT_IDENTIFIED")}
       fullAnchored++
      }
      if subset==15&&anchorMode==0&&!ok{fullUnanchoredAmbiguous++}
     }
    }
   }
  }
 }
 if total!=4096||fullAnchored!=128||fullUnanchoredAmbiguous==0{
  t.Fatalf("O7_INCOMPLETE_PUBLIC_CERTIFICATE_SCREEN n=%d anchored=%d unanchored=%d",total,fullAnchored,fullUnanchoredAmbiguous)
 }
 t.Logf("O7_ALL_BINARY_LAWS_PARTIAL_ANCHOR_CERTIFICATES=%d O7_FULL_ANCHORED_IDENTIFIED=%d O7_UNANCHORED_ABSTENTIONS=%d O7_HARD_FALSE_POSITIVES=0",total,fullAnchored,fullUnanchoredAmbiguous)
}
func TestO7TwoHopExactCompositionWithAndWithoutPublicPortGroundings(t *testing.T){
 cases:=0;certifiedAllAnchored:=0;unanchoredAbstentions:=0
 for firstLaw:=uint8(0);firstLaw<16;firstLaw++{
  for secondLaw:=uint8(0);secondLaw<16;secondLaw++{
   for firstSwap:=uint8(0);firstSwap<2;firstSwap++{
    for secondSwap:=uint8(0);secondSwap<2;secondSwap++{
     for anchorMask:=uint8(0);anchorMask<4;anchorMask++{
      a:=&O7AnchoredANF{};b:=&O7AnchoredANF{}
      x:=NewO7PhysicalSymbolicControl();y:=NewO7PhysicalSymbolicControl()
      o7ObserveAll(t,firstLaw,firstSwap,a,x)
      o7ObserveAll(t,secondLaw,secondSwap,b,y)
      if anchorMask&1!=0{
       e:=o7PublicAnchor(firstSwap)
       if err:=a.Ground(e);err!=nil{t.Fatal(err)}
       if err:=x.Ground(e);err!=nil{t.Fatal(err)}
      }
      if anchorMask&2!=0{
       e:=o7PublicAnchor(secondSwap)
       if err:=b.Ground(e);err!=nil{t.Fatal(err)}
       if err:=y.Ground(e);err!=nil{t.Fatal(err)}
      }
      for input:=uint8(0);input<8;input++{
       u,v,w:=(input>>2)&1,(input>>1)&1,input&1
       got,ok,err:=O7ComposeTwoHopExact(a,b,u,v,w)
       baseline,peerOK,peerErr:=O7ComposeTwoHopSymbolic(x,y,u,v,w)
       actual:=o6TableValue(secondLaw,o6TableValue(firstLaw,u,v),w)
       if err!=nil||peerErr!=nil||ok!=peerOK||(ok&&(got!=baseline||got!=actual)){
        t.Fatalf("O7_TWO_HOP_FALSE_COUNTERFACTUAL first=%d second=%d swaps=%d,%d anchors=%d input=%d",firstLaw,secondLaw,firstSwap,secondSwap,anchorMask,input)
       }
       if anchorMask==3{
        if !ok{t.Fatal("O7_BOTH_GROUNDED_COMPLETE_EVIDENCE_NOT_CERTIFIED")}
        certifiedAllAnchored++
       }
       if anchorMask!=3&&!ok{unanchoredAbstentions++}
       cases++
      }
     }
    }
   }
  }
 }
 if cases!=32768||certifiedAllAnchored!=8192||unanchoredAbstentions==0{
  t.Fatalf("O7_TWO_HOP_COVERAGE cases=%d anchored=%d abstentions=%d",cases,certifiedAllAnchored,unanchoredAbstentions)
 }
 t.Logf("O7_TWO_HOP_EXHAUSTIVE_CASES=%d O7_BOTH_GROUNDED_CERTIFIED=%d O7_UNGROUNDED_CAUSAL_ABSTENTIONS=%d O7_HARD_FALSE_POSITIVES=0",cases,certifiedAllAnchored,unanchoredAbstentions)
}
func TestO7ExternallyGroundedPortEvidenceCannotBeSpoofedOrOverwriteState(t *testing.T){
 learner:=&O7AnchoredANF{}
 control:=NewO7PhysicalSymbolicControl()
 for _,x:=range []O7Grounding{
  {SemanticAPhysical:0,IndependentlyWitnessed:false,AuthenticatedOutsideOperator:true},
  {SemanticAPhysical:0,IndependentlyWitnessed:true,AuthenticatedOutsideOperator:false},
  {SemanticAPhysical:2,IndependentlyWitnessed:true,AuthenticatedOutsideOperator:true},
 }{
  if !errors.Is(learner.Ground(x),ErrO7Anchor)||!errors.Is(control.Ground(x),ErrO7Anchor){
   t.Fatal("O7_SPOOFED_ANCHOR_ACCEPTED")
  }
 }
 if learner.hasGrounding||control.hasGrounding||learner.PossibleSemanticTables()!=0xffff||
  control.PossibleSemanticTables()!=0xffff{t.Fatal("O7_UNTRUSTED_ANCHOR_MUTATED")}
 good:=o7ObservedFixture(6,1,0,0)
 if err:=learner.Observe(good);err!=nil{t.Fatal(err)}
 if err:=control.Observe(good);err!=nil{t.Fatal(err)}
 beforeLearner,beforeControl:=learner.PossibleSemanticTables(),control.PossibleSemanticTables()
 for _,bad:=range []O7PhysicalIntervention{
  {P:0,Q:0,Output:1,IndependentlyAssigned:true},
  {P:0,Q:0,Output:1,InterventionAttested:true},
  {P:2,Q:0,Output:1,IndependentlyAssigned:true,InterventionAttested:true},
 }{
  if !errors.Is(learner.Observe(bad),ErrO7Evidence)||!errors.Is(control.Observe(bad),ErrO7Evidence){
   t.Fatal("O7_UNTRUSTED_INTERVENTION_ACCEPTED")
  }
 }
 contradicted:=good
 contradicted.Output^=1
 if !errors.Is(learner.Observe(contradicted),ErrO7Conflict)||
  !errors.Is(control.Observe(contradicted),ErrO7Conflict){
  t.Fatal("O7_CONFLICTING_INTERVENTION_ACCEPTED")
 }
 if learner.PossibleSemanticTables()!=beforeLearner||
  control.PossibleSemanticTables()!=beforeControl{t.Fatal("O7_INVALID_INTERVENTION_MUTATED_CAUSAL_STATE")}
 anchor:=o7PublicAnchor(1)
 if err:=learner.Ground(anchor);err!=nil{t.Fatal(err)}
 if err:=control.Ground(anchor);err!=nil{t.Fatal(err)}
 opposite:=o7PublicAnchor(0)
 if !errors.Is(learner.Ground(opposite),ErrO7Conflict)||
  !errors.Is(control.Ground(opposite),ErrO7Conflict)||
  learner.grounding!=1||control.grounding!=1{t.Fatal("O7_CONFLICTING_ANCHOR_MUTATED_STATE")}
 for _,bad:=range [][2]uint8{{2,0},{0,2}}{
  if _,ok,err:=learner.PredictCanonical(bad[0],bad[1]);ok||!errors.Is(err,ErrO7Query){
   t.Fatal("O7_INVALID_COUNTERFACTUAL_ACCEPTED")
  }
 }
 t.Log("O7_SYNTHETIC_ATTESTATION_IS_NOT_ORIGIN=PASS O7_CONFLICT_ATOMICITY=PASS O7_PORT_ANCHOR_DEFAULT_DENY=PASS")
}
