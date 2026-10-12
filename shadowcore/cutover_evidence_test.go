package shadowcore
import("errors";"strings";"testing";"github.com/spoonman136668-ai/forge/researchstate")
func TestCutoverEvidenceMustBindExactCurrentHead(t *testing.T){
 j:=seeded(t);h,err:=researchstate.Head(j);if err!=nil{t.Fatal(err)}
 r:=CutoverReadiness{ExistingWinglessCustodyAuthenticated:true,ExistingYggdrasilCustodyAuthenticated:true,OldOwnerQuiescenceAuthenticated:true,OldOwnerExecutionRevoked:true,IndependentFenceVerified:true,IndependentOriginalLedgersReconciled:true,WorkerEpochEnforced:true,FinalIntegrationRegressionPassed:true,OriginalScientificCyclesVerified:true}
 e:=ReadinessEvidence{JournalHeadSHA256:h,WinglessCustodySHA256:strings.Repeat("a",64),YggdrasilCustodySHA256:strings.Repeat("b",64),CKBRevocationSHA256:strings.Repeat("c",64),IndependentAuthoritySHA256:strings.Repeat("d",64),ConsumedLedgerSHA256:strings.Repeat("e",64),QualificationSHA256:strings.Repeat("f",64),OperatorAuthorizationSHA256:strings.Repeat("1",64)}
 if err:=VerifyReadinessEvidence(j,r,e);err!=nil{t.Fatal(err)}
 e.JournalHeadSHA256=strings.Repeat("0",64)
 if err:=VerifyReadinessEvidence(j,r,e);!errors.Is(err,ErrUnwitnessed){t.Fatal("stale head accepted",err)}
 e.JournalHeadSHA256=h;e.YggdrasilCustodySHA256=e.WinglessCustodySHA256
 if err:=VerifyReadinessEvidence(j,r,e);!errors.Is(err,ErrUnwitnessed){t.Fatal("shared custody accepted",err)}
}
