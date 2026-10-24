package plane

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestAcceptanceNativeGoLaunchAndIsolation(t *testing.T) {
	realGo := realGoForAcceptanceTest(t)

	for _, tc := range []struct {
		name string
		tool string
		want string
		pass bool
	}{
		{"pass", realGo, "1 matching", true},
		{"version", buildFakeGoForAcceptanceTest(t, realGo, "version-mismatch"), "WINDOWS_TOOLCHAIN_MISMATCH", false},
		{"launch", buildFakeGoForAcceptanceTest(t, realGo, "launch-fail"), "GO_NATIVE_LAUNCH_FAILED", false},
	} {
		t.Run(tc.name, func(t *testing.T) {
			root := t.TempDir()
			writeNativeAcceptanceFixture(t, root)

			p := &Engine{}
			p.Config.Tools.Go = tc.tool
			p.Config.Repos = map[string]Repo{"toy": {Mode: "source"}}

			j := Job{Workspace: root, Evidence: root}
			j.Order.Repo = "toy"
			j.Order.RequiredTests.Packages = []string{"./..."}

			pass, detail := p.goTest(context.Background(), j, "^TestToy$", false, 0)
			if pass != tc.pass || !strings.Contains(detail, tc.want) {
				t.Fatalf("pass=%v detail=%q, want pass=%v and detail containing %q", pass, detail, tc.pass, tc.want)
			}

			launch := filepath.Join(root, "go-focused-0.jsonl.launch.json")
			b, err := os.ReadFile(launch)
			if err != nil {
				t.Fatal(err)
			}
			var launchDiag struct {
				Program   string `json:"program"`
				Directory string `json:"directory"`
			}
			if err := json.Unmarshal(b, &launchDiag); err != nil {
				t.Fatalf("launch diagnostic is not valid JSON: %v\n%s", err, b)
			}
			if !strings.EqualFold(filepath.Clean(launchDiag.Program), filepath.Clean(tc.tool)) {
				t.Fatalf("launch diagnostic program=%q, want %q; raw=%s", launchDiag.Program, tc.tool, b)
			}
			if !strings.EqualFold(filepath.Clean(launchDiag.Directory), filepath.Clean(root)) {
				t.Fatalf("launch diagnostic directory=%q, want %q; raw=%s", launchDiag.Directory, root, b)
			}

			if tc.name == "pass" {
				out, err := os.ReadFile(filepath.Join(root, "go-focused-0.jsonl"))
				if err != nil {
					t.Fatal(err)
				}
				if !strings.Contains(string(out), "TestToy") {
					t.Fatalf("test output missing TestToy: %s", out)
				}
			}
		})
	}
}

func TestAcceptanceCacheFreshAndEnvironmentDeduplicated(t *testing.T) {
	_, a, e := acceptanceEnv()
	if e != nil {
		t.Fatal(e)
	}
	defer os.RemoveAll(a)
	_, b, e := acceptanceEnv()
	if e != nil {
		t.Fatal(e)
	}
	defer os.RemoveAll(b)
	if a == b {
		t.Fatal("shared cache")
	}
	env := replaceEnv([]string{"Temp=old", "TEMP=duplicate", "PATH=keep"}, map[string]string{"TEMP": "new"})
	if strings.Join(env, ";") != "PATH=keep;TEMP=new" {
		t.Fatal(env)
	}
}

func writeNativeAcceptanceFixture(t *testing.T, root string) {
	t.Helper()
	writeTestFile(t, filepath.Join(root, "go.mod"), "module ckb-plane-native-acceptance-fixture\n\ngo 1.25.5\n")
	writeTestFile(t, filepath.Join(root, "toy_test.go"), `package toy

import "testing"

func TestToy(t *testing.T) {}
`)
}

func buildFakeGoForAcceptanceTest(t *testing.T, realGo, mode string) string {
	t.Helper()
	root := t.TempDir()
	src := filepath.Join(root, "fakego")
	if err := os.MkdirAll(src, 0700); err != nil {
		t.Fatal(err)
	}
	writeTestFile(t, filepath.Join(src, "go.mod"), "module fakego\n\ngo 1.25.5\n")

	versionBody := `fmt.Println("go version go1.25.4 windows/amd64")`
	if mode == "launch-fail" {
		versionBody = `fmt.Fprintln(os.Stderr, "native launch failed"); os.Exit(1)`
	}
	writeTestFile(t, filepath.Join(src, "main.go"), fmt.Sprintf(`package main

import (
	"fmt"
	"os"
)

func main() {
	if len(os.Args) > 1 && os.Args[1] == "version" {
		%s
		return
	}
	fmt.Println("{\"Action\":\"pass\",\"Test\":\"TestToy\"}")
}
`, versionBody))

	exe := filepath.Join(root, "fake-go"+exeSuffix())
	cache := filepath.Join(root, "cache")
	tmp := filepath.Join(root, "tmp")
	if err := os.Mkdir(cache, 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.Mkdir(tmp, 0700); err != nil {
		t.Fatal(err)
	}
	cmd := exec.Command(realGo, "build", "-o", exe, ".")
	cmd.Dir = src
	cmd.Env = replaceEnv(os.Environ(), map[string]string{
		"GOFLAGS":  "-buildvcs=false",
		"GOCACHE":  cache,
		"GOTMPDIR": tmp,
		"TEMP":     tmp,
		"TMP":      tmp,
	})
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("build fake go: %v\n%s", err, out)
	}
	return exe
}

func realGoForAcceptanceTest(t *testing.T) string {
	t.Helper()
	candidates := []string{}
	if v := os.Getenv("CKB_PLANE_TEST_GO"); v != "" {
		candidates = append(candidates, v)
	}
	if p, err := exec.LookPath("go"); err == nil {
		candidates = append(candidates, p)
	}
	if goroot := runtime.GOROOT(); goroot != "" {
		candidates = append(candidates, filepath.Join(goroot, "bin", "go"+exeSuffix()))
	}

	seen := map[string]bool{}
	for _, c := range candidates {
		c = filepath.Clean(c)
		if c == "." || seen[strings.ToLower(c)] {
			continue
		}
		seen[strings.ToLower(c)] = true
		if info, err := os.Stat(c); err != nil || !info.Mode().IsRegular() {
			continue
		}
		out, err := exec.Command(c, "version").CombinedOutput()
		if err == nil && strings.TrimSpace(string(out)) == "go version go1.25.5 windows/amd64" {
			return c
		}
	}
	t.Skipf("no exact go1.25.5 windows/amd64 tool found among %v", candidates)
	return ""
}

func exeSuffix() string {
	if runtime.GOOS == "windows" {
		return ".exe"
	}
	return ""
}

func writeTestFile(t *testing.T, path, content string) {
	t.Helper()
	if err := os.WriteFile(path, []byte(content), 0600); err != nil {
		t.Fatal(err)
	}
}
