package infogain

import (
	"reflect"
	"strings"
	"testing"
)

func repHex(n int, c string) string { return strings.Repeat(c,n) }

func informative() [][4]uint16 {
	return [][4]uint16{{10000,0,0,0},{0,10000,0,0}}
}
func uninformative() [][4]uint16 {
	return [][4]uint16{{5000,5000,0,0},{5000,5000,0,0}}
}
func fixture() Frozen {
	f:=Frozen{
		Schema:FrozenSchema,Lane:"Wingless",SourceSHA:repHex(40,"f"),Epoch:1,
		Weights:Weights{InformationBP:7000,TransferBP:2000,LimitationBP:1000},
		ComputeBudget:200, MinInformationMicrobits:10000, MaxSelected:3,MaxPerFamily:2,
		Hypotheses:[]Hypothesis{
			{IdentitySHA256:repHex(64,"1"),PriorBP:5000},
			{IdentitySHA256:repHex(64,"2"),PriorBP:5000},
		},
		Candidates:[]Candidate{
			{ID:"learned-causal-fast",MechanismSHA256:repHex(64,"a"),
				SourceSHA:repHex(40,"a"),Family:"causal-representation",
				Generator:"dream_rsi",OutcomeGivenHypothesis:informative(),
				ExpectedTransferBP:5000,ExpectedTransferGainBP:5000,ComputeUnits:10},
			{ID:"learned-causal-slow",MechanismSHA256:repHex(64,"b"),
				SourceSHA:repHex(40,"b"),Family:"causal-representation",
				Generator:"shinka_pareto",OutcomeGivenHypothesis:informative(),
				ExpectedTransferBP:5000,ExpectedTransferGainBP:5000,ComputeUnits:100},
			{ID:"uninformative-quick-win",MechanismSHA256:repHex(64,"c"),
				SourceSHA:repHex(40,"c"),Family:"benchmark-rate",
				Generator:"frozen_control",OutcomeGivenHypothesis:uninformative(),
				ExpectedTransferBP:10000,ExpectedTransferGainBP:10000,ComputeUnits:1},
		},
	}
	f.HistorySHA256=HistoryDigest(f.History)
	return f
}
func TestInformationPerComputeBeatsCheapUninformativeThroughput(t *testing.T){
	f:=fixture()
	pin:=Digest(f)
	got,err:=Recommend(f,pin)
	if err!=nil {t.Fatal(err)}
	if len(got.Selected)!=2||got.Selected[0].ID!="learned-causal-fast"||
		got.Selected[1].ID!="learned-causal-slow" {t.Fatalf("unexpected ranking: %+v",got.Selected)}
	if got.Selected[0].ExpectedInformationMicrobits!=1000000 {
		t.Errorf("1-bit perfect discrimination expected, got %d",got.Selected[0].ExpectedInformationMicrobits)
	}
	if got.Selected[0].ExpectedUncertaintyReductionBP!=10000 {
		t.Fatalf("uncertainty not reduced: %+v",got.Selected[0])
	}
	if len(got.Excluded)!=1||got.Excluded[0].Reason!="INSUFFICIENT_HYPOTHESIS_DISCRIMINATION"{
		t.Fatalf("uninformative quick-win not excluded: %+v",got.Excluded)
	}
	if got.ScientificAccepted||got.ScientificFirstUseAuthorized||
		got.DispatchAuthorized||got.PolicyPromotionAuthorized||got.AcceptedRefMutation||!got.EstimatedOnly {
		t.Fatalf("advisory acquired authority: %+v",got)
	}
	if got.ComputeReserved!=110{t.Fatalf("incorrect cost: %d",got.ComputeReserved)}
}

func TestHistoricalNegativeAndConsumedSourceRetainedNeverRedispatched(t *testing.T){
	f:=fixture()
	f.Candidates=append(f.Candidates, Candidate{
		ID:"known-negative", MechanismSHA256:repHex(64,"d"),SourceSHA:repHex(40,"d"),
		Family:"memory",Generator:"theta_evolve",
		OutcomeGivenHypothesis:informative(),ComputeUnits:1,
	})
	f.History=[]HistoryRecord{
		{MechanismSHA256:repHex(64,"d"),SourceSHA:repHex(40,"4"),
			EvidenceSHA256:repHex(64,"8"),Classification:"NEGATIVE"},
		{MechanismSHA256:repHex(64,"e"),SourceSHA:repHex(40,"5"),
			EvidenceSHA256:repHex(64,"9"),Classification:"CONSUMED_INDETERMINATE"},
	}
	f.HistorySHA256=HistoryDigest(f.History)
	got,err:=Recommend(f,Digest(f))
	if err!=nil{t.Fatal(err)}
	if got.NegativeCount!=1||got.IndeterminateCount!=1||
		!reflect.DeepEqual(got.HistoryPreserved,f.History){
		t.Fatalf("history discarded or reclassified: %+v",got)
	}
	for _,c:=range got.Selected{if c.ID=="known-negative"{t.Fatal("repeated exact negative mechanism")}}
	found:=false
	for _,c:=range got.Excluded {if c.ID=="known-negative"&&c.Reason=="HISTORICAL_MECHANISM_OR_SOURCE_ALREADY_CONSUMED"{found=true}}
	if !found{t.Fatalf("did not explicitly retain negative exclusion: %+v",got.Excluded)}
}

