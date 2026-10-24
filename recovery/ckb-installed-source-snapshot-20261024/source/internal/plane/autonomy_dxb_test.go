package plane

import (
	"strings"
	"testing"
)

func TestDXBChartCriticalVisibilityUsesViewportIntersection(t *testing.T) {
	b, err := browserHarness.ReadFile("harness/browser.cjs")
	if err != nil {
		t.Fatal(err)
	}
	s := string(b)

	for _, marker := range []string{
		"const state=async(page,id,width,chart)=>",
		"if(chart)",
		"state(cand.page,id,width,id===spec.ChartID)",
		"box.x<width&&box.x+box.width>0&&box.y<900&&box.y+box.height>0",
		"box.x>=0&&box.y>=0&&box.x+box.width<=width&&box.y+box.height<=900",
		"state(cand.page,spec.ChartID,width,true)",
		"BROWSER_CHART_CANVAS",
	} {
		if !strings.Contains(s, marker) {
			t.Fatalf("browser harness missing chart-visibility semantic marker %q", marker)
		}
	}
	if !strings.Contains(s, "check('BROWSER_CHART_CANVAS',!b.ok||c.ok") &&
		!strings.Contains(s, "check('BROWSER_CHART_CANVAS',c.ok") {
		t.Fatal("independent chart-canvas geometry gate missing")
	}
}
