package optimizerbridge

import (
 "errors"
 "strings"
 "testing"
)

type stagedEvidenceCheck struct {
 blockProspective bool
 blockAdmission bool
}
func (c stagedEvidenceCheck) VerifyProspectiveResearchSelection(p ProspectiveSelection)error{
 if c.blockProspective{return errors.New("no authenticated randomization or first-use")}
 return nil
}
func (c stagedEvidenceCheck) VerifyAcceptedScientificOutcome(p IndependentlyAcceptedOutcome)error{
 if c.blockAdmission{return errors.New("no independent custody admission")}
 return nil
}
func fill(c string,n int)string{return strings.Repeat(c,n)}
func baselineTrial(lane string)ProspectiveSelection{
 tag:="a"
 if lane=="Yggdrasil"{tag="b"}
 return ProspectiveSelection{
  Lane:lane,FrozenBaselinePolicySHA256:[]string{fill("1",64),fill("2",64)},
  FrozenDreamPolicySHA256:fill("3",64),FrozenParetoPolicySHA256:fill("4",64),
  PreregistrationSHA256:fill("5",64),ProspectiveSourceSHA:fill(tag,40),
  FirstUseReceiptSHA256:fill(tag,64),
  RandomizationAuditSHA256:fill("6",64),
  IndependentCausalReviewSHA256:fill("7",64),
 }
}
func baselineOutcome(lane string)IndependentlyAcceptedOutcome{
 ev:="8"
 if lane=="Yggdrasil"{ev="9"}
 return IndependentlyAcceptedOutcome{Lane:lane,SourceSHA:fill("c",40),
  AcceptedEvidenceSHA256:fill(ev,64),IndependentAdmissionSHA256:fill("d",64),
  FreshSinceFrozenPolicy:true}
}
func distinctProposal(lane string,generator string)StructuralMechanismProposal{
 id:="e"
 if lane=="Yggdrasil"{id="f"}
 return StructuralMechanismProposal{
 Lane:lane,SourceSHA:fill("a",40),CandidateSHA256:fill(id,64),
 Generator:generator,ParentRepresentation:"fixed-role-vector",
 NewRepresentation:"learned-public-belief-state",ParentConsumer:"greedy-ranker",
 NewConsumer:"trainable-binding-composer",
 ParentTestEnvironment:"fixed-grammar",NewTestEnvironment:"novel-relation-grammar",
 FrozenControlSHA256:[]string{fill("1",64),fill("2",64)},Status:"UNTESTED",
 }
}
func TestStageActivationActualDefaultBlocked(t *testing.T){
 got,err:=AssessActivation(nil,nil,nil,nil)
 if err!=nil{t.Fatal(err)}
 if got.DreamPareto!="WAITING_AUTHENTIC_PROSPECTIVE_COMPARISON"||
  got.ThetaEvolve!="WAITING_INDEPENDENTLY_ACCEPTED_NEW_RESULTS"||
  got.PromptbreederAndGenEnv!="WAITING_NOVEL_SOURCE_PROPOSALS"||
  got.ScientificOriginalDispatchAuthorized||got.ControllerCutoverAuthorized||
  got.AcceptedRefMutation||got.AuthenticatedProspectiveResearchSelection{
   t.Fatalf("unsafe default %+v",got)
 }
}
func TestStageActivationAuthenticTrustIsNotInferred(t *testing.T){
 w,y:=baselineTrial("Wingless"),baselineTrial("Yggdrasil")
 t.Run("missing verifier",func(t *testing.T){
  got,err:=AssessActivation([]ProspectiveSelection{w,y},nil,nil,nil)
  if err!=nil||got.AuthenticatedProspectiveResearchSelection||got.ThetaEvolve!="WAITING_INDEPENDENTLY_ACCEPTED_NEW_RESULTS"{
   t.Fatalf("source hashes forged trust %+v %v",got,err)
  }
 })
 t.Run("failed independent review",func(t *testing.T){
  got,err:=AssessActivation([]ProspectiveSelection{w,y},nil,nil,stagedEvidenceCheck{blockProspective:true})
  if !errors.Is(err,ErrStageEvidence)||got.AuthenticatedProspectiveResearchSelection{t.Fatalf("accepted unverified prospective %v %+v",err,got)}
 })
 t.Run("two verified comparison claims are not scientific promotion",func(t *testing.T){
  got,err:=AssessActivation([]ProspectiveSelection{w,y},nil,nil,stagedEvidenceCheck{})
  if err!=nil||!got.AuthenticatedProspectiveResearchSelection||
  got.DreamPareto!="ELIGIBLE_FOR_EXISTING_CONTROLLER_POLICY_GATE"||
  got.ThetaEvolve!="WAITING_INDEPENDENTLY_ACCEPTED_NEW_RESULTS"||
  got.ControllerCutoverAuthorized||got.ScientificOriginalDispatchAuthorized||
  got.AcceptedRefMutation{t.Fatalf("prematurely promoted science %v %+v",err,got)}
 })
 t.Run("one lane blocked",func(t *testing.T){
  if _,err:=AssessActivation([]ProspectiveSelection{w},nil,nil,stagedEvidenceCheck{});!errors.Is(err,ErrStageEvidence){t.Fatalf("single lane entered %v",err)}
 })
 t.Run("same receipt blocked",func(t *testing.T){
  y.FirstUseReceiptSHA256=w.FirstUseReceiptSHA256
  if _,err:=AssessActivation([]ProspectiveSelection{w,y},nil,nil,stagedEvidenceCheck{});!errors.Is(err,ErrStageEvidence){t.Fatalf("duplicate receipt entered %v",err)}
 })
}
func TestThetaRequiresIndependentAcceptedOutcomesAfterSelection(t *testing.T){
 trials:=[]ProspectiveSelection{baselineTrial("Wingless"),baselineTrial("Yggdrasil")}
 w,y:=baselineOutcome("Wingless"),baselineOutcome("Yggdrasil")
 for name,tc:=range map[string]func()[]IndependentlyAcceptedOutcome{
  "same parent source":func()[]IndependentlyAcceptedOutcome{
   o:=w;o.SourceSHA=trials[0].ProspectiveSourceSHA;return []IndependentlyAcceptedOutcome{o,y}},
  "not independent":func()[]IndependentlyAcceptedOutcome{
   o:=w;o.FreshSinceFrozenPolicy=false;return []IndependentlyAcceptedOutcome{o,y}},
  "duplicate evidence":func()[]IndependentlyAcceptedOutcome{
   o:=y;o.AcceptedEvidenceSHA256=w.AcceptedEvidenceSHA256;return []IndependentlyAcceptedOutcome{w,o}},
  "same source lane":func()[]IndependentlyAcceptedOutcome{
   o:=w;o.AcceptedEvidenceSHA256=fill("f",64);return []IndependentlyAcceptedOutcome{w,o}},
 }{
  t.Run(name,func(t *testing.T){
   if _,err:=AssessActivation(trials,tc(),nil,stagedEvidenceCheck{});!errors.Is(err,ErrStageEvidence){t.Fatalf("unsafe theta data accepted %v",err)}
  })
 }
 if _,err:=AssessActivation(trials,[]IndependentlyAcceptedOutcome{w,y},nil,stagedEvidenceCheck{blockAdmission:true});!errors.Is(err,ErrStageEvidence){
  t.Fatalf("rejected independent custody accepted %v",err)
 }
 good,err:=AssessActivation(trials,[]IndependentlyAcceptedOutcome{w,y},nil,stagedEvidenceCheck{})
 if err!=nil||good.ThetaEvolve!="ELIGIBLE_FOR_EXISTING_FROZEN_TRAINING_GATE"||
  good.ScientificOriginalDispatchAuthorized||good.AcceptedRefMutation{
  t.Fatalf("theta admissibility not constrained %v %+v",err,good)
 }
}
func TestPromptAndGenEnvDemandSubstantivelyDifferentMechanisms(t *testing.T){
 w:=distinctProposal("Wingless","Promptbreeder")
 y:=distinctProposal("Yggdrasil","DGM/GenEnv")
 result,err:=AssessActivation(nil,nil,[]StructuralMechanismProposal{w,y},nil)
 if err!=nil||result.PromptbreederAndGenEnv!="BOUNDED_UNTESTED_NOVELTY_PROPOSALS_READY"||
  result.ThetaEvolve!="WAITING_INDEPENDENTLY_ACCEPTED_NEW_RESULTS"||
  result.DreamPareto!="WAITING_AUTHENTIC_PROSPECTIVE_COMPARISON"||
  result.ScientificOriginalDispatchAuthorized||result.ControllerCutoverAuthorized{
  t.Fatalf("novelty should be untested only %v %+v",err,result)
 }
 cases:=map[string]func(*StructuralMechanismProposal){
  "cosmetic only":func(p *StructuralMechanismProposal){p.NewConsumer=p.ParentConsumer;p.NewRepresentation=p.ParentRepresentation},
  "missing meaningful control":func(p *StructuralMechanismProposal){p.FrozenControlSHA256=nil},
  "not untested":func(p *StructuralMechanismProposal){p.Status="SUPPORTED"},
  "source unpinned":func(p *StructuralMechanismProposal){p.SourceSHA=""},
  "unsupported generator":func(p *StructuralMechanismProposal){p.Generator="external-paid-model"},
 }
 for name,mutate:=range cases{
  t.Run(name,func(t *testing.T){
   changed:=w;mutate(&changed)
   if _,err:=AssessActivation(nil,nil,[]StructuralMechanismProposal{changed},nil);!errors.Is(err,ErrStageEvidence){
    t.Fatalf("structurally weak candidate passed %v",err)
   }
  })
 }
 y.CandidateSHA256=w.CandidateSHA256
 if _,err:=AssessActivation(nil,nil,[]StructuralMechanismProposal{w,y},nil);!errors.Is(err,ErrStageEvidence){
  t.Fatalf("duplicate novelty candidate accepted %v",err)
 }
}
