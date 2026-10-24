package plane

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

const successorPostBTVParent = "V11110_POSTKCH_KTRADE_BTV02_REPAINT_LOOKAHEAD_MTF_CAUSALITY_INSPECTOR_R1"
const successorPostBTVChild = "V11110_POSTKCH_KTRADE_BTV03_MULTI_SYMBOL_PORTFOLIO_PINE_R1"

func TestRoadmapSuccessorPostBTVCatalogShape(t *testing.T) {
	c, err := loadRoadmapSuccessorCatalog()
	if err != nil {
		t.Fatal(err)
	}
	if c.Schema != roadmapSuccessorCatalogSchema || len(c.Entries) != 18 {
		t.Fatalf("catalog schema=%s entries=%d", c.Schema, len(c.Entries))
	}
	if c.Entries[0].Key != "BTV-03" || c.Entries[0].ID != successorPostBTVChild || c.Entries[0].ParentID != successorPostBTVParent {
		t.Fatalf("unexpected first entry: %#v", c.Entries[0])
	}
	for i := 1; i < len(c.Entries); i++ {
		if c.Entries[i].ParentID != c.Entries[i-1].ID {
			t.Fatalf("entry[%d] parent=%s previous=%s", i, c.Entries[i].ParentID, c.Entries[i-1].ID)
		}
	}
	for i := 0; i < 17; i++ {
		if !c.Entries[i].AutoAuthorized {
			t.Fatalf("%s unexpectedly requires operator", c.Entries[i].Key)
		}
		for _, preserve := range c.Entries[i].Preserve {
			if len(c.Entries[i].UI.Markers[preserve]) == 0 {
				t.Fatalf("%s preserve %q lacks explicit marker contract", c.Entries[i].Key, preserve)
			}
		}
	}
	last := c.Entries[len(c.Entries)-1]
	if last.Key != "LIVE-PROMOTION" || last.AutoAuthorized || !strings.Contains(last.OperatorReason, "Live promotion") {
		t.Fatalf("protected boundary invalid: %#v", last)
	}
}

func TestRoadmapSuccessorBaseRendererStaysBoundedPostBTV(t *testing.T) {
	c, err := loadRoadmapSuccessorCatalog()
	if err != nil {
		t.Fatal(err)
	}
	e := c.Entries[0]
	sha := strings.Repeat("a", 40)
	w, raw, err := roadmapSuccessorWorkOrder(e, sha)
	if err != nil {
		t.Fatal(err)
	}
	if w.ID != e.ID || w.Baseline.Ref != localCandidateBaselinePrefix+e.ParentID || w.Baseline.SHA != sha {
		t.Fatalf("baseline/id mismatch: %+v", w)
	}
	if !w.Acceptance.ProtectRefs || !w.Acceptance.Clean || !w.Acceptance.All || !w.Acceptance.Browser {
		t.Fatalf("acceptance weakened: %+v", w.Acceptance)
	}
	if !strings.Contains(raw, e.Title) {
		t.Fatal("rendered YAML missing title")
	}
	for _, p := range []string{
		"pkg/risk.go",
		"pkg/accounting.go",
		"pkg/reconciliation_state.go",
		"pkg/broker_live.go",
		"pkg/coinbase_client.go",
	} {
		if w.Allows(p) {
			t.Fatalf("protected path allowed: %s", p)
		}
	}
}

func TestRoadmapSuccessorParentAwareRendererPreservesUIAndPreserve(t *testing.T) {
	c, err := loadRoadmapSuccessorCatalog()
	if err != nil {
		t.Fatal(err)
	}
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
	w, _, err := roadmapSuccessorWorkOrderWithParent(c.Entries[0], parent, strings.Repeat("b", 40))
	if err != nil {
		t.Fatal(err)
	}
	for _, want := range []string{"historical UI-lock composability", "BTV-02 repaint/lookahead/MTF causality"} {
		found := false
		for _, got := range w.Preserve {
			if got == want {
				found = true
				break
			}
		}
		if !found {
			t.Fatalf("missing inherited preserve %q: %#v", want, w.Preserve)
		}
	}
	if got := w.UI.Markers["BTV-02 repaint/lookahead/MTF causality"]; jsonText(got) != jsonText([]string{"pineEditorButton", "priceCanvas"}) {
		t.Fatalf("inherited marker changed: %#v", got)
	}
	if got := w.UI.Markers["BTV-03 deterministic multi-symbol / portfolio Pine"]; jsonText(got) != jsonText([]string{"pineEditorButton", "priceCanvas"}) {
		t.Fatalf("child BTV-03 marker missing or changed: %#v", got)
	}
}

