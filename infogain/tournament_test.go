package infogain

import (
 "reflect"
 "strings"
 "testing"
 "math/big"
)

func tournamentHex(s string,n int) string { return strings.Repeat(s,n) }

func tournamentFixture() Frozen {
 a,b,c := [4]uint16{10000,0,0,0},[4]uint16{0,10000,0,0},[4]uint16{0,0,10000,0}
 f:=Frozen{
  Schema:FrozenSchema,Lane:"Yggdrasil",SourceSHA:tournamentHex("f",40),
  Epoch:1,Weights:Weights{InformationBP:10000},
  Hypotheses:[]Hypothesis{
   {IdentitySHA256:tournamentHex("1",64),PriorBP:3334},
   {IdentitySHA256:tournamentHex("2",64),PriorBP:3333},
   {IdentitySHA256:tournamentHex("3",64),PriorBP:3333},
  },
  Candidates:[]Candidate{
   {ID:"first",MechanismSHA256:tournamentHex("a",64),SourceSHA:tournamentHex("a",40),Family:"separate-a",Generator:"frozen_control",OutcomeGivenHypothesis:[][4]uint16{a,b,b},ComputeUnits:1},
   {ID:"second",MechanismSHA256:tournamentHex("b",64),SourceSHA:tournamentHex("b",40),Family:"separate-b",Generator:"frozen_control",OutcomeGivenHypothesis:[][4]uint16{c,a,b},ComputeUnits:10},
  },
  ComputeBudget:11,MaxSelected:2,MaxPerFamily:2,MinInformationMicrobits:10000,
 }
 f.HistorySHA256=HistoryDigest(f.History)
 return f
}

