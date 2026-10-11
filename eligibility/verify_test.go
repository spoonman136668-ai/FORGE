package eligibility

import (
 "errors"
 "strings"
 "testing"
)
func fixture()(Frozen,Witness){
 h:=func(n int)string{return strings.Repeat("a",n)}
 p:=Frozen{Schema:Schema,Lane:"Wingless",CandidateID:"candidate_01",SourceSHA:h(40),
  PreregSHA256:h(64),CohortSHA256:strings.Repeat("b",64),ProtocolSHA256:strings.Repeat("c",64),
  BudgetUnits:5,SeedIDs:[]string{"Wingless:seed_01"}}
 w:=Witness{Lane:p.Lane,SourceSHA:p.SourceSHA,PreregSHA256:p.PreregSHA256,
  CohortSHA256:p.CohortSHA256,ProtocolSHA256:p.ProtocolSHA256,
  LedgerAuthenticated:true,StartReconciled:true,ConsumedCohorts:map[string]bool{}}
 fp,err:=Fingerprint(p);if err!=nil{panic(err)};w.FrozenSHA256=fp
 return p,w
}
func TestMatchingSourceOnly(t *testing.T){
 p,w:=fixture()
 if err:=Check(p,w);err!=nil{t.Fatal(err)}
 a,err:=Fingerprint(p);if err!=nil{t.Fatal(err)}
 b,err:=Fingerprint(p);if err!=nil||a!=b{t.Fatal("non-deterministic frozen fingerprint")}
}
func TestFailClosed(t *testing.T){
 cases:=[]struct{name string;change func(*Frozen,*Witness)}{
  {"unverified ledger",func(_ *Frozen,w *Witness){w.LedgerAuthenticated=false}},
  {"nil consumed ledger",func(_ *Frozen,w *Witness){w.ConsumedCohorts=nil}},
  {"reused cohort",func(p *Frozen,w *Witness){w.ConsumedCohorts[p.CohortSHA256]=true}},
  {"uncertain start",func(_ *Frozen,w *Witness){w.StartReconciled=false}},
  {"cross lane",func(_ *Frozen,w *Witness){w.Lane="Yggdrasil"}},
  {"mismatched source",func(_ *Frozen,w *Witness){w.SourceSHA=strings.Repeat("d",40)}},
  {"mismatched preregistration",func(_ *Frozen,w *Witness){w.PreregSHA256=strings.Repeat("d",64)}},
  {"mismatched cohort",func(_ *Frozen,w *Witness){w.CohortSHA256=strings.Repeat("d",64)}},
  {"mismatched protocol",func(_ *Frozen,w *Witness){w.ProtocolSHA256=strings.Repeat("d",64)}},
  {"duplicate seed",func(p *Frozen,_ *Witness){p.SeedIDs=append(p.SeedIDs,"Wingless:seed_01")}},
  {"wrong lane seed",func(p *Frozen,_ *Witness){p.SeedIDs=[]string{"Yggdrasil:seed_01"}}},
  {"altered candidate",func(p *Frozen,_ *Witness){p.CandidateID="candidate_02"}},
  {"altered budget",func(p *Frozen,_ *Witness){p.BudgetUnits=6}},
  {"altered seeds",func(p *Frozen,_ *Witness){p.SeedIDs=[]string{"Wingless:seed_02"}}},
  {"missing independent fingerprint",func(_ *Frozen,w *Witness){w.FrozenSHA256=""}},
  {"noncanonical digest",func(p *Frozen,_ *Witness){p.SourceSHA=strings.Repeat("A",40)}},
  {"zero budget",func(p *Frozen,_ *Witness){p.BudgetUnits=0}},
  {"wrong schema",func(p *Frozen,_ *Witness){p.Schema="other"}},
 }
 for _,tc:=range cases{
  t.Run(tc.name,func(t *testing.T){p,w:=fixture();tc.change(&p,&w)
   if err:=Check(p,w);!errors.Is(err,ErrBlocked){t.Fatalf("must block: %v",err)}
  })
 }
}
