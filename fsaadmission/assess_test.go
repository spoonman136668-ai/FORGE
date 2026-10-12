package fsaadmission

import (
    "errors"
    "strings"
    "testing"

    "github.com/spoonman136668-ai/forge/eligibility"
    "github.com/spoonman136668-ai/forge/researchlog"
    "github.com/spoonman136668-ai/forge/startrecovery"
)

func testEvidence(t *testing.T) Evidence {
    t.Helper()
    h := func(c string, n int) string { return strings.Repeat(c, n) }
    p := eligibility.Frozen{
        Schema: eligibility.Schema, Lane: "Wingless",
        CandidateID: "exp_01", SourceSHA: h("a", 40),
        PreregSHA256: h("b", 64), CohortSHA256: h("c", 64),
        ProtocolSHA256: h("d", 64), BudgetUnits: 10,
        SeedIDs: []string{"Wingless:seed_01"},
    }
    journal := researchlog.New()
    appendKind := func(kind researchlog.Kind, runID uint64) {
        event := researchlog.Event{
            Lane: p.Lane, Generation: 7, ExperimentID: p.CandidateID,
            Kind: kind, SourceCommitSHA: p.SourceSHA,
            PreregSHA256: p.PreregSHA256, CohortSHA256: p.CohortSHA256,
            WitnessSHA256: h("e", 64), RunID: runID,
        }
        if kind == researchlog.Hypothesis {
            event.PreregSHA256 = ""; event.CohortSHA256 = ""; event.WitnessSHA256 = ""
        }
        if kind == researchlog.Preregister { event.WitnessSHA256 = "" }
        next, err := researchlog.Append(journal, event)
        if err != nil { t.Fatal(err) }
        journal = next
    }
    appendKind(researchlog.Hypothesis, 0)
    appendKind(researchlog.Preregister, 0)
    appendKind(researchlog.SourceQualified, 0)
    ledger := eligibility.LedgerSnapshot{
        Schema: "forge.eligibility.ledger-snapshot.v1",
        Scope: "ALL_LANES", Generation: 7,
        ConsumedCohorts: []string{}, ActiveCohorts: []string{},
        Starts: []eligibility.StartRecord{},
    }
    fpin, err := eligibility.Fingerprint(p)
    if err != nil { t.Fatal(err) }
    lpin, err := eligibility.LedgerFingerprint(ledger)
    if err != nil { t.Fatal(err) }
    return Evidence{
        Frozen: p, FrozenPinSHA256: fpin,
        Ledger: ledger, LedgerPinSHA256: lpin, LedgerGeneration: 7,
        CompleteAllLanes: true, Journal: journal,
        JournalHead: startrecovery.TrustedHead{
            Sequence: uint64(len(journal.Entries)),
            SHA256: journal.Entries[len(journal.Entries)-1].RecordSHA256,
            IndependentlyAuthenticated: true,
        },
        ExperimentGeneration: 7,
    }
}

