package plane

import (
	"path/filepath"
	"strings"
	"testing"
)

func TestBrowserAcceptanceDirectSupervisionProcessSpec(t *testing.T) {
	node := filepath.Join("C:", "Program Files", "nodejs", "node.exe")
	workspace := filepath.Join("C:", "work", "candidate")
	script := "process.stdout.write('ok')"
	input := "{\"root\":\"x\"}"
	env := []string{"NODE_PATH=x", "PLAYWRIGHT_BROWSERS_PATH=y"}

	spec := browserAcceptanceProcessSpec(node, workspace, script, input, env)
	if spec.Program != filepath.Clean(node) {
		t.Fatalf("program=%q want=%q", spec.Program, filepath.Clean(node))
	}
	if spec.Dir != workspace || spec.Input != input {
		t.Fatalf("unexpected dir/input: %#v", spec)
	}
	if len(spec.Args) != 2 || spec.Args[0] != "-e" || spec.Args[1] != script {
		t.Fatalf("browser harness args changed: %#v", spec.Args)
	}
	joined := strings.ToLower(spec.Program + " " + strings.Join(spec.Args, " "))
	if strings.Contains(joined, "codex") || strings.Contains(joined, "sandbox") {
		t.Fatalf("browser acceptance must not re-enter the Codex Windows sandbox: %s", joined)
	}
	if len(spec.Env) != len(env) {
		t.Fatalf("environment changed: %#v", spec.Env)
	}
	spec.Env[0] = "MUTATED=1"
	if env[0] != "NODE_PATH=x" {
		t.Fatal("process spec must own a copy of the environment slice")
	}
}

func TestBrowserAcceptanceHarnessRetainsStaticNetworkFenceAndChromiumSandbox(t *testing.T) {
	raw, err := browserHarness.ReadFile("harness/browser.cjs")
	if err != nil {
		t.Fatal(err)
	}
	s := string(raw)
	for _, want := range []string{
		"chromiumSandbox:true",
		"serviceWorkers:'block'",
		"ctx.route('**/*'",
		"u.hostname!=='ckb-plane.test'",
		"ctx.routeWebSocket('**/*'",
		"ws=>ws.close()",
	} {
		if !strings.Contains(s, want) {
			t.Fatalf("browser harness safety contract missing %q", want)
		}
	}
}
