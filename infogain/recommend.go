// Package infogain ranks FROZEN experimental proposals by predicted information
// per compute unit. It cannot execute, originate scientific first-use, train a
// model, accept evidence, promote a policy, or change a protected reference.
package infogain

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"math"
	"sort"
)

const (
	FrozenSchema = "forge.infogain.frozen-experiment-selection.v1"
	DecisionSchema = "forge.infogain.advisory.v1"
	Domain = "FORGE-INFOGAIN-FROZEN-V1\n"
)
var ErrFrozen = errors.New("FORGE_INFOGAIN_FROZEN_SOURCE_OR_POLICY_INVALID")

// Reuse FORGE's existing mechanism families without importing authority from
// their non-executing optimizer packages. Theta remains proposal-only.
var generators = map[string]bool{
	"frozen_control": true, "dream_rsi": true, "shinka_pareto": true,
	"theta_evolve": true, "promptbreeder": true, "dgm_genenv": true,
}

type Hypothesis struct {
	IdentitySHA256 string `json:"identity_sha256"`
	PriorBP uint16 `json:"prior_bp"`
}

type Candidate struct {
	ID string `json:"id"`
	MechanismSHA256 string `json:"mechanism_sha256"`
	SourceSHA string `json:"source_sha"`
	Family string `json:"family"`
	Generator string `json:"generator"`
	// One 4-outcome distribution per hypothesis, in frozen hypothesis order.
	// Outcomes: supports, refutes, exposes limitation, uninformative.
	OutcomeGivenHypothesis [][4]uint16 `json:"outcome_given_hypothesis"`
	ExpectedTransferBP uint16 `json:"expected_transfer_bp"`
	ExpectedTransferGainBP uint16 `json:"expected_transfer_gain_bp"`
	ComputeUnits int64 `json:"compute_units"`
	TrainingOnly bool `json:"training_only"`
}

// Historical results, including negatives and indeterminate cases, remain
// present in the frozen archive. Hashes are identities, not proof that an
// external scientific custodian independently admitted the outcome.
type HistoryRecord struct {
	MechanismSHA256 string `json:"mechanism_sha256"`
	SourceSHA string `json:"source_sha"`
	EvidenceSHA256 string `json:"evidence_sha256"`
	Classification string `json:"classification"`
}

type Weights struct {
	InformationBP uint16 `json:"information_bp"`
	TransferBP uint16 `json:"transfer_bp"`
	LimitationBP uint16 `json:"limitation_bp"`
}

type Frozen struct {
	Schema string `json:"schema"`
	Lane string `json:"lane"`
	SourceSHA string `json:"source_sha"`
	Epoch uint64 `json:"epoch"`
	Hypotheses []Hypothesis `json:"hypotheses"`
	Candidates []Candidate `json:"candidates"`
	History []HistoryRecord `json:"history"`
	// Bound to a separately supplied historical record corpus. Equality is
	// local integrity, not a claim of completeness or independent custody.
	HistorySHA256 string `json:"history_sha256"`
	Weights Weights `json:"weights"`
	ComputeBudget int64 `json:"compute_budget"`
	MinInformationMicrobits int64 `json:"min_information_microbits"`
	MaxSelected int `json:"max_selected"`
	MaxPerFamily int `json:"max_per_family"`
}

type Ranked struct {
	ID string `json:"id"`
	Generator string `json:"generator"`
	MechanismSHA256 string `json:"mechanism_sha256"`
	SourceSHA string `json:"source_sha"`
	ExpectedInformationMicrobits int64 `json:"expected_information_microbits"`
	ExpectedUncertaintyReductionBP int64 `json:"expected_uncertainty_reduction_bp"`
	ExpectedTransferValueBP int64 `json:"expected_transfer_value_bp"`
	ExpectedLimitationBP int64 `json:"expected_limitation_bp"`
	EstimatedComputeUnits int64 `json:"estimated_compute_units"`
	PredictedValuePerComputeMicro int64 `json:"predicted_value_per_compute_micro"`
	Status string `json:"status"`
}

type Excluded struct {
	ID string `json:"id"`
	Reason string `json:"reason"`
}

type Decision struct {
	Schema string `json:"schema"`
	Lane string `json:"lane"`
	FrozenSHA256 string `json:"frozen_sha256"`
	Selected []Ranked `json:"selected"`
	Excluded []Excluded `json:"excluded"`
	HistoryPreserved []HistoryRecord `json:"history_preserved"`
	HistorySHA256 string `json:"history_sha256"`
	NegativeCount int `json:"negative_count"`
	InvalidCount int `json:"invalid_count"`
	IndeterminateCount int `json:"indeterminate_count"`
	ComputeReserved int64 `json:"compute_reserved"`
	EstimatedOnly bool `json:"estimated_only"`
	ScientificAccepted bool `json:"scientific_accepted"`
	ScientificFirstUseAuthorized bool `json:"scientific_first_use_authorized"`
	DispatchAuthorized bool `json:"dispatch_authorized"`
	PolicyPromotionAuthorized bool `json:"policy_promotion_authorized"`
	AcceptedRefMutation bool `json:"accepted_ref_mutation"`
}

