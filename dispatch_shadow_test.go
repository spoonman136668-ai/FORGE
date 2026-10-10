package progression

import (
	"encoding/json"
	"strings"
	"testing"
)

func admittedFixture(t *testing.T) (State, DispatchIdentity) {
	t.Helper()
	s := NewState()
	for _, step := range steps(LaneWingless, 1, strings.Repeat("a", 64), strings.Repeat("b", 64), strings.Repeat("1", 40))[:4] {
		s = must(t, s, step)
	}
	ls := s.Lanes[LaneWingless]
	if ls.Phase != Qualified {
		t.Fatal("fixture is not qualified")
	}
	s = must(t, s, Event{Schema: EventSchema, Kind: Admit, Lane: LaneWingless, Generation: 1,
		CandidateSHA256: ls.CandidateSHA256, CohortSHA256: ls.CohortSHA256,
		SourceRef: ls.SourceRef, WitnessSHA256: strings.Repeat("e", 64),
		PreregSHA256: ls.PreregSHA256, QualificationSHA256: ls.QualificationSHA256})
	return s, DispatchIdentity{Lane: LaneWingless, Generation: 1, CandidateSHA256: ls.CandidateSHA256,
		CohortSHA256: ls.CohortSHA256, SourceRef: ls.SourceRef, PreregSHA256: ls.PreregSHA256,
		QualificationSHA256: ls.QualificationSHA256, Workflow: "research-authority-generic.yml", Attempt: 1, AuthorityEpoch: 9}
}

func TestShadowDispatchIdempotenceAndNoOutboundCapability(t *testing.T) {
	s, id := admittedFixture(t)
	b, row, ok, err := ReserveDispatchInShadow(s, NewDispatchBook(), id)
	if err != nil || !ok || row.DispatchPermitted || row.Phase != ShadowReserved {
		t.Fatalf("reservation=%+v new=%v err=%v", row, ok, err)
	}
	replay, dup, created, err := ReserveDispatchInShadow(s, b, id)
	if err != nil || created || dup.IdentitySHA256 != row.IdentitySHA256 || len(replay.Reservations) != 1 {
		t.Fatalf("duplicate=%+v created=%v err=%v", dup, created, err)
	}
	if b.Reservations[row.IdentitySHA256].Phase != ShadowReserved {
		t.Fatal("prior book mutated")
	}
}
func TestShadowDispatchPinsAndAuthorityCannotChange(t *testing.T) {
	s, id := admittedFixture(t)
	for _, change := range []func(*DispatchIdentity){
		func(x *DispatchIdentity) { x.AuthorityEpoch = 0 },
		func(x *DispatchIdentity) { x.Workflow = "r213-synthetic-execute.yml" },
		func(x *DispatchIdentity) { x.Attempt = 2 },
		func(x *DispatchIdentity) { x.CandidateSHA256 = strings.Repeat("e", 64) },
		func(x *DispatchIdentity) { x.PreregSHA256 = strings.Repeat("e", 64) },
		func(x *DispatchIdentity) { x.QualificationSHA256 = strings.Repeat("e", 64) },
		func(x *DispatchIdentity) { x.Lane = LaneYggdrasil },
	} {
		bad := id
		change(&bad)
		if _, _, _, err := ReserveDispatchInShadow(s, NewDispatchBook(), bad); err == nil {
			t.Fatalf("accepted untrusted identity %+v", bad)
		}
	}
}
func TestShadowDispatchSameGenerationConflict(t *testing.T) {
	s, id := admittedFixture(t)
	b, _, _, err := ReserveDispatchInShadow(s, NewDispatchBook(), id)
	if err != nil {
		t.Fatal(err)
	}
	amended := id
	amended.AuthorityEpoch++
	if _, _, _, err := ReserveDispatchInShadow(s, b, amended); err == nil || !strings.Contains(err.Error(), "DIFFERENT_IDENTITY") {
		t.Fatalf("authority epoch drift not rejected: %v", err)
	}
}
func TestShadowDispatchFailsClosedOnAmbiguousNetworkOutcome(t *testing.T) {
	s, id := admittedFixture(t)
	b, row, _, err := ReserveDispatchInShadow(s, NewDispatchBook(), id)
	if err != nil {
		t.Fatal(err)
	}
	// No receipt is supplied: subsequent wakes cannot mint another reservation
	// or infer that absence of a matching run permits another dispatch.
	for i := 0; i < 30; i++ {
		nb, r, created, err := ReserveDispatchInShadow(s, b, id)
		if err != nil || created || r.Phase != ShadowReserved || r.DispatchPermitted || len(nb.Reservations) != 1 {
			t.Fatalf("wake %d granted retry: %v", i, err)
		}
	}
	if _, _, _, err := ObserveDispatchInShadow(b, DispatchObservation{IdentitySHA256: row.IdentitySHA256, Kind: "TERMINAL", RunID: 10, Attempt: 1,
		Workflow: id.Workflow, SourceRef: id.SourceRef, WitnessSHA256: strings.Repeat("c", 64), Outcome: "SUPPORTED"}); err == nil {
		t.Fatal("terminal without start was accepted")
	}
}
func TestShadowDispatchObservationsRetainNegativeEvidence(t *testing.T) {
	s, id := admittedFixture(t)
	b, row, _, err := ReserveDispatchInShadow(s, NewDispatchBook(), id)
	if err != nil {
		t.Fatal(err)
	}
	started := DispatchObservation{IdentitySHA256: row.IdentitySHA256, Kind: "STARTED", RunID: 100, Attempt: 1,
		Workflow: id.Workflow, SourceRef: id.SourceRef, WitnessSHA256: strings.Repeat("c", 64)}
	b, row, changed, err := ObserveDispatchInShadow(b, started)
	if err != nil || !changed || row.Phase != ShadowStarted {
		t.Fatalf("start: %+v %v", row, err)
	}
	terminal := started
	terminal.Kind = "TERMINAL"
	terminal.Outcome = "NEGATIVE"
	terminal.WitnessSHA256 = strings.Repeat("d", 64)
	b, row, changed, err = ObserveDispatchInShadow(b, terminal)
	if err != nil || !changed || row.Outcome != "NEGATIVE" || row.DispatchPermitted {
		t.Fatalf("terminal: %+v %v", row, err)
	}
	_, r, changed, err := ObserveDispatchInShadow(b, terminal)
	if err != nil || changed || r.Outcome != "NEGATIVE" {
		t.Fatalf("duplicate terminal changed state: %+v %v", r, err)
	}
	terminal.Outcome = "SUPPORTED"
	if _, _, _, err := ObserveDispatchInShadow(b, terminal); err == nil {
		t.Fatal("changed classification accepted")
	}
	started.RunID = 101
	if _, _, _, err := ObserveDispatchInShadow(b, started); err == nil {
		t.Fatal("conflicting run accepted")
	}
}
func TestShadowDispatchNeverBlocksUnrelatedLaneWithoutSharedCohort(t *testing.T) {
	s, id := admittedFixture(t)
	// Distinct lane reserves its own admitted source and unrelated cohort.
	l := LaneYggdrasil
	for _, ev := range steps(l, 1, strings.Repeat("c", 64), strings.Repeat("d", 64), strings.Repeat("2", 40))[:4] {
		s = must(t, s, ev)
	}
	ls := s.Lanes[l]
	s = must(t, s, Event{Schema: EventSchema, Kind: Admit, Lane: l, Generation: 1, CandidateSHA256: ls.CandidateSHA256,
		CohortSHA256: ls.CohortSHA256, SourceRef: ls.SourceRef, WitnessSHA256: strings.Repeat("e", 64),
		PreregSHA256: ls.PreregSHA256, QualificationSHA256: ls.QualificationSHA256})
	b, _, _, err := ReserveDispatchInShadow(s, NewDispatchBook(), id)
	if err != nil {
		t.Fatal(err)
	}
	other := DispatchIdentity{Lane: l, Generation: 1, CandidateSHA256: ls.CandidateSHA256, CohortSHA256: ls.CohortSHA256,
		SourceRef: ls.SourceRef, PreregSHA256: ls.PreregSHA256, QualificationSHA256: ls.QualificationSHA256,
		Workflow: id.Workflow, Attempt: 1, AuthorityEpoch: id.AuthorityEpoch}
	b, row, created, err := ReserveDispatchInShadow(s, b, other)
	if err != nil || !created || row.DispatchPermitted || len(b.Reservations) != 2 {
		t.Fatalf("distinct lane rejected: %+v, %v", row, err)
	}
}
func TestShadowDispatchRejectsConsumedOrNonAdmittedState(t *testing.T) {
	s, id := admittedFixture(t)
	already := NewState()
	if _, _, _, err := ReserveDispatchInShadow(already, NewDispatchBook(), id); err == nil {
		t.Fatal("idle allowed")
	}
	s.Consumed[id.CohortSHA256] = "previous-consumption"
	if _, _, _, err := ReserveDispatchInShadow(s, NewDispatchBook(), id); err == nil {
		t.Fatal("consumed cohort allowed")
	}
}

