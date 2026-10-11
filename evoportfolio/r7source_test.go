package evoportfolio
import("strings";"testing")
func TestR19HR7ArchivedSourceNeverAdmitsScience(t *testing.T){
 r:=R7SourceReceipt{Schema:"ckb-plane.research-source-qualification.r168",Lane:"Wingless",CandidateSHA256:"60a421d4ed786b92cd8d0e8a4b58988dd5d89229277ad2b91e5b11ca47f6cf8a",ParentSHA:"b6716df4d94bdac07fde526de4e3a37c5b4f23ee",Status:"PINNED_IMPLEMENTATION_COMPILES_SCIENCE_STILL_BLOCKED",FocusedGoTestInvocations:2,VerifiedSourceFiles:2,ScientificClassification:"NOT_EVALUATED",PredecessorReceiptSHA256:strings.Repeat("a",64)}
 if err:=ValidateR7ArchivedSource(r);err!=nil{t.Fatal(err)}
 x:=r;x.ReadyResearchAuthority=true
 if ValidateR7ArchivedSource(x)==nil{t.Fatal("source attestation minted readiness")}
 x=r;x.FullHistoricalDisjointnessProven=true
 if ValidateR7ArchivedSource(x)==nil{t.Fatal("source attestation minted disjointness")}
 x=r;x.Status="READY"
 if ValidateR7ArchivedSource(x)==nil{t.Fatal("source status drift admitted")}
 y:=r;y.Lane="Yggdrasil";y.CandidateSHA256="ead6681782763de8b953a705783bb3babd5858da30f94257545a394bad928f88";y.ParentSHA="d5e3715c7124e1fd0fc91da5efbef850ec1d9254";y.Status="BLOCKED_REQUIRE_FULL_PARENT_SOURCE";y.FocusedGoTestInvocations=0;y.VerifiedSourceFiles=0
 if err:=ValidateR7ArchivedSource(y);err!=nil{t.Fatal(err)}
}
