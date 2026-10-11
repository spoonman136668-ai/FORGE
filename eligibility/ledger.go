package eligibility

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
)

// LedgerSnapshot is advisory input only. It must be independently authenticated
// against an externally pinned digest before inspection. No mutation occurs.
type LedgerSnapshot struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 Generation uint64 `json:"generation"`
 ConsumedCohorts []string `json:"consumed_cohorts"`
 Starts []StartRecord `json:"starts"`
}
type StartRecord struct {
 FrozenSHA256 string `json:"frozen_sha256"`
 State string `json:"state"`
}

// VerifyLedger is a fail-closed read-only conflict detector, not science admission.
// Both pinnedSHA and complete come from a separate authenticated authority.
func VerifyLedger(p Frozen, snapshot LedgerSnapshot, pinnedSHA string, complete bool) error {
 if !complete || !lowerHex(pinnedSHA,64) || snapshot.Schema!="forge.eligibility.ledger-snapshot.v1" ||
  snapshot.Lane!=p.Lane || snapshot.Generation==0 {
  return fmt.Errorf("%w: ledger witness unavailable",ErrBlocked)
 }
 raw,err:=json.Marshal(snapshot)
 if err!=nil{return fmt.Errorf("%w: ledger serialization",ErrBlocked)}
 hash:=sha256.Sum256(append([]byte("FORGE-ELIGIBILITY-LEDGER-SNAPSHOT-V1\n"),raw...))
 if hex.EncodeToString(hash[:])!=pinnedSHA {return fmt.Errorf("%w: ledger identity mismatch",ErrBlocked)}
 seen:=map[string]bool{}
 for _,cohort:=range snapshot.ConsumedCohorts {
  if !lowerHex(cohort,64)||seen[cohort] {return fmt.Errorf("%w: consumed ledger malformed",ErrBlocked)}
  seen[cohort]=true
 }
 if seen[p.CohortSHA256] {return fmt.Errorf("%w: cohort consumed",ErrBlocked)}
 starts:=map[string]bool{}
 for _,entry:=range snapshot.Starts{
  if !lowerHex(entry.FrozenSHA256,64)||starts[entry.FrozenSHA256]{
   return fmt.Errorf("%w: ambiguous start ledger",ErrBlocked)
  }
  starts[entry.FrozenSHA256]=true
  switch entry.State {
  case "STARTED","TERMINAL","INDETERMINATE":
  default: return fmt.Errorf("%w: invalid start status",ErrBlocked)
  }
 }
 fingerprint,err:=Fingerprint(p)
 if err!=nil||starts[fingerprint]{return fmt.Errorf("%w: prior or uncertain start",ErrBlocked)}
 return nil
}

// LedgerFingerprint computes canonical bytes for independently pinning a complete
// ledger snapshot; returning this hash does NOT authenticate its provenance.
func LedgerFingerprint(s LedgerSnapshot)(string,error){
 raw,err:=json.Marshal(s)
 if err!=nil{return "",errors.Join(ErrBlocked,err)}
 h:=sha256.Sum256(append([]byte("FORGE-ELIGIBILITY-LEDGER-SNAPSHOT-V1\n"),raw...))
 return hex.EncodeToString(h[:]),nil
}
