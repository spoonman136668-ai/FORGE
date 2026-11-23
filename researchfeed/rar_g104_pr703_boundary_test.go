package researchfeed

import (
    "encoding/json"
    "os"
    "path/filepath"
    "testing"
)

func rarG104Manifest(t *testing.T) map[string]any {
    t.Helper()
    raw, err := os.ReadFile(filepath.Join("..", "research", "replay_acceleration", "rar_g104_pr703_source_mechanism_boundary.json"))
    if err != nil { t.Fatal(err) }
    var m map[string]any
    if err := json.Unmarshal(raw, &m); err != nil { t.Fatal(err) }
    if m["schema"] != "forge.research.rar-pr703-source-mechanism-boundary.v1" {
        t.Fatal("unrecognized source-only candidate mapping")
    }
    return m
}

func g104Map(t *testing.T, v any) map[string]any {
    t.Helper()
    x, ok := v.(map[string]any)
    if !ok {t.Fatalf("missing candidate evidence map: %T",v)}
    return x
}

// G104 is a bounded original-source *snapshot*, not a running selection
// mechanism or scientific candidate admission. Shared baseline identity
// cannot propagate G7/G8 replay negatives onto PR703's new method.
func TestRARG104PR703BaselineIdentityDoesNotEstablishReplayEquivalence(t *testing.T) {
    d := rarG104Manifest(t)
    replay := g104Map(t,d["replay_evidence"])
    candidate := g104Map(t,d["candidate"])
    base := g104Map(t,replay["referenced_baseline"])
    link := g104Map(t,d["linkage"])
    snap := g104Map(t,d["snapshot"])
    if snap["protected_forge_main"] != "d444bf3551d1a6917562c1ad58a84c4c28f6aed5" ||
        snap["postmerge_workflow_conclusion"] != "success" ||
        snap["read_only"] != true { t.Fatal("postmerge evidence drift") }
    if replay["source_commit"] != rarEvidenceCommit ||
        replay["source_git_blob"] != rarG78Blob ||
        replay["source_path"] != "research/replay_acceleration/rar_g7_g8_advisory_evidence.json" ||
        replay["source_only"] != true ||
        replay["first_use_cleared"] != false ||
        replay["scientific_accepted"] != false { t.Fatal("replay source or authority drift") }
    original := rarG99Source(t,"rar_g7_g8_advisory_evidence.json")
    var g78 struct {
        Source struct {
            Repository string `json:"repository"`
            Commit string `json:"commit"`
            File string `json:"file"`
            GitBlob string `json:"git_blob"`
        } `json:"source"`
        G7 struct {Classification string `json:"classification"`} `json:"G7"`
        G8 struct {Classification string `json:"classification"`} `json:"G8"`
    }
    if err := json.Unmarshal(original,&g78);err != nil {t.Fatal(err)}
    if g78.Source.Repository != base["repository"] ||
        g78.Source.Commit != base["commit"] ||
        g78.Source.File != base["path"] ||
        g78.Source.GitBlob != base["git_blob"] ||
        g78.Source.GitBlob != "c4a69a56cb59a7df3322d6d7fd9101b3c1e89d25" ||
        g78.G7.Classification != "REJECT_SURPRISE" ||
        g78.G8.Classification != "SCREEN_NEGATIVE_OR_INCONCLUSIVE" { t.Fatal("original G7/G8 baseline drift") }
    outcomes := g104Map(t,replay["outcomes"])
    if outcomes["RAR-G7"] != "NEGATIVE" || outcomes["RAR-G8"] != "INCONCLUSIVE" {
        t.Fatal("historical replay findings reclassified")
    }
    if candidate["repository"] != base["repository"] ||
        candidate["base_commit"] != base["commit"] ||
        candidate["path"] != base["path"] ||
        candidate["head_commit"] != "ddee0d82a1e37038304fb862ac725240142c840f" ||
        candidate["head_git_blob"] != "5c9a9904e31688bebc2e53723569e1fb988a981f" ||
        candidate["head_git_blob"] == base["git_blob"] ||
        candidate["pr_number"] != float64(703) ||
        candidate["diff_files"] != float64(1) ||
        candidate["diff_commit_count"] != float64(1) ||
        candidate["changed_lines"] != float64(18) ||
        candidate["new_method"] != "observed_action_contrast" ||
        candidate["replay_training_added"] != false {
        t.Fatal("unverified or mutated PR703 source-only identity")
    }
    if link["shared_baseline_source_identity_verified"] != true ||
        link["candidate_source_diff_identity_verified"] != true ||
        link["candidate_mechanism_identical_to_prior_replay"] != false ||
        link["candidate_mechanism_equivalence_authenticated"] != false ||
        link["original_candidate_experimental_receipts_authenticated"] != false ||
        link["transfer_prior_negative_to_candidate"] != false ||
        link["candidate_specific_replay_advisory"] != "NO_INDEXED_REPLAY_MATCH_FOR_CANDIDATE" {
        t.Fatal("unproven mechanism mapping elevated")
    }
    for _,flag := range []string{
        "planning_preference_change_authorized",
        "already_active_task_reprioritization_authorized",
        "scientific_first_use","scientific_accepted",
        "execution_authorized","accepted_ref_mutation","owner_controller_changed",
    } {
        if v,ok := link[flag]; !ok || v != false {
            t.Fatalf("G104 falsely asserted live authority for %s",flag)
        }
    }
}

// Even with exact source baseline identity, G99's hypothetical interface
// must leave an unlinked real candidate neutral, not inherit a negative.
func TestRARG104UnlinkedPR703CannotInheritReplayPenalty(t *testing.T) {
    index,g78,g33 := rarG99Inputs(t)
    got,err := PreviewRARPlanning(index,g78,g33,[]RARHypothesis{{ID:"Yggdrasil-PR703"}})
    if err != nil {t.Fatal(err)}
    if len(got.Choices)!=1 || got.InputOrderChanged ||
        got.Choices[0].Advisory != "NO_INDEXED_REPLAY_FINDING" ||
        got.Choices[0].LinkageAuthenticated ||
        got.CandidateMechanismLinkageAuthenticated ||
        !got.AdvisoryOnly ||
        got.ScientificAccepted || got.DispatchAuthorized ||
        got.AcceptedRefMutation || got.ScientificFirstUseAuthorized {
        t.Fatalf("false PR703 replay transfer or authority: %#v",got)
    }
}
