package infogain

import (
	"strings"
	"testing"

	"github.com/spoonman136668-ai/forge/dreamrsi"
	"github.com/spoonman136668-ai/forge/evoportfolio"
	"github.com/spoonman136668-ai/forge/genenv"
	"github.com/spoonman136668-ai/forge/promptlineage"
	"github.com/spoonman136668-ai/forge/thetaadapt"
)

func requireProposalOnly(t *testing.T, a NativeOrigin){
	t.Helper()
	if a.ScientificAccepted||a.DispatchAuthorized||a.IndependentNewSourceBorn||
		!validHex(a.NativeOutputSHA256,64)||!validHex(a.MechanismSHA256,64) {
		t.Fatalf("native optimizer bypassed scientific authority: %+v",a)
	}
}

func TestPromptbreederReuseIsTypedAndNeverSourceBirth(t *testing.T){
	f:=promptlineage.Frozen{
		Schema:promptlineage.Schema,Lane:"Wingless",Epoch:1,
		SourceSHA:strings.Repeat("a",40),Parent:"reason with bounded evidence",
		Vocabulary:[]string{"verified","strict"},MaxOperations:2,
		Operations:[]promptlineage.Operation{
			{Kind:"replace",Position:2,Replacement:"verified"},
			{Kind:"swap-next",Position:0},
		},
	}
	pin:=promptlineage.Digest(f)
	out,err:=PromptOrigins(f,pin)
	if err!=nil||len(out)!=2{t.Fatalf("adapter failed: %v %+v",err,out)}
	for _,a:=range out {
		requireProposalOnly(t,a)
		if a.Generator!="promptbreeder"||a.HistoricalClass!="UNTESTED"||
			a.ParentSourceSHA!=f.SourceSHA{t.Fatalf("lineage lost: %+v",a)}
	}
	f.Parent="tampered parent text"
	if _,err:=PromptOrigins(f,pin);err!=ErrFrozen{t.Fatalf("tampered prompt accepted: %v",err)}
}

func TestNativeGenEnvRetainsNegativeTrainingProvenance(t *testing.T){
	h:=genenv.History{Schema:genenv.HistorySchema,Lane:"Yggdrasil",
		SourceSHA:strings.Repeat("b",40),Records:[]genenv.Record{
			{Sequence:1,EvidenceSHA256:strings.Repeat("f",64),
				TrainingOnly:true,Classification:"NEGATIVE",Vector:[]int64{0,1,1}},
	}}
	hpin:=genenv.HistoryDigest(h)
	f:=genenv.Frozen{Schema:genenv.FrozenSchema,Lane:"Yggdrasil",
		Epoch:1,SourceSHA:h.SourceSHA,HistorySHA256:hpin,
		Base:[]int64{1,1,1},MaxLevel:3,MaxCandidates:1,MaxOperations:1,
		Requests:[]genenv.Request{{ID:"newenv",Changes:[]genenv.Change{{Index:2,Delta:1}}}},
	}
	out,err:=GenEnvOrigins(f,genenv.FrozenDigest(f),h,hpin)
	if err!=nil||len(out)!=1{t.Fatalf("GenEnv integration denied: %v %+v",err,out)}
	requireProposalOnly(t,out[0])
	if out[0].Generator!="dgm_genenv"||!out[0].TrainingOnly{
		t.Fatalf("unqualified GenEnv output: %+v",out[0])
	}
	h.Records[0].Classification="SUPPORTED"
	if _,err:=GenEnvOrigins(f,genenv.FrozenDigest(f),h,hpin);err!=ErrFrozen{
		t.Fatalf("hidden negative-history drift accepted: %v",err)
	}
}

func TestNativeThetaTrainingOnlyAndNoScientificAuthority(t *testing.T){
	h:=thetaadapt.Training{Schema:thetaadapt.TrainingSchema,Lane:"Wingless",
		SourceSHA:strings.Repeat("c",40),Records:[]thetaadapt.TrainingRecord{
			{Sequence:1,EvidenceSHA256:strings.Repeat("1",64),
				Classification:"NEGATIVE",TrainingOnly:true,
				Compute:2,Direction:[]int64{1,-1}},
		}}
	hpin:=thetaadapt.TrainingDigest(h)
	f:=thetaadapt.Frozen{
		Schema:thetaadapt.FrozenSchema,Lane:"Wingless",Epoch:1,
		SourceSHA:h.SourceSHA,TrainingSHA256:hpin,FeatureCount:2,
		InitialWeights:[]int64{0,0},MaxAbsWeight:4,LearningStep:1,
		MaxUpdates:1,MaxTrainingCompute:3,
	}
	pin:=thetaadapt.FrozenDigest(f)
	o,err:=ThetaOrigin(f,pin,h,hpin)
	if err!=nil{t.Fatal(err)}
	requireProposalOnly(t,o)
	if !o.TrainingOnly||o.Generator!="theta_evolve"{
		t.Fatalf("Theta training-only boundary removed: %+v",o)
	}
	h.Records[0].TrainingOnly=false
	if _,err:=ThetaOrigin(f,pin,h,hpin);err!=ErrFrozen{
		t.Fatalf("unqualified theta training admitted: %v",err)
	}
}

func TestNativeParetoRetainsNegativeAndNoOutcomePromotion(t *testing.T){
	f:=evoportfolio.Frozen{
		Schema:evoportfolio.Schema,Lane:"Wingless",Epoch:1,
		HistoricalSourceSHA:strings.Repeat("e",64),MaxScreenCompute:10,
		MaxSealedCompute:10,MaxFinalists:2,MaxPerFamily:2,
		MaxScreensPerFamily:2,
		Candidates:[]evoportfolio.Candidate{
			{ID:"baseline",Family:"one",SourceSHA:strings.Repeat("a",40),
				ScreenSHA:strings.Repeat("a",64),HistoricalClass:"SUPPORTED",
				Score:8,ScreenCompute:2,SealedCompute:2},
			{ID:"negative",Family:"one",SourceSHA:strings.Repeat("b",40),
				ScreenSHA:strings.Repeat("b",64),HistoricalClass:"NEGATIVE",
				Score:0,ScreenCompute:2,SealedCompute:2},
		},
	}
	origins,err:=ParetoOrigins(f,evoportfolio.Digest(f))
	if err!=nil||len(origins)!=2{t.Fatalf("Pareto adapter failed: %v %+v",err,origins)}
	negative:=0
	for _,o:=range origins{
		requireProposalOnly(t,o)
		if o.HistoricalClass=="NEGATIVE"{negative++}
	}
	if negative!=1{t.Fatal("Pareto negative result silently omitted")}
	f.Candidates[0].Score=3000000
	if _,err:=ParetoOrigins(f,evoportfolio.Digest(f));err!=ErrFrozen{
		t.Fatalf("outside Pareto score bounds accepted: %v",err)
	}
}

func TestUnvalidatedDreamRSIPolicyCannotBeSourceBirth(t *testing.T){
	if _,err:=DreamRSIOrigin(dreamrsi.Optimization{
		Schema:dreamrsi.OptimizationSchema,Lane:"Wingless",
	},strings.Repeat("d",40));err!=ErrFrozen{
		t.Fatalf("forged Dream-RSI evidence accepted: %v",err)
	}
}