func TestTournamentTwoDevelopmentFeedbackStepsAndColdReplay(t *testing.T){
 f:=tournamentFixture();pin:=Digest(f);original:=tournamentFixture()
 s,err:=NewTournament(f,pin);if err!=nil{t.Fatal(err)}
 p,err:=NextTournamentProbe(f,pin,s)
 if err!=nil||p.CandidateID!="first"||p.BudgetRemaining!=11{t.Fatalf("unexpected first choice %v %+v",err,p)}
 first:=TournamentObservation{CandidateID:p.CandidateID,SourceSHA:p.SourceSHA,MechanismSHA256:p.MechanismSHA256,Outcome:1,EvidenceSHA256:tournamentHex("9",64)}
 s2,err:=RecordTournamentOutcome(f,pin,s,first);if err!=nil{t.Fatal(err)}
 if len(s.Observations)!=0{t.Fatal("original state mutated")}
 p,err=NextTournamentProbe(f,pin,s2)
 if err!=nil||p.CandidateID!="second"||p.PosteriorBP[0]!=0||p.BudgetRemaining!=10||p.StepsCompleted!=1{t.Fatalf("feedback not used %v %+v",err,p)}
 second:=TournamentObservation{CandidateID:p.CandidateID,SourceSHA:p.SourceSHA,MechanismSHA256:p.MechanismSHA256,Outcome:0,EvidenceSHA256:tournamentHex("8",64)}
 s3,err:=RecordTournamentOutcome(f,pin,s2,second);if err!=nil{t.Fatal(err)}
 p,err=NextTournamentProbe(f,pin,s3)
 if err!=nil||!p.Exhausted||p.BudgetRemaining!=0||p.StepsCompleted!=2||p.PosteriorBP[1]!=10000{t.Fatalf("incorrect terminal result %v %+v",err,p)}
 if !reflect.DeepEqual(f,original){t.Fatal("frozen data mutated")}
 cold,err:=NextTournamentProbe(f,pin,s3)
 if err!=nil||!reflect.DeepEqual(p,cold){t.Fatal("cold replay changed")}
 other:=first;other.Outcome=0;other.EvidenceSHA256=tournamentHex("7",64)
 otherState,err:=RecordTournamentOutcome(f,pin,s,other);if err!=nil{t.Fatal(err)}
 otherProbe,err:=NextTournamentProbe(f,pin,otherState)
 if err!=nil||!otherProbe.Exhausted||otherProbe.PosteriorBP[0]!=10000{t.Fatalf("opposite outcome did not change continuation %v %+v",err,otherProbe)}
 if !s3.DevelopmentOnly||s3.ScientificAccepted||s3.DispatchAuthorized||s3.ScientificFirstUseAuthorized||s3.AcceptedRefMutation{t.Fatal("development gained authority")}
}
func TestTournamentHistoricalNegativeAndZeroLikelihood(t *testing.T){
 f:=tournamentFixture();pin:=Digest(f);s,_:=NewTournament(f,pin);p,_:=NextTournamentProbe(f,pin,s)
 bad:=TournamentObservation{CandidateID:p.CandidateID,MechanismSHA256:p.MechanismSHA256,SourceSHA:p.SourceSHA,Outcome:2,EvidenceSHA256:tournamentHex("8",64)}
 if _,err:=RecordTournamentOutcome(f,pin,s,bad);err==nil{t.Fatal("impossible outcome accepted")}
 for _,prior:=range [][]uint16{{1,9999},{5000,5000},{0,0}}{
  if _,err:=tournamentPosterior(prior,[]uint16{0,0});err==nil{t.Fatal("zero mass accepted")}
 }
 f.History=[]HistoryRecord{{MechanismSHA256:f.Candidates[0].MechanismSHA256,SourceSHA:f.Candidates[0].SourceSHA,EvidenceSHA256:tournamentHex("7",64),Classification:"NEGATIVE"}}
 f.HistorySHA256=HistoryDigest(f.History);pin=Digest(f);s,_=NewTournament(f,pin)
 p,err:=NextTournamentProbe(f,pin,s)
 if err!=nil||p.CandidateID!="second"{t.Fatalf("historical negative reused %v %+v",err,p)}
}
func TestTournamentTamperAndReplayDenials(t *testing.T){
 f:=tournamentFixture();pin:=Digest(f);s,_:=NewTournament(f,pin);p,_:=NextTournamentProbe(f,pin,s)
 obs:=TournamentObservation{CandidateID:p.CandidateID,MechanismSHA256:p.MechanismSHA256,SourceSHA:p.SourceSHA,Outcome:1,EvidenceSHA256:tournamentHex("8",64)}
 done,err:=RecordTournamentOutcome(f,pin,s,obs);if err!=nil{t.Fatal(err)}
 changes:=[]TournamentState{done,done,done,done,done}
 changes[0].ReceiptSHA256="0"+done.ReceiptSHA256[1:]
 changes[1].DispatchAuthorized=true;changes[1].ReceiptSHA256=tournamentReceipt(changes[1])
 changes[2].Observations=append([]TournamentObservation(nil),done.Observations...);changes[2].Observations[0].CandidateID="second";changes[2].ReceiptSHA256=tournamentReceipt(changes[2])
 changes[3].Observations=append([]TournamentObservation(nil),done.Observations...);changes[3].Observations[0].Outcome=2;changes[3].ReceiptSHA256=tournamentReceipt(changes[3])
 changes[4].Lane="Wingless";changes[4].ReceiptSHA256=tournamentReceipt(changes[4])
 for i,x:=range changes{if _,err:=NextTournamentProbe(f,pin,x);err==nil{t.Fatalf("tamper %d accepted",i)}}
 bad:=obs;bad.EvidenceSHA256="untrusted"
 if _,err:=RecordTournamentOutcome(f,pin,s,bad);err==nil{t.Fatal("invalid evidence ID admitted")}
 step,err:=NextTournamentProbe(f,pin,done);if err!=nil{t.Fatal(err)}
 reused:=TournamentObservation{CandidateID:step.CandidateID,MechanismSHA256:step.MechanismSHA256,SourceSHA:step.SourceSHA,Outcome:0,EvidenceSHA256:obs.EvidenceSHA256}
 if _,err:=RecordTournamentOutcome(f,pin,done,reused);err==nil{t.Fatal("duplicate evidence admitted")}
 changed:=tournamentFixture();changed.ComputeBudget=12
 if _,err:=NextTournamentProbe(changed,pin,done);err==nil{t.Fatal("source drift admitted")}
}

