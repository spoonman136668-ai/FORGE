package coordination

import (
    "encoding/json"
    "os"
    "regexp"
    "testing"
)

// These tests run with the existing cross-platform Go qualification. This
// directory remains inert: the manifest is never imported by a controller.
func readRegistry(t *testing.T) map[string]json.RawMessage {
    t.Helper()
    raw, err := os.ReadFile("registry.v1.json")
    if err != nil { t.Fatal(err) }
    var out map[string]json.RawMessage
    if err := json.Unmarshal(raw, &out); err != nil { t.Fatal(err) }
    return out
}

func TestRegistryNoExecutionOrAcceptance(t *testing.T) {
    root := readRegistry(t)
    var advisory bool
    if err := json.Unmarshal(root["advisory_only"], &advisory); err != nil || !advisory { t.Fatal("not explicitly advisory") }
    var authority map[string]json.RawMessage
    if err := json.Unmarshal(root["authority"], &authority); err != nil { t.Fatal(err) }
    required := []string{"execute", "dispatch", "scientific_accept", "first_use", "promote", "deploy", "modify_controller", "create_scheduler", "modify_queues"}
    if len(authority) != len(required) { t.Fatal("authority field drift") }
    for _, name := range required {
        raw, ok := authority[name]
        if !ok || string(raw) != "false" { t.Fatalf("%s requires exact false", name) }
    }
}

func TestRegistryPreservesSixLanesAndSeparateTracks(t *testing.T) {
    root := readRegistry(t)
    var tracks []struct {
        ID string `json:"id"`
        Route string `json:"evidence_route"`
        State string `json:"scientific_status"`
        Source string `json:"source_status"`
        Pointer string `json:"source_pointer"`
    }
    if err := json.Unmarshal(root["tracks"], &tracks); err != nil { t.Fatal(err) }
    if len(tracks) < 10 || len(tracks) > 40 { t.Fatal("track count") }
    canonical := map[string]bool{"wingless":true, "yggdrasil":true, "bio":true, "optimizer":true, "mass-research":true, "language-research":true}
    idOK := regexp.MustCompile(`^[a-z][a-z0-9-]{2,63}$`)
    seen := make(map[string]bool)
    for _, x := range tracks {
        if !idOK.MatchString(x.ID) || seen[x.ID] { t.Fatalf("invalid/duplicate id %q", x.ID) }
        seen[x.ID] = true
        want := "SEPARATE_ADVISORY"
        if canonical[x.ID] { want = "EXISTING_SIX_LANE" }
        if x.Route != want || x.State != "UNVERIFIED" || x.Source != "POINTER_ONLY" { t.Fatalf("unqualified route or acceptance for %s", x.ID) }
        if len(x.Pointer) < 20 { t.Fatalf("missing source pointer: %s", x.ID) }
    }
    for key := range canonical { if !seen[key] { t.Fatalf("lost canonical lane: %s", key) } }
}

func TestRegistryDoesNotClaimChatRetirement(t *testing.T) {
    root := readRegistry(t)
    var gates []struct {
        ID string `json:"id"`
        Status string `json:"status"`
        Evidence []string `json:"evidence"`
    }
    if err := json.Unmarshal(root["readiness_gates"], &gates); err != nil { t.Fatal(err) }
    required := map[string]bool{"owner-continuity":true,"research-handoff":true,"evidence-routing":true,"unattended-cycles":true,"science-and-owner-signoff":true}
    if len(gates) != len(required) { t.Fatal("missing readiness gates") }
    for _, g := range gates {
        if !required[g.ID] || g.Status != "UNVERIFIED" || len(g.Evidence) != 0 { t.Fatalf("fabricated retirement readiness: %s", g.ID) }
        delete(required, g.ID)
    }
    if len(required) != 0 { t.Fatalf("missing gates: %v", required) }
}
