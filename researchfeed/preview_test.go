package researchfeed

import (
 "encoding/json"
 "strings"
 "testing"
)

func sixLanes() []Candidate {
 return []Candidate{
  {Lane:"Wingless",ResearchID:"W-01",SourceRepo:"spoonman136668-ai/Wingless",SourceCommit:strings.Repeat("a",40),SourcePath:"research/w01/evidence.json",Outcome:"NEGATIVE",EvidenceState:"SOURCE_POINTER_ONLY"},
  {Lane:"Yggdrasil",ResearchID:"Y-01",SourceRepo:"spoonman136668-ai/Yggdrasil",SourceCommit:strings.Repeat("b",40),SourcePath:"research/y01/evidence.json",Outcome:"MIXED",EvidenceState:"SOURCE_POINTER_ONLY"},
  {Lane:"BIO",ResearchID:"BIO-72",SourceRepo:"spoonman136668-ai/Mind-Palace",SourceCommit:strings.Repeat("c",40),SourcePath:"archive/research/bio/2026-10-23/bio72/BIO72_RESULT.md",Outcome:"NEGATIVE",EvidenceState:"ORIGINAL_BYTES_CUSTODY_UNRESOLVED"},
  {Lane:"Optimizer Work",ResearchID:"Q21",SourceRepo:"spoonman136668-ai/FORGE",SourceCommit:strings.Repeat("d",40),SourcePath:"research/q21/outcome.json",Outcome:"INCONCLUSIVE",EvidenceState:"SOURCE_POINTER_ONLY"},
  {Lane:"Mass Research",ResearchID:"MR-01",SourceRepo:"spoonman136668-ai/Mind-Palace",SourceCommit:strings.Repeat("e",40),SourcePath:"archive/research/mass/mr01.json",Outcome:"INVALID",EvidenceState:"SOURCE_POINTER_ONLY"},
  {Lane:"Language Research",ResearchID:"ELG-01",SourceRepo:"spoonman136668-ai/FORGE",SourceCommit:strings.Repeat("f",40),SourcePath:"research/language/elg01.json",Outcome:"POSITIVE",EvidenceState:"REPORTED_BYTES_UNAUTHENTICATED",ReportedSHA256:strings.Repeat("1",64)},
 }
}
func encode(c []Candidate)[]byte{b,e:=json.Marshal(Input{Schema:Schema,Candidates:c});if e!=nil{panic(e)};return b}
func expectBlocked(t *testing.T,c []Candidate){t.Helper();if _,e:=PreviewCandidates(encode(c));e==nil{t.Fatal("unsafe source accepted")}}
func TestSixLanesPreserveAllOutcomesNoAuthority(t *testing.T){
 raw:=encode(sixLanes());p,e:=PreviewCandidates(raw);if e!=nil{t.Fatal(e)}
 if len(p.Entries)!=6||!p.AdvisoryOnly||p.ScientificAccepted||p.ScientificFirstUseCleared||p.ExecutionAuthorized||p.OriginalBytesAuthenticated||len(p.InputSHA256)!=64{t.Fatalf("false authorization: %#v",p)}
 outcomes:=map[string]string{}
 for _,x:=range p.Entries{outcomes[x.Lane]=x.Outcome}
 if outcomes["BIO"]!="NEGATIVE"||outcomes["Yggdrasil"]!="MIXED"||outcomes["Mass Research"]!="INVALID"||outcomes["Language Research"]!="POSITIVE"{t.Fatalf("lost scientific negatives/mixed/invalid: %#v",outcomes)}
}
func TestDeterministicSortedOutput(t *testing.T){
 c:=sixLanes();p,e:=PreviewCandidates(encode(c));if e!=nil{t.Fatal(e)}
 for i:=1;i<len(p.Entries);i++{if p.Entries[i-1].Lane>p.Entries[i].Lane{t.Fatal("not sorted")}}
 p2,e:=PreviewCandidates(encode(c));if e!=nil||p.InputSHA256!=p2.InputSHA256{t.Fatal("nondeterministic")}
}
func TestFirstUseClaimBlocked(t *testing.T){c:=sixLanes();c[0].FirstUseCleared=true;expectBlocked(t,c)}
func TestScientificAcceptanceClaimBlocked(t *testing.T){c:=sixLanes();c[0].ScientificAccepted=true;expectBlocked(t,c)}
func TestExecutionClaimBlocked(t *testing.T){c:=sixLanes();c[0].ExecuteRequested=true;expectBlocked(t,c)}
func TestUnapprovedSourceForbidden(t *testing.T){c:=sixLanes();c[0].SourceRepo="spoonman136668-ai/not-an-approved-research-source";expectBlocked(t,c)}
func TestWrongLaneRepositoryForbidden(t *testing.T){c:=sixLanes();c[2].SourceRepo="spoonman136668-ai/Wingless";expectBlocked(t,c)}
func TestPathTraversalForbidden(t *testing.T){c:=sixLanes();c[2].SourcePath="archive/research/../../secrets";expectBlocked(t,c)}
func TestForbiddenPrivatePath(t *testing.T){c:=sixLanes();c[2].SourcePath=".ice/records.json";expectBlocked(t,c)}
func TestInvalidPinBlocked(t *testing.T){c:=sixLanes();c[0].SourceCommit="main";expectBlocked(t,c)}
func TestMissingReportedDigestBlocked(t *testing.T){c:=sixLanes();c[5].ReportedSHA256="";expectBlocked(t,c)}
func TestAdvisoryDoesNotAuthenticateAnyDigest(t *testing.T){p,e:=PreviewCandidates(encode(sixLanes()));if e!=nil||p.OriginalBytesAuthenticated{t.Fatal("reported hash was falsely authenticated")}}
func TestDuplicateResearchIDBlocked(t *testing.T){c:=sixLanes();c=append(c,c[0]);expectBlocked(t,c)}
func TestUnknownLaneBlocked(t *testing.T){c:=sixLanes();c[0].Lane="CKB-plane";expectBlocked(t,c)}
func TestOutcomeCannotBeSilentlyReclassified(t *testing.T){c:=sixLanes();c[2].Outcome="ACCEPTED";expectBlocked(t,c)}
func TestUnknownJSONFieldBlocked(t *testing.T){
 raw:=encode(sixLanes());raw=append(raw[:len(raw)-1],[]byte(`,"controller":"restart"}`)...)
 if _,e:=PreviewCandidates(raw);e==nil{t.Fatal("unknown input control admitted")}
}
func TestDuplicateJSONAuthorityKeyBlocked(t *testing.T){
 raw:=encode(sixLanes())
 s:=strings.Replace(string(raw),`"scientific_accepted":false`,`"scientific_accepted":false,"scientific_accepted":true`,1)
 if _,e:=PreviewCandidates([]byte(s));e==nil{t.Fatal("duplicate authority admitted")}
}
func TestCaseAmbiguousJSONBlocked(t *testing.T){
 raw:=encode(sixLanes())
 s:=strings.Replace(string(raw),`"first_use_cleared":false`,`"first_use_cleared":false,"First_Use_Cleared":true`,1)
 if _,e:=PreviewCandidates([]byte(s));e==nil{t.Fatal("case-ambiguous authority admitted")}
}
func TestTrailingJSONBlocked(t *testing.T){raw:=append(encode(sixLanes()),[]byte(" {}")...);if _,e:=PreviewCandidates(raw);e==nil{t.Fatal("trailing document admitted")}}
func TestOversizedPayloadBlocked(t *testing.T){if _,e:=PreviewCandidates([]byte(strings.Repeat("x",MaxBytes+1)));e==nil{t.Fatal("unbounded payload accepted")}}
func TestUnverifiedShaMalformedBlocked(t *testing.T){c:=sixLanes();c[5].ReportedSHA256=strings.Repeat("G",64);expectBlocked(t,c)}
