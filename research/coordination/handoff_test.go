package coordination

import (
    "encoding/json"
    "os"
    "testing"
)

// This is an inert source-only custody inventory test. It does not run models,
// access protected scientific sources, or turn research notes into permissions.
func TestHandoffPreservesIndependentNativeAndResearchScopes(t *testing.T) {
    b, err := os.ReadFile("handoff.v1.json")
    if err != nil { t.Fatal(err) }
    var h struct {
        Schema string `json:"schema"`
        AdvisoryOnly bool `json:"advisory_only"`
        ExecutionAuthorized bool `json:"execution_authorized"`
        ChatRetirementReady bool `json:"chat_retirement_ready"`
        InventoryCompleteness string `json:"inventory_completeness"`
        Workstreams []struct {
            ID string `json:"id"`
            Oversight string `json:"oversight"`
            Separate bool `json:"separate_scientific_lineage"`
            HandoffStatus string `json:"handoff_status"`
        } `json:"workstreams"`
    }
    if err := json.Unmarshal(b, &h); err != nil { t.Fatal(err) }
    if h.Schema != "forge.research-chat-handoff.v1" || !h.AdvisoryOnly ||
        h.ExecutionAuthorized || h.ChatRetirementReady || h.InventoryCompleteness != "UNVERIFIED" {
        t.Fatal("handoff cannot grant runtime or retirement authority")
    }
    if len(h.Workstreams) < 11 { t.Fatal("incomplete research handoff inventory") }
    required := map[string]bool{
        "native-intelligence": true, "n-research": true, "e-research": true,
        "replay-acceleration": true, "llm-acceleration": true,
        "independent-science": true, "bio-research": true, "optimizer-research": true, "language-research": true,
        "mass-research": true, "forge-operations": true,
    }
    seen := make(map[string]bool)
    for _, w := range h.Workstreams {
        if seen[w.ID] || !w.Separate || w.HandoffStatus != "UNVERIFIED" {
            t.Fatalf("duplicate, merged, or self-qualified research lane %q", w.ID)
        }
        seen[w.ID] = true
        want := "unified-research"
        if w.ID == "forge-operations" { want = "forge-operations" }
        if w.Oversight != want { t.Fatalf("owner scope drift: %s",w.ID) }
        delete(required,w.ID)
    }
    if len(required) != 0 { t.Fatalf("lost research roles: %v",required) }
}

func TestOriginalOwnerSourceAnchorsRemainAdvisory(t *testing.T) {
    b, err := os.ReadFile("handoff.v1.json")
    if err != nil { t.Fatal(err) }
    var h struct {
        ChatRetirementReady bool `json:"chat_retirement_ready"`
        Workstreams []struct {
            ID string `json:"id"`
            HandoffStatus string `json:"handoff_status"`
            SourcePointers []struct {
                URL string `json:"url"`
                SHA string `json:"sha"`
                Claim string `json:"claim"`
            } `json:"source_pointers"`
        } `json:"workstreams"`
    }
    if err := json.Unmarshal(b, &h); err != nil { t.Fatal(err) }
    if h.ChatRetirementReady { t.Fatal("source witnesses cannot retire research chats") }
    expected := map[string]string{
        "https://github.com/spoonman136668-ai/FORGE/pull/1264": "c2469e2844a9e99ad9cd273898c3113d06468251",
        "https://github.com/spoonman136668-ai/Yggdrasil/pull/703": "ddee0d82a1e37038304fb862ac725240142c840f",
        "https://github.com/spoonman136668-ai/Yggdrasil/pull/715": "356d9a7c9a5e58eab85589d5de31650cbf60cb03",
    }
    found := false
    for _, row := range h.Workstreams {
        if row.ID != "forge-operations" { continue }
        if found || row.HandoffStatus != "UNVERIFIED" || len(row.SourcePointers) != len(expected) {
            t.Fatal("F139 original owner handoff boundary changed")
        }
        found = true
        seen := make(map[string]bool)
        for _, ptr := range row.SourcePointers {
            if seen[ptr.URL] || expected[ptr.URL] != ptr.SHA || ptr.Claim != "SOURCE_POINTER_ONLY" {
                t.Fatalf("F139 original owner source pointer drift: %s", ptr.URL)
            }
            seen[ptr.URL] = true
        }
    }
    if !found { t.Fatal("missing original F139 owner workstream") }
}
