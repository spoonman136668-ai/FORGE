package plane

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestDXPlaywrightProcessEnvBindsModuleAndBrowserRoots(t *testing.T) {
	root := filepath.Join("tool-root", "ckb-ci-tools")
	env := playwrightProcessEnv(root)
	got := strings.Join(env, "\n")
	wantNodeParts := []string{
		filepath.Join(root, "playwright", "node_modules"),
		filepath.Join(root, "node_modules"),
		root,
	}
	var nodePath, browsers string
	for _, entry := range env {
		if strings.HasPrefix(entry, "NODE_PATH=") {
			nodePath = strings.TrimPrefix(entry, "NODE_PATH=")
		}
		if strings.HasPrefix(entry, "PLAYWRIGHT_BROWSERS_PATH=") {
			browsers = strings.TrimPrefix(entry, "PLAYWRIGHT_BROWSERS_PATH=")
		}
	}
	if nodePath == "" || browsers == "" {
		t.Fatalf("missing Playwright process environment: %s", got)
	}
	parts := strings.Split(nodePath, string(os.PathListSeparator))
	for _, want := range wantNodeParts {
		found := false
		for _, part := range parts {
			if filepath.Clean(part) == filepath.Clean(want) {
				found = true
				break
			}
		}
		if !found {
			t.Fatalf("NODE_PATH missing %q: %q", want, nodePath)
		}
	}
	if filepath.Clean(browsers) != filepath.Clean(filepath.Join(root, "playwright-browsers")) {
		t.Fatalf("unexpected browser root: %q", browsers)
	}
}
