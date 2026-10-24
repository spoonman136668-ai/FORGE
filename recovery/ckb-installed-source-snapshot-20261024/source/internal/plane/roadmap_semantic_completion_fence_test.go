package plane

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func roadmapSemanticFixture(t *testing.T, p *Engine, w WorkOrder, files map[string]string) Job {
	t.Helper()
	w.Scope.Allowed = []string{"docs/**", "pkg/**", "demo.txt"}
	evidence := filepath.Join(p.Root, "evidence", "roadmap-semantic-fixture")
	candidateRoot := filepath.Join(evidence, "candidate_files")
	if err := os.MkdirAll(candidateRoot, 0700); err != nil {
		t.Fatal(err)
	}
	entries := make([]CandidateEntry, 0, len(files))
	for name, body := range files {
		path := filepath.Join(candidateRoot, filepath.FromSlash(name))
		if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
			t.Fatal(err)
		}
		data := []byte(body)
		if err := os.WriteFile(path, data, 0600); err != nil {
			t.Fatal(err)
		}
		entries = append(entries, CandidateEntry{Path: name, SHA256: digest(data)})
	}
	if err := writeJSON(filepath.Join(evidence, "candidate_inventory.json"), entries); err != nil {
		t.Fatal(err)
	}
	return Job{ID: "SEMANTIC_FIXTURE", Order: w, Evidence: evidence}
}

func TestRoadmapSemanticCompletionFenceBlocksExplicitNotReady(t *testing.T) {
	p, w := setup(t)
	j := roadmapSemanticFixture(t, p, w, map[string]string{
		"docs/KTRADE_PINE_ENGINE_INVENTORY.md": "PINE-08 status: NOT READY\nThe mandatory semantic implementation remains unfinished.\n",
		"pkg/pine_runtime.go":                  "package pkg\n",
	})
	disposition, detail, err := p.roadmapParentSemanticDisposition(j)
	if err != nil {
		t.Fatal(err)
	}
	if disposition != roadmapSemanticBlockedPrerequisite {
		t.Fatalf("disposition=%s detail=%s", disposition, detail)
	}
	if !strings.Contains(detail, "STATUS: NOT READY") {
		t.Fatalf("missing blocker detail: %s", detail)
	}
}

func TestRoadmapSemanticCompletionFenceTreatsDocsTestsOnlyAsInvestigation(t *testing.T) {
	p, w := setup(t)
	j := roadmapSemanticFixture(t, p, w, map[string]string{
		"docs/KTRADE_PINE_ENGINE_INVENTORY.md": "Inventory updated with current findings.\n",
		"pkg/ktrade_pine08_test.go":            "package pkg\n",
	})
	disposition, detail, err := p.roadmapParentSemanticDisposition(j)
	if err != nil {
		t.Fatal(err)
	}
	if disposition != roadmapSemanticInvestigationComplete {
		t.Fatalf("disposition=%s detail=%s", disposition, detail)
	}
}

func TestRoadmapSemanticCompletionFenceAcceptsImplementationDelta(t *testing.T) {
	p, w := setup(t)
	j := roadmapSemanticFixture(t, p, w, map[string]string{
		"docs/KTRADE_PINE_ENGINE_INVENTORY.md": "Implementation evidence retained.\n",
		"pkg/pine_runtime.go":                  "package pkg\n",
		"pkg/ktrade_pine08_test.go":            "package pkg\n",
	})
	disposition, detail, err := p.roadmapParentSemanticDisposition(j)
	if err != nil {
		t.Fatal(err)
	}
	if disposition != roadmapSemanticAcceptedImplementation {
		t.Fatalf("disposition=%s detail=%s", disposition, detail)
	}
	if !strings.Contains(detail, "pkg/pine_runtime.go") {
		t.Fatalf("implementation delta missing from detail: %s", detail)
	}
}
