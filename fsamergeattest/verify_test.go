package fsamergeattest

import (
 "strings"
 "testing"
)
func good() Snapshot {
 oid:=strings.Repeat("a",40)
 return Snapshot{
  Repository:"spoonman136668-ai/FORGE",
  PR:PR{Number:600,Author:"spoonman136668-ai",HeadRepo:"spoonman136668-ai/FORGE",
   BaseRef:"main",SourceBranch:"proposal/fsa16-source-r1",HeadSHA:oid},
  Files:[]File{{Path:"eligibility/review.go",Status:"added"}},
  Runs:[]WorkflowRun{
   {Name:qualificationWorkflow,HeadSHA:oid,Status:"completed",Conclusion:"success",
    Jobs:map[string]string{"linux":"success","windows":"success"}},
   {Name:"FORGE FSA-17 qualification",HeadSHA:oid,Status:"completed",Conclusion:"success",
    Jobs:map[string]string{"qualify":"success"}},
  },
  Reviews:[]Review{{Reviewer:ReviewBot,CommitID:oid,State:"APPROVED"}},
  Pages:Completeness{PullRequest:true,Files:true,WorkflowRuns:true,
   Reviews:true,InlineComments:true,Threads:true},
 }
}
func TestQualifiedSourceNeverGrantsMerge(t *testing.T) {
 r:=Check(good())
 if !r.SourceQualified || r.MergeAuthorized ||
    r.Reason!="SOURCE_REVIEW_QUALIFIED_NO_MERGE_AUTHORITY" {t.Fatalf("unexpected %+v",r)}
}
func TestAllBoundariesFailClosed(t *testing.T) {
 cases:=map[string]func(*Snapshot){
  "no review":func(s *Snapshot){s.Reviews=nil},
  "abbreviated sha":func(s *Snapshot){s.Reviews[0].CommitID=s.PR.HeadSHA[:7]},
  "stale review":func(s *Snapshot){s.Reviews[0].CommitID=strings.Repeat("b",40)},
  "self review":func(s *Snapshot){s.Reviews[0].Reviewer="spoonman136668-ai"},
  "summary cannot approve":func(s *Snapshot){s.Reviews=nil},
  "changes requested":func(s *Snapshot){s.Reviews=append(s.Reviews,Review{Reviewer:"human",CommitID:s.PR.HeadSHA,State:"CHANGES_REQUESTED"})},
  "priority finding":func(s *Snapshot){s.InlineComments=[]InlineComment{{Author:ReviewBot,CommitID:s.PR.HeadSHA,Body:"[P1] crash on bad input"}}},
  "unresolved thread":func(s *Snapshot){s.Threads=[]Thread{{Resolved:false,Complete:true,AllAuthorsTrusted:true}}},
  "incomplete thread":func(s *Snapshot){s.Threads=[]Thread{{Resolved:true,Complete:false,AllAuthorsTrusted:true}}},
  "untrusted thread":func(s *Snapshot){s.Threads=[]Thread{{Resolved:true,Complete:true,AllAuthorsTrusted:false}}},
  "incomplete pages":func(s *Snapshot){s.Pages.Reviews=false},
  "wrong head":func(s *Snapshot){s.PR.HeadSHA=strings.Repeat("c",40)},
  "missing windows":func(s *Snapshot){delete(s.Runs[0].Jobs,"windows")},
  "stale workflow":func(s *Snapshot){s.Runs[0].HeadSHA=strings.Repeat("c",40)},
  "missing FSA":func(s *Snapshot){s.Runs=s.Runs[:1]},
  "unsafe path":func(s *Snapshot){s.Files[0].Path=".github/workflows/forge-automerge.yml"},
  "path traversal":func(s *Snapshot){s.Files[0].Path="eligibility/../bad.go"},
  "renamed":func(s *Snapshot){s.Files[0].Status="renamed"},
  "fork":func(s *Snapshot){s.PR.HeadRepo="other/FORGE"},
  "draft":func(s *Snapshot){s.PR.Draft=true},
  "wrong branch":func(s *Snapshot){s.PR.SourceBranch="research/optimizer-bridge"},
  "wrong base":func(s *Snapshot){s.PR.BaseRef="feature"},
  "truncated reviews":func(s *Snapshot){for i:=0;i<100;i++ {s.Reviews=append(s.Reviews,Review{})}},
 }
 for name,fn:=range cases {
  t.Run(name,func(t *testing.T){
   s:=good();fn(&s);r:=Check(s)
   if r.SourceQualified || r.MergeAuthorized || r.Reason=="" {t.Fatalf("unsafe %+v",r)}
  })
 }
}
func TestIssueSummaryCannotGrantReview(t *testing.T){
 s:=good();s.Reviews=[]Review{{Reviewer:ReviewBot,CommitID:"",State:"COMMENTED"}}
 r:=Check(s)
 if r.Reason!="FULL_OID_INDEPENDENT_REVIEW_MISSING" {t.Fatal(r)}
}
