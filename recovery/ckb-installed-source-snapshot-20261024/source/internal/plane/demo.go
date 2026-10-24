package plane

import (
	"fmt"
	"gopkg.in/yaml.v3"
	"os"
	"path/filepath"
)

func DemoInit(dir string) error {
	root, e := filepath.Abs(dir)
	if e != nil {
		return e
	}
	if _, e = os.Stat(root); !os.IsNotExist(e) {
		return fmt.Errorf("demo directory must not already exist")
	}
	repo := filepath.Join(root, "fixture")
	if e = os.MkdirAll(repo, 0700); e != nil {
		return e
	}
	for n, b := range map[string]string{"go.mod": "module plane-demo\n\ngo 1.25.5\n", "demo.txt": "baseline\n", "demo_test.go": "package demo\nimport (\"os\";\"strings\";\"testing\")\nfunc TestDemoCandidate(t *testing.T){ b,e:=os.ReadFile(\"demo.txt\");if e!=nil||!strings.Contains(string(b),\"candidate produced\"){t.Fatal(\"candidate missing\")} }\n"} {
		if e = os.WriteFile(filepath.Join(repo, n), []byte(b), 0600); e != nil {
			return e
		}
	}
	for _, a := range [][]string{{"init"}, {"add", "."}, {"-c", "user.name=Plane Demo", "-c", "user.email=plane-demo@localhost", "commit", "-m", "Demo baseline"}, {"branch", "accepted/demo"}} {
		if _, e = git("git", repo, a...); e != nil {
			return e
		}
	}
	sha, e := git("git", repo, "rev-parse", "HEAD")
	if e != nil {
		return e
	}
	w := WorkOrder{ID: "DEMO", Title: "Deterministic fake-worker demonstration", Repo: "demo"}
	w.Baseline.Ref = "accepted/demo"
	w.Baseline.SHA = sha
	w.Worker.Branch = "codex/demo"
	w.Worker.Preferred = "fake"
	w.Scope.Allowed = []string{"demo.txt"}
	w.Acceptance.ProtectRefs = true
	w.Acceptance.Clean = true
	w.RequiredTests.FocusedGo = []string{"^TestDemoCandidate$"}
	c := Config{Repos: map[string]Repo{"demo": {LocalPath: repo, Mode: "demo"}}}
	c.Server.Bind = "127.0.0.1"
	c.Server.Port = 8791
	c.State.SQLitePath = "state/ckb-plane.db"
	c.Tools.Git = "git"
	c.Tools.Go = "go"
	c.Tools.Codex = "codex"
	c.Tools.Powershell = "powershell.exe"
	c.Policy.MaxAttempts = 3
	if e = os.MkdirAll(filepath.Join(root, "config"), 0700); e != nil {
		return e
	}
	for n, v := range map[string]any{"config/local.yaml": c, "workorder.yaml": w} {
		b, e := yaml.Marshal(v)
		if e != nil {
			return e
		}
		if e = os.WriteFile(filepath.Join(root, n), b, 0600); e != nil {
			return e
		}
	}
	fmt.Println("Demo fixture created:", root)
	fmt.Println("Next: init, serve, load workorder.yaml, authorize DEMO, dispatch DEMO using --config", filepath.Join(root, "config", "local.yaml"))
	return nil
}