func TestFrozenSourceAndPreOutcomeIdentityTamperingDenied(t *testing.T){
	f:=fixture()
	pin:=Digest(f)
	f.Candidates[0].ComputeUnits++
	if _,err:=Recommend(f,pin);err!=ErrFrozen{t.Fatalf("unfrozen compute changed: %v",err)}
	f=fixture()
	f.HistorySHA256=repHex(64,"0")
	if _,err:=Recommend(f,Digest(f));err!=ErrFrozen{t.Fatalf("hidden archive tampering accepted: %v",err)}
	f=fixture()
	f.Hypotheses[0].PriorBP=9000
	if _,err:=Recommend(f,Digest(f));err!=ErrFrozen{t.Fatalf("broken hypothesis prior accepted: %v",err)}
	f=fixture()
	f.Candidates[0].OutcomeGivenHypothesis[0][0]=9000
	if _,err:=Recommend(f,Digest(f));err!=ErrFrozen{t.Fatalf("non-normalized probability accepted: %v",err)}
	f=fixture()
	f.Candidates[0].SourceSHA=f.SourceSHA
	if _,err:=Recommend(f,Digest(f));err!=ErrFrozen{t.Fatalf("parent source reused as novel proposal: %v",err)}
	f=fixture()
	f.Candidates[0].Generator="github-execution-authority"
	if _,err:=Recommend(f,Digest(f));err!=ErrFrozen{t.Fatalf("unsafe optimizer accepted: %v",err)}
	f=fixture()
	f.Weights.InformationBP=4900;f.Weights.TransferBP=4100
	if _,err:=Recommend(f,Digest(f));err!=ErrFrozen{t.Fatalf("info deprioritized below threshold: %v",err)}
}

func TestAllExistingOptimizersAreAdvisoryAndLanesIsolated(t *testing.T){
	for _,lane:=range []string{"Wingless","Yggdrasil","MassResearch"}{
		f:=fixture()
		f.Lane=lane
		f.MaxSelected=8
		f.MaxPerFamily=2
		f.ComputeBudget=200
		f.Candidates=nil
		for i,generator:=range []string{
			"frozen_control","dream_rsi","shinka_pareto",
			"theta_evolve","promptbreeder","dgm_genenv",
		}{
			c:=Candidate{
				ID:"candidate-"+generator,
				MechanismSHA256:repHex(64,string(rune('a'+i))),
				SourceSHA:repHex(40,string(rune('g'+i))),
				Family:"mechanism-"+generator,Generator:generator,
				OutcomeGivenHypothesis:informative(),ComputeUnits:int64(1+i),
			}
			f.Candidates=append(f.Candidates,c)
		}
		got,err:=Recommend(f,Digest(f))
		if err!=nil{t.Fatal(err)}
		if len(got.Selected)!=6||got.Lane!=lane {t.Errorf("%s advisory omitted optimization: %+v",lane,got)}
		if got.ScientificAccepted||got.DispatchAuthorized||got.ScientificFirstUseAuthorized{
			t.Fatal("optimizer route granted scientific authority")
		}
	}
}

func TestBudgetDiversityAndDeterministicSelection(t *testing.T){
	f:=fixture()
	f.Candidates=f.Candidates[:2]
	f.MaxSelected=2
	f.MaxPerFamily=1
	got,err:=Recommend(f,Digest(f))
	if err!=nil{t.Fatal(err)}
	if len(got.Selected)!=1||got.Selected[0].ID!="learned-causal-fast"{
		t.Fatalf("diversity not enforced: %+v",got)
	}
	f.MaxPerFamily=2
	f.ComputeBudget=100
	// The second item costs 100, but 10 units have already been reserved.
	got,err=Recommend(f,Digest(f))
	if err!=nil{t.Fatal(err)}
	if len(got.Selected)!=1||got.Excluded[0].Reason!="COMPUTE_BUDGET_BOUND"{
		t.Fatalf("compute budget not enforced: %+v",got)
	}
	second,err:=Recommend(f,Digest(f))
	if err!=nil||!reflect.DeepEqual(got,second){t.Fatalf("nondeterministic ranking: %v",err)}
}

func TestLimitationEvidenceCanBeInformativeWithoutSuccess(t *testing.T){
	f:=fixture()
	f.Candidates=[]Candidate{{
		ID:"limitation-finder",MechanismSHA256:repHex(64,"d"),
		SourceSHA:repHex(40,"d"),Family:"limits",Generator:"dgm_genenv",
		OutcomeGivenHypothesis:[][4]uint16{
			{0,0,10000,0},
			{0,0,0,10000},
		},ComputeUnits:20,
	}}
	r,err:=Recommend(f,Digest(f))
	if err!=nil||len(r.Selected)!=1{t.Fatalf("limit-finder was discarded: %v %+v",err,r)}
	if r.Selected[0].ExpectedLimitationBP!=5000{
		t.Fatalf("limitation discriminability miscomputed: %+v",r.Selected[0])
	}
}