func TestRoadmapSuccessorPostBTVProtectedBoundaryStopsBeforeQueue(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)
	c, err := loadRoadmapSuccessorCatalog()
	if err != nil {
		t.Fatal(err)
	}
	protected := c.Entries[len(c.Entries)-1]
	sourceQueue(t, p, w, protected.ParentID)
	if err = p.AutonomyTick(context.Background()); err != nil {
		t.Fatal(err)
	}
	if got := wait(t, p, protected.ParentID); got.State != "ACCEPTED" {
		t.Fatalf("parent not accepted: %+v", got)
	}
	if err = p.AutonomyTick(context.Background()); err != nil {
		t.Fatal(err)
	}
	err = p.materializeRoadmapSuccessor(context.Background(), protected)
	if err == nil || !strings.Contains(err.Error(), "ROADMAP_OPERATOR_REQUIRED: LIVE-PROMOTION") {
		t.Fatalf("unexpected protected-boundary result: %v", err)
	}
	var count int
	if err = p.Store.DB.QueryRow("SELECT count(*) FROM queue_items WHERE id=?", protected.ID).Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count != 0 {
		t.Fatalf("protected stage queued: %d", count)
	}
}

func TestRoadmapSuccessorPostBTVSourceHygieneRecoveryRemainsScoped(t *testing.T) {
	if retryable("SOURCE_HYGIENE_FAILED") || retryPolicyFailureRetryable("SOURCE_HYGIENE_FAILED") {
		t.Fatal("global source-hygiene policy must remain hard-blocked")
	}
	p, w := setup(t)
	testAuthority(p)
	sourceQueue(t, p, w, successorPostBTVParent)
	if err := p.AutonomyTick(context.Background()); err != nil {
		t.Fatal(err)
	}
	if got := wait(t, p, successorPostBTVParent); got.State != "ACCEPTED" {
		t.Fatalf("fixture parent not accepted: %+v", got)
	}
	if _, err := p.Store.DB.Exec("UPDATE work_orders SET state='BLOCKED',reason='SOURCE_HYGIENE_FAILED' WHERE id=?", successorPostBTVParent); err != nil {
		t.Fatal(err)
	}
	if _, err := p.Store.DB.Exec("UPDATE queue_items SET state='FAILED',reason='SOURCE_HYGIENE_FAILED' WHERE id=?", successorPostBTVParent); err != nil {
		t.Fatal(err)
	}
	c, err := loadRoadmapSuccessorCatalog()
	if err != nil {
		t.Fatal(err)
	}
	recovered, err := p.recoverRoadmapSourceHygieneLocked(context.Background(), c)
	if err != nil {
		t.Fatal(err)
	}
	if !recovered {
		t.Fatal("catalog-scoped source-hygiene recovery did not run")
	}
	var qs, js string
	if err := p.Store.DB.QueryRow("SELECT state FROM queue_items WHERE id=?", successorPostBTVParent).Scan(&qs); err != nil {
		t.Fatal(err)
	}
	if err := p.Store.DB.QueryRow("SELECT state FROM work_orders WHERE id=?", successorPostBTVParent).Scan(&js); err != nil {
		t.Fatal(err)
	}
	if qs != "QUEUED" || js != "DRAFT" {
		t.Fatalf("recovery states queue=%s job=%s", qs, js)
	}
}

func TestRoadmapSuccessorPostBTVExactParentExport(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)
	sourceQueue(t, p, w, successorPostBTVParent)
	if err := p.AutonomyTick(context.Background()); err != nil {
		t.Fatal(err)
	}
	if got := wait(t, p, successorPostBTVParent); got.State != "ACCEPTED" {
		t.Fatalf("parent not accepted: %+v", got)
	}
	if err := p.AutonomyTick(context.Background()); err != nil {
		t.Fatal(err)
	}
	c, err := loadRoadmapSuccessorCatalog()
	if err != nil {
		t.Fatal(err)
	}
	if err = p.materializeRoadmapSuccessor(context.Background(), c.Entries[0]); err != nil {
		t.Fatal(err)
	}
	var raw []byte
	if err = p.Store.DB.QueryRow("SELECT raw FROM queue_items WHERE id=?", successorPostBTVChild).Scan(&raw); err != nil {
		t.Fatal(err)
	}
	var q QueueOrder
	if err = json.Unmarshal(raw, &q); err != nil {
		t.Fatal(err)
	}
	order, err := ParseOrder([]byte(q.WorkOrderYAML))
	if err != nil {
		t.Fatal(err)
	}
	manifestRaw, err := os.ReadFile(filepath.Join(p.Root, "exports", successorPostBTVParent, "1", "candidate.json"))
	if err != nil {
		t.Fatal(err)
	}
	var manifest localCandidateExport
	if err = json.Unmarshal(manifestRaw, &manifest); err != nil {
		t.Fatal(err)
	}
	if order.Baseline.SHA != manifest.CandidateSHA || manifest.Published || manifest.AcceptedRefMutated {
		t.Fatalf("candidate binding mismatch child=%s export=%+v", order.Baseline.SHA, manifest)
	}
}
