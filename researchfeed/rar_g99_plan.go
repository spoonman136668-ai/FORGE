package researchfeed

import (
    "crypto/sha1"
    "encoding/hex"
    "encoding/json"
    "errors"
    "fmt"
    "sort"
)

// G99 is pinned to already-merged source bytes. Authenticating those blobs
// does NOT authenticate missing original experimental receipts or future
// candidate mechanism equivalence, and never accepts scientific results.
const (
    RARG99Schema = "forge.research.rar-offline-planning-observation.v1"
    rarEvidenceCommit = "f9afb43056d0b045e482e0ed1f8ce9177c070dd1"
    rarG78Blob = "176984375e75625d4de57b09941f3bb94ffa07f8"
    rarG33Blob = "8635060abe6a5c57b95d4e61cd32eee3d2b63715"
)

var ErrRARPlanning = errors.New("FORGE_RAR_PLANNING_SOURCE_OR_AUTHORITY_UNVERIFIED")

type RARHypothesis struct {
    ID string `json:"id"`
    // This link is caller-declared, never independently proven equivalent.
    PriorResearchID string `json:"prior_research_id"`
}
type RARPlanningChoice struct {
    ID string `json:"id"`
    PriorResearchID string `json:"prior_research_id"`
    Advisory string `json:"advisory"`
    LinkageAuthenticated bool `json:"linkage_authenticated"`
}
type RARPlanningObservation struct {
    Schema string `json:"schema"`
    SourceIndexSHA256 string `json:"source_index_sha256"`
    EvidenceCommit string `json:"evidence_commit"`
    GitBlobsVerified bool `json:"git_blobs_verified"`
    SourceClassificationsVerified bool `json:"source_classifications_verified"`
    InputOrderChanged bool `json:"input_order_changed"`
    Choices []RARPlanningChoice `json:"choices"`
    AdvisoryOnly bool `json:"advisory_only"`
    OriginalExperimentalBytesAuthenticated bool `json:"original_experimental_bytes_authenticated"`
    CandidateMechanismLinkageAuthenticated bool `json:"candidate_mechanism_linkage_authenticated"`
    ScientificAccepted bool `json:"scientific_accepted"`
    ScientificFirstUseAuthorized bool `json:"scientific_first_use_authorized"`
    DispatchAuthorized bool `json:"dispatch_authorized"`
    AcceptedRefMutation bool `json:"accepted_ref_mutation"`
}

func rarGitBlob(raw []byte) string {
    h := sha1.New()
    _, _ = fmt.Fprintf(h, "blob %d\x00", len(raw))
    _, _ = h.Write(raw)
    return hex.EncodeToString(h.Sum(nil))
}

