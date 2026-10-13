package pilotf4

import "testing"

func TestF4EligibilityFailClosed(t *testing.T){
 v:=Eligibility{QualifiedSource:"95095aca6d2035bcf00220eefc61f0654dde67d0",
  RequestedSource:"95095aca6d2035bcf00220eefc61f0654dde67d0",
  FrozenBlob:FreezeBlob,FirstCreation:true,FirstAttempt:true}
 if CheckEligibility(v)==nil{t.Fatal("unverified custody admitted")}
 v.IndependentCommitVerified=true
 if CheckEligibility(v)==nil{t.Fatal("missing raw archive admitted")}
 v.ExternalRawCustodyVerified=true
 if err:=CheckEligibility(v);err!=nil{t.Fatal(err)}
 for _,mod:=range []func(*Eligibility){
  func(v *Eligibility){v.UncertainStart=true},
  func(v *Eligibility){v.PreviouslyConsumed=true},
  func(v *Eligibility){v.FirstAttempt=false},
  func(v *Eligibility){v.FirstCreation=false},
  func(v *Eligibility){v.RequestedSource="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
  func(v *Eligibility){v.FrozenBlob="bad"},
 }{
  candidate:=v
  mod(&candidate)
  if CheckEligibility(candidate)==nil{t.Fatal("unsafe release accepted")}
 }
}
