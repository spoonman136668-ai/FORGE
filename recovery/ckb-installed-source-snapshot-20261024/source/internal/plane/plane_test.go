package plane

import (
	"context"
	"encoding/json"
	"gopkg.in/yaml.v3"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
)

func setup(t *testing.T) (*Engine, WorkOrder) {
	t.Helper()
	root := filepath.Join(t.TempDir(), "plane")
	if e := DemoInit(root); e != nil {
		t.Fatal(e)
	}
	c, e := LoadConfig(filepath.Join(root, "config/local.yaml"))
	if e != nil {
		t.Fatal(e)
	}
	p, e := NewEngine(c, root)
	if e != nil {
		t.Fatal(e)
	}
	t.Cleanup(func() {
		p.mu.Lock()
		for _, cancel := range p.cancels {
			cancel()
		}
		p.mu.Unlock()
		deadline := time.Now().Add(5 * time.Second)
		for time.Now().Before(deadline) {
			p.mu.Lock()
			n := len(p.cancels)
			p.mu.Unlock()
			if n == 0 {
				break
			}
			time.Sleep(10 * time.Millisecond)
		}
		p.Store.DB.Close()
	})
	b, e := os.ReadFile(filepath.Join(root, "workorder.yaml"))
	if e != nil {
		t.Fatal(e)
	}
	w, e := ParseOrder(b)
	if e != nil {
		t.Fatal(e)
	}
	return p, w
}
func load(t *testing.T, p *Engine, w WorkOrder) {
	t.Helper()
	b, e := yaml.Marshal(w)
	if e != nil {
		t.Fatal(e)
	}
	if e = p.Store.Load(b); e != nil {
		t.Fatal(e)
	}
	if e = p.Store.Authorize(w.ID); e != nil {
		t.Fatal(e)
	}
	if e = p.Ready(w.ID); e != nil {
		t.Fatal(e)
	}
}
func wait(t *testing.T, p *Engine, id string) Job {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	j, e := p.Wait(ctx, id)
	if e != nil {
		_ = p.Cancel(id)
		t.Fatalf("attempt wait: %v; state=%s reason=%q workspace=%q evidence=%q", e, j.State, j.Reason, j.Workspace, j.Evidence)
	}
	for {
		p.mu.Lock()
		n := len(p.cancels)
		p.mu.Unlock()
		if n == 0 {
			break
		}
		select {
		case <-ctx.Done():
			t.Fatal(ctx.Err())
		case <-time.After(10 * time.Millisecond):
		}
	}
	return j
}
func TestWorkOrderParsingValidation(t *testing.T) {
	_, w := setup(t)
	b, _ := yaml.Marshal(w)
	if _, e := ParseOrder(append(b, []byte("\nunknown: true\n")...)); e == nil {
		t.Fatal("unknown field accepted")
	}
	if _, e := ParseOrder(append(b, []byte("\n---\nid: other\n")...)); e == nil {
		t.Fatal("extra document accepted")
	}
	w.Baseline.SHA = "short"
	if w.Validate() == nil {
		t.Fatal("bad SHA accepted")
	}
}
func TestScopeMatching(t *testing.T) {
	w := WorkOrder{}
	w.Scope.Allowed = []string{"pkg/web/**", "pkg/*stage_br*_test.go", "**/*"}
	w.Scope.Forbidden = []string{"**/*private*"}
	for _, p := range []string{"pkg/web/app.css", "pkg/example_stage_br_test.go"} {
		if !w.Allows(p) {
			t.Fatal(p)
		}
	}
	for _, p := range []string{"../escape", "C:/escape", "pkg/risk.go", "pkg/COINBASE.go", "pkg/accounting.go", "pkg/web/private.css", ".git/config"} {
		if w.Allows(p) {
			t.Fatal("forbidden allowed:", p)
		}
	}
}
func TestStateTransitions(t *testing.T) {
	for _, pair := range [][2]string{{"DRAFT", "AUTHORIZED"}, {"AUTHORIZED", "READY"}, {"READY", "DISPATCHED"}, {"DISPATCHED", "ENGINEERING"}, {"ENGINEERING", "CANDIDATE"}, {"CANDIDATE", "ACCEPTING"}, {"ACCEPTING", "ACCEPTED"}} {
		if !transition(pair[0], pair[1]) {
			t.Fatal(pair)
		}
	}
	if transition("DRAFT", "ACCEPTED") || transition("ACCEPTED", "READY") {
		t.Fatal("illegal transition")
	}
}
func TestLeaseExclusivity(t *testing.T) {
	p, w := setup(t)
	load(t, p, w)
	var wg sync.WaitGroup
	var mu sync.Mutex
	success := 0
	for i := 0; i < 8; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			if _, e := p.Store.Lease(w.ID, "fake", 3); e == nil {
				mu.Lock()
				success++
				mu.Unlock()
			}
		}()
	}
	wg.Wait()
	if success != 1 {
		t.Fatalf("%d leases", success)
	}
}
func TestFakeWorkerAcceptancePass(t *testing.T) {
	p, w := setup(t)
	load(t, p, w)
	if e := p.Dispatch(w.ID); e != nil {
		t.Fatal(e)
	}
	j := wait(t, p, w.ID)
	if j.State != "ACCEPTED" {
		t.Fatalf("%s: %s", j.State, j.Reason)
	}
	if e := VerifyManifest(j.Evidence); e != nil {
		t.Fatal(e)
	}
	b, e := os.ReadFile(filepath.Join(p.Config.Repos[w.Repo].LocalPath, "demo.txt"))
	if e != nil || string(b) != "baseline\n" {
		t.Fatal("source repository modified")
	}
	checks, e := p.Checks(w.ID)
	if e != nil || len(checks) < 8 {
		t.Fatal("missing checks")
	}
}
func TestFakeWorkerFailureAndRetryLimit(t *testing.T) {
	p, w := setup(t)
	p.Config.Policy.MaxAttempts = 2
	p.workers["fake"] = FakeWorker{Fail: true}
	load(t, p, w)
	if e := p.Dispatch(w.ID); e != nil {
		t.Fatal(e)
	}
	j := wait(t, p, w.ID)
	if j.State != "REJECTED_RETRYABLE" {
		t.Fatal(j)
	}
	if e := p.Retry(w.ID); e != nil {
		t.Fatal(e)
	}
	j = wait(t, p, w.ID)
	if j.State != "BLOCKED" || !strings.Contains(j.Reason, "RETRY_LIMIT_REACHED") {
		t.Fatal(j)
	}
	if e := p.Retry(w.ID); e == nil {
		t.Fatal("retry beyond limit")
	}
}
func TestAcceptanceFailsOnMissingFocusedTest(t *testing.T) {
	p, w := setup(t)
	w.RequiredTests.FocusedGo = []string{"^TestMissing$"}
	load(t, p, w)
	if e := p.Dispatch(w.ID); e != nil {
		t.Fatal(e)
	}
	j := wait(t, p, w.ID)
	if j.State != "REJECTED_RETRYABLE" || j.Reason != "FOCUSED_TEST_FAILED" {
		t.Fatal(j)
	}
}
func TestBaselineMismatch(t *testing.T) {
	p, w := setup(t)
	w.Baseline.SHA = strings.Repeat("a", 40)
	b, _ := yaml.Marshal(w)
	if e := p.Store.Load(b); e != nil {
		t.Fatal(e)
	}
	p.Store.Authorize(w.ID)
	if e := p.Ready(w.ID); e == nil || e.Error() != "BASELINE_MISMATCH" {
		t.Fatal(e)
	}
	j, _ := p.Store.Get(w.ID)
	if j.State != "BLOCKED" {
		t.Fatal(j)
	}
}

