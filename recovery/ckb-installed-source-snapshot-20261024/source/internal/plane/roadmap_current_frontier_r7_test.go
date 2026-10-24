package plane

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

const postBTVCurrentParent = "V11110_POSTKCH_KTRADE_BTV02_REPAINT_LOOKAHEAD_MTF_CAUSALITY_INSPECTOR_R1"
const postBTVFirstChild = "V11110_POSTKCH_KTRADE_BTV03_MULTI_SYMBOL_PORTFOLIO_PINE_R1"

func hasRoadmapString(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}

func TestRoadmapCurrentFrontierPostBTVCatalogContract(t *testing.T) {
	c, err := loadRoadmapSuccessorCatalog()
	if err != nil {
		t.Fatal(err)
	}
	if c.Schema != roadmapSuccessorCatalogSchema || len(c.Entries) != 18 {
		t.Fatalf("catalog schema=%s entries=%d", c.Schema, len(c.Entries))
	}
	want := []string{
		"BTV-03", "BTV-04", "BTV-05", "BTV-06",
		"PXT-01", "PXT-02", "PXT-03", "PXT-04",
		"PAPER-TOOLS", "DIC-01", "DIC-02", "DIC-03",
		"CLOSE-01", "CLOSE-02", "CLOSE-03", "CLOSE-04", "CLOSE-05",
		"LIVE-PROMOTION",
	}
	for i, key := range want {
		if c.Entries[i].Key != key {
			t.Fatalf("entry[%d]=%s want=%s", i, c.Entries[i].Key, key)
		}
		if i > 0 && c.Entries[i].ParentID != c.Entries[i-1].ID {
			t.Fatalf("entry[%d] parent=%s previous=%s", i, c.Entries[i].ParentID, c.Entries[i-1].ID)
		}
	}
	if c.Entries[0].ID != postBTVFirstChild || c.Entries[0].ParentID != postBTVCurrentParent {
		t.Fatalf("post-BTV frontier mismatch: %#v", c.Entries[0])
	}
	for i := 0; i < 17; i++ {
		if !c.Entries[i].AutoAuthorized {
			t.Fatalf("%s must remain auto-authorized", c.Entries[i].Key)
		}
	}
	if c.Entries[17].AutoAuthorized || !strings.Contains(c.Entries[17].OperatorReason, "Live promotion") {
		t.Fatalf("live promotion boundary invalid: %#v", c.Entries[17])
	}
}

func TestRoadmapCurrentFrontierPostBTVParentInheritance(t *testing.T) {
	c, err := loadRoadmapSuccessorCatalog()
	if err != nil {
		t.Fatal(err)
	}
	e := c.Entries[0]
	parent := WorkOrder{}
	parent.Preserve = []string{"historical UI-lock composability", "BTV-02 repaint/lookahead/MTF causality"}
	parent.UI.Root = "pkg/web"
	parent.UI.Pages = []UIPage{{
		Path:        "strategy.html",
		CriticalIDs: []string{"priceCanvas", "pineEditorButton", "paperOrderTicket", "chartEditorWorkspace"},
		ChartID:     "priceCanvas",
	}}
	parent.UI.Markers = map[string][]string{
		"BTV-02 repaint/lookahead/MTF causality": {"pineEditorButton", "priceCanvas"},
	}

	w, raw, err := roadmapSuccessorWorkOrderWithParent(e, parent, strings.Repeat("a", 40))
	if err != nil {
		t.Fatal(err)
	}
	if w.ID != postBTVFirstChild || w.Baseline.Ref != localCandidateBaselinePrefix+postBTVCurrentParent {
		t.Fatalf("rendered child mismatch: %+v", w)
	}
	if !hasRoadmapString(w.Preserve, "historical UI-lock composability") ||
		!hasRoadmapString(w.Preserve, "BTV-02 repaint/lookahead/MTF causality") {
		t.Fatalf("preserve inheritance invalid: %#v", w.Preserve)
	}
	if got := w.UI.Markers["BTV-03 deterministic multi-symbol / portfolio Pine"]; jsonText(got) != jsonText([]string{"pineEditorButton", "priceCanvas"}) {
		t.Fatalf("child BTV-03 marker missing or changed: %#v", got)
	}
	if w.UI.Root != "pkg/web" || len(w.UI.Pages) != 1 || w.UI.Pages[0].ChartID != "priceCanvas" {
		t.Fatalf("UI inheritance invalid: %+v", w.UI)
	}
	if got := w.UI.Markers["BTV-02 repaint/lookahead/MTF causality"]; jsonText(got) != jsonText([]string{"pineEditorButton", "priceCanvas"}) {
		t.Fatalf("inherited marker changed: %#v", got)
	}
	if !strings.Contains(raw, e.Title) {
		t.Fatal("rendered YAML missing child title")
	}
}

func TestRoadmapCurrentFrontierPostBTVMaterializesBTV03(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)
	sourceQueue(t, p, w, postBTVCurrentParent)

	if err := p.AutonomyTick(context.Background()); err != nil {
		t.Fatal(err)
	}
	parent := wait(t, p, postBTVCurrentParent)
	if parent.State != "ACCEPTED" {
		t.Fatalf("parent not accepted: %+v", parent)
	}
	if err := p.AutonomyTick(context.Background()); err != nil {
		t.Fatal(err)
	}

	var parentQueue string
	if err := p.Store.DB.QueryRow("SELECT state FROM queue_items WHERE id=?", postBTVCurrentParent).Scan(&parentQueue); err != nil {
		t.Fatal(err)
	}
	if parentQueue != "COMPLETED" {
		t.Fatalf("parent queue=%s", parentQueue)
	}

	p.Config.Autonomy.PineSuccessorController = true
	if err := p.reconcilePineSuccessor(context.Background()); err != nil {
		t.Fatal(err)
	}

	var raw []byte
	var state, auth, mode string
	if err := p.Store.DB.QueryRow(
		"SELECT raw,state,authorization,mode FROM queue_items WHERE id=?",
		postBTVFirstChild,
	).Scan(&raw, &state, &auth, &mode); err != nil {
		t.Fatal(err)
	}
	if state != "QUEUED" || auth != "operator" || mode != "source" {
		t.Fatalf("child queue state=%s auth=%s mode=%s", state, auth, mode)
	}

	var q QueueOrder
	if err := json.Unmarshal(raw, &q); err != nil {
		t.Fatal(err)
	}
	if len(q.Dependencies) != 1 || q.Dependencies[0] != postBTVCurrentParent {
		t.Fatalf("dependencies=%#v", q.Dependencies)
	}
	order, err := ParseOrder([]byte(q.WorkOrderYAML))
	if err != nil {
		t.Fatal(err)
	}

	manifestRaw, err := os.ReadFile(filepath.Join(p.Root, "exports", postBTVCurrentParent, "1", "candidate.json"))
	if err != nil {
		t.Fatal(err)
	}
	var manifest localCandidateExport
	if err := json.Unmarshal(manifestRaw, &manifest); err != nil {
		t.Fatal(err)
	}
	if order.Baseline.SHA != manifest.CandidateSHA || manifest.Published || manifest.AcceptedRefMutated {
		t.Fatalf("candidate binding mismatch order=%s export=%+v", order.Baseline.SHA, manifest)
	}
}
