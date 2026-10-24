package plane

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"sync"
	"testing"
	"time"
)

// Test child modes exercise the same supervisor used by the built executable.
func TestMain(m *testing.M) {
	if runArchiveFixture() {
		os.Exit(0)
	}
	if len(os.Args) == 2 && os.Args[1] == "__plane-host" {
		os.Exit(HostMain())
	}
	if len(os.Args) > 1 && os.Args[1] == "-c" {
		input, _ := io.ReadAll(os.Stdin)
		if !bytes.Contains(input, []byte("WORK ORDER:")) {
			os.Exit(3)
		}
		if e := os.WriteFile("demo.txt", []byte("candidate produced by subprocess fixture\n"), 0600); e != nil {
			os.Exit(4)
		}
		fmt.Fprintln(os.Stdout, `{"type":"turn.completed"}`)
		os.Exit(0)
	}
	if len(os.Args) > 1 && os.Args[1] == "__fixture-process" {
		switch os.Args[2] {
		case "exit":
			os.Exit(7)
		case "spawn":
			exe, _ := os.Executable()
			child := exec.Command(exe, "__fixture-process", "sleep")
			child.Stdout = os.Stdout
			child.Stderr = os.Stderr
			if e := child.Start(); e != nil {
				os.Exit(4)
			}
			fmt.Fprintf(os.Stdout, "CHILD=%d\n", child.Process.Pid)
			time.Sleep(30 * time.Second)
		case "sleep":
			fmt.Fprintln(os.Stdout, "READY")
			time.Sleep(30 * time.Second)
		case "echo":
			io.Copy(os.Stdout, os.Stdin)
		case "flood":
			for i := 0; i < 17000; i++ {
				os.Stdout.Write(bytes.Repeat([]byte("x"), 1024))
			}
		}
		os.Exit(0)
	}
	os.Exit(m.Run())
}
func TestSupervisedProcessExitAndCapture(t *testing.T) {
	exe, _ := os.Executable()
	var out, errout bytes.Buffer
	r := SupervisedRunner{}
	e := r.Run(context.Background(), ProcessSpec{Program: exe, Args: []string{"__fixture-process", "echo"}, Input: "captured", Env: minimalEnv()}, &out, &errout)
	if e != nil || out.String() != "captured" {
		t.Fatal(e, out.String(), errout.String())
	}
	e = r.Run(context.Background(), ProcessSpec{Program: exe, Args: []string{"__fixture-process", "exit"}, Env: minimalEnv()}, io.Discard, io.Discard)
	if exitCode(e) != 7 {
		t.Fatal(e)
	}
}
func TestSupervisedCancellation(t *testing.T) {
	exe, _ := os.Executable()
	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()
	start := time.Now()
	e := (SupervisedRunner{}).Run(ctx, ProcessSpec{Program: exe, Args: []string{"__fixture-process", "sleep"}, Env: minimalEnv()}, io.Discard, io.Discard)
	if !errors.Is(e, context.DeadlineExceeded) || time.Since(start) > 5*time.Second {
		t.Fatal(e)
	}
}
func TestOutputLimitTerminatesHost(t *testing.T) {
	exe, _ := os.Executable()
	e := (SupervisedRunner{}).Run(context.Background(), ProcessSpec{Program: exe, Args: []string{"__fixture-process", "flood"}, Env: minimalEnv()}, io.Discard, io.Discard)
	if e == nil || !strings.Contains(e.Error(), "PROCESS_OUTPUT_LIMIT") {
		t.Fatal(e)
	}
}

type recordingRunner struct {
	spec ProcessSpec
	err  error
}