func TestTournamentRejectsHistoricalEvidenceIDReuse(t *testing.T) {
 f := tournamentFixture()
 // The previous negative belongs to a distinct source and mechanism, so
 // both fresh proposal candidates remain eligible. Only the evidence
 // identity must be globally consumed.
 f.History = []HistoryRecord{{
  MechanismSHA256: tournamentHex("d", 64),
  SourceSHA: tournamentHex("c", 40),
  EvidenceSHA256: tournamentHex("9", 64),
  Classification: "NEGATIVE",
 }}
 f.HistorySHA256 = HistoryDigest(f.History)
 pin := Digest(f)
 state, err := NewTournament(f, pin)
 if err != nil { t.Fatal(err) }
 first, err := NextTournamentProbe(f, pin, state)
 if err != nil || first.Exhausted || first.CandidateID != "first" {
  t.Fatalf("fresh candidate incorrectly excluded: %v %+v", err, first)
 }
 obs := TournamentObservation{
  CandidateID: first.CandidateID, SourceSHA: first.SourceSHA,
  MechanismSHA256: first.MechanismSHA256, Outcome: 1,
  EvidenceSHA256: f.History[0].EvidenceSHA256,
 }
 if _, err := RecordTournamentOutcome(f, pin, state, obs); err == nil {
  t.Fatal("pre-consumed historical evidence silently reused")
 }
 // A locally rehashed transcript is not an exception to the replay guard.
 forged := state
 forged.Observations = []TournamentObservation{obs}
 forged.ReceiptSHA256 = tournamentReceipt(forged)
 if _, err := NextTournamentProbe(f, pin, forged); err == nil {
  t.Fatal("rehashing a duplicate historical event bypassed replay guard")
 }
 obs.EvidenceSHA256 = tournamentHex("8", 64)
 after, err := RecordTournamentOutcome(f, pin, state, obs)
 if err != nil { t.Fatalf("new evidence rejected: %v", err) }
 followUp, err := NextTournamentProbe(f, pin, after)
 if err != nil || followUp.CandidateID != "second" || followUp.StepsCompleted != 1 {
  t.Fatalf("legitimate fresh evidence failed: %v %+v", err, followUp)
 }
}

func TestTournamentSubBasisPointPosteriorRevivesAfterLaterEvidence(t *testing.T) {
    f := tournamentFixture()
    // The first unlikely observation reduces H0 below one basis point,
    // but does not make it mathematically impossible.
    f.Hypotheses[0].PriorBP = 1
    f.Hypotheses[1].PriorBP = 4999
    f.Hypotheses[2].PriorBP = 5000
    f.Candidates[0].OutcomeGivenHypothesis = [][4]uint16{
        {1000,9000,0,0}, {9000,1000,0,0}, {9000,1000,0,0},
    }
    f.Candidates[1].OutcomeGivenHypothesis = [][4]uint16{
        {10000,0,0,0}, {1,9999,0,0}, {1,0,9999,0},
    }
    // Cheap diagnostic first, then expensive discriminator; both
    // candidates are valid under the exact same frozen budget.
    f.Candidates[1].ComputeUnits = 10000
    f.ComputeBudget = 10001
    f.MinInformationMicrobits = 1
    pin := Digest(f)
    state, err := NewTournament(f, pin)
    if err != nil { t.Fatal(err) }
    first, err := NextTournamentProbe(f, pin, state)
    if err != nil || first.CandidateID != "first" {
        t.Fatalf("unexpected first experiment: %v %+v", err, first)
    }
    firstOutcome := TournamentObservation{
        CandidateID:first.CandidateID, SourceSHA:first.SourceSHA,
        MechanismSHA256:first.MechanismSHA256, Outcome:0,
        EvidenceSHA256:tournamentHex("8",64),
    }
    one, err := RecordTournamentOutcome(f, pin, state, firstOutcome)
    if err != nil { t.Fatal(err) }
    second, err := NextTournamentProbe(f, pin, one)
    if err != nil || second.CandidateID != "second" || second.PosteriorBP[0] != 0 {
        t.Fatalf("expected rounded-out H0 and eligible second probe: %v %+v", err, second)
    }
    // A legacy rounded-first multiplication would permanently make H0 zero.
    lossy, err := tournamentPosterior(second.PosteriorBP, []uint16{10000,1,1})
    if err != nil || lossy[0] != 0 {
        t.Fatalf("control unexpectedly recovered rounded-out mass: %v %v", err, lossy)
    }
    secondOutcome := TournamentObservation{
        CandidateID:second.CandidateID, SourceSHA:second.SourceSHA,
        MechanismSHA256:second.MechanismSHA256, Outcome:0,
        EvidenceSHA256:tournamentHex("9",64),
    }
    two, err := RecordTournamentOutcome(f, pin, one, secondOutcome)
    if err != nil { t.Fatal(err) }
    recovered, err := NextTournamentProbe(f, pin, two)
    if err != nil || !recovered.Exhausted || recovered.StepsCompleted != 2 ||
       recovered.PosteriorBP[0] < 900 || recovered.PosteriorBP[0] > 1100 {
        t.Fatalf("exact posterior could not recover H0: %v %+v", err, recovered)
    }
    cold, err := NextTournamentProbe(f, pin, two)
    if err != nil || !reflect.DeepEqual(cold, recovered) {
        t.Fatal("cold exact-mass replay inconsistent")
    }
    if recovered.DispatchAuthorized || !recovered.ForecastOnly ||
       two.ScientificAccepted || two.ScientificFirstUseAuthorized {
        t.Fatal("advisory mass recovery changed authority")
    }
}

