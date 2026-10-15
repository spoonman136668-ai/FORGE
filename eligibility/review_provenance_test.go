package eligibility

import (
 "errors"
 "strings"
 "testing"
)

// TestSourceOnlyStructuralDenials guards the boundary independently of
// externally authenticated cohort custody. No experiment may be dispatched
// or admitted based on a structurally valid Frozen record.
func TestSourceOnlyStructuralDenials(t *testing.T) {
 cases:=[]struct {
  name string
  change func(*Frozen)
 }{
  {"candidate traversal",func(p *Frozen){p.CandidateID="../escape"}},
  {"candidate short",func(p *Frozen){p.CandidateID="ab"}},
  {"candidate whitespace",func(p *Frozen){p.CandidateID="candidate 02"}},
  {"cross-lane future seed",func(p *Frozen){p.SeedIDs=[]string{"Yggdrasil:seed_02"}}},
  {"duplicate second seed",func(p *Frozen){p.SeedIDs=[]string{"Wingless:seed_02","Wingless:seed_02"}}},
  {"invalid seed suffix",func(p *Frozen){p.SeedIDs=[]string{"Wingless:seed/02"}}},
  {"zero seeds",func(p *Frozen){p.SeedIDs=nil}},
  {"too many seeds",func(p *Frozen){
   for len(p.SeedIDs)<=128 {p.SeedIDs=append(p.SeedIDs,"Wingless:seed_"+strings.Repeat("a",len(p.SeedIDs)+1))}
  }},
  {"excessive budget",func(p *Frozen){p.BudgetUnits=1000001}},
  {"unknown lane",func(p *Frozen){p.Lane="FORGE"}},
  {"uppercase protocol identity",func(p *Frozen){p.ProtocolSHA256=strings.Repeat("A",64)}},
 }
 for _,tc:=range cases {
  t.Run(tc.name,func(t *testing.T){
   p,w:=fixture()
   tc.change(&p)
   // Even when the advisory witness was recomputed to match the altered
   // source bytes, structural rejection must remain mandatory.
   if fp,err:=Fingerprint(p);err==nil {w.FrozenSHA256=fp}
   if err:=Check(p,w);!errors.Is(err,ErrBlocked){
    t.Fatalf("invalid source cleared eligibility: %v",err)
   }
  })
 }
}