func (r *recordingRunner) Run(_ context.Context, s ProcessSpec, out, errout io.Writer) error {
	r.spec = s
	return r.err
}
func TestCodexAdapterBuildsBoundedInvocation(t *testing.T) {
	_, w := setup(t)
	r := &recordingRunner{}
	a := CodexAdapter{Tool: "codex.exe", Home: "dedicated-home", Runner: r, Feedback: "TestExample failed"}
	if e := a.Run(context.Background(), t.TempDir(), w, io.Discard, io.Discard); e != nil {
		t.Fatal(e)
	}
	args := strings.Join(r.spec.Args, " ")
	for _, s := range []string{"exec", "workspace-write", "approval_policy=\"never\"", "network_access=false", "windows.sandbox=\"unelevated\"", "--ephemeral"} {
		if !strings.Contains(args, s) {
			t.Fatal(args)
		}
	}
	if strings.Contains(args, "bypass") || strings.Contains(args, "danger-full-access") {
		t.Fatal(args)
	}
	if !strings.Contains(r.spec.Input, w.ID) || !strings.Contains(r.spec.Input, "TestExample failed") {
		t.Fatal("missing authority/feedback")
	}
}
func TestAuthorizationContractDetectsConfigChange(t *testing.T) {
	p, w := setup(t)
	b, _ := os.ReadFile(filepath.Join(p.Root, "workorder.yaml"))
	if e := p.Store.Load(b); e != nil {
		t.Fatal(e)
	}
	if e := p.Authorize(w.ID); e != nil {
		t.Fatal(e)
	}
	r := p.Config.Repos[w.Repo]
	r.Mode = "engineering"
	p.Config.Repos[w.Repo] = r
	if p.verifyContract(w) == nil {
		t.Fatal("changed authority accepted")
	}
}
func TestRecoveryNeverReclaimsLiveSupervisor(t *testing.T) {
	p, _ := setup(t)
	p.Store.DB.Exec("INSERT INTO process_records(work_order_id,attempt,pid,finished) VALUES('x',1,?,0)", os.Getpid())
	if p.recoverInterrupted() == nil {
		t.Fatal("live supervisor reclaimed")
	}
}
func TestRecoveryInterruptedAttempt(t *testing.T) {
	p, w := setup(t)
	load(t, p, w)
	p.Store.Lease(w.ID, "fake", 3)
	if e := p.recoverInterrupted(); e != nil {
		t.Fatal(e)
	}
	j, _ := p.Store.Get(w.ID)
	if j.State != "REJECTED_RETRYABLE" {
		t.Fatal(j)
	}
	var n int
	p.Store.DB.QueryRow("SELECT count(*) FROM worker_leases").Scan(&n)
	if n != 0 {
		t.Fatal("lease retained")
	}
}
func TestControllerLockExclusivity(t *testing.T) {
	p, _ := setup(t)
	lock, e := p.controllerLock()
	if e != nil {
		t.Fatal(e)
	}
	if other, e := p.controllerLock(); e == nil {
		other.Close()
		t.Fatal("duplicate controller")
	}
	lock.Close()
	other, e := p.controllerLock()
	if e != nil {
		t.Fatal(e)
	}
	other.Close()
}
func TestFrozenTreeRejectsMutation(t *testing.T) {
	p, w := setup(t)
	load(t, p, w)
	if e := p.Dispatch(w.ID); e != nil {
		t.Fatal(e)
	}
	j := wait(t, p, w.ID)
	if j.State != "ACCEPTED" {
		t.Fatal(j)
	}
	dir := filepath.Join(p.Root, "acceptance", j.ID, "1")
	before, e := treeInventory(dir)
	if e != nil {
		t.Fatal(e)
	}
	os.WriteFile(filepath.Join(dir, "extra.txt"), []byte("mutated"), 0600)
	after, e := treeInventory(dir)
	if e != nil || sameInventory(before, after) {
		t.Fatal("new file not detected")
	}
}
func TestHTMLIDDataBinding(t *testing.T) {
	before, e := htmlContract([]byte(`<div id="a" data-state="ok"></div><div id="b"></div>`))
	if e != nil {
		t.Fatal(e)
	}
	after, _ := htmlContract([]byte(`<div id="a"></div><div id="b" data-state="ok"></div>`))
	if before["data:div:a:data-state=ok"] != 1 || after["data:div:a:data-state=ok"] != 0 {
		t.Fatal("data owner was not bound")
	}
}

func TestCodexAdapterRealSubprocessFixture(t *testing.T) {
	_, w := setup(t)
	dir := t.TempDir()
	exe, _ := os.Executable()
	a := CodexAdapter{Tool: exe, Home: t.TempDir(), Runner: SupervisedRunner{}}
	var out, errout bytes.Buffer
	if e := a.Run(context.Background(), dir, w, &out, &errout); e != nil {
		t.Fatal(e, errout.String())
	}
	b, e := os.ReadFile(filepath.Join(dir, "demo.txt"))
	if e != nil || !bytes.Contains(b, []byte("subprocess fixture")) || !strings.Contains(out.String(), "turn.completed") {
		t.Fatal("subprocess fixture failed")
	}
}