func TestTournamentExactMassZeroLikelihoodAndNonmutation(t *testing.T) {
    seed := tournamentExactMass([]uint16{1,9999})
    first, err := tournamentExactUpdate(seed, []uint16{1000,9000})
    if err != nil { t.Fatal(err) }
    if seed[0].Int64() != 1 || seed[1].Int64() != 9999 {
        t.Fatal("exact mass update mutated prior")
    }
    // Even many cumulative unlikely outcomes may not overflow int64,
    // because exact weights use bounded big.Int products.
    state := first
    for i:=0; i<8; i++ {
        state,err=tournamentExactUpdate(state, []uint16{10000,1})
        if err != nil { t.Fatal(err) }
    }
    rounded,err:=tournamentRoundExact(state)
    if err!=nil || int(rounded[0])+int(rounded[1])!=10000 {
        t.Fatalf("invalid normalized mass %v %v",err,rounded)
    }
    if _,err=tournamentExactUpdate(seed,[]uint16{0,0});err==nil {
        t.Fatal("impossible outcome accepted")
    }
    if _,err=tournamentRoundExact([]*big.Int{big.NewInt(0),big.NewInt(0)});err==nil {
        t.Fatal("zero mass state accepted")
    }
}

func TestTournamentUnroundedSelectionRetainsRareLiveHypothesis(t *testing.T) {
    f := tournamentFixture()
    f.Hypotheses = append([]Hypothesis(nil), f.Hypotheses[:2]...)
    f.Hypotheses[0].PriorBP = 1
    f.Hypotheses[1].PriorBP = 9999
    // The cheap first result makes H0 ~0.111 basis points, below
    // display resolution. The second source discriminates H0 sharply.
    f.Candidates[0].OutcomeGivenHypothesis = [][4]uint16{
        {1000,9000,0,0}, {9000,1000,0,0},
    }
    f.Candidates[1].OutcomeGivenHypothesis = [][4]uint16{
        {10000,0,0,0}, {1,9999,0,0},
    }
    f.Candidates[1].ComputeUnits = 10000
    f.ComputeBudget = 10001
    f.MinInformationMicrobits = 1
    pin := Digest(f)
    state, err := NewTournament(f, pin)
    if err != nil { t.Fatal(err) }
    first, err := NextTournamentProbe(f, pin, state)
    if err != nil || first.Exhausted || first.CandidateID != "first" {
        t.Fatalf("expected cheap first discriminating probe: %v %+v", err, first)
    }
    one, err := RecordTournamentOutcome(f, pin, state, TournamentObservation{
        CandidateID:first.CandidateID, SourceSHA:first.SourceSHA,
        MechanismSHA256:first.MechanismSHA256, Outcome:0,
        EvidenceSHA256:tournamentHex("8",64),
    })
    if err != nil { t.Fatal(err) }
    probe, err := NextTournamentProbe(f, pin, one)
    if err != nil || probe.Exhausted || probe.CandidateID != "second" ||
       probe.PosteriorBP[0] != 0 || probe.ProjectedInformationMicrobits < 100 {
        t.Fatalf("unrounded rare-hypothesis information was discarded: %v %+v",err,probe)
    }
    // Old 10,000-basis-point-only ranking incorrectly considered the
    // second candidate noninformative and stopped after step one.
    lossy := measureWithPrior(f, f.Candidates[1], []float64{0,1})
    if lossy.ExpectedInformationMicrobits != 0 {
        t.Fatalf("rounded-control unexpectedly has information: %+v",lossy)
    }
    cold, err := NextTournamentProbe(f, pin, one)
    if err != nil || !reflect.DeepEqual(probe,cold) {
        t.Fatal("cold replay with exact scoring differed")
    }
    if probe.DispatchAuthorized || !probe.ForecastOnly ||
       one.DispatchAuthorized || one.ScientificAccepted ||
       one.ScientificFirstUseAuthorized || one.AcceptedRefMutation {
        t.Fatal("exact ranking granted experimental authority")
    }
}

func TestTournamentExactScoringPreservesFrozenRecommendScores(t *testing.T) {
    f:=tournamentFixture()
    prior:=make([]float64,len(f.Hypotheses))
    for i,h:=range f.Hypotheses {prior[i]=float64(h.PriorBP)/10000}
    for _,c:=range f.Candidates {
        if got,want:=measureWithPrior(f,c,prior),measure(f,c);!reflect.DeepEqual(got,want) {
            t.Fatalf("existing frozen-score path changed: got %+v want %+v",got,want)
        }
    }
}
