package lcrm01

import "testing"

func o9Fixture(law,swap,p,q uint8)O7PhysicalIntervention{
    a,b:=p,q
    if swap==1{a,b=q,p}
    return O7PhysicalIntervention{P:p,Q:q,Output:o6TableValue(law,a,b),
        InterventionAttested:true,IndependentlyAssigned:true}
}
func o9SamePrediction(t *testing.T, learned *O9CompiledPhysicalMemory,
    symbolic *O7PhysicalSymbolicControl){
    t.Helper()
    if learned.PossibleSemanticTables()!=symbolic.PossibleSemanticTables(){
        t.Fatal("O9_PHYSICAL_HYPOTHESIS_PARITY_FAILURE")
    }
    for a:=uint8(0);a<2;a++{
        for b:=uint8(0);b<2;b++{
            x,xok,xe:=learned.PredictCanonical(a,b)
            y,yok,ye:=symbolic.PredictCanonical(a,b)
            if (xe==nil)!=(ye==nil)||xok!=yok || (xok&&x!=y) {
                t.Fatalf("O9_QUERY_PARITY:%d/%d",a,b)
            }
        }
    }
}

func TestO9CompiledExactAcrossAllPublicEvidenceSubsets(t *testing.T){
    cases:=0
    for law:=uint8(0);law<16;law++{
        for swap:=uint8(0);swap<2;swap++{
            for subset:=uint8(0);subset<16;subset++{
                for grounded:=uint8(0);grounded<2;grounded++{
                    compact:=NewO9CompiledPhysicalMemory()
                    exact:=NewO7PhysicalSymbolicControl()
                    // Observe first; grounding after evidence tests commuting updates.
                    for cell:=uint8(0);cell<4;cell++{
                        if subset&(uint8(1)<<cell)==0{continue}
                        observation:=o9Fixture(law,swap,cell>>1,cell&1)
                        if err:=compact.Observe(observation);err!=nil{t.Fatal(err)}
                        if err:=exact.Observe(observation);err!=nil{t.Fatal(err)}
                    }
                    if grounded==1{
                        anchor:=O7Grounding{SemanticAPhysical:swap,
                          IndependentlyWitnessed:true,AuthenticatedOutsideOperator:true}
                        if err:=compact.Ground(anchor);err!=nil{t.Fatal(err)}
                        if err:=exact.Ground(anchor);err!=nil{t.Fatal(err)}
                    }
                    o9SamePrediction(t,compact,exact)
                    cases++
                }
            }
        }
    }
    if cases!=1024{t.Fatalf("O9_UNEXPECTED_CASES:%d",cases)}
}

func TestO9CompiledAtomicFailuresAndNoFabricatedGrounding(t *testing.T){
    o:=NewO9CompiledPhysicalMemory()
    invalid:=O7Grounding{SemanticAPhysical:0,
        IndependentlyWitnessed:false,AuthenticatedOutsideOperator:true}
    prior:=o.PossibleSemanticTables()
    if o.Ground(invalid)==nil||o.PossibleSemanticTables()!=prior{
        t.Fatal("O9_UNAUTHENTICATED_GROUNDING_ACCEPTED")
    }
    trusted:=O7Grounding{SemanticAPhysical:0,
        IndependentlyWitnessed:true,AuthenticatedOutsideOperator:true}
    if err:=o.Ground(trusted);err!=nil{t.Fatal(err)}
    trusted.SemanticAPhysical=1
    after:=o.PossibleSemanticTables()
    if o.Ground(trusted)==nil || o.PossibleSemanticTables()!=after{
        t.Fatal("O9_CONFLICTING_GROUNDING_NOT_ATOMIC")
    }
    e:=o9Fixture(11,0,0,0)
    if err:=o.Observe(e);err!=nil{t.Fatal(err)}
    stable:=o.PossibleSemanticTables()
    bad:=e;bad.Output^=1
    if o.Observe(bad)==nil||o.PossibleSemanticTables()!=stable{
        t.Fatal("O9_CONTRADICTORY_PUBLIC_EVIDENCE_NOT_ATOMIC")
    }
    bad=e;bad.InterventionAttested=false
    if o.Observe(bad)==nil||o.PossibleSemanticTables()!=stable{
        t.Fatal("O9_UNTRUSTED_INTERVENTION_ACCEPTED")
    }
}

func TestO9CompiledTwoHopMatchesIndependentSymbolic(t *testing.T){
    subsets:=[]uint8{0,1,3,7,15}
    count:=0
    for firstLaw:=uint8(0);firstLaw<16;firstLaw++{
        secondLaw:=uint8((int(firstLaw)*7+5)%16)
        for firstSwap:=uint8(0);firstSwap<2;firstSwap++{
            for secondSwap:=uint8(0);secondSwap<2;secondSwap++{
                for _,firstSubset:=range subsets{
                    for _,secondSubset:=range subsets{
                        a,b:=NewO9CompiledPhysicalMemory(),NewO9CompiledPhysicalMemory()
                        x,y:=NewO7PhysicalSymbolicControl(),NewO7PhysicalSymbolicControl()
                        one:=O7Grounding{SemanticAPhysical:firstSwap,
                         IndependentlyWitnessed:true,AuthenticatedOutsideOperator:true}
                        two:=O7Grounding{SemanticAPhysical:secondSwap,
                         IndependentlyWitnessed:true,AuthenticatedOutsideOperator:true}
                        if err:=a.Ground(one);err!=nil{t.Fatal(err)}
                        if err:=x.Ground(one);err!=nil{t.Fatal(err)}
                        if err:=b.Ground(two);err!=nil{t.Fatal(err)}
                        if err:=y.Ground(two);err!=nil{t.Fatal(err)}
                        for cell:=uint8(0);cell<4;cell++{
                            if firstSubset&(uint8(1)<<cell)!=0{
                                e:=o9Fixture(firstLaw,firstSwap,cell>>1,cell&1)
                                if err:=a.Observe(e);err!=nil{t.Fatal(err)}
                                if err:=x.Observe(e);err!=nil{t.Fatal(err)}
                            }
                            if secondSubset&(uint8(1)<<cell)!=0{
                                e:=o9Fixture(secondLaw,secondSwap,cell>>1,cell&1)
                                if err:=b.Observe(e);err!=nil{t.Fatal(err)}
                                if err:=y.Observe(e);err!=nil{t.Fatal(err)}
                            }
                        }
                        for query:=uint8(0);query<8;query++{
                            aa,bb,cc:=(query>>2)&1,(query>>1)&1,query&1
                            av,aok,ae:=O9ComposeTwoHopCompiled(a,b,aa,bb,cc)
                            ev,eok,ee:=O7ComposeTwoHopSymbolic(x,y,aa,bb,cc)
                            if (ae==nil)!=(ee==nil)||aok!=eok||(aok&&av!=ev){
                                t.Fatalf("O9_TWO_HOP_UNSOUND:%d/%d/%d",firstLaw,firstSubset,query)
                            }
                            if aok{
                                truth:=o6TableValue(secondLaw,
                                    o6TableValue(firstLaw,aa,bb),cc)
                                if av!=truth{t.Fatal("O9_FALSE_CAUSAL_CERTIFICATION")}
                            }
                            count++
                        }
                    }
                }
            }
        }
    }
    if count!=12800{t.Fatalf("O9_WRONG_COVERAGE:%d",count)}
}
