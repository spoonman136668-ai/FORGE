package shadowcore
import("errors";"testing")
func TestCutoverNeverInfersAuthorityFromGreenShadowCI(t *testing.T){
 j:=seeded(t)
 full:=CutoverReadiness{ExistingWinglessCustodyAuthenticated:true,ExistingYggdrasilCustodyAuthenticated:true,OldOwnerQuiescenceAuthenticated:true,OldOwnerExecutionRevoked:true,IndependentFenceVerified:true,IndependentOriginalLedgersReconciled:true,WorkerEpochEnforced:true,FinalIntegrationRegressionPassed:true,OriginalScientificCyclesVerified:true}
 if err:=CheckCutover(j,full);err!=nil{t.Fatal(err)}
 for _,change:=range []func(*CutoverReadiness){
  func(r *CutoverReadiness){r.OldOwnerExecutionRevoked=false},
  func(r *CutoverReadiness){r.IndependentOriginalLedgersReconciled=false},
  func(r *CutoverReadiness){r.OriginalScientificCyclesVerified=false},
  func(r *CutoverReadiness){r.ExistingYggdrasilCustodyAuthenticated=false},
 }{r:=full;change(&r);if err:=CheckCutover(j,r);!errors.Is(err,ErrCutoverBlocked){t.Fatal("unqualified cutover passed",err)}}
}