func TestAcceptanceMutationOverridesRetryableFailure(t *testing.T) {
	p, w := setup(t)
	repo := p.Config.Repos[w.Repo].LocalPath
	test := `package demo
import("os";"testing")
func TestDemoCandidate(t *testing.T){os.WriteFile("unexpected.txt",[]byte("mutation"),0600);t.Fatal("deliberate test failure")}
`
	if e := os.WriteFile(filepath.Join(repo, "demo_test.go"), []byte(test), 0600); e != nil {
		t.Fatal(e)
	}
	for _, args := range [][]string{{"add", "."}, {"-c", "user.name=Test", "-c", "user.email=test@localhost", "commit", "-m", "mutating fixture"}, {"branch", "-f", "accepted/demo", "HEAD"}} {
		if _, e := git("git", repo, args...); e != nil {
			t.Fatal(e)
		}
	}
	w.Baseline.SHA, _ = git("git", repo, "rev-parse", "HEAD")
	load(t, p, w)
	if e := p.Dispatch(w.ID); e != nil {
		t.Fatal(e)
	}
	j := wait(t, p, w.ID)
	if j.State != "BLOCKED" || j.Reason != "ACCEPTANCE_INPUT_MUTATED" {
		b, _ := os.ReadFile(filepath.Join(j.Evidence, "go-focused-0.jsonl"))
		t.Log(string(b))
		t.Fatal(j)
	}
}
func TestEvidenceAnchorDetectsRewrittenManifest(t *testing.T) {
	p, w := setup(t)
	load(t, p, w)
	p.Dispatch(w.ID)
	j := wait(t, p, w.ID)
	if j.State != "ACCEPTED" {
		t.Fatal(j)
	}
	if e := p.VerifyEvidence(j); e != nil {
		t.Fatal(e)
	}
	os.WriteFile(filepath.Join(j.Evidence, "worker_stdout.log"), []byte("changed"), 0600)
	m, _ := Manifest(j.Evidence)
	writeJSON(filepath.Join(j.Evidence, "evidence_manifest.json"), m)
	if e := p.VerifyEvidence(j); e == nil || e.Error() != "EVIDENCE_ANCHOR_MISMATCH" {
		t.Fatal(e)
	}
}

type childCapture struct {
	mu   sync.Mutex
	b    strings.Builder
	pid  chan int
	once sync.Once
}

func (w *childCapture) Write(b []byte) (int, error) {
	w.mu.Lock()
	defer w.mu.Unlock()
	w.b.Write(b)
	for _, line := range strings.Split(w.b.String(), "\n") {
		if strings.HasPrefix(line, "CHILD=") {
			if pid, e := strconv.Atoi(strings.TrimPrefix(line, "CHILD=")); e == nil {
				w.once.Do(func() { w.pid <- pid })
			}
		}
	}
	return len(b), nil
}
func TestWindowsJobKillsDescendants(t *testing.T) {
	if runtime.GOOS != "windows" {
		t.Skip("native Windows Job Object qualification")
	}
	exe, _ := os.Executable()
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	capture := &childCapture{pid: make(chan int, 1)}
	done := make(chan error, 1)
	go func() {
		done <- (SupervisedRunner{}).Run(ctx, ProcessSpec{Program: exe, Args: []string{"__fixture-process", "spawn"}, Env: minimalEnv()}, capture, io.Discard)
	}()
	var pid int
	select {
	case pid = <-capture.pid:
	case <-time.After(15 * time.Second):
		t.Fatal("descendant did not start")
	}
	cancel()
	select {
	case <-done:
	case <-time.After(5 * time.Second):
		t.Fatal("supervisor did not stop")
	}
	deadline := time.Now().Add(5 * time.Second)
	for processAlive(pid) && time.Now().Before(deadline) {
		time.Sleep(20 * time.Millisecond)
	}
	if processAlive(pid) {
		t.Fatal("descendant outlived cancelled supervisor")
	}
}
