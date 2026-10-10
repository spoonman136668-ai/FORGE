package contracts

import (
	"context"
	"strings"
	"testing"
)

func baseCandidate() CandidateDraft {
	return CandidateDraft{Schema: CandidateSchema, Lane: Wingless, Generation: 2, CandidateID: "W-2",
		SourceCommitSHA: strings.Repeat("a", 40), CandidateSHA256: strings.Repeat("b", 64),
		PreregistrationSHA256: strings.Repeat("c", 64), CohortSHA256: strings.Repeat("d", 64),
		EvidenceClass: Synthetic, SeedIdentities: []string{"Wingless:1001", "Wingless:1002"},
		AllowedPaths: []string{"research/wingless/experiment.go"},
		Budget:       Budget{TimeoutSeconds: 600, MemoryMiB: 1024, ComputeUnits: 100}}
}
func TestCandidateSeparationFromExecution(t *testing.T) {
	c := baseCandidate()
	h, err := CanonicalCandidateSHA256(c)
	if err != nil || len(h) != 64 {
		t.Fatalf("baseline: %s %v", h, err)
	}
	e := c
	e.Generation++
	h2, err := CanonicalCandidateSHA256(e)
	if err != nil || h == h2 {
		t.Fatal("changed generation reused digest")
	}
	f := c
	f.ScientificPrimary = true
	if ValidateCandidate(f) == nil {
		t.Fatal("primary allowed")
	}
	f = c
	f.DispatchAuthorized = true
	if ValidateCandidate(f) == nil {
		t.Fatal("dispatch allowed")
	}
	f = c
	f.AcceptedRefMutation = true
	if ValidateCandidate(f) == nil {
		t.Fatal("accepted ref allowed")
	}
	f = c
	f.ExternalSourceAdmitted = true
	if ValidateCandidate(f) == nil {
		t.Fatal("external certification forged")
	}
	f = c
	f.ProductionAuthority = true
	if ValidateCandidate(f) == nil {
		t.Fatal("production allowed")
	}
}
func TestCandidateProvenanceAndResourceDenial(t *testing.T) {
	cases := []struct {
		name string
		edit func(*CandidateDraft)
	}{
		{"wrong_schema", func(c *CandidateDraft) { c.Schema = "v2" }},
		{"lane", func(c *CandidateDraft) { c.Lane = "KTRADE" }},
		{"sha", func(c *CandidateDraft) { c.SourceCommitSHA = "foo" }},
		{"upper_hex", func(c *CandidateDraft) { c.CandidateSHA256 = strings.Repeat("A", 64) }},
		{"zero_budget", func(c *CandidateDraft) { c.Budget.TimeoutSeconds = 0 }},
		{"excess_budget", func(c *CandidateDraft) { c.Budget.MemoryMiB = 32769 }},
		{"cross_lane_seed", func(c *CandidateDraft) { c.SeedIdentities[0] = "Yggdrasil:1001" }},
		{"duplicate_seed", func(c *CandidateDraft) { c.SeedIdentities[1] = c.SeedIdentities[0] }},
		{"path_traversal", func(c *CandidateDraft) { c.AllowedPaths[0] = "research/../../.github/workflows/activate.yml" }},
		{"authority_path", func(c *CandidateDraft) { c.AllowedPaths[0] = "snapshot/source/main.go" }},
		{"secrets_path", func(c *CandidateDraft) { c.AllowedPaths[0] = ".github/workflows/main.yml" }},
		{"windows_path", func(c *CandidateDraft) { c.AllowedPaths[0] = `C:\forbidden\not-allowed` }},
		{"duplicate_path", func(c *CandidateDraft) { c.AllowedPaths = append(c.AllowedPaths, c.AllowedPaths[0]) }},
		{"no_seed", func(c *CandidateDraft) { c.SeedIdentities = nil }},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			c := baseCandidate()
			tc.edit(&c)
			if err := ValidateCandidate(c); err == nil {
				t.Fatal("accepted unsafe candidate")
			}
		})
	}
}
func TestObservationAndAcknowledgmentNotAuthority(t *testing.T) {
	source := strings.Repeat("1", 64)
	ledger := strings.Repeat("2", 64)
	o := Observation{Schema: ObservationSchema, Lane: Yggdrasil, AuthorityEpoch: 5, SourceWitnessSHA256: source, LedgerWitnessSHA256: ledger, LatestOutcome: "CONSUMED_INDETERMINATE"}
	if err := ValidateObservation(o); err != nil {
		t.Fatal(err)
	}
	o.ScientificAuthority = true
	if ValidateObservation(o) == nil {
		t.Fatal("observation forged authority")
	}
	o.ScientificAuthority = false
	o.LatestOutcome = "FORGED"
	if ValidateObservation(o) == nil {
		t.Fatal("unrecognized outcome")
	}
	h, err := CanonicalCandidateSHA256(baseCandidate())
	if err != nil {
		t.Fatal(err)
	}
	a := QuarantineAcknowledgment{Schema: AcknowledgmentSchema, ProposalSHA256: h, Status: "QUARANTINE_ONLY"}
	if err := ValidateAcknowledgment(a, h); err != nil {
		t.Fatal(err)
	}
	a.DispatchAuthorized = true
	if ValidateAcknowledgment(a, h) == nil {
		t.Fatal("quarantine became dispatch")
	}
	a.DispatchAuthorized = false
	if ValidateAcknowledgment(a, ledger) == nil {
		t.Fatal("wrong proposal hash accepted")
	}
}

// Compile-time proof of the intended unprivileged two-port boundary.
type fakeEvidence struct{}

func (fakeEvidence) ReadLatest(context.Context, Lane) (Observation, error) { return Observation{}, nil }

type fakeInbox struct{}

func (fakeInbox) SubmitDraft(context.Context, CandidateDraft) (QuarantineAcknowledgment, error) {
	return QuarantineAcknowledgment{}, nil
}

var _ EvidenceReader = fakeEvidence{}
var _ QuarantineInbox = fakeInbox{}
