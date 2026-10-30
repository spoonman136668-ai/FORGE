package researchfeed

import (
    "encoding/json"
    "os"
    "path/filepath"
    "testing"
)

const rarG90MergedEvidence = "f9afb43056d0b045e482e0ed1f8ce9177c070dd1"

func rarG90Index(t *testing.T) []byte {
    t.Helper()
    raw, err := os.ReadFile(filepath.Join("..", "research", "replay_acceleration", "rar_g90_source_index.json"))
    if err != nil { t.Fatal(err) }
    return raw
}

// The merged replay results remain untrusted source pointers. This does not
// authenticate original bytes, admit science, modify F139, or dispatch work.
func TestRARG90ExistingReaderPreservesNegativeAndInvalidEvidence(t *testing.T) {
    preview, err := PreviewCandidates(rarG90Index(t))
    if err != nil { t.Fatal(err) }
    if !preview.AdvisoryOnly || preview.ScientificAccepted ||
        preview.ScientificFirstUseCleared || preview.ExecutionAuthorized ||
        preview.OriginalBytesAuthenticated || len(preview.Entries) != 3 {
        t.Fatalf("replay index elevated authority: %#v", preview)
    }
    expected := map[string]string{
        "RAR-G7": "NEGATIVE",
        "RAR-G8": "INCONCLUSIVE",
        "RAR-G33": "INVALID",
    }
    for _, e := range preview.Entries {
        if want, ok := expected[e.ResearchID]; !ok || e.Outcome != want {
            t.Fatalf("replay outcome changed: %#v", e)
        }
        if e.Lane != "Optimizer Work" ||
            e.SourceRepo != "spoonman136668-ai/FORGE" ||
            e.SourceCommit != rarG90MergedEvidence ||
            e.EvidenceState != "SOURCE_POINTER_ONLY" ||
            e.ReportedSHA256 != "" {
            t.Fatalf("replay source unexpectedly admitted: %#v", e)
        }
        delete(expected, e.ResearchID)
    }
    if len(expected) != 0 { t.Fatalf("missing replay outcomes: %#v", expected) }
}

func TestRARG90IndexCannotRequestScientificAuthority(t *testing.T) {
    var input Input
    if err := json.Unmarshal(rarG90Index(t), &input); err != nil { t.Fatal(err) }
    if len(input.Candidates) != 3 { t.Fatal("unexpected candidate count") }
    for _, forbidden := range []string{"first-use", "scientific-acceptance", "dispatch"} {
        modified := input
        modified.Candidates = append([]Candidate(nil), input.Candidates...)
        switch forbidden {
        case "first-use": modified.Candidates[0].FirstUseCleared = true
        case "scientific-acceptance": modified.Candidates[0].ScientificAccepted = true
        case "dispatch": modified.Candidates[0].ExecuteRequested = true
        }
        raw, err := json.Marshal(modified)
        if err != nil { t.Fatal(err) }
        if _, err := PreviewCandidates(raw); err == nil {
            t.Fatalf("forbidden %s accepted from untrusted replay evidence", forbidden)
        }
    }
}
