package autonomychain
import ("errors";"fmt";"strings";"testing")
func one(lane,id,run string,n int,successor string)Original{
 sha:=func(n int)string{return fmt.Sprintf("%064x",n)}
 return Original{Lane:lane,ExperimentID:id,OriginalRunID:run,
  SourceCommitSHA:strings.Repeat("a",40),FrozenPlanSHA256:sha(256),
  StartReceiptSHA256:sha(n*3+1),
  TerminalReceiptSHA256:sha(n*3+2),
  IndependentReviewSHA256:sha(n*3+3),
  SuccessorExperimentID:successor,Classification:"NEGATIVE"}
}
func fixture()Candidate{
 return Candidate{Schema:Schema,
 Wingless:[]Original{one("Wingless","W1","w-run-1",0,"W2"),one("Wingless","W2","w-run-2",1,"W3")},
 Yggdrasil:[]Original{one("Yggdrasil","Y1","y-run-1",2,"Y2"),one("Yggdrasil","Y2","y-run-2",3,"Y3")}}
}
func TestCandidateIsNeverAuthority(t *testing.T){
 r,err:=Audit(fixture());if err!=nil{t.Fatal(err)}
 if !r.StructuralContinuity||r.ConnectedOriginalsPerLane!=2||r.CandidateSHA256==""||
 r.AuthenticFirstUseVerified||r.IndependentScientificAcceptance||r.AutonomousDispatchAuthorized||r.OwnerCutoverAuthorized{
  t.Fatalf("non-authorizing contract violated: %+v",r)
 }
 r2,err:=Audit(fixture());if err!=nil||r!=r2{t.Fatal("non-deterministic audit")}
}
func TestFailClosedOnReplayAndMissingHandoff(t *testing.T){
 tests:=map[string]func(*Candidate){
  "train only does not establish two originals":func(c *Candidate){c.Wingless=c.Wingless[:1]},
  "broken successor chain":func(c *Candidate){c.Wingless[0].SuccessorExperimentID="wrong"},
  "duplicate consumed original":func(c *Candidate){c.Yggdrasil[1].OriginalRunID=c.Wingless[0].OriginalRunID},
  "duplicate receipt":func(c *Candidate){c.Yggdrasil[1].TerminalReceiptSHA256=c.Wingless[0].TerminalReceiptSHA256},
  "missing independent review":func(c *Candidate){c.Wingless[1].IndependentReviewSHA256=""},
  "unknown classification":func(c *Candidate){c.Wingless[1].Classification="CI_GREEN"},
  "source digest drift":func(c *Candidate){c.Wingless[0].SourceCommitSHA="deadbeef"},
  "third successor reused":func(c *Candidate){c.Yggdrasil[1].SuccessorExperimentID="W1"},
 }
 for name,mutate:=range tests{t.Run(name,func(t *testing.T){
  c:=fixture();mutate(&c);if _,err:=Audit(c);!errors.Is(err,ErrBlocked){t.Fatalf("accepted bad evidence: %v",err)}
 })}
}
