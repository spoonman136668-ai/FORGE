package plane

import (
	"strings"
	"testing"
)

func TestBrowserHarnessUsesProductionAssetRoutingAndPinnedBaseline(t *testing.T) {
	script, err := browserHarness.ReadFile("harness/browser.cjs")
	if err != nil {
		t.Fatal(err)
	}
	text := string(script)
	for _, marker := range []string{
		"baselineRoot",
		"cfg.baselineRoot?",
		"if(base)",
		"requestPath.startsWith('assets/')",
		"requestPath.slice('assets/'.length)",
		"!b.ok||c.ok",
		"BROWSER_SCRIPT_ERRORS",
		"BROWSER_HORIZONTAL_OVERFLOW",
	} {
		if !strings.Contains(text, marker) {
			t.Fatalf("browser harness missing %q", marker)
		}
	}
}
