package progression

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"
)

const (
	candA   = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	candB   = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
	cohortA = "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
	cohortB = "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
	witness = "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
	prereg  = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
	qual    = "1212121212121212121212121212121212121212121212121212121212121212"
	raw     = "3434343434343434343434343434343434343434343434343434343434343434"
	refA    = "abababababababababababababababababababab"
	refB    = "cdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcd"
)

func e(lane Lane, gen uint64, kind Kind, candidate, cohort, ref string) Event {
	v := Event{Schema: EventSchema, Lane: lane, Generation: gen, Kind: kind, CandidateSHA256: candidate, CohortSHA256: cohort, SourceRef: ref, WitnessSHA256: witness}
	switch kind {
	case Freeze:
		v.PreregSHA256 = prereg
	case Qualify:
		v.QualificationSHA256 = qual
	case Admit:
		v.PreregSHA256 = prereg
		v.QualificationSHA256 = qual
	case Start:
		v.RunID = 100 + gen
		v.Attempt = 1
	case Finish:
		v.RunID = 100 + gen
		v.Attempt = 1
		v.EvidenceSHA256 = raw
		v.Outcome = "NEGATIVE"
	case Archive:
		v.RunID = 100 + gen
		v.Attempt = 1
		v.EvidenceSHA256 = raw
		v.ArchiveSHA256 = witness
	case Block:
		v.Reason = "GITHUB_WITNESS_MISSING"
	}
	return v
}

func steps(lane Lane, gen uint64, candidate, cohort, ref string) []Event {
	types := []Kind{Select, Freeze, Build, Qualify, Admit, Start, Finish, Archive, Close}
	out := make([]Event, 0, len(types))
	for _, k := range types {
		out = append(out, e(lane, gen, k, candidate, cohort, ref))
	}
	return out
}

func must(t *testing.T, s State, event Event) State {
	t.Helper()
	_, next, changed, err := ProposeRecord(s, event)
	if err != nil {
		t.Fatalf("unexpected %s error: %v", event.Kind, err)
	}
	if !changed {
		t.Fatalf("unexpected no-op %s", event.Kind)
	}
	return next
}

func reject(t *testing.T, s State, event Event) {
	t.Helper()
	_, _, _, err := ProposeRecord(s, event)
	if err == nil {
		t.Fatalf("accepted invalid %s at %+v", event.Kind, s.Lanes[event.Lane])
	}
}

func TestTwoGenerationsBothLanesAndNegativeRetention(t *testing.T) {
	s := NewState()
	for _, x := range steps(LaneWingless, 1, candA, cohortA, refA) {
		s = must(t, s, x)
	}
	for _, x := range steps(LaneYggdrasil, 1, candB, cohortB, refB) {
		s = must(t, s, x)
	}
	if s.Lanes[LaneWingless].Phase != Idle || s.Lanes[LaneYggdrasil].Phase != Idle || len(s.Consumed) != 2 {
		t.Fatalf("unexpected terminal state: %+v", s)
	}
	if s.Lanes[LaneWingless].Outcome != "NEGATIVE" {
		t.Fatal("negative result discarded")
	}
	for _, x := range steps(LaneWingless, 2, candB, raw, refA) {
		s = must(t, s, x)
	}
	for _, x := range steps(LaneYggdrasil, 2, candA, qual, refB) {
		s = must(t, s, x)
	}
	if s.Sequence != 36 || len(s.Consumed) != 4 {
		t.Fatalf("failed twice-through: seq=%d consumed=%d", s.Sequence, len(s.Consumed))
	}
	if len(Advisory(s)) != 2 {
		t.Fatal("not both lanes")
	}
}

func TestExactDuplicateIsNoopWithJournalEvidence(t *testing.T) {
	s := NewState()
	event := e(LaneWingless, 1, Select, candA, cohortA, refA)
	s = must(t, s, event)
	record, next, changed, err := ProposeRecord(s, event)
	if err != nil || changed || next.Sequence != 2 || next.Lanes[LaneWingless] != s.Lanes[LaneWingless] {
		t.Fatalf("duplicate incorrectly applied: %+v %v", next, err)
	}
	if _, _, err = ApplyRecord(s, record); err != nil {
		t.Fatalf("duplicate journal record rejected: %v", err)
	}
}

