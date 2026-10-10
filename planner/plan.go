// Package planner ranks previously frozen scientific proposals without
// granting execution, qualification or scientific admission authority.
package planner

import (
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "sort"
 "strings"

 "github.com/spoonman136668-ai/forge/contracts"
)

const InputSchema = "forge.frozen-portfolio.v1"
const DecisionSchema = "forge.portfolio-decision.v1"

type Candidate struct {
 Draft contracts.CandidateDraft `json:"draft"`
 MechanismFamily string `json:"mechanism_family"`
 ParentReceiptSHA256 string `json:"parent_receipt_sha256"`
 Impact uint32 `json:"impact"`
 Novelty uint32 `json:"novelty"`
 Robustness uint32 `json:"robustness"`
 Cost uint32 `json:"cost"`
}
type FrozenPortfolio struct {
 Schema string `json:"schema"`
 AuthorityEpoch uint64 `json:"authority_epoch"`
 Observations []contracts.Observation `json:"observations"`
 ConsumedSeedIdentities []string `json:"consumed_seed_identities"`
 Candidates []Candidate `json:"candidates"`
}
type LaneDecision struct {
 Lane contracts.Lane `json:"lane"`
 Disposition string `json:"disposition"`
 CandidateID string `json:"candidate_id,omitempty"`
 ProposalSHA256 string `json:"proposal_sha256,omitempty"`
 Score int64 `json:"score,omitempty"`
 Draft *contracts.CandidateDraft `json:"draft,omitempty"`
}
type Decision struct {
 Schema string `json:"schema"`
 FrozenInputSHA256 string `json:"frozen_input_sha256"`
 AuthorityEpoch uint64 `json:"authority_epoch"`
 Lanes []LaneDecision `json:"lanes"`
 ScientificAdmitted bool `json:"scientific_admitted"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 AcceptedRefMutation bool `json:"accepted_ref_mutation"`
 ExternalSourceVerified bool `json:"external_source_verified"`
}
func digest(v any) (string,error) {
 b,e:=json.Marshal(v);if e!=nil{return "",e};h:=sha256.Sum256(b);return hex.EncodeToString(h[:]),nil
}
func lowerSHA(s string)bool {
 if len(s)!=64{return false}
 for _,c:=range s {if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func score(c Candidate)int64 {return 4*int64(c.Impact)+2*int64(c.Novelty)+int64(c.Robustness)-int64(c.Cost)}
func validTag(s string)bool{
 if s==""||len(s)>100||strings.TrimSpace(s)!=s{return false}
 for _,c:=range s{if !(c>='A'&&c<='Z'||c>='a'&&c<='z'||c>='0'&&c<='9'||c=='-'||c=='_'){return false}}
 return true
}
// FreezeSHA256 is only a structural digest. The expected hash passed to
// Build must be independently pinned by the existing CKB authority.
func FreezeSHA256(f FrozenPortfolio)(string,error){return digest(f)}
func Build(f FrozenPortfolio,pin string)(Decision,error){
 var zero Decision
 hash,e:=digest(f)
 if e!=nil{return zero,e}
 if !lowerSHA(pin)||hash!=pin{return zero,errors.New("FORGE_FROZEN_INPUT_DRIFT")}
 if f.Schema!=InputSchema||f.AuthorityEpoch==0||len(f.Observations)!=2||f.ConsumedSeedIdentities==nil||len(f.Candidates)>64{return zero,errors.New("FORGE_PORTFOLIO_SCOPE")}
 obs:=map[contracts.Lane]contracts.Observation{}
 for _,o:=range f.Observations{
  if e:=contracts.ValidateObservation(o);e!=nil{return zero,e}
  if o.AuthorityEpoch!=f.AuthorityEpoch{return zero,errors.New("FORGE_AUTHORITY_EPOCH_DRIFT")}
  if _,exists:=obs[o.Lane];exists{return zero,errors.New("FORGE_DUPLICATE_LANE")}
  obs[o.Lane]=o
 }
 if len(obs)!=2||obs[contracts.Wingless].Lane!=contracts.Wingless||obs[contracts.Yggdrasil].Lane!=contracts.Yggdrasil{return zero,errors.New("FORGE_MISSING_LANE")}
 used:=map[string]bool{}
 for _,seed:=range f.ConsumedSeedIdentities{
  if seed==""||len(seed)>128||strings.TrimSpace(seed)!=seed||(!strings.HasPrefix(seed,"Wingless:")&&!strings.HasPrefix(seed,"Yggdrasil:"))||used[seed]{return zero,errors.New("FORGE_CONSUMPTION_LEDGER_INVALID")}
  used[seed]=true
 }
 seen:=map[string]bool{}
 cohortOwner:=map[string]string{}
 for _,c:=range f.Candidates{
  if e:=contracts.ValidateCandidate(c.Draft);e!=nil{return zero,e}
  if c.Draft.Generation<=1||!validTag(c.MechanismFamily)||!lowerSHA(c.ParentReceiptSHA256)||c.Impact>100||c.Novelty>100||c.Robustness>100||c.Cost>100{return zero,errors.New("FORGE_CANDIDATE_UNFROZEN")}
  id:=string(c.Draft.Lane)+":"+c.Draft.CandidateID
  if seen[id]{return zero,errors.New("FORGE_DUPLICATE_CANDIDATE")};seen[id]=true
  if prior,exists:=cohortOwner[c.Draft.CohortSHA256];exists{return zero,fmt.Errorf("FORGE_COHORT_HASH_REUSED:%s",prior)}
  cohortOwner[c.Draft.CohortSHA256]=id
  for _,seed:=range c.Draft.SeedIdentities{
   if used[seed]{return zero,errors.New("FORGE_CONSUMED_OR_OVERLAPPING_SEED")}
   used[seed]=true
  }
 }
 result:=Decision{Schema:DecisionSchema,FrozenInputSHA256:hash,AuthorityEpoch:f.AuthorityEpoch,Lanes:make([]LaneDecision,0,2)}
 for _,lane:=range []contracts.Lane{contracts.Wingless,contracts.Yggdrasil}{
  d:=LaneDecision{Lane:lane,Disposition:"AWAITING_FROZEN_CANDIDATE"}
  switch obs[lane].LatestOutcome {
  case "UNKNOWN","INVALID","CONSUMED_INDETERMINATE":
   d.Disposition="BLOCKED_REQUIRES_CKB_RECONCILIATION"
  default:
   choices:=[]Candidate{}
   for _,c:=range f.Candidates{if c.Draft.Lane==lane{choices=append(choices,c)}}
   sort.Slice(choices,func(i,j int)bool{
    a,b:=score(choices[i]),score(choices[j])
    if a!=b{return a>b}
    if choices[i].Draft.CandidateSHA256!=choices[j].Draft.CandidateSHA256{return choices[i].Draft.CandidateSHA256<choices[j].Draft.CandidateSHA256}
    return choices[i].Draft.CandidateID<choices[j].Draft.CandidateID
   })
   if len(choices)>0{
    draft:=choices[0].Draft
    h,e:=contracts.CanonicalCandidateSHA256(draft);if e!=nil{return zero,e}
    d=LaneDecision{Lane:lane,Disposition:"QUARANTINE_ONLY_NEEDS_INDEPENDENT_REVIEW",CandidateID:draft.CandidateID,ProposalSHA256:h,Score:score(choices[0]),Draft:&draft}
   }
  }
  result.Lanes=append(result.Lanes,d)
 }
 return result,nil
}
// ReviewOnly is the full unprivileged interface round-trip. The backend
// remains responsible for idempotency and validating external authenticity.
// No operation here can dispatch a workflow or mutate an accepted reference.
func ReviewOnly(ctx context.Context,reader contracts.EvidenceReader,inbox contracts.QuarantineInbox,f FrozenPortfolio,pin string)(Decision,[]contracts.QuarantineAcknowledgment,error){
 var zero Decision
 if reader==nil||inbox==nil{return zero,nil,errors.New("FORGE_BACKEND_MISSING")}
 plan,e:=Build(f,pin);if e!=nil{return zero,nil,e}
 for _,frozen:=range f.Observations{
  live,e:=reader.ReadLatest(ctx,frozen.Lane);if e!=nil{return zero,nil,e}
  if e=contracts.ValidateObservation(live);e!=nil{return zero,nil,e}
  a,_:=digest(live);b,_:=digest(frozen)
  if a!=b{return zero,nil,errors.New("FORGE_OBSERVATION_DRIFT")}
 }
 receipts:=[]contracts.QuarantineAcknowledgment{}
 for _,d:=range plan.Lanes{
  if d.Draft==nil{continue}
  if e=ctx.Err();e!=nil{return plan,receipts,e}
  ack,e:=inbox.SubmitDraft(ctx,*d.Draft);if e!=nil{return plan,receipts,fmt.Errorf("FORGE_INBOX:%w",e)}
  if e=contracts.ValidateAcknowledgment(ack,d.ProposalSHA256);e!=nil{return plan,receipts,e}
  receipts=append(receipts,ack)
 }
 return plan,receipts,nil
}