func validHex(s string, n int) bool {
	if len(s)!=n { return false }
	for _,c:=range s {if !((c>='0'&&c<='9')||(c>='a'&&c<='f')) {return false}}
	return true
}
func validID(s string) bool {
	if len(s)==0||len(s)>72{return false}
	for _,c:=range s {
		if !((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='-'||c=='_'){return false}
	}
	return true
}
func validClass(s string) bool {
	switch s {
	case "SUPPORTED","NEGATIVE","MIXED","INVALID","CONSUMED_INDETERMINATE","LIMITATION":
		return true
	}
	return false
}
func validLane(s string) bool {
	return s=="Wingless"||s=="Yggdrasil"||s=="MassResearch"
}
func HistoryDigest(h []HistoryRecord) string {
	raw,_:=json.Marshal(h)
	sum:=sha256.Sum256(append([]byte("FORGE-INFOGAIN-HISTORY-V1\n"),raw...))
	return hex.EncodeToString(sum[:])
}
func Digest(f Frozen) string {
	raw,_:=json.Marshal(f)
	data:=append([]byte(Domain),raw...)
	sum:=sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}

func validate(f Frozen, pin string) error {
	if f.Schema!=FrozenSchema||!validLane(f.Lane)||!validHex(f.SourceSHA,40)||
		f.Epoch==0||!validHex(pin,64)||pin!=Digest(f)||
		f.ComputeBudget<1||f.ComputeBudget>1_000_000_000||
		f.MinInformationMicrobits<1||f.MinInformationMicrobits>2_000_000||
		!validHex(f.HistorySHA256,64)||HistoryDigest(f.History)!=f.HistorySHA256||
		f.MaxSelected<1||f.MaxSelected>8||f.MaxPerFamily<1||f.MaxPerFamily>2||
		len(f.Hypotheses)<2||len(f.Hypotheses)>6||
		len(f.Candidates)<1||len(f.Candidates)>40||len(f.History)>200||
		f.Weights.InformationBP<5000||
		uint32(f.Weights.InformationBP)+uint32(f.Weights.TransferBP)+uint32(f.Weights.LimitationBP)!=10000 {
		return ErrFrozen
	}
	prior:=uint32(0)
	for i,h:=range f.Hypotheses {
		if !validHex(h.IdentitySHA256,64)||h.PriorBP==0||h.PriorBP>10000||
			(i>0 && f.Hypotheses[i-1].IdentitySHA256>=h.IdentitySHA256){
			return ErrFrozen
		}
		prior+=uint32(h.PriorBP)
	}
	if prior!=10000{return ErrFrozen}
	experimentIDs:=map[string]bool{}
	mechanisms:=map[string]bool{}
	sources:=map[string]bool{}
	for _,c:=range f.Candidates {
		if !validID(c.ID)||experimentIDs[c.ID]||
			!validHex(c.MechanismSHA256,64)||mechanisms[c.MechanismSHA256]||
			!validHex(c.SourceSHA,40)||sources[c.SourceSHA]||
			!validID(c.Family)||!generators[c.Generator]||
			c.ComputeUnits<1||c.ComputeUnits>f.ComputeBudget||
			c.ExpectedTransferBP>10000||c.ExpectedTransferGainBP>10000||
			len(c.OutcomeGivenHypothesis)!=len(f.Hypotheses) {
			return ErrFrozen
		}
		for _,dist:=range c.OutcomeGivenHypothesis {
			var mass uint32
			for _,p:=range dist {mass+=uint32(p)}
			if mass!=10000{return ErrFrozen}
		}
		experimentIDs[c.ID]=true
		mechanisms[c.MechanismSHA256]=true
		sources[c.SourceSHA]=true
	}
	historyMechanisms:=map[string]bool{}
	historySources:=map[string]bool{}
	historyEvidence:=map[string]bool{}
	for _,h:=range f.History {
		if !validHex(h.MechanismSHA256,64)||!validHex(h.SourceSHA,40)||
			!validHex(h.EvidenceSHA256,64)||!validClass(h.Classification)||
			historySources[h.SourceSHA]||historyEvidence[h.EvidenceSHA256]||
			historyMechanisms[h.MechanismSHA256]{
			return ErrFrozen
		}
		historySources[h.SourceSHA]=true
		historyEvidence[h.EvidenceSHA256]=true
		historyMechanisms[h.MechanismSHA256]=true
	}
	return nil
}
func entropy(p []float64) float64 {
	var h float64
	for _,x:=range p {if x>0{h-=x*math.Log2(x)}}
	return h
}
func measure(f Frozen, c Candidate) Ranked {
	prob:=make([]float64,4)
	var conditionH float64
	for i,pred:=range c.OutcomeGivenHypothesis {
		p:=float64(f.Hypotheses[i].PriorBP)/10000
		dist:=make([]float64,4)
		for j,bp:=range pred {dist[j]=float64(bp)/10000;prob[j]+=p*dist[j]}
		conditionH+=p*entropy(dist)
	}
	info:=math.Max(0,entropy(prob)-conditionH)
	micro:=int64(math.Round(info*1_000_000))
	priordist:=make([]float64, len(f.Hypotheses))
	for i,h:=range f.Hypotheses {priordist[i]=float64(h.PriorBP)/10000}
	priorH:=entropy(priordist)
	uncertaintyBP:=int64(0)
	if priorH>0{uncertaintyBP=int64(math.Round(info/priorH*10000))}
	expectedTransfer:=int64(c.ExpectedTransferBP)*int64(c.ExpectedTransferGainBP)/10000
	limitationBP:=int64(math.Round(prob[2]*10000))
	// Every weight and forecast is frozen before observation. The score is a
	// projected preference, never measured scientific improvement.
	numerator:=int64(f.Weights.InformationBP)*(micro/100)+
		int64(f.Weights.TransferBP)*expectedTransfer+
		int64(f.Weights.LimitationBP)*limitationBP
	score:=numerator*1_000_000/c.ComputeUnits
	return Ranked{
		ID:c.ID, Generator:c.Generator, MechanismSHA256:c.MechanismSHA256,
		SourceSHA:c.SourceSHA, ExpectedInformationMicrobits:micro,
		ExpectedUncertaintyReductionBP:uncertaintyBP,
		ExpectedTransferValueBP:expectedTransfer, ExpectedLimitationBP:limitationBP,
		EstimatedComputeUnits:c.ComputeUnits,
		PredictedValuePerComputeMicro:score, Status:"UNTESTED_ESTIMATE_NOT_SCIENTIFIC_ACCEPTANCE",
	}
}

// Recommend emits only an immutable advisory. The pin authenticates equality
// with a frozen supplied snapshot, NOT external origin, prospective witnessing,
// independent experiments, real transfer or the authority to dispatch anything.
func Recommend(f Frozen, independentPin string)(Decision,error){
	var zero Decision
	if err:=validate(f,independentPin);err!=nil{return zero,err}
	out:=Decision{
		Schema:DecisionSchema,Lane:f.Lane,FrozenSHA256:independentPin,
		Selected:[]Ranked{},Excluded:[]Excluded{},
		HistoryPreserved:append([]HistoryRecord{},f.History...),
		HistorySHA256:f.HistorySHA256,EstimatedOnly:true,
	}
	consumedMechanisms:=map[string]bool{}
	consumedSources:=map[string]bool{}
	for _,record:=range f.History {
		consumedMechanisms[record.MechanismSHA256]=true
		consumedSources[record.SourceSHA]=true
		switch record.Classification{
		case "NEGATIVE","LIMITATION":out.NegativeCount++
		case "INVALID":out.InvalidCount++
		case "CONSUMED_INDETERMINATE":out.IndeterminateCount++
		}
	}
	eligible:=[]Ranked{}
	for _,c:=range f.Candidates {
		if consumedMechanisms[c.MechanismSHA256]||consumedSources[c.SourceSHA]{
			out.Excluded=append(out.Excluded,Excluded{ID:c.ID,Reason:"HISTORICAL_MECHANISM_OR_SOURCE_ALREADY_CONSUMED"})
			continue
		}
		r:=measure(f,c)
		if r.ExpectedInformationMicrobits<f.MinInformationMicrobits{
			out.Excluded=append(out.Excluded,Excluded{ID:c.ID,Reason:"INSUFFICIENT_HYPOTHESIS_DISCRIMINATION"})
			continue
		}
		eligible=append(eligible,r)
	}
	sort.Slice(eligible,func(i,j int)bool{
		if eligible[i].PredictedValuePerComputeMicro!=eligible[j].PredictedValuePerComputeMicro{
			return eligible[i].PredictedValuePerComputeMicro>eligible[j].PredictedValuePerComputeMicro
		}
		if eligible[i].ExpectedInformationMicrobits!=eligible[j].ExpectedInformationMicrobits{
			return eligible[i].ExpectedInformationMicrobits>eligible[j].ExpectedInformationMicrobits
		}
		return eligible[i].ID<eligible[j].ID
	})
	families:=map[string]int{}
	byID:=map[string]Candidate{}
	for _,c:=range f.Candidates {byID[c.ID]=c}
	for _,r:=range eligible{
		c:=byID[r.ID]
		reason:=""
		switch{
		case len(out.Selected)>=f.MaxSelected:reason="PORTFOLIO_SIZE_BOUND"
		case families[c.Family]>=f.MaxPerFamily:reason="FAMILY_DIVERSITY_BOUND"
		case r.EstimatedComputeUnits>f.ComputeBudget-out.ComputeReserved:reason="COMPUTE_BUDGET_BOUND"
		}
		if reason!="" {
			out.Excluded=append(out.Excluded,Excluded{ID:r.ID,Reason:reason})
			continue
		}
		out.Selected=append(out.Selected,r)
		families[c.Family]++
		out.ComputeReserved+=r.EstimatedComputeUnits
	}
	sort.Slice(out.Excluded,func(i,j int)bool{return out.Excluded[i].ID<out.Excluded[j].ID})
	return out,nil
}