func requireBlocked(t *testing.T, e Evidence) {
    t.Helper()
    decision, err := Assess(e)
    if decision != "" || !errors.Is(err, ErrBlocked) {
        t.Fatalf("expected fail closed; decision=%q error=%v", decision, err)
    }
}
func TestComposedSourcePreflightIsNotAdmission(t *testing.T) {
    e := testEvidence(t)
    decision, err := Assess(e)
    if err != nil || decision != PreflightOnly {
        t.Fatalf("source preflight = %q, %v", decision, err)
    }
    if strings.Contains(string(decision), "AUTHORIZED") ||
        strings.Contains(string(decision), "EXECUTE") {
        t.Fatal("preflight wording accidentally grants execution authority")
    }
}
func TestComposedPreflightRejectsUnauthenticatedAndStaleEvidence(t *testing.T) {
    for name, mutate := range map[string]func(*Evidence){
        "untrusted head": func(e *Evidence){ e.JournalHead.IndependentlyAuthenticated=false },
        "stale head": func(e *Evidence){ e.JournalHead.Sequence-- },
        "wrong head": func(e *Evidence){ e.JournalHead.SHA256=strings.Repeat("f",64) },
        "incomplete all-lane ledger": func(e *Evidence){ e.CompleteAllLanes=false },
        "missing ledger pin": func(e *Evidence){ e.LedgerPinSHA256="" },
        "ledger generation": func(e *Evidence){ e.LedgerGeneration++ },
        "frozen digest drift": func(e *Evidence){ e.FrozenPinSHA256=strings.Repeat("f",64) },
        "corrupted journal": func(e *Evidence){ e.Journal.Entries[0].RecordSHA256=strings.Repeat("f",64) },
    } {
        t.Run(name,func(t *testing.T) {
            e:=testEvidence(t)
            mutate(&e)
            requireBlocked(t,e)
        })
    }
}
func TestComposedPreflightRejectsCrossLaneAndPriorStart(t *testing.T) {
    t.Run("active cohort in any lane",func(t *testing.T){
        e:=testEvidence(t)
        e.Ledger.ActiveCohorts=append(e.Ledger.ActiveCohorts,e.Frozen.CohortSHA256)
        pin,err:=eligibility.LedgerFingerprint(e.Ledger)
        if err!=nil {t.Fatal(err)}
        e.LedgerPinSHA256=pin
        requireBlocked(t,e)
    })
    t.Run("consumed cohort in any lane",func(t *testing.T){
        e:=testEvidence(t)
        e.Ledger.ConsumedCohorts=append(e.Ledger.ConsumedCohorts,e.Frozen.CohortSHA256)
        pin,err:=eligibility.LedgerFingerprint(e.Ledger)
        if err!=nil {t.Fatal(err)}
        e.LedgerPinSHA256=pin
        requireBlocked(t,e)
    })
    t.Run("ambiguous start ledger",func(t *testing.T){
        e:=testEvidence(t)
        e.Ledger.Starts=append(e.Ledger.Starts,eligibility.StartRecord{
            FrozenSHA256:e.FrozenPinSHA256,State:"INDETERMINATE",
        })
        pin,err:=eligibility.LedgerFingerprint(e.Ledger)
        if err!=nil {t.Fatal(err)}
        e.LedgerPinSHA256=pin
        requireBlocked(t,e)
    })
    t.Run("already started journal",func(t *testing.T){
        e:=testEvidence(t)
        next,err:=researchlog.Append(e.Journal,researchlog.Event{
            Lane:e.Frozen.Lane,Generation:7,ExperimentID:e.Frozen.CandidateID,
            Kind:researchlog.PrimaryStarted,SourceCommitSHA:e.Frozen.SourceSHA,
            PreregSHA256:e.Frozen.PreregSHA256,CohortSHA256:e.Frozen.CohortSHA256,
            WitnessSHA256:strings.Repeat("e",64),RunID:42,
        })
        if err!=nil {t.Fatal(err)}
        e.Journal=next
        e.JournalHead.Sequence=uint64(len(next.Entries))
        e.JournalHead.SHA256=next.Entries[len(next.Entries)-1].RecordSHA256
        requireBlocked(t,e)
    })
}
func TestComposedPreflightBindsExactExperimentAndFrozenInputs(t *testing.T) {
    for name,mutate := range map[string]func(*Evidence){
        "source mismatch":func(e *Evidence){e.Frozen.SourceSHA=strings.Repeat("f",40)},
        "cohort mismatch":func(e *Evidence){e.Frozen.CohortSHA256=strings.Repeat("f",64)},
        "prereg mismatch":func(e *Evidence){e.Frozen.PreregSHA256=strings.Repeat("f",64)},
        "wrong candidate":func(e *Evidence){e.Frozen.CandidateID="exp_02"},
        "generation mismatch":func(e *Evidence){e.ExperimentGeneration=8;e.LedgerGeneration=8;e.Ledger.Generation=8},
    }{
        t.Run(name,func(t *testing.T){
            e:=testEvidence(t)
            mutate(&e)
            fpin,err:=eligibility.Fingerprint(e.Frozen)
            if err!=nil{t.Fatal(err)}
            e.FrozenPinSHA256=fpin
            lpin,err:=eligibility.LedgerFingerprint(e.Ledger)
            if err!=nil{t.Fatal(err)}
            e.LedgerPinSHA256=lpin
            requireBlocked(t,e)
        })
    }
}
