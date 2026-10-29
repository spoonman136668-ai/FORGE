//go:build acc34_archived_source_only

package acc34
import "testing"
func TestFrozenCorrectnessAndHiddenFITCounterexample(t *testing.T){
 for _,s:=range []string{"benign","hidden_interaction"}{
  f,e:=Run("full",s,91101,256);if e!=nil{t.Fatal(e)}
  v,e:=Run("verified",s,91101,256);if e!=nil{t.Fatal(e)}
  o,e:=Run("oracle",s,91101,256);if e!=nil{t.Fatal(e)}
  u,e:=Run("unverified",s,91101,256);if e!=nil{t.Fatal(e)}
  if v.Checksum!=f.Checksum||o.Checksum!=f.Checksum{t.Fatalf("truth parity %s",s)}
  if s=="benign"&&u.Checksum!=f.Checksum{t.Fatal("benign mismatch")}
  if s=="hidden_interaction"&&(u.Checksum==f.Checksum||v.VerificationRepairs==0){t.Fatal("missed hidden FIT fault")}
  if v.FitEvaluations!=uint64(Nodes*(Inputs+1))||f.FitEvaluations!=0{t.Fatal("fit accounting")}
 }
}
func TestVerificationIsActuallyWholeOutput(t *testing.T){
 v,_:=Run("verified","hidden_interaction",91103,96)
 if v.VerificationEvaluations!=96*Nodes{t.Fatalf("unpriced verification %d",v.VerificationEvaluations)}
 if v.ActionEvaluations<=Nodes||v.FitEvaluations==0{t.Fatal("candidate did not learn")}
 if v.SourceOwnedEpisodes!=0||v.NativeModelsChanged||v.ScientificFirstUse{t.Fatal("science misclaimed")}
}
func TestCaseRejections(t *testing.T){
 for _,x:=range []struct{mode,scenario string;seed,events int}{
  {"unbounded","benign",91101,32},{"verified","fake",91101,32},
  {"oracle","benign",0,32},{"full","benign",91101,0},{"full","benign",91101,4097},
 }{if _,e:=Run(x.mode,x.scenario,x.seed,x.events);e==nil{t.Fatalf("invalid %+v",x)}}
}
func TestKnownDependencyCannotDiscoverConjunction(t *testing.T){
 d,_:=discover();if d[1][0]{t.Fatal("FIT learned hidden conjunction from zero bit probes")}
 o:=trueDeps();if !o[1][0]{t.Fatal("oracle lacks true unavailable dependency")}
}
func TestBenignPublicScheduleNeverContainsUndiscoveredConjunction(t *testing.T){
 for _,seed:=range []int{91101,91103,91107,91109,91111}{
  var st [Inputs]bool
  for i:=0;i<Events;i++{
   b:=bitAt(i,seed,"benign",&st);st[b]=!st[b]
   if st[0]&&st[1]{t.Fatalf("hidden conjunction in benign %d/%d",seed,i)}
  }
 }
}
func TestAllFiveFrozenPairedSeedsProduceSourceFreeExactVerified(t *testing.T){
 for _,seed:=range []int{91101,91103,91107,91109,91111}{
  for _,s:=range []string{"benign","hidden_interaction"}{
   f,e:=Run("full",s,seed,256);if e!=nil{t.Fatal(e)}
   v,e:=Run("verified",s,seed,256);if e!=nil{t.Fatal(e)}
   o,e:=Run("oracle",s,seed,256);if e!=nil{t.Fatal(e)}
   if f.Checksum!=v.Checksum||f.Checksum!=o.Checksum{t.Fatalf("parity %s/%d",s,seed)}
  }
 }
}
