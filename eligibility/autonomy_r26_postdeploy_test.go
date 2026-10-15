package eligibility

import (
    "errors"
    "testing"
)

// TestR26PostDeploySourceAdmissionDenials is strictly a source-only
// qualification fixture. It cannot issue scientific start authority.
func TestR26PostDeploySourceAdmissionDenials(t *testing.T) {
    p, w := fixture()
    w.LedgerAuthenticated = false
    if err := Check(p, w); !errors.Is(err, ErrBlocked) {
        t.Fatalf("untrusted source evidence was admitted: %v", err)
    }
}
