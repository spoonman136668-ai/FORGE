package evoportfolio

import (
 "reflect"
 "strings"
 "testing"
)
func islandFixture()(Frozen,ParetoFreeze,[]IslandLineage){
 f:=fixture()
 members:=map[string]string{"alpha":"island_a","beta":"island_a",
  "gamma":"island_b","invalid":"island_b"}
 rows:=make([]IslandLineage,0,len(f.Candidates))
 for _,c:=range f.Candidates{
  rows=append(rows,IslandLineage{CandidateID:c.ID,Family:c.Family,
   IslandID:members[c.ID],SourceSHA:c.SourceSHA,ScreenSHA:c.ScreenSHA,
   HistoricalClass:c.HistoricalClass,OperatorSHA256:strings.Repeat("f",64),
   ParentSHAs:[]string{}})
 }
 p:=ParetoFreeze{Schema:ParetoFreezeSchema,Lane:f.Lane,
  PortfolioSHA256:Digest(f),LineageSHA256:DigestIslandLineage(rows),
  BaselineID:"gamma",Islands:[]string{"island_b","island_a"},
  MaxFinalists:2,MaxIslandFinalists:1,FixedBeforeScreening:true,
  HistoricalOnly:true}
 return f,p,rows
}
func TestR8ParetoPreservesNegativeAndComparesIdenticalFrozenBudget(t *testing.T){
 f,p,rows:=islandFixture()
 o,err:=ParetoAdvisory(f,Digest(f),p,DigestParetoFreeze(p),rows)
 if err!=nil{t.Fatal(err)}
 if o.Schema!=ParetoResultSchema||o.Lane!="Wingless"||
  !reflect.DeepEqual(o.ParetoFinalists,[]string{"alpha","gamma"})||
  len(o.Archive)!=4||o.ReservedSealedCompute!=5||
  o.NegativeCount!=1||o.MixedCount!=1||
  o.OriginalHistoricalScore!=25||o.ParetoHistoricalScore!=17||
  o.ImprovementScientificallyEstablished||o.MutationRuntimeActivated||
  o.ScientificAccepted||o.DispatchAuthorized||o.AcceptedRefMutation{
  t.Fatalf("R8 advisory budget or scientific safeguards lost: %+v",o)
 }
 retained:=map[string]IslandArchived{}
 for _,row:=range o.Archive{retained[row.Lineage.CandidateID]=row}
 if len(retained)!=4||retained["beta"].Selected||
  retained["beta"].Lineage.HistoricalClass!="NEGATIVE"||
  retained["invalid"].Selected||
  retained["invalid"].Lineage.HistoricalClass!="INVALID"{
  t.Fatalf("suppressed R8 historical negative or invalid: %+v",retained)
 }
 // A permutation of the same externally frozen source must not produce
 // a different winner, cost, archive or accepted result.
 reordered:=append([]IslandLineage(nil),rows...)
 reordered[0],reordered[3]=reordered[3],reordered[0]
 again,err:=ParetoAdvisory(f,Digest(f),p,DigestParetoFreeze(p),reordered)
 if err!=nil||!reflect.DeepEqual(o,again){t.Fatal("frozen lineage order changed selection",err)}
 // The original frozen candidate array is itself identity-pinned: unlike
 // an untrusted external mutation it may NOT be reordered silently.
 changed:=f;changed.Candidates=append([]Candidate(nil),f.Candidates...)
 changed.Candidates[0],changed.Candidates[3]=changed.Candidates[3],changed.Candidates[0]
 if _,err:=ParetoAdvisory(changed,Digest(changed),p,DigestParetoFreeze(p),rows);err==nil{
  t.Fatal("portfolio identity drift reused old Pareto policy")
 }
}
func TestR8ParetoRejectsUnfrozenMutationCapacityAndOracles(t *testing.T){
 changes:=[]struct{name string;change func(*ParetoFreeze)}{
  {"mutation runtime",func(p *ParetoFreeze){p.MutationRuntimeEnabled=true}},
  {"sealed use",func(p *ParetoFreeze){p.SealedOutcomeAccess=true}},
  {"permission change",func(p *ParetoFreeze){p.PermissionMutation=true}},
  {"budget increase",func(p *ParetoFreeze){p.BudgetExpansion=true}},
  {"not historical",func(p *ParetoFreeze){p.HistoricalOnly=false}},
  {"post screening policy",func(p *ParetoFreeze){p.FixedBeforeScreening=false}},
  {"extra finalists",func(p *ParetoFreeze){p.MaxFinalists=4}},
  {"extra per island",func(p *ParetoFreeze){p.MaxIslandFinalists=3}},
  {"foreign lane",func(p *ParetoFreeze){p.Lane="Other"}},
  {"duplicate island",func(p *ParetoFreeze){p.Islands=[]string{"island_a","island_a"}}},
  {"missing island",func(p *ParetoFreeze){p.Islands=[]string{"island_a"}}},
 }
 for _,tt:=range changes{t.Run(tt.name,func(t *testing.T){
  f,p,rows:=islandFixture();tt.change(&p)
  if _,err:=ParetoAdvisory(f,Digest(f),p,DigestParetoFreeze(p),rows);err==nil{
   t.Fatal("unfrozen, hidden or overbudget R8 policy admitted")
  }
 })}
}
func TestR8ParetoRejectsBirthLineageTamperingAndHistoryRewrite(t *testing.T){
 changes:=[]struct{name string;change func(*[]IslandLineage)}{
  {"missing negative",func(rows *[]IslandLineage){*rows=(*rows)[:3]}},
  {"orphan",func(rows *[]IslandLineage){(*rows)[0].CandidateID="unknown"}},
  {"family drift",func(rows *[]IslandLineage){(*rows)[0].Family="c"}},
  {"source drift",func(rows *[]IslandLineage){(*rows)[0].SourceSHA=strings.Repeat("0",40)}},
  {"screen receipt drift",func(rows *[]IslandLineage){(*rows)[0].ScreenSHA=strings.Repeat("0",64)}},
  {"class forged",func(rows *[]IslandLineage){(*rows)[1].HistoricalClass="SUPPORTED"}},
  {"island forged",func(rows *[]IslandLineage){(*rows)[1].IslandID="unexpected"}},
  {"operator unpinned",func(rows *[]IslandLineage){(*rows)[1].OperatorSHA256=""}},
  {"duplicate parent",func(rows *[]IslandLineage){(*rows)[0].ParentSHAs=[]string{strings.Repeat("e",40),strings.Repeat("e",40)}}},
  {"self parent",func(rows *[]IslandLineage){(*rows)[0].ParentSHAs=[]string{strings.Repeat("a",40)}}},
 }
 for _,tt:=range changes{t.Run(tt.name,func(t *testing.T){
  f,p,rows:=islandFixture()
  tt.change(&rows)
  // Even an attacker-supplied updated freeze hash cannot make invalid
  // or contradicted lineage satisfy the independent portfolio.
  p.LineageSHA256=DigestIslandLineage(rows)
  if _,err:=ParetoAdvisory(f,Digest(f),p,DigestParetoFreeze(p),rows);err==nil{
   t.Fatal("R8 accepted altered historical negative or source ancestry")
  }
 })}
}
func TestR8ParetoRejectsUnpinnedPolicyOrFrozenPortfolio(t *testing.T){
 f,p,rows:=islandFixture()
 if _,err:=ParetoAdvisory(f,Digest(f),p,strings.Repeat("0",64),rows);err==nil{
  t.Fatal("untrusted R8 policy allowed")
 }
 f.Candidates[0].Score=100
 if _,err:=ParetoAdvisory(f,Digest(f),p,DigestParetoFreeze(p),rows);err==nil{
  t.Fatal("post-freeze historical score rewrite admitted")
 }
}
