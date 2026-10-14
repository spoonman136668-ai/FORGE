package f4preflight

import (
 "encoding/json"
 "errors"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/eligibility"
)

func fixture()(eligibility.Frozen,eligibility.LedgerSnapshot,string){
 candidate:=eligibility.Frozen{
  Schema:eligibility.Schema,Lane:"Yggdrasil",CandidateID:TargetID,
  SourceSHA:strings.Repeat("a",40),PreregSHA256:strings.Repeat("b",64),
  CohortSHA256:strings.Repeat("c",64),ProtocolSHA256:strings.Repeat("d",64),
  BudgetUnits:4,SeedIDs:[]string{"Yggdrasil:67640","Yggdrasil:67641"},
 }
 snapshot:=eligibility.LedgerSnapshot{
  Schema:"forge.eligibility.ledger-snapshot.v1",Scope:"ALL_LANES",
  Generation:8,ConsumedCohorts:[]string{},Starts:[]eligibility.StartRecord{},
  ActiveCohorts:[]string{},
 }
 pin,err:=eligibility.LedgerFingerprint(snapshot)
 if err!=nil{panic(err)}
 return candidate,snapshot,pin
}

func proto()[]byte{
 p:=map[string]any{
  "status":ProposalStatus,
  "planned_original_id":TargetID,
  "source_requirements":map[string]any{"implementation_source_sha":"UNRESOLVED_REQUIRED_BEFORE_FREEZE"},
  "proposed_cohorts":map[string]any{
   "development_seeds":[]int{67600,67601,67602,67603,67604,67605,67606,67607},
   "sealed_candidate_seeds":[]int{67640,67641,67642,67643,67644,67645,67646,67647,67648,67649,67650,67651,67652,67653,67654,67655},
   "seed_first_use_status":"UNVERIFIED_MUST_INDEPENDENTLY_PROVE_UNUSED_BEFORE_CLAIM",
  },
 }
 raw,_:=json.Marshal(p)
 return raw
}

func TestF4ProposalIsNotAnExecutionToken(t *testing.T){
 if _,err:=LoadProtocol(proto());err!=nil{t.Fatal(err)}
 c,s,pin:=fixture()
 data,_:=json.Marshal(s)
 decision,err:=ReportCurrent(proto(),data,pin,8,true,c)
 if !errors.Is(err,ErrBlocked){t.Fatalf("must never authorize: %v",err)}
 if decision.ScientificDispatchAuthorized||decision.FrozenSourceVerified||
  decision.IndividualSeedFirstUseVerified||decision.FirstUseClaimsCreated!=0{
  t.Fatal("unsafe positive authority claim")
 }
 if !decision.LedgerSnapshotVerified{t.Fatal("expected advisory structural detection")}
}

func TestReadOnlyCLIAbsentLedgerIsBlocked(t *testing.T){
 // Even a legitimate frozen source cannot be assumed from this proposal.
 d:=ReadOnlyCLI("missing.json","","",0)
 if d.Status!="BLOCKED"||d.ScientificDispatchAuthorized{t.Fatal(d)}
}

func TestMissingOrBadLedgerPinBlocks(t *testing.T){
 c,s,pin:=fixture()
 raw,_:=json.Marshal(s)
 cases:=[]struct{
  name string;raw []byte;pin string;gen uint64;complete bool
 }{
  {"absent",nil,pin,8,true},
  {"untrusted pin",raw,"",8,true},
  {"wrong pin",raw,strings.Repeat("0",64),8,true},
  {"generation drift",raw,pin,9,true},
  {"incomplete",raw,pin,8,false},
  {"corrupt JSON",[]byte("{"),pin,8,true},
  {"oversized",make([]byte,1<<20+1),pin,8,true},
 }
 for _,tt:=range cases{
  t.Run(tt.name,func(t *testing.T){
   decision,err:=ExamineLedger(tt.raw,tt.pin,tt.gen,tt.complete,c)
   if !errors.Is(err,ErrBlocked)||decision.ScientificDispatchAuthorized{t.Fatalf("%v %+v",err,decision)}
  })
 }
}

func TestCohortCollisionAndAmbiguousStartsBlock(t *testing.T){
 c,baseline,_:=fixture()
 fingerprint,err:=eligibility.Fingerprint(c)
 if err!=nil{t.Fatal(err)}
 cases:=[]struct{name string;change func(*eligibility.LedgerSnapshot)}{
  {"consumed",func(s *eligibility.LedgerSnapshot){s.ConsumedCohorts=[]string{c.CohortSHA256}}},
  {"active",func(s *eligibility.LedgerSnapshot){s.ActiveCohorts=[]string{c.CohortSHA256}}},
  {"started",func(s *eligibility.LedgerSnapshot){s.Starts=[]eligibility.StartRecord{{FrozenSHA256:fingerprint,State:"STARTED"}}}},
  {"indeterminate",func(s *eligibility.LedgerSnapshot){s.Starts=[]eligibility.StartRecord{{FrozenSHA256:fingerprint,State:"INDETERMINATE"}}}},
  {"lane_scope",func(s *eligibility.LedgerSnapshot){s.Scope="Yggdrasil"}},
 }
 for _,tc:=range cases{
  t.Run(tc.name,func(t *testing.T){
   s:=baseline
   tc.change(&s)
   pin,e:=eligibility.LedgerFingerprint(s)
   if e!=nil{t.Fatal(e)}
   data,_:=json.Marshal(s)
   decision,err:=ExamineLedger(data,pin,8,true,c)
   if !errors.Is(err,ErrBlocked)||decision.ScientificDispatchAuthorized{t.Fatalf("accepted unsafe ledger %v %v",decision,err)}
  })
 }
}

func TestSeedAndSourceIdentityDriftBlock(t *testing.T){
 var p map[string]any
 if err:=json.Unmarshal(proto(),&p);err!=nil{t.Fatal(err)}
 cohorts:=p["proposed_cohorts"].(map[string]any)
 cohorts["sealed_candidate_seeds"]=[]int{67640,67641,67642,67643,67644,67645,67646,67647,67648,67649,67650,67651,67652,67653,67654,67600}
 b,_:=json.Marshal(p)
 if _,err:=LoadProtocol(b);!errors.Is(err,ErrBlocked){t.Fatal("overlap was accepted")}
 cohorts["sealed_candidate_seeds"]=[]int{67640,67641,67642,67643,67644,67645,67646,67647,67648,67649,67650,67651,67652,67653,67654,67655}
 p["source_requirements"].(map[string]any)["implementation_source_sha"]=strings.Repeat("a",40)
 b,_=json.Marshal(p)
 if _,err:=LoadProtocol(b);!errors.Is(err,ErrBlocked){t.Fatal("unqualified source was accepted")}
}
