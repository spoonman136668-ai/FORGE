package plane

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func writeDQUIFile(t *testing.T, root, rel, body string) {
	t.Helper()
	path := filepath.Join(root, filepath.FromSlash(rel))
	if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(body), 0600); err != nil {
		t.Fatal(err)
	}
}

func dqUIWorkOrder() WorkOrder {
	var w WorkOrder
	w.ID = "DQ_UI_ACCEPTANCE_SCOPE"
	w.Repo = "ckb"
	w.Scope.Allowed = []string{"pkg/web/app.js", "pkg/web/strategy.html", "pkg/web/app.css"}
	w.Acceptance.ProtectRefs = true
	w.Acceptance.Clean = true
	w.Preserve = []string{"custom chart and candle behavior", "JavaScript behavior"}
	w.UI.Root = "pkg/web"
	w.UI.Pages = []UIPage{{Path: "strategy.html", CriticalIDs: []string{"marketQuality", "priceCanvas"}, ChartID: "priceCanvas"}}
	w.UI.Markers = map[string][]string{
		"custom chart and candle behavior": {"priceCanvas"},
		"JavaScript behavior":              {"updateMarketDataQuality"},
	}
	return w
}

func failedDQUIChecks(checks []Check) []Check {
	var failed []Check
	for _, c := range checks {
		if !c.Pass {
			failed = append(failed, c)
		}
	}
	return failed
}

func TestDQUIAcceptanceAllowsExplicitlyScopedJavaScriptChange(t *testing.T) {
	p, _ := setup(t)
	base := filepath.Join(t.TempDir(), "base")
	after := filepath.Join(t.TempDir(), "after")
	page := `<html><body><div id="marketQuality" data-state="unknown"></div><canvas id="priceCanvas" data-layer="price"></canvas><script defer src="/assets/app.js?v=stage"></script></body></html>`
	writeDQUIFile(t, base, "pkg/web/strategy.html", page)
	writeDQUIFile(t, after, "pkg/web/strategy.html", page)
	writeDQUIFile(t, base, "pkg/web/app.js", `function updateMarketDataQuality(){ return "priceCanvas"; }`)
	writeDQUIFile(t, after, "pkg/web/app.js", `function updateMarketDataQuality(){ return "priceCanvas"; }
function updateUnifiedFreshnessCompleteness(){ return "presentation-only"; }`)

	w := dqUIWorkOrder()
	checks := p.uiChecks(Job{Order: w, Workspace: after}, base)
	if failed := failedDQUIChecks(checks); len(failed) != 0 {
		t.Fatalf("explicitly scoped JavaScript change should preserve UI contract: %+v", failed)
	}
}

func TestDQUIAcceptanceRejectsUnscopedJavaScriptChange(t *testing.T) {
	p, _ := setup(t)
	base := filepath.Join(t.TempDir(), "base")
	after := filepath.Join(t.TempDir(), "after")
	page := `<html><body><div id="marketQuality" data-state="unknown"></div><canvas id="priceCanvas" data-layer="price"></canvas><script defer src="/assets/app.js?v=stage"></script></body></html>`
	writeDQUIFile(t, base, "pkg/web/strategy.html", page)
	writeDQUIFile(t, after, "pkg/web/strategy.html", page)
	writeDQUIFile(t, base, "pkg/web/app.js", `function updateMarketDataQuality(){ return "priceCanvas"; }`)
	writeDQUIFile(t, after, "pkg/web/app.js", `function updateMarketDataQuality(){ return "priceCanvas"; }
function updateUnifiedFreshnessCompleteness(){ return "presentation-only"; }`)

	w := dqUIWorkOrder()
	w.Scope.Allowed = []string{"pkg/web/strategy.html", "pkg/web/app.css"}
	checks := p.uiChecks(Job{Order: w, Workspace: after}, base)
	for _, c := range checks {
		if c.Name == "UI_BEHAVIOR_PARITY" && strings.Contains(c.Detail, "app.js") && !c.Pass {
			return
		}
	}
	t.Fatalf("expected unscoped JavaScript change to fail UI_BEHAVIOR_PARITY: %+v", checks)
}