func TestShadowDispatchRestartAndTamperedBookFailClosed(t *testing.T) {
	s, id := admittedFixture(t)
	before, row, _, err := ReserveDispatchInShadow(s, NewDispatchBook(), id)
	if err != nil {
		t.Fatal(err)
	}
	raw, err := json.Marshal(before)
	if err != nil {
		t.Fatal(err)
	}
	var restored DispatchBook
	if err = json.Unmarshal(raw, &restored); err != nil {
		t.Fatal(err)
	}
	if err = ValidateDispatchBook(restored); err != nil {
		t.Fatal(err)
	}
	after, r, newly, err := ReserveDispatchInShadow(s, restored, id)
	if err != nil || newly || r.DispatchPermitted || len(after.Reservations) != 1 {
		t.Fatalf("restart invented a second dispatch: %v", err)
	}
	forged := cloneBook(restored)
	rec := forged.Reservations[row.IdentitySHA256]
	rec.DispatchPermitted = true
	forged.Reservations[row.IdentitySHA256] = rec
	if err = ValidateDispatchBook(forged); err == nil {
		t.Fatal("forged dispatch capability accepted")
	}
	forged = cloneBook(restored)
	delete(forged.CohortOwners, id.CohortSHA256)
	if err = ValidateDispatchBook(forged); err == nil {
		t.Fatal("missing cohort index accepted")
	}
	forged = cloneBook(restored)
	rec = forged.Reservations[row.IdentitySHA256]
	rec.Phase = ShadowEnded
	forged.Reservations[row.IdentitySHA256] = rec
	if err = ValidateDispatchBook(forged); err == nil {
		t.Fatal("terminal without start and evidence accepted")
	}
}
