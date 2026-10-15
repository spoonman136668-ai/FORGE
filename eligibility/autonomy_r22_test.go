package eligibility

import (
 "errors"
 "strings"
 "testing"
)

// TestR22ReadOnlySourceQualification exercises existing frozen-source
// rejection without triggering scientific execution, admission or custody.
func TestR22ReadOnlySourceQualification(t *testing.T) {
 for _,tc:=range []struct{
  name string
  edit func(*Frozen,*Witness)
 }{
  {"source-sha-drift",func(p *Frozen,_ *Witness){p.SourceSHA=strings.Repeat("d",40)}},
  {"unknown-lane",func(p *Frozen,_ *Witness){p.Lane="UNKNOWN"}},
  {"reused-cohort",func(p *Frozen,w *Witness){w.ConsumedCohorts[p.CohortSHA256]=true}},
  {"ambiguous-start",func(_ *Frozen,w *Witness){w.StartReconciled=false}},
  {"untrusted-ledger",func(_ *Frozen,w *Witness){w.LedgerAuthenticated=false}},
 }{
  t.Run(tc.name,func(t *testing.T){
   p,w:=fixture()
   tc.edit(&p,&w)
   if err:=Check(p,w); !errors.Is(err,ErrBlocked) {
    t.Fatalf("frozen source violation admitted: %v",err)
   }
  })
 }
}
