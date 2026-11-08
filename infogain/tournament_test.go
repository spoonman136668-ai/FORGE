package infogain

import (
 "reflect"
 "strings"
 "testing"
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
