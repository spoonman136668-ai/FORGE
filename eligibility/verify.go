// Package eligibility validates frozen, source-bound research proposals.
// It does not admit science, consume cohorts, issue start receipts, or authorize dispatch.
package eligibility

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
)

const Schema = "forge.eligibility.frozen.v1"

type Frozen struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 CandidateID string `json:"candidate_id"`
 SourceSHA string `json:"source_sha"`
 PreregSHA256 string `json:"prereg_sha256"`
 CohortSHA256 string `json:"cohort_sha256"`
 ProtocolSHA256 string `json:"protocol_sha256"`
 BudgetUnits uint64 `json:"budget_units"`
 SeedIDs []string `json:"seed_ids"`
}

type Witness struct {
 Lane string
 SourceSHA string
 PreregSHA256 string
 CohortSHA256 string
 ProtocolSHA256 string
 // ConsumedCohorts must originate from an independently qualified,
 // complete and authenticated ledger, never the proposal or Mind-Palace.
 ConsumedCohorts map[string]bool
 LedgerAuthenticated bool
 // StartReconciled must be established externally; an unknown prior start
 // is terminally blocked until an independent reconciliation.
 StartReconciled bool
}

var ErrBlocked = errors.New("FORGE_ELIGIBILITY_BLOCKED_NO_SCIENTIFIC_AUTHORITY")

func lowerHex(s string, n int) bool {
 if len(s)!=n {return false}
 for _,c:=range s {if !((c>='0'&&c<='9')||(c>='a'&&c<='f')) {return false}}
 return true
}
func identifier(s string) bool {
 if len(s)<3 || len(s)>128 {return false}
 for _,c:=range s {if !((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'||c=='-'||c=='.') {return false}}
 return true
}

// Check is a deterministic negative-only preflight; success means only
// structural consistency, never eligibility for scientific execution.
// The caller must never infer READY_RESEARCH from a nil error.
func Check(p Frozen,w Witness) error {
 if p.Schema!=Schema || (p.Lane!="Wingless"&&p.Lane!="Yggdrasil") || !identifier(p.CandidateID) ||
  !lowerHex(p.SourceSHA,40) || !lowerHex(p.PreregSHA256,64) ||
  !lowerHex(p.CohortSHA256,64) || !lowerHex(p.ProtocolSHA256,64) ||
  p.BudgetUnits==0 || p.BudgetUnits>1000000 || len(p.SeedIDs)==0 || len(p.SeedIDs)>128 {
  return fmt.Errorf("%w: frozen contract",ErrBlocked)
 }
 seeds:=make(map[string]bool,len(p.SeedIDs))
 for _,s:=range p.SeedIDs {
  if !identifier(s)||seeds[s] {return fmt.Errorf("%w: seed collision",ErrBlocked)}
  seeds[s]=true
 }
 if w.Lane!=p.Lane || w.SourceSHA!=p.SourceSHA ||
  w.PreregSHA256!=p.PreregSHA256 || w.CohortSHA256!=p.CohortSHA256 ||
  w.ProtocolSHA256!=p.ProtocolSHA256 {
  return fmt.Errorf("%w: independently pinned witness mismatch",ErrBlocked)
 }
 if !w.LedgerAuthenticated || w.ConsumedCohorts==nil || !w.StartReconciled {
  return fmt.Errorf("%w: missing authenticated ledger or uncertain start",ErrBlocked)
 }
 if w.ConsumedCohorts[p.CohortSHA256] {
  return fmt.Errorf("%w: cohort previously consumed",ErrBlocked)
 }
 return nil
}

// Fingerprint binds the exact immutable preregistration inputs using the
// fixed field-order JSON representation. It carries no scientific authority.
func Fingerprint(p Frozen) (string,error) {
 if p.Schema!=Schema {return "",ErrBlocked}
 raw,err:=json.Marshal(p)
 if err!=nil{return "",err}
 h:=sha256.Sum256(append([]byte("FORGE-ELIGIBILITY-FROZEN-V1\n"),raw...))
 return hex.EncodeToString(h[:]),nil
}