func TestOutOfOrderAndIdentityDrift(t *testing.T) {
	s := NewState()
	reject(t, s, e(LaneWingless, 1, Start, candA, cohortA, refA))
	s = must(t, s, e(LaneWingless, 1, Select, candA, cohortA, refA))
	reject(t, s, e(LaneWingless, 1, Qualify, candA, cohortA, refA))
	reject(t, s, e(LaneWingless, 1, Freeze, candB, cohortA, refA))
	reject(t, s, e(LaneWingless, 2, Freeze, candA, cohortA, refA))
	reject(t, s, e(LaneWingless, 1, Start, candA, cohortA, refA))
	s = must(t, s, e(LaneWingless, 1, Freeze, candA, cohortA, refA))
	s = must(t, s, e(LaneWingless, 1, Build, candA, cohortA, refA))
	s = must(t, s, e(LaneWingless, 1, Qualify, candA, cohortA, refA))
	admission := e(LaneWingless, 1, Admit, candA, cohortA, refA)
	admission.PreregSHA256 = candA
	reject(t, s, admission)
}

func TestCrossLaneCohortCollisionAndConsumption(t *testing.T) {
	s := must(t, NewState(), e(LaneWingless, 1, Select, candA, cohortA, refA))
	reject(t, s, e(LaneYggdrasil, 1, Select, candB, cohortA, refB))
	for _, kind := range []Kind{Freeze, Build, Qualify, Admit, Start} {
		s = must(t, s, e(LaneWingless, 1, kind, candA, cohortA, refA))
	}
	reject(t, s, e(LaneYggdrasil, 1, Select, candB, cohortA, refB))
	for _, kind := range []Kind{Finish, Archive, Close} {
		s = must(t, s, e(LaneWingless, 1, kind, candA, cohortA, refA))
	}
	reject(t, s, e(LaneWingless, 2, Select, candB, cohortA, refA))
	reject(t, s, e(LaneYggdrasil, 1, Select, candB, cohortA, refB))
}

func TestInvalidTerminalAlwaysConsumedAndArchived(t *testing.T) {
	s := NewState()
	for _, kind := range []Kind{Select, Freeze, Build, Qualify, Admit, Start} {
		s = must(t, s, e(LaneWingless, 1, kind, candA, cohortA, refA))
	}
	terminal := e(LaneWingless, 1, Finish, candA, cohortA, refA)
	terminal.Outcome = "CONSUMED_INDETERMINATE"
	s = must(t, s, terminal)
	reject(t, s, e(LaneWingless, 1, Close, candA, cohortA, refA))
	archive := e(LaneWingless, 1, Archive, candA, cohortA, refA)
	archive.EvidenceSHA256 = candB
	reject(t, s, archive)
	s = must(t, s, e(LaneWingless, 1, Archive, candA, cohortA, refA))
	s = must(t, s, e(LaneWingless, 1, Close, candA, cohortA, refA))
	reject(t, s, e(LaneWingless, 2, Select, candB, cohortA, refA))
	if s.Lanes[LaneWingless].Outcome != "CONSUMED_INDETERMINATE" {
		t.Fatal("ambiguous consumption lost")
	}
}

func TestIndependentBlockedLane(t *testing.T) {
	s := must(t, NewState(), e(LaneWingless, 1, Select, candA, cohortA, refA))
	s = must(t, s, e(LaneWingless, 1, Block, candA, cohortA, refA))
	s = must(t, s, e(LaneYggdrasil, 1, Select, candB, cohortB, refB))
	if s.Lanes[LaneWingless].Phase != Blocked || s.Lanes[LaneYggdrasil].Phase != Selected {
		t.Fatal("blocked lane contaminated sibling")
	}
	reject(t, s, e(LaneWingless, 1, Start, candA, cohortA, refA))
}

func TestJournalReplayTamperAndTruncation(t *testing.T) {
	s := NewState()
	var journal bytes.Buffer
	for _, event := range steps(LaneWingless, 1, candA, cohortA, refA) {
		record, next, _, err := ProposeRecord(s, event)
		if err != nil {
			t.Fatal(err)
		}
		blob, err := json.Marshal(record)
		if err != nil {
			t.Fatal(err)
		}
		journal.Write(blob)
		journal.WriteByte('\n')
		s = next
	}
	replayed, err := Replay(bytes.NewReader(journal.Bytes()))
	if err != nil {
		t.Fatal(err)
	}
	if replayed.LastRecordSHA256 != s.LastRecordSHA256 || replayed.Sequence != 9 {
		t.Fatal("replay nondeterministic")
	}
	tampered := strings.Replace(journal.String(), candA, candB, 1)
	if _, err := Replay(strings.NewReader(tampered)); err == nil {
		t.Fatal("modified event accepted")
	}
	broken := strings.Replace(journal.String(), "\"sequence\":2", "\"sequence\":3", 1)
	if _, err := Replay(strings.NewReader(broken)); err == nil {
		t.Fatal("out of order event accepted")
	}
	if _, err := Replay(strings.NewReader(journal.String() + "{}\n")); err == nil {
		t.Fatal("unsigned event accepted")
	}
	duplicateKey := strings.Replace(journal.String(), "\"sequence\":1", "\"sequence\":1,\"sequence\":1", 1)
	if _, err := Replay(strings.NewReader(duplicateKey)); err == nil {
		t.Fatal("duplicate JSON key accepted")
	}
}

