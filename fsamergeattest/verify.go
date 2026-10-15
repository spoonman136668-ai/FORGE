// Package fsamergeattest checks immutable GitHub source-review evidence.
// It performs no I/O and never authorizes merging or scientific execution.
package fsamergeattest

import (
 "regexp"
 "strings"
)

const (
 ReviewBot = "chatgpt-codex-connector[bot]"
 qualificationWorkflow = "FORGE public Linux and Windows qualification"
)
var fullOID=regexp.MustCompile("^[0-9a-f]{40}$")
var fsaBranch=regexp.MustCompile("^proposal/fsa[a-zA-Z0-9/_-]*$")
var priorityFinding=regexp.MustCompile(`\[P[012](?:\]|\s|:)`)

type PR struct {
 Number int
 Author, HeadRepo, BaseRef, SourceBranch, HeadSHA string
 Draft bool
}
type File struct { Path, Status string }
type WorkflowRun struct {
 Name, HeadSHA, Status, Conclusion string
 Jobs map[string]string
}
type Review struct { Reviewer, CommitID, State string }
type InlineComment struct { Author, CommitID, Body string }
type Thread struct { Resolved, AllAuthorsTrusted, Complete bool }
type Completeness struct {
 PullRequest, Files, WorkflowRuns, Reviews, InlineComments, Threads bool
}
type Snapshot struct {
 Repository string
 PR PR
 Files []File
 Runs []WorkflowRun
 Reviews []Review
 InlineComments []InlineComment
 Threads []Thread
 Pages Completeness
}
type Result struct {
 HeadSHA string
 SourceQualified, MergeAuthorized bool
 Reason string
}
func deny(s Snapshot, reason string) Result {
 return Result{HeadSHA:s.PR.HeadSHA, Reason:reason}
}

// Check is non-authorizing and assumes all source arrays were independently
// fetched and fully paginated from GitHub REST/GraphQL. No issue-comment
// summary or abbreviated OID can substitute for a native GitHub PR review.
func Check(s Snapshot) Result {
 p:=s.PR
 if !(s.Pages.PullRequest && s.Pages.Files && s.Pages.WorkflowRuns &&
       s.Pages.Reviews && s.Pages.InlineComments && s.Pages.Threads) {
  return deny(s,"INCOMPLETE_GITHUB_EVIDENCE")
 }
 if !fullOID.MatchString(p.HeadSHA) || s.Repository=="" || p.Number<=0 ||
    p.Author!="spoonman136668-ai" || p.HeadRepo!=s.Repository ||
    p.BaseRef!="main" || p.Draft || !fsaBranch.MatchString(p.SourceBranch) {
  return deny(s,"SOURCE_IDENTITY_NOT_ELIGIBLE")
 }
 if len(s.Files)==0 || len(s.Files)>8 || len(s.Files)>=100 ||
    len(s.Runs)>=100 || len(s.Reviews)>=100 ||
    len(s.InlineComments)>=100 || len(s.Threads)>=100 {
  return deny(s,"UNBOUNDED_GITHUB_EVIDENCE")
 }
 for _,f:=range s.Files {
  allowed:=((strings.HasPrefix(f.Path,"eligibility/") ||
    strings.HasPrefix(f.Path,"startrecovery/")) && strings.HasSuffix(f.Path,".go")) ||
    (strings.HasPrefix(f.Path,"docs/FSA-") && strings.HasSuffix(f.Path,".md"))
  if !allowed || strings.Contains(f.Path,"..") ||
    (f.Status!="added" && f.Status!="modified") {
   return deny(s,"UNAUTHORIZED_SOURCE_SCOPE")
  }
 }
 linuxWindows,fsa:=false,false
 for _,r:=range s.Runs {
  if r.HeadSHA!=p.HeadSHA || r.Status!="completed" || r.Conclusion!="success" {continue}
  if r.Name==qualificationWorkflow && r.Jobs["linux"]=="success" &&
       r.Jobs["windows"]=="success" {linuxWindows=true}
  if strings.HasPrefix(r.Name,"FORGE FSA-") &&
      strings.Contains(r.Name,"qualification") && len(r.Jobs)>0 {
   passed:=true
   for _,j:=range r.Jobs {if j!="success" {passed=false}}
   if passed {fsa=true}
  }
 }
 if !linuxWindows || !fsa {return deny(s,"EXACT_HEAD_REGRESSION_INCOMPLETE")}
 approved:=false
 for _,r:=range s.Reviews {
  if r.State=="CHANGES_REQUESTED" {return deny(s,"REVIEW_CHANGES_REQUESTED")}
  if r.Reviewer==ReviewBot && r.State=="APPROVED" &&
     r.CommitID==p.HeadSHA && fullOID.MatchString(r.CommitID) {approved=true}
 }
 if !approved {return deny(s,"FULL_OID_INDEPENDENT_REVIEW_MISSING")}
 for _,c:=range s.InlineComments {
  if c.Author==ReviewBot && c.CommitID==p.HeadSHA && priorityFinding.MatchString(c.Body) {
   return deny(s,"UNRESOLVED_PRIORITY_FINDING")
  }
 }
 for _,t:=range s.Threads {
  if !t.Complete || !t.Resolved {return deny(s,"UNRESOLVED_OR_INCOMPLETE_THREAD")}
  if !t.AllAuthorsTrusted {return deny(s,"THREAD_AUTHOR_UNTRUSTED")}
 }
 return Result{HeadSHA:p.HeadSHA, SourceQualified:true,
  MergeAuthorized:false, Reason:"SOURCE_REVIEW_QUALIFIED_NO_MERGE_AUTHORITY"}
}
