package lcrm01

import "testing"

func TestO2SourceFreeMatchedRetention(t *testing.T) {
    names:=[]O2Arm{O2Learned,O2TrainedPeer,O2Untrained,O2Recency}
    results:=map[O2Arm]O2Report{}
    for _,arm:=range names{
        r,err:=O2Screen(arm)
        if err!=nil{t.Fatalf("%s: %v",arm,err)}
        if r.Episodes!=6||r.MaxPhysicalSlots!=8||r.OtherRecallCorrect!=6||!r.QueryBlind{
            t.Fatalf("source-free bounded retention contract: %+v",r)
        }
        if r.ScientificAccepted||r.IndependentFirstUse||r.OptimizerAdmitted{
            t.Fatalf("unauthorized source-free promotion: %+v",r)
        }
        results[arm]=r
    }
    if results[O2Learned].OldImportantRetained!=6||results[O2TrainedPeer].OldImportantRetained!=6{
        t.Fatalf("equally trained predictive peer must receive equal structural recall: %+v",results)
    }
    if results[O2Untrained].OldImportantRetained!=0||results[O2Recency].OldImportantRetained!=0{
        t.Fatalf("untrained or recency survived expired-slot distraction: %+v",results)
    }
    if results[O2Learned].TrainUpdates!=results[O2TrainedPeer].TrainUpdates{
        t.Fatal("training information not matched")
    }
    if results[O2Learned].TrainUpdates!=48{
        t.Fatalf("unexpected public-only updates: %+v",results[O2Learned])
    }
    t.Log("O2 internal stress: learned retention = trained predictive peer = 6/6; no trained-peer advantage, no independent transfer claim")
}
func TestO2NoncausalSelfAttestationGuard(t *testing.T){
    m,_:=New(ForFamily(Joint))
    if err:=m.LearnAction(ActionEvidence{Action:1,Outcome:1,TrainingOnly:true});err==nil{
        t.Fatal("observational correlation admitted as causal")
    }
    if err:=m.LearnAction(ActionEvidence{Action:1,Outcome:1,TrainingOnly:true,Intervention:true,AssignedRandomly:true});err==nil{
        t.Fatal("unmatched interventional record admitted")
    }
    if m.Snapshot().ScientificAccepted||m.Snapshot().DispatchAuthorized{
        t.Fatal("unverified action claim promoted")
    }
}
func BenchmarkO2ScreenLearned(b *testing.B){
    b.ReportAllocs()
    for n:=0;n<b.N;n++{if _,e:=O2Screen(O2Learned);e!=nil{b.Fatal(e)}}
}
func BenchmarkO2ScreenTrainedPeer(b *testing.B){
    b.ReportAllocs()
    for n:=0;n<b.N;n++{if _,e:=O2Screen(O2TrainedPeer);e!=nil{b.Fatal(e)}}
}
func BenchmarkO2ScreenUntrained(b *testing.B){
    b.ReportAllocs()
    for n:=0;n<b.N;n++{if _,e:=O2Screen(O2Untrained);e!=nil{b.Fatal(e)}}
}
func BenchmarkO2ScreenRecency(b *testing.B){
    b.ReportAllocs()
    for n:=0;n<b.N;n++{if _,e:=O2Screen(O2Recency);e!=nil{b.Fatal(e)}}
}
