package hybridresearch

import (
 "bytes"
 "encoding/json"
 "strings"
 "testing"
)

func testCandidate(id string,pr uint64) Candidate {
 return Candidate{
  ExperimentID:id,PullRequest:pr,HeadSHA:strings.Repeat("a",40),
  ProtocolSHA256:strings.Repeat("b",64),
  PullRequestURL:"https://github.com/"+Project+"/pull/"+func()string {
   if pr==39{return "39"};return "40"
  }(),
  Stage:"PROTOCOL_DESIGN",
 }
}
func testSnapshot()[]byte {
 raw,_:=json.Marshal(Snapshot{
  Schema:SnapshotSchema,Repository:Project,
  Candidates:[]Candidate{testCandidate("G7-S25",40),testCandidate("G7-S24",39)},
 })
 return raw
}
func TestHybridSnapshotDeterministicNonAuthorizing(t *testing.T) {
 raw:=testSnapshot()
 report,err:=Inspect(raw)
 if err!=nil {t.Fatal(err)}
 if err:=VerifyOutput(report);err!=nil {t.Fatal(err)}
 if report.Schema!=ReportSchema||report.Repository!=Project||
  len(report.Candidates)!=2||report.Candidates[0].ExperimentID!="G7-S24"||
  report.Candidates[1].ExperimentID!="G7-S25"||
  report.ExecutionAuthorized||report.TrainingExecuted||
  report.OriginalFirstUseAuthenticated||report.ScientificAccepted {
  t.Fatalf("candidate metadata elevated to science or changed order: %+v",report)
 }
 again,err:=Inspect(raw)
 if err!=nil||again.SnapshotSHA256!=report.SnapshotSHA256 {t.Fatal("unstable snapshot",err)}
 for _,candidate:=range report.Candidates {
  if candidate.Classification!="UNVERIFIED_NOT_SCIENTIFIC_EVIDENCE"||
   candidate.SourceAuthenticated||candidate.OriginalFirstUseAuthenticated||
   candidate.ScientificAccepted {t.Fatal("unsafe candidate classification",candidate)}
 }
 rawOutput,err:=json.Marshal(report)
 if err!=nil||!bytes.Contains(rawOutput,[]byte(`"execution_authorized":false`)) {
  t.Fatal("report did not preserve explicit non-authorization",err)
 }
}
func TestRejectMalformedAndAmbiguousSources(t *testing.T) {
 raw:=testSnapshot()
 fixtures:=map[string][]byte{
  "empty":nil,
  "trailing":append(append([]byte{},raw...),[]byte("{}")...),
  "bad repository":bytes.Replace(raw,[]byte(Project),[]byte("foreign/Repo"),1),
  "foreign url":bytes.Replace(raw,[]byte("https://github.com/"+Project+"/pull/40"),[]byte("https://github.com/foreign/Repo/pull/40"),1),
  "uppercase SHA":bytes.Replace(raw,[]byte(strings.Repeat("a",40)),[]byte(strings.Repeat("A",40)),1),
  "wrong protocol hash":bytes.Replace(raw,[]byte(strings.Repeat("b",64)),[]byte("bad"),1),
  "unknown stage":bytes.Replace(raw,[]byte("PROTOCOL_DESIGN"),[]byte("READY_TO_EXECUTE"),1),
  "unknown authority flag":bytes.Replace(raw,[]byte(`"repository"`),[]byte(`"execution_authorized":true,"repository"`),1),
  "duplicate field":bytes.Replace(raw,[]byte(`"schema"`),[]byte(`"schema":"x","schema"`),1),
  "duplicate differently cased field":bytes.Replace(raw,[]byte(`"schema"`),[]byte(`"Schema":"x","schema"`),1),
  "duplicate candidate id":bytes.Replace(raw,[]byte("G7-S24"),[]byte("G7-S25"),1),
  "duplicate PR":bytes.Replace(raw,[]byte(`"pull_request":39`),[]byte(`"pull_request":40`),1),
  "size cap":bytes.Repeat([]byte("x"),MaximumBytes+1),
 }
 for name,fixture:=range fixtures {
  t.Run(name,func(t *testing.T){
   if _,err:=Inspect(fixture);err==nil {t.Fatal("unsafe hybrid snapshot accepted")}
  })
 }
}
func TestRejectElevationInOutput(t *testing.T) {
 out,err:=Inspect(testSnapshot())
 if err!=nil {t.Fatal(err)}
 cases:=[]struct{name string;change func(*Report)}{
  {"execution",func(x *Report){x.ExecutionAuthorized=true}},
  {"training",func(x *Report){x.TrainingExecuted=true}},
  {"first-use",func(x *Report){x.OriginalFirstUseAuthenticated=true}},
  {"science",func(x *Report){x.ScientificAccepted=true}},
  {"source",func(x *Report){x.Candidates[0].SourceAuthenticated=true}},
  {"candidate science",func(x *Report){x.Candidates[0].ScientificAccepted=true}},
  {"classification",func(x *Report){x.Candidates[0].Classification="SCIENTIFIC_PASS"}},
  {"duplicate",func(x *Report){x.Candidates[1]=x.Candidates[0]}},
 }
 for _,tc:=range cases {
  t.Run(tc.name,func(t *testing.T){
   copy:=out
   copy.Candidates=append([]Observed{},out.Candidates...)
   tc.change(&copy)
   if err:=VerifyOutput(copy);err==nil {t.Fatal("unsafe report accepted")}
  })
 }
}
