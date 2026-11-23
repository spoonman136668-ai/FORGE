package evoportfolio

// R8 implements a pure, NONEXECUTING, Shinka-inspired island/Pareto replay
// of the SAME already-frozen R1-R7 historical portfolio. It is a bounded
// FORGE-native translation of the isolated CKB PR #296 algorithmic ideas;
// it does not call ShinkaEvolve, create mutations, use sealed data or run science.
import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "sort"
)

const ParetoFreezeSchema="forge.evoportfolio.island-pareto-freeze.v1"
const ParetoResultSchema="forge.evoportfolio.island-pareto-advisory.v1"

type IslandLineage struct{
 CandidateID string `json:"candidate_id"`
 Family string `json:"family"`
 IslandID string `json:"island_id"`
 SourceSHA string `json:"source_sha"`
 ScreenSHA string `json:"screen_sha"`
 HistoricalClass string `json:"historical_class"`
 OperatorSHA256 string `json:"operator_sha256"`
 ParentSHAs []string `json:"parent_shas"`
}
type ParetoFreeze struct{
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 PortfolioSHA256 string `json:"portfolio_sha256"`
 LineageSHA256 string `json:"lineage_sha256"`
 BaselineID string `json:"baseline_id"`
 Islands []string `json:"islands"`
 MaxFinalists int `json:"max_finalists"`
 MaxIslandFinalists int `json:"max_island_finalists"`
 FixedBeforeScreening bool `json:"fixed_before_screening"`
 HistoricalOnly bool `json:"historical_only"`
 MutationRuntimeEnabled bool `json:"mutation_runtime_enabled"`
 SealedOutcomeAccess bool `json:"sealed_outcome_access"`
 PermissionMutation bool `json:"permission_mutation"`
 BudgetExpansion bool `json:"budget_expansion"`
}
type IslandArchived struct{
 Lineage IslandLineage `json:"lineage"`
 HistoricalScore int64 `json:"historical_score"`
 EstimatedSealedCompute int64 `json:"estimated_sealed_compute"`
 Selected bool `json:"selected"`
}
type IslandParetoResult struct{
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 FrozenPolicySHA256 string `json:"frozen_policy_sha256"`
 PortfolioSHA256 string `json:"portfolio_sha256"`
 LineageSHA256 string `json:"lineage_sha256"`
 BaselineID string `json:"baseline_id"`
 OriginalFinalists []string `json:"original_finalists"`
 ParetoFinalists []string `json:"pareto_finalists"`
 OriginalHistoricalScore int64 `json:"original_historical_score"`
 ParetoHistoricalScore int64 `json:"pareto_historical_score"`
 ReservedSealedCompute int64 `json:"reserved_sealed_compute"`
 NegativeCount int `json:"negative_count"`
 MixedCount int `json:"mixed_count"`
 Archive []IslandArchived `json:"archive"`
 HistoricalOnly bool `json:"historical_only"`
 ImprovementScientificallyEstablished bool `json:"improvement_scientifically_established"`
 MutationRuntimeActivated bool `json:"mutation_runtime_activated"`
 ScientificAccepted bool `json:"scientific_accepted"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 AcceptedRefMutation bool `json:"accepted_ref_mutation"`
}
func DigestIslandLineage(rows []IslandLineage)string{
 cloned:=append([]IslandLineage(nil),rows...)
 sort.Slice(cloned,func(i,j int)bool{return cloned[i].CandidateID<cloned[j].CandidateID})
 raw,_:=json.Marshal(cloned)
 sum:=sha256.Sum256(append([]byte("FORGE-ISLAND-LINEAGE-V1\n"),raw...))
 return hex.EncodeToString(sum[:])
}
func DigestParetoFreeze(p ParetoFreeze)string{
 raw,_:=json.Marshal(p)
 sum:=sha256.Sum256(append([]byte("FORGE-FROZEN-ISLAND-PARETO-V1\n"),raw...))
 return hex.EncodeToString(sum[:])
}
// ParetoAdvisory preserves every negative and nonfinalist, and uses exactly
// the same frozen historical screens and sealed-compute budget as the
// incumbent Select() policy. Pins MUST be supplied from independent custody.
func ParetoAdvisory(f Frozen,portfolioPin string,p ParetoFreeze,policyPin string,
 lineage []IslandLineage)(IslandParetoResult,error){
 var zero IslandParetoResult
 incumbent,err:=Select(f,portfolioPin)
 if err!=nil||p.Schema!=ParetoFreezeSchema||p.Lane!=f.Lane||
  p.PortfolioSHA256!=portfolioPin||p.LineageSHA256!=DigestIslandLineage(lineage)||
  !isHex(policyPin,64)||DigestParetoFreeze(p)!=policyPin||
  len(p.Islands)==0||len(p.Islands)>6||p.MaxFinalists<1||
  p.MaxFinalists>f.MaxFinalists||p.MaxIslandFinalists<1||
  p.MaxIslandFinalists>p.MaxFinalists||
  !p.FixedBeforeScreening||!p.HistoricalOnly||
  p.MutationRuntimeEnabled||p.SealedOutcomeAccess||
  p.PermissionMutation||p.BudgetExpansion||
  len(lineage)!=len(f.Candidates){
  return zero,ErrFrozen
 }
 islands:=map[string]bool{}
 for _,id:=range p.Islands{
  if !validID(id)||islands[id]{return zero,ErrFrozen}
  islands[id]=true
 }
 byID:=map[string]Candidate{}
 for _,c:=range f.Candidates{byID[c.ID]=c}
 baseline,ok:=byID[p.BaselineID]
 if !ok||baseline.HistoricalClass=="NEGATIVE"||
  baseline.HistoricalClass=="INVALID"||
  baseline.HistoricalClass=="CONSUMED_INDETERMINATE"{return zero,ErrFrozen}
 byIsland:=map[string][]Candidate{}
 archive:=make([]IslandArchived,0,len(lineage))
 seen:=map[string]bool{}
 islandFor:=map[string]string{}
 for _,line:=range lineage{
  candidate,ok:=byID[line.CandidateID]
  if !ok||seen[line.CandidateID]||!islands[line.IslandID]||
   line.Family!=candidate.Family||line.SourceSHA!=candidate.SourceSHA||
   line.ScreenSHA!=candidate.ScreenSHA||line.HistoricalClass!=candidate.HistoricalClass||
   !isHex(line.OperatorSHA256,64)||len(line.ParentSHAs)>4{return zero,ErrFrozen}
  parents:=map[string]bool{}
  for _,parent:=range line.ParentSHAs{
   if !isHex(parent,40)||parent==candidate.SourceSHA||parents[parent]{return zero,ErrFrozen}
   parents[parent]=true
  }
  seen[line.CandidateID]=true
  islandFor[line.CandidateID]=line.IslandID
  archive=append(archive,IslandArchived{Lineage:line,
   HistoricalScore:candidate.Score,EstimatedSealedCompute:candidate.SealedCompute})
 }
 if len(seen)!=len(byID){return zero,ErrFrozen}
 // Construct historical Pareto fronts within each frozen island. Negatives,
 // invalids and consumed indeterminates are retained but cannot dominate.
 eligible:=func(c Candidate)bool{
  return c.HistoricalClass!="NEGATIVE"&&c.HistoricalClass!="INVALID"&&
   c.HistoricalClass!="CONSUMED_INDETERMINATE"
 }
 for _,c:=range f.Candidates{
  if !eligible(c)||c.Score<baseline.Score{continue}
  dominated:=false
  for _,peer:=range f.Candidates{
   if peer.ID==c.ID||islandFor[peer.ID]!=islandFor[c.ID]||!eligible(peer){continue}
   if peer.Score>=c.Score&&peer.SealedCompute<=c.SealedCompute&&
    (peer.Score>c.Score||peer.SealedCompute<c.SealedCompute){dominated=true;break}
  }
  if !dominated{byIsland[islandFor[c.ID]]=append(byIsland[islandFor[c.ID]],c)}
 }
 for island:=range byIsland{
  list:=byIsland[island]
  sort.Slice(list,func(i,j int)bool{
   if list[i].Score!=list[j].Score{return list[i].Score>list[j].Score}
   if list[i].SealedCompute!=list[j].SealedCompute{return list[i].SealedCompute<list[j].SealedCompute}
   return list[i].ID<list[j].ID
  })
  byIsland[island]=list
 }
 order:=append([]string(nil),p.Islands...)
 sort.Strings(order)
 picked:=map[string]bool{}
 familyCounts:=map[string]int{}
 islandCounts:=map[string]int{}
 signatureUsed:=map[string]bool{}
 var reserved,score int64
 chosen:=make([]string,0,p.MaxFinalists)
 for len(chosen)<p.MaxFinalists{
  progressed:=false
  for _,island:=range order{
   if len(chosen)>=p.MaxFinalists{break}
   if islandCounts[island]>=p.MaxIslandFinalists{continue}
   for _,c:=range byIsland[island]{
    if picked[c.ID]||familyCounts[c.Family]>=f.MaxPerFamily||
     reserved>f.MaxSealedCompute-c.SealedCompute{continue}
    signature:=c.Signature
    if signature==""{signature="legacy:"+c.ID}
    if signatureUsed[signature]{continue}
    chosen=append(chosen,c.ID)
    picked[c.ID]=true
    familyCounts[c.Family]++
    islandCounts[island]++
    signatureUsed[signature]=true
    reserved+=c.SealedCompute
    score+=c.Score
    progressed=true
    break
   }
  }
  if !progressed{break}
 }
 sort.Slice(archive,func(i,j int)bool{
  return archive[i].Lineage.CandidateID<archive[j].Lineage.CandidateID})
 for i:=range archive{archive[i].Selected=picked[archive[i].Lineage.CandidateID]}
 incumbentIDs:=make([]string,0,len(incumbent.Finalists))
 var incumbentScore int64
 for _,c:=range incumbent.Finalists{
  incumbentIDs=append(incumbentIDs,c.ID)
  incumbentScore+=c.Score
 }
 return IslandParetoResult{Schema:ParetoResultSchema,Lane:f.Lane,
  FrozenPolicySHA256:policyPin,PortfolioSHA256:portfolioPin,
  LineageSHA256:p.LineageSHA256,BaselineID:p.BaselineID,
  OriginalFinalists:incumbentIDs,ParetoFinalists:chosen,
  OriginalHistoricalScore:incumbentScore,ParetoHistoricalScore:score,
  ReservedSealedCompute:reserved,NegativeCount:incumbent.NegativeCount,
  MixedCount:incumbent.MixedCount,Archive:archive,HistoricalOnly:true},nil
}
