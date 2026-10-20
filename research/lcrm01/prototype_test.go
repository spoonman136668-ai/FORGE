package lcrm01

import "testing"

func f(first,second int8)Features{
    var x Features
    x[0]=first;x[1]=second
    return x
}
func TestFreezeAndAdvisoryOnly(t *testing.T){
    families:=[]Family{EncoderOnly,FutureRetention,InterventionalValue,LearnedComposition,Joint}
    for _,kind:=range families{
        spec:=ForFamily(kind)
        m,err:=New(spec)
        if err!=nil{t.Fatalf("valid %v: %v",kind,err)}
        s:=m.Snapshot()
        if s.ScientificAccepted||s.DispatchAuthorized||s.IndependentlyReplicated||
           s.Parameters>3*FeatureCount||s.Stored!=0{t.Fatal("unauthorized admission or budget")}
        spec.SourceFirstUse=true
        if _,err:=New(spec);err==nil{t.Fatal("unreviewed science admission")}
        spec=ForFamily(kind)
        spec.ProductionEnabled=true
        if _,err:=New(spec);err==nil{t.Fatal("production activation")}
    }
    if _,err:=New(ForFamily(Family("optimizer-hallucination")));err==nil{
        t.Fatal("unknown family")
    }
}
func TestQueryBlindFutureTaskValueRetention(t *testing.T){
    m,err:=New(ForFamily(FutureRetention))
    if err!=nil{t.Fatal(err)}
    if err:=m.LearnFutureTaskValue(f(1,0),1,true);err!=nil{t.Fatal(err)}
    old:=Relation{Subject:1,Object:2,Predicate:1,Features:f(1,0)}
    if err:=m.Observe(old);err!=nil{t.Fatal(err)}
    for i:=0;i<20;i++{
        r:=Relation{Subject:10+i,Object:100+i,Predicate:1,Features:f(0,1)}
        if err:=m.Observe(r);err!=nil{t.Fatal(err)}
        if _,ok:=m.Recall(1,2,1);!ok{
            t.Fatal("future-useful older relation discarded by query-blind retention")
        }
    }
    if m.Snapshot().Stored>MaxSlots{t.Fatal("memory grew")}
    before:=m.Snapshot()
    for i:=0;i<500;i++{_,_ = m.Recall(123,456,0)}
    after:=m.Snapshot()
    if before!=after{t.Fatal("query-time read changed retention or learning")}
    if err:=m.LearnFutureTaskValue(f(1,0),1,false);err==nil{
        t.Fatal("test-side label accepted")
    }
    if err:=m.CheckBounded();err!=nil{t.Fatal(err)}
}
func TestInterventionCauseIsolationAndComposition(t *testing.T){
    m,_:=New(ForFamily(Joint))
    a:=Relation{Subject:1,Object:2,Predicate:1,Features:f(1,1)}
    b:=Relation{Subject:2,Object:3,Predicate:2,Features:f(1,1)}
    if err:=m.Observe(a);err!=nil{t.Fatal(err)}
    if err:=m.Observe(b);err!=nil{t.Fatal(err)}
    bad:=ActionEvidence{Action:2,Outcome:1,TrainingOnly:true}
    if err:=m.LearnAction(bad);err==nil{t.Fatal("observational correlation accepted as intervention")}
    bad.Intervention=true
    if err:=m.LearnAction(bad);err==nil{t.Fatal("nonrandom assignment accepted")}
    bad.AssignedRandomly=true
    if err:=m.LearnAction(bad);err==nil{t.Fatal("unmatched controls accepted")}
    bad.MatchedControls=true
    if err:=m.LearnAction(bad);err!=nil{t.Fatal(err)}
    if err:=m.LearnComposition(CompositionEvidence{Left:f(1,1),Right:f(1,1),
        Target:1,TrainingOnly:true});err!=nil{t.Fatal(err)}
    estimate,err:=m.EstimateCounterfactual(a,b,2)
    if err!=nil{t.Fatal(err)}
    if estimate.Certified||estimate.ScientificEvidence{t.Fatal("model guess upgraded into a proof")}
    if estimate.EstimateSign!=1{t.Fatalf("unexpected source-free positive train sign: %+v",estimate)}
    if _,err:=m.EstimateCounterfactual(a,b,4);err==nil{
        t.Fatal("unseen action hallucinated")
    }
    if err:=m.CheckBounded();err!=nil{t.Fatal(err)}
}
func TestRoleRelabelingAndCausalAblations(t *testing.T){
    var signs []int
    for _,offset:=range []int{0,1000}{
        m,_:=New(ForFamily(Joint))
        if err:=m.LearnEncoder(f(1,0),1,true);err!=nil{t.Fatal(err)}
        if err:=m.LearnFutureTaskValue(f(1,0),1,true);err!=nil{t.Fatal(err)}
        if err:=m.LearnAction(ActionEvidence{Action:1,Outcome:1,AssignedRandomly:true,
            Intervention:true,MatchedControls:true,TrainingOnly:true});err!=nil{t.Fatal(err)}
        if err:=m.LearnComposition(CompositionEvidence{Left:f(1,0),Right:f(1,0),
            Target:1,TrainingOnly:true});err!=nil{t.Fatal(err)}
        a:=Relation{Subject:1+offset,Object:2+offset,Predicate:1,Features:f(1,0)}
        b:=Relation{Subject:2+offset,Object:3+offset,Predicate:2,Features:f(1,0)}
        if err:=m.Observe(a);err!=nil{t.Fatal(err)}
        if err:=m.Observe(b);err!=nil{t.Fatal(err)}
        outcome,err:=m.EstimateCounterfactual(a,b,1)
        if err!=nil{t.Fatal(err)}
        signs=append(signs,outcome.EstimateSign)
    }
    if signs[0]!=signs[1]{t.Fatal("renaming changed structural outcome")}
    encoder,_:=New(ForFamily(EncoderOnly))
    if err:=encoder.LearnAction(ActionEvidence{TrainingOnly:true});err==nil{
        t.Fatal("action-value ablation not enforced")
    }
    if err:=encoder.LearnFutureTaskValue(f(1,0),1,true);err==nil{
        t.Fatal("retention ablation not enforced")
    }
    if err:=encoder.LearnComposition(CompositionEvidence{TrainingOnly:true});err==nil{
        t.Fatal("composition ablation not enforced")
    }
}
func TestLimitsAndZeroErrorsFailClosed(t *testing.T){
    m,_:=New(ForFamily(Joint))
    if err:=m.Observe(Relation{Subject:3,Object:3});err==nil{
        t.Fatal("invalid self-link")
    }
    impossible:=f(0,0)
    impossible[5]=2
    if err:=m.LearnEncoder(impossible,1,true);err==nil{
        t.Fatal("unbounded feature")
    }
    for i:=0;i<MaxTrainingUpdates;i++{
        if err:=m.LearnEncoder(f(1,0),1,true);err!=nil{t.Fatal(err)}
    }
    if err:=m.LearnEncoder(f(1,0),1,true);err==nil{
        t.Fatal("training budget not sealed")
    }
    if err:=m.CheckBounded();err!=nil{t.Fatal(err)}
    if m.Snapshot().TrainingUpdates!=MaxTrainingUpdates{t.Fatal("wrong train count")}
}