func TestEventStructuralRejections(t *testing.T) {
	initial := NewState()
	cases := []Event{
		{Schema: EventSchema, Kind: Select, Lane: "KTRADE", Generation: 1, CandidateSHA256: candA, CohortSHA256: cohortA, SourceRef: refA, WitnessSHA256: witness},
		{Schema: EventSchema, Kind: Select, Lane: LaneWingless, Generation: 1, CandidateSHA256: strings.ToUpper(candA), CohortSHA256: cohortA, SourceRef: refA, WitnessSHA256: witness},
		{Schema: EventSchema, Kind: Select, Lane: LaneWingless, Generation: 1, CandidateSHA256: candA, CohortSHA256: cohortA, SourceRef: refA, WitnessSHA256: ""},
	}
	for _, event := range cases {
		reject(t, initial, event)
	}
}

// A started primary with no captured raw bytes is irreversibly consumed and
// may only be closed after separately sealed immutable archive evidence.
func TestS06MissingRawIsNotFabricatedOrReplayable(t *testing.T) {
	s := NewState()
	for _, k := range []Kind{Select, Freeze, Build, Qualify, Admit, Start} {
		s = must(t, s, e(LaneYggdrasil, 1, k, candB, cohortB, refB))
	}
	terminal := e(LaneYggdrasil, 1, Finish, candB, cohortB, refB)
	terminal.Outcome = "CONSUMED_INDETERMINATE"
	terminal.EvidenceSHA256 = "" // Actual S06 Y raw bytes were not captured.
	s = must(t, s, terminal)
	noArchive := e(LaneYggdrasil, 1, Archive, candB, cohortB, refB)
	noArchive.EvidenceSHA256 = ""
	noArchive.ArchiveSHA256 = ""
	reject(t, s, noArchive)
	noArchive.ArchiveSHA256 = witness // This is a separate ZIP/archive digest.
	s = must(t, s, noArchive)
	s = must(t, s, e(LaneYggdrasil, 1, Close, candB, cohortB, refB))
	if s.Lanes[LaneYggdrasil].EvidenceSHA256 != "" ||
		s.Lanes[LaneYggdrasil].ArchiveSHA256 != witness ||
		s.Lanes[LaneYggdrasil].Outcome != "CONSUMED_INDETERMINATE" {
		t.Fatalf("missing raw fabricated or archive discarded: %+v", s.Lanes[LaneYggdrasil])
	}
	reject(t, s, e(LaneWingless, 1, Select, candA, cohortB, refA))
	reject(t, s, e(LaneYggdrasil, 2, Select, candA, cohortB, refB))
}

func TestSupportedCannotUseMissingRawAndArchiveMustBeDistinct(t *testing.T) {
	s := NewState()
	for _, k := range []Kind{Select, Freeze, Build, Qualify, Admit, Start} {
		s = must(t, s, e(LaneWingless, 1, k, candA, cohortA, refA))
	}
	terminal := e(LaneWingless, 1, Finish, candA, cohortA, refA)
	terminal.Outcome = "SUPPORTED"
	terminal.EvidenceSHA256 = ""
	reject(t, s, terminal)
	terminal.EvidenceSHA256 = raw
	s = must(t, s, terminal)
	archive := e(LaneWingless, 1, Archive, candA, cohortA, refA)
	archive.EvidenceSHA256 = ""
	reject(t, s, archive)
	archive.EvidenceSHA256 = raw
	archive.ArchiveSHA256 = ""
	reject(t, s, archive)
	archive.ArchiveSHA256 = witness
	s = must(t, s, archive)
	if s.Lanes[LaneWingless].ArchiveSHA256 != witness {
		t.Fatal("separate archive SHA lost")
	}
}