// PreviewRARPlanning is purely offline. It accepts the indexed evidence plus
// exact merged original SOURCE FILE bytes from a separately read-only source.
// Both original Git blob identities and all outcome labels must match before
// considering a caller-supplied hypothetical planning order. It never reads
// the F139 ledger, modifies selection, performs first use, or dispatches work.
func PreviewRARPlanning(rawIndex, rawG78, rawG33 []byte, hypotheses []RARHypothesis) (RARPlanningObservation, error) {
    var zero RARPlanningObservation
    if len(rawG78) == 0 || len(rawG78) > MaxBytes ||
        len(rawG33) == 0 || len(rawG33) > MaxBytes ||
        rarGitBlob(rawG78) != rarG78Blob || rarGitBlob(rawG33) != rarG33Blob {
        return zero, ErrRARPlanning
    }
    index, err := PreviewCandidates(rawIndex)
    if err != nil || !index.AdvisoryOnly || index.ScientificAccepted ||
        index.ScientificFirstUseCleared || index.ExecutionAuthorized ||
        index.OriginalBytesAuthenticated || len(index.Entries) != 3 {
        return zero, ErrRARPlanning
    }
    expected := map[string]struct { path, outcome string }{
        "RAR-G7": {"research/replay_acceleration/rar_g7_g8_advisory_evidence.json", "NEGATIVE"},
        "RAR-G8": {"research/replay_acceleration/rar_g7_g8_advisory_evidence.json", "INCONCLUSIVE"},
        "RAR-G33": {"research/replay_acceleration/rar_g33_original_cross_os_nested_receipts.json", "INVALID"},
    }
    for _, entry := range index.Entries {
        want, ok := expected[entry.ResearchID]
        if !ok || entry.Lane != "Optimizer Work" ||
            entry.SourceRepo != "spoonman136668-ai/FORGE" ||
            entry.SourceCommit != rarEvidenceCommit || entry.SourcePath != want.path ||
            entry.Outcome != want.outcome || entry.EvidenceState != "SOURCE_POINTER_ONLY" ||
            entry.ReportedSHA256 != "" {
            return zero, ErrRARPlanning
        }
        delete(expected, entry.ResearchID)
    }
    if len(expected) != 0 { return zero, ErrRARPlanning }
    var g78 struct {
        Schema string `json:"schema"`
        GateIDs []string `json:"gate_ids"`
        G7 struct { Classification string `json:"classification"` } `json:"G7"`
        G8 struct { Classification string `json:"classification"` } `json:"G8"`
        Custody struct {
            FirstUse bool `json:"scientific_first_use"`
            Accepted bool `json:"scientific_accepted"`
        } `json:"custody"`
        AllowCandidateIngestion bool `json:"allow_candidate_ingestion"`
        AllowPromotion bool `json:"allow_promotion"`
        AllowDispatch bool `json:"allow_autonomous_dispatch"`
    }
    if err := json.Unmarshal(rawG78, &g78); err != nil ||
        g78.Schema != "forge.research.replay-acceleration.advisory-evidence.v1" ||
        len(g78.GateIDs) != 2 || g78.GateIDs[0] != "RAR-G7" || g78.GateIDs[1] != "RAR-G8" ||
        g78.G7.Classification != "REJECT_SURPRISE" ||
        g78.G8.Classification != "SCREEN_NEGATIVE_OR_INCONCLUSIVE" ||
        g78.Custody.FirstUse || g78.Custody.Accepted || g78.AllowCandidateIngestion ||
        g78.AllowPromotion || g78.AllowDispatch {
        return zero, ErrRARPlanning
    }
    var g33 struct {
        Gate string `json:"gate"`
        Classification string `json:"classification"`
        Correction struct {
            ScientificResult string `json:"scientific_result"`
            SourceOnly bool `json:"source_only"`
        } `json:"correction"`
        Safety struct {
            ScientificFirstUse bool `json:"scientific_first_use"`
            AdvisoryOnly bool `json:"advisory_only"`
        } `json:"safety"`
        Distinctions struct {
            LinuxCPUPassWithdrawn bool `json:"linux_cpu_pass_withdrawn"`
            LinuxCPUReceiptsValid bool `json:"linux_cpu_receipts_valid"`
        } `json:"distinctions"`
    }
    if err := json.Unmarshal(rawG33, &g33); err != nil ||
        g33.Gate != "RAR-G33" ||
        g33.Classification != "SOURCE_ONLY_G32_LINUX_NESTED_CPU_TOTAL_INVALID_DOUBLE_COUNT_UNVERIFIED_WINDOWS_CPU_AND_FULL_TREE" ||
        g33.Correction.ScientificResult != "LINUX_CPU_PASS_WITHDRAWN" ||
        !g33.Correction.SourceOnly || !g33.Safety.AdvisoryOnly ||
        g33.Safety.ScientificFirstUse || !g33.Distinctions.LinuxCPUPassWithdrawn ||
        g33.Distinctions.LinuxCPUReceiptsValid {
        return zero, ErrRARPlanning
    }
    if len(hypotheses) == 0 || len(hypotheses) > 12 { return zero, ErrRARPlanning }
    seen := map[string]bool{}
    choices := make([]RARPlanningChoice, 0, len(hypotheses))
    for _, item := range hypotheses {
        if !safeID(item.ID) || seen[item.ID] { return zero, ErrRARPlanning }
        seen[item.ID] = true
        advisory := "NO_INDEXED_REPLAY_FINDING"
        switch item.PriorResearchID {
        case "":
        case "RAR-G7": advisory = "NEGATIVE_REQUIRES_GENUINELY_NEW_MECHANISM_AND_FRESH_CONTROLS"
        case "RAR-G8": advisory = "INCONCLUSIVE_REQUIRES_FRESH_COMPARATIVE_CONTROLS"
        case "RAR-G33": advisory = "INVALID_CPU_MEASUREMENT_CANNOT_SUPPORT_SPEEDUP"
        default: return zero, ErrRARPlanning
        }
        choices = append(choices, RARPlanningChoice{
            ID:item.ID, PriorResearchID:item.PriorResearchID, Advisory:advisory,
        })
    }
    priority := func(c RARPlanningChoice) int {
        switch c.PriorResearchID {
        case "RAR-G8": return 1
        case "RAR-G7": return 2
        case "RAR-G33": return 3
        }
        return 0
    }
    sort.SliceStable(choices, func(i,j int)bool{return priority(choices[i]) < priority(choices[j])})
    changed := false
    for i, c := range choices {
        if c.ID != hypotheses[i].ID { changed = true; break }
    }
    return RARPlanningObservation{
        Schema:RARG99Schema,SourceIndexSHA256:index.InputSHA256,
        EvidenceCommit:rarEvidenceCommit,GitBlobsVerified:true,
        SourceClassificationsVerified:true,InputOrderChanged:changed,
        Choices:choices,AdvisoryOnly:true,
    },nil
}
