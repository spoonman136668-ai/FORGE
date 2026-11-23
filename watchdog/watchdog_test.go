package watchdog
import ("strings";"testing")
func obs(lane string)Observation{return Observation{Lane:lane,OriginalExperimentID:"original",JournalHeadSHA256:strings.Repeat("a",64),OwnerEpoch:5,Authenticated:true,Phase:Orchestration,LastProgressUnix:1000}}
func TestFiveMinuteOrchestrationBoundary(t *testing.T){
 o:=obs("Wingless")
 for _,tc:=range []struct{now uint64;want Action}{{1300,Healthy},{1301,DiagnoseOrchestration}}{
  got,err:=Assess(tc.now,o);if err!=nil||got.Action!=tc.want{t.Fatalf("%d got %v %v",tc.now,got.Action,err)}
 }
}
func TestScienceHasNoArbitraryRuntimeCeiling(t *testing.T){
 o:=obs("Yggdrasil");o.Phase=ScientificExecution;o.WorkerHeartbeatAuthenticated=true;o.LastWorkerHeartbeatUnix=9999
 got,err:=Assess(10000,o);if err!=nil||got.Action!=Healthy{t.Fatal(got,err)}
 o.FirstUseRisk=true
 got,err=Assess(10000,o);if err!=nil||got.Action!=ReconcileOriginal{t.Fatal(got,err)}
 o.FirstUseRisk=false;o.WorkerHeartbeatAuthenticated=false
 got,err=Assess(10000,o);if err!=nil||got.Action!=DiagnoseWorker{t.Fatal(got,err)}
}
func TestAuthenticityAndNoReplacementLanes(t *testing.T){
 a,b:=obs("Wingless"),obs("Yggdrasil")
 if got,err:=AssessBoth(1301,[]Observation{b,a});err!=nil||got[0].Action!=DiagnoseOrchestration||got[1].Action!=DiagnoseOrchestration{t.Fatal(got,err)}
 if _,err:=AssessBoth(1301,[]Observation{a,a});err==nil{t.Fatal("duplicate lane")}
 a.Authenticated=false
 if _,err:=AssessBoth(1301,[]Observation{a,b});err==nil{t.Fatal("untrusted progress")}
 a=obs("Wingless");a.JournalHeadSHA256="bad"
 if _,err:=Assess(1301,a);err==nil{t.Fatal("invalid evidence head")}
 a=obs("Wingless");a.Phase=Quarantined
 if got,err:=Assess(1301,a);err!=nil||got.Action!=ReconcileOriginal{t.Fatal(got,err)}
}
