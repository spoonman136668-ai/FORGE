package planner

import (
 "context"
 "errors"
 "reflect"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/contracts"
)

type fixtureBackend struct {
 observations map[contracts.Lane]contracts.Observation
 recorded map[string]contracts.QuarantineAcknowledgment
 submits int
 refuse bool
 forgeAck bool
}
func (b *fixtureBackend) ReadLatest(_ context.Context,l contracts.Lane)(contracts.Observation,error){
 o,ok:=b.observations[l];if !ok{return o,errors.New("missing evidence")};return o,nil
}
func (b *fixtureBackend) SubmitDraft(_ context.Context,d contracts.CandidateDraft)(contracts.QuarantineAcknowledgment,error){
 if b.refuse{return contracts.QuarantineAcknowledgment{},errors.New("inbox unavailable")}
 if e:=contracts.ValidateCandidate(d);e!=nil{return contracts.QuarantineAcknowledgment{},e}
 h,e:=contracts.CanonicalCandidateSHA256(d);if e!=nil{return contracts.QuarantineAcknowledgment{},e}
 b.submits++
 if prev,ok:=b.recorded[h];ok{return prev,nil}
 receipt:=contracts.QuarantineAcknowledgment{Schema:contracts.AcknowledgmentSchema,ProposalSHA256:h,Status:"QUARANTINE_ONLY"}
 if b.forgeAck{receipt.DispatchAuthorized=true}
 b.recorded[h]=receipt
 return receipt,nil
}
func example()FrozenPortfolio{
 result:=FrozenPortfolio{Schema:InputSchema,AuthorityEpoch:42,ConsumedSeedIdentities:[]string{"Wingless:100","Yggdrasil:100"},Candidates:[]Candidate{},Observations:[]contracts.Observation{}}
 for i,l:=range []contracts.Lane{contracts.Wingless,contracts.Yggdrasil}{
  id:=string('a'+rune(i))
  result.Observations=append(result.Observations,contracts.Observation{Schema:contracts.ObservationSchema,Lane:l,AuthorityEpoch:42,SourceWitnessSHA256:strings.Repeat("a",64),LedgerWitnessSHA256:strings.Repeat("b",64),LatestOutcome:"NEGATIVE"})
  result.Candidates=append(result.Candidates,Candidate{
   Draft:contracts.CandidateDraft{Schema:contracts.CandidateSchema,Lane:l,Generation:2,CandidateID:"prospective-"+string(l),SourceCommitSHA:strings.Repeat(id,40),CandidateSHA256:strings.Repeat(id,64),PreregistrationSHA256:strings.Repeat("c",64),CohortSHA256:strings.Repeat(id,64),EvidenceClass:contracts.Synthetic,SeedIdentities:[]string{string(l)+":200"},AllowedPaths:[]string{"research/experiment/main.go"},Budget:contracts.Budget{TimeoutSeconds:600,MemoryMiB:512,ComputeUnits:10}},
   MechanismFamily:"causal",ParentReceiptSHA256:strings.Repeat("e",64),Impact:80,Novelty:50,Robustness:70,Cost:20})
 }
 return result
}
func pin(t *testing.T,f FrozenPortfolio)string{t.Helper();h,e:=FreezeSHA256(f);if e!=nil{t.Fatal(e)};return h}
func backend(f FrozenPortfolio)*fixtureBackend{
 b:=&fixtureBackend{observations:map[contracts.Lane]contracts.Observation{},recorded:map[string]contracts.QuarantineAcknowledgment{}}
 for _,o:=range f.Observations{b.observations[o.Lane]=o}
 return b
}
func TestEndToEndTwoIndependentLanesAndIdempotentInbox(t *testing.T){
 f:=example();b:=backend(f);sha:=pin(t,f)
 first,ack,e:=ReviewOnly(context.Background(),b,b,f,sha)
 if e!=nil||len(ack)!=2||b.submits!=2||first.ScientificAdmitted||first.DispatchAuthorized||first.AcceptedRefMutation||first.ExternalSourceVerified{t.Fatalf("unsafe outcome: %+v %v",first,e)}
 repeat,ack2,e:=ReviewOnly(context.Background(),b,b,f,sha)
 if e!=nil||!reflect.DeepEqual(first,repeat)||!reflect.DeepEqual(ack,ack2)||len(b.recorded)!=2{t.Fatalf("replay failed: %v",e)}
 f.Candidates[0],f.Candidates[1]=f.Candidates[1],f.Candidates[0]
 reordered,e:=Build(f,pin(t,f))
 if e!=nil||reordered.Lanes[0].CandidateID!=first.Lanes[0].CandidateID||reordered.Lanes[1].CandidateID!=first.Lanes[1].CandidateID{t.Fatalf("nondeterministic selection: %v",e)}
}
func TestAmbiguousWinglessCannotBlockOtherLane(t *testing.T){
 f:=example();f.Observations[0].LatestOutcome="CONSUMED_INDETERMINATE";b:=backend(f)
 out,acks,e:=ReviewOnly(context.Background(),b,b,f,pin(t,f))
 if e!=nil||len(acks)!=1||out.Lanes[0].Draft!=nil||out.Lanes[1].Draft==nil||b.submits!=1{t.Fatalf("lane isolation failed: %v %+v",e,out)}
}
func TestTamperAndSourceDriftFailBeforeSubmission(t *testing.T){
 f:=example();b:=backend(f);original:=pin(t,f);f.Candidates[0].Impact++
 _,_,e:=ReviewOnly(context.Background(),b,b,f,original)
 if e==nil||b.submits!=0{t.Fatal("tampered freeze accepted")}
 f=example();b=backend(f);o:=b.observations[contracts.Wingless];o.LatestOutcome="SUPPORTED";b.observations[contracts.Wingless]=o
 _,_,e=ReviewOnly(context.Background(),b,b,f,pin(t,f))
 if e==nil||b.submits!=0{t.Fatal("drifted evidence accepted")}
}
func TestRejectEntireUnsafeFrozenBatch(t *testing.T){
 edits:=[]struct{name string;fn func(*FrozenPortfolio)}{
  {"consumed",func(f *FrozenPortfolio){f.ConsumedSeedIdentities=append(f.ConsumedSeedIdentities,"Wingless:200")}},
  {"seed_overlap",func(f *FrozenPortfolio){f.Candidates[1].Draft.SeedIdentities[0]="Wingless:200"}},
  {"duplicate",func(f *FrozenPortfolio){f.Candidates=append(f.Candidates,f.Candidates[0])}},
  {"missing_ledger",func(f *FrozenPortfolio){f.ConsumedSeedIdentities=nil}},
  {"privilege",func(f *FrozenPortfolio){f.Candidates[1].Draft.DispatchAuthorized=true}},
  {"budget",func(f *FrozenPortfolio){f.Candidates[0].Draft.Budget.ComputeUnits=0}},
  {"epoch",func(f *FrozenPortfolio){f.Observations[0].AuthorityEpoch=41}},
  {"duplicate_lane",func(f *FrozenPortfolio){f.Observations[1].Lane=contracts.Wingless}},
 }
 for _,tc:=range edits{t.Run(tc.name,func(t *testing.T){f:=example();tc.fn(&f);b:=backend(f);_,_,e:=ReviewOnly(context.Background(),b,b,f,pin(t,f));if e==nil||b.submits!=0{t.Fatalf("unsafe batch accepted: %v",e)}})}
}
func TestMaliciousAcknowledgmentCannotAuthorizePrimary(t *testing.T){
 f:=example();b:=backend(f);b.forgeAck=true
 out,ack,e:=ReviewOnly(context.Background(),b,b,f,pin(t,f))
 if e==nil||len(ack)!=0||out.DispatchAuthorized{t.Fatalf("elevated acknowledgment accepted: %v",e)}
}
func TestOfflineOrMissingBackendDoesNotBecomeSuccess(t *testing.T){
 f:=example();b:=backend(f);b.refuse=true
 _,_,e:=ReviewOnly(context.Background(),b,b,f,pin(t,f));if e==nil{t.Fatal("failed inbox accepted")}
 delete(b.observations,contracts.Yggdrasil);b.refuse=false
 _,_,e=ReviewOnly(context.Background(),b,b,f,pin(t,f));if e==nil{t.Fatal("missing evidence accepted")}
}
func TestTieBreakAndNoCandidateNoInvention(t *testing.T){
 f:=example();c:=f.Candidates[0];c.Draft.CandidateID="alternate";c.Draft.CandidateSHA256=strings.Repeat("0",64);c.Draft.CohortSHA256=strings.Repeat("f",64);c.Draft.SeedIdentities=[]string{"Wingless:201"};f.Candidates=append(f.Candidates,c)
 out,e:=Build(f,pin(t,f));if e!=nil||out.Lanes[0].CandidateID!="alternate"{t.Fatalf("tie-break failed: %v",e)}
 f.Candidates=nil
 out,e=Build(f,pin(t,f));if e!=nil||out.Lanes[0].Draft!=nil||out.Lanes[1].Draft!=nil{t.Fatalf("invented candidate: %v",e)}
}

func TestFrozenCohortHashCollisionIsDenied(t *testing.T){
 f:=example()
 f.Candidates[1].Draft.CohortSHA256=f.Candidates[0].Draft.CohortSHA256
 b:=backend(f)
 _,_,e:=ReviewOnly(context.Background(),b,b,f,pin(t,f))
 if e==nil||b.submits!=0{t.Fatalf("cross-lane cohort identity collision accepted: %v",e)}
}
