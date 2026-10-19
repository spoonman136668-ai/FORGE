package infogain

// These typed adapters REUSE qualified native FORGE optimizer implementations.
// Their results are proposal lineage identities ONLY: a native mutation or
// policy delta is not a new independent source birth, experiment or science
// accepted outcome. A separately frozen, independently originated candidate
// source and pre-outcome forecast are required before Recommend may rank one.

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"

	"github.com/spoonman136668-ai/forge/dreamrsi"
	"github.com/spoonman136668-ai/forge/evoportfolio"
	"github.com/spoonman136668-ai/forge/genenv"
	"github.com/spoonman136668-ai/forge/promptlineage"
	"github.com/spoonman136668-ai/forge/thetaadapt"
)

type NativeOrigin struct {
	Generator string `json:"generator"`
	Lane string `json:"lane"`
	ParentSourceSHA string `json:"parent_source_sha"`
	MechanismSHA256 string `json:"mechanism_sha256"`
	NativeOutputSHA256 string `json:"native_output_sha256"`
	HistoricalClass string `json:"historical_class"`
	IndependentNewSourceBorn bool `json:"independent_new_source_born"`
	ScientificAccepted bool `json:"scientific_accepted"`
	DispatchAuthorized bool `json:"dispatch_authorized"`
	TrainingOnly bool `json:"training_only"`
}
func nativeHash(kind string,result any)string {
	raw,_:=json.Marshal(result)
	data:=append([]byte("FORGE-INFOGAIN-NATIVE-"+kind+"\n"),raw...)
	sum:=sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}
func native(generator,lane,parent,mechanism,artifact,classification string,trainingOnly bool)(NativeOrigin,error) {
	if !validLane(lane)||!validHex(parent,40)||!validHex(mechanism,64)||
		!validHex(artifact,64)||!generators[generator]{
		return NativeOrigin{},ErrFrozen
	}
	return NativeOrigin{
		Generator:generator,Lane:lane,ParentSourceSHA:parent,
		MechanismSHA256:mechanism,NativeOutputSHA256:artifact,
		HistoricalClass:classification,TrainingOnly:trainingOnly,
	},nil
}

// DreamRSIOrigin consumes an already validated Dream-RSI selection.
// Its original source must be separately anchored by the caller.
func DreamRSIOrigin(o dreamrsi.Optimization, parentSourceSHA string)(NativeOrigin,error){
	if dreamrsi.ValidateOptimization(o)!=nil{return NativeOrigin{},ErrFrozen}
	return native("dream_rsi",o.Lane,parentSourceSHA,
		o.SelectedPolicySHA256,nativeHash("DREAMRSI",o),"HISTORICAL_OPTIMIZATION",false)
}

// ParetoOrigins calls the existing bounded Pareto family selector and retains
// native historical classifications, including negatives. No source promotion.
func ParetoOrigins(f evoportfolio.Frozen, independentPin string)([]NativeOrigin,error){
	result,err:=evoportfolio.Select(f,independentPin)
	if err!=nil{return nil,ErrFrozen}
	out:=make([]NativeOrigin,0,len(result.Archive))
	for _,candidate:=range result.Archive{
		// Every historical record remains visible for negative-memory reuse.
		proof:=nativeHash("PARETO",struct{
			Freeze string `json:"freeze"`
			Candidate evoportfolio.Candidate `json:"candidate"`
		}{independentPin,candidate})
		origin,e:=native("shinka_pareto",f.Lane,candidate.SourceSHA,
			candidate.ScreenSHA,proof,candidate.HistoricalClass,false)
		if e!=nil{return nil,ErrFrozen}
		out=append(out,origin)
	}
	return out,nil
}

// ThetaOrigin derives training-only optimizer adaptations; never convert
// apparently positive results into accepted policy or scientific outcomes.
func ThetaOrigin(f thetaadapt.Frozen,pin string,h thetaadapt.Training,hpin string)(NativeOrigin,error){
	p,err:=thetaadapt.Adapt(f,pin,h,hpin)
	if err!=nil{return NativeOrigin{},ErrFrozen}
	proof:=nativeHash("THETA",p)
	return native("theta_evolve",f.Lane,f.SourceSHA,proof,proof,"TRAINING_ONLY",true)
}

// PromptOrigins uses FORGE's native bounded prompt-lineage generator; each
// output still requires a genuinely new qualified experimental source.
func PromptOrigins(f promptlineage.Frozen,pin string)([]NativeOrigin,error){
	p,err:=promptlineage.Generate(f,pin)
	if err!=nil{return nil,ErrFrozen}
	out:=make([]NativeOrigin,0,len(p.Candidates))
	for _,candidate:=range p.Candidates{
		proof:=nativeHash("PROMPTBREEDER",struct{
			Freeze string `json:"freeze"`
			Candidate promptlineage.Candidate `json:"candidate"`
		}{pin,candidate})
		o,e:=native("promptbreeder",f.Lane,f.SourceSHA,
			candidate.CandidateSHA256,proof,candidate.Classification,false)
		if e!=nil{return nil,ErrFrozen}
		out=append(out,o)
	}
	return out,nil
}

// GenEnvOrigins preserves all native training history and produces untested
// environment identities without calling a model, worker or FSA.
func GenEnvOrigins(f genenv.Frozen,pin string,h genenv.History,hpin string)([]NativeOrigin,error){
	p,err:=genenv.Generate(f,pin,h,hpin)
	if err!=nil{return nil,ErrFrozen}
	out:=make([]NativeOrigin,0,len(p.Candidates))
	for _,candidate:=range p.Candidates{
		proof:=nativeHash("GENENV",struct{
			Freeze string `json:"freeze"`
			Candidate genenv.Candidate `json:"candidate"`
		}{pin,candidate})
		o,e:=native("dgm_genenv",f.Lane,f.SourceSHA,
			candidate.EnvironmentSHA256,proof,candidate.Classification,true)
		if e!=nil{return nil,ErrFrozen}
		out=append(out,o)
	}
	return out,nil
}
