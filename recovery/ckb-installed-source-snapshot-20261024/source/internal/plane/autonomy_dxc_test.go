package plane

import (
	"strings"
	"testing"
)

func TestDXCBrowserHarnessStripsPublicAssetsAlias(t *testing.T) {
	b, err := browserHarness.ReadFile("harness/browser.cjs")
	if err != nil {
		t.Fatal(err)
	}
	s := string(b)

	if !strings.Contains(s, "requestPath.startsWith('assets/')?requestPath.slice('assets/'.length):requestPath") {
		t.Fatal("browser harness does not translate the public /assets/ URL alias to UI.Root")
	}
	if !strings.Contains(s, "if(!file.startsWith(root+path.sep)){await route.abort();return;}") {
		t.Fatal("browser harness lost root-containment guard")
	}
	if !strings.Contains(s, "fs.lstatSync(file)") || !strings.Contains(s, "st.isSymbolicLink()") {
		t.Fatal("browser harness lost regular-file/symlink guard")
	}
}