type modifyingWorker struct{ kind string }

func (modifyingWorker) Name() string { return "fake" }
func (w modifyingWorker) Run(ctx context.Context, dir string, o WorkOrder, out, errout io.Writer) error {
	if e := (FakeWorker{}).Run(ctx, dir, o, out, errout); e != nil {
		return e
	}
	switch w.kind {
	case "forbidden":
		return os.WriteFile(filepath.Join(dir, "outside.txt"), []byte("out of scope"), 0600)
	case "refs":
		_, e := git("git", dir, "tag", "accepted/tampered")
		return e
	}
	return nil
}
func TestForbiddenFileAndAcceptedRefDetection(t *testing.T) {
	for _, kind := range []string{"forbidden", "refs"} {
		t.Run(kind, func(t *testing.T) {
			p, w := setup(t)
			p.workers["fake"] = modifyingWorker{kind}
			load(t, p, w)
			if e := p.Dispatch(w.ID); e != nil {
				t.Fatal(e)
			}
			j := wait(t, p, w.ID)
			want := "FORBIDDEN_PATH_MODIFIED"
			if kind == "refs" {
				want = "ACCEPTED_REF_MUTATION_DETECTED"
			}
			if j.State != "BLOCKED" || j.Reason != want {
				t.Fatal(j)
			}
		})
	}
}
func TestManifestTampering(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "test"), []byte("a"), 0600)
	m, e := Manifest(dir)
	if e != nil {
		t.Fatal(e)
	}
	writeJSON(filepath.Join(dir, "evidence_manifest.json"), m)
	if e = VerifyManifest(dir); e != nil {
		t.Fatal(e)
	}
	os.WriteFile(filepath.Join(dir, "test"), []byte("b"), 0600)
	if VerifyManifest(dir) == nil {
		t.Fatal("tampering accepted")
	}
}
func TestEventsAndChat(t *testing.T) {
	p, w := setup(t)
	load(t, p, w)
	events, e := p.Store.Events(0)
	if e != nil || len(events) != 3 {
		t.Fatal(events, e)
	}
	for _, text := range []string{"why idle", "dispatch DEMO", "show evidence for DEMO", "pause dispatch"} {
		if _, e = p.ParseChat(text); e != nil {
			t.Fatal(e)
		}
	}
	for _, text := range []string{"powershell calc", "dispatch DEMO;whoami", "authorize absent"} {
		if _, e = p.ParseChat(text); e == nil {
			t.Fatal("invalid command accepted")
		}
	}
}
func TestAPIAuthenticationAndOrigin(t *testing.T) {
	p, _ := setup(t)
	handler := p.Handler("test-token")
	for _, v := range []struct {
		token, origin, host string
		want                int
	}{{"", "", "127.0.0.1:8791", 401}, {"test-token", "http://evil.test", "127.0.0.1:8791", 403}, {"test-token", "", "evil.test", 403}, {"test-token", "", "127.0.0.1:8791", 200}} {
		req := httptest.NewRequest("GET", "http://"+v.host+"/api/state", nil)
		req.Header.Set("Authorization", "Bearer "+v.token)
		req.Header.Set("Origin", v.origin)
		rr := httptest.NewRecorder()
		handler.ServeHTTP(rr, req)
		if rr.Code != v.want {
			t.Fatalf("%d != %d", rr.Code, v.want)
		}
	}
}
func TestHTTPStateAndSSE(t *testing.T) {
	p, w := setup(t)
	load(t, p, w)
	server := httptest.NewServer(p.Handler("test"))
	defer server.Close()
	req, _ := http.NewRequest("GET", server.URL+"/api/state", nil)
	req.Header.Set("Authorization", "Bearer test")
	res, e := http.DefaultClient.Do(req)
	if e != nil {
		t.Fatal(e)
	}
	var state map[string]any
	e = json.NewDecoder(res.Body).Decode(&state)
	res.Body.Close()
	if e != nil || state["why"] == nil {
		t.Fatal(state, e)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	req, _ = http.NewRequestWithContext(ctx, "GET", server.URL+"/api/events", nil)
	req.Header.Set("Authorization", "Bearer test")
	res, e = http.DefaultClient.Do(req)
	if e != nil {
		t.Fatal(e)
	}
	defer res.Body.Close()
	buf := make([]byte, 4096)
	n, e := res.Body.Read(buf)
	if e != nil || !strings.Contains(string(buf[:n]), "data:") {
		t.Fatal("SSE missing", e)
	}
}
