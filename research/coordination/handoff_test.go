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
    if len(h.Workstreams) < 9 { t.Fatal("incomplete research handoff inventory") }
    required := map[string]bool{
        "native-intelligence": true, "n-research": true, "e-research": true,
        "replay-acceleration": true, "llm-acceleration": true,
        "independent-science": true, "bio-optimizer-language": true,
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
