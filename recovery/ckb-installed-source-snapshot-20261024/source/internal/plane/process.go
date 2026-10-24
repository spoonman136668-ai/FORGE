package plane

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strings"
	"sync"
	"time"
)

// ProcessSpec is created by trusted engine code, never decoded from HTTP input.
type ProcessSpec struct {
	Program string
	Args    []string
	Dir     string
	Input   string
	Env     []string
}
type ProcessRunner interface {
	Run(context.Context, ProcessSpec, io.Writer, io.Writer) error
}
type SupervisedRunner struct {
	OnStart        func(int) error
	OnFinish       func(int)
	HostExecutable string   // qualification seam; empty preserves production self-host behavior.
	HostEnv        []string // optional sanitized host environment; nil preserves existing behavior.
}
type ProcessError struct {
	Code int
	Err  error
}

func (e *ProcessError) Error() string { return fmt.Sprintf("process exit %d: %v", e.Code, e.Err) }
func (e *ProcessError) Unwrap() error { return e.Err }
func exitCode(e error) int {
	var p *ProcessError
	if errors.As(e, &p) {
		return p.Code
	}
	if e != nil {
		return -1
	}
	return 0
}

// A pipe ties the host lifetime to its owning engine. The Windows host joins a
// kill-on-close Job Object BEFORE creating the executable or any descendants.
func (runner SupervisedRunner) Run(ctx context.Context, s ProcessSpec, out, stderr io.Writer) error {
	exe := runner.HostExecutable
	if exe == "" {
		var e error
		exe, e = os.Executable()
		if e != nil {
			return e
		}
	}
	read, write, e := os.Pipe()
	if e != nil {
		return e
	}
	defer read.Close()
	defer write.Close()
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()
	budget := &outputBudget{left: 16 << 20, cancel: cancel}
	cmd := exec.CommandContext(ctx, exe, "__plane-host")
	if runner.HostEnv != nil {
		cmd.Env = append([]string(nil), runner.HostEnv...)
	}
	cmd.Stdin = read
	cmd.Stdout = cappedOutput{budget, out}
	cmd.Stderr = cappedOutput{budget, stderr}
	cmd.WaitDelay = 3 * time.Second
	configureHost(cmd)
	if e = cmd.Start(); e != nil {
		return e
	}
	read.Close()
	if runner.OnStart != nil {
		if e = runner.OnStart(cmd.Process.Pid); e != nil {
			_ = cmd.Cancel()
			_ = cmd.Wait()
			return e
		}
	}
	if runner.OnFinish != nil {
		defer runner.OnFinish(cmd.Process.Pid)
	}
	if e = json.NewEncoder(write).Encode(s); e != nil {
		_ = cmd.Cancel()
		_ = cmd.Wait()
		return e
	}
	e = cmd.Wait()
	if budget.exceeded {
		return &ProcessError{Code: -1, Err: errors.New("PROCESS_OUTPUT_LIMIT")}
	}
	if ctx.Err() != nil {
		return &ProcessError{Code: -1, Err: ctx.Err()}
	}
	if e != nil {
		code := -1
		if cmd.ProcessState != nil {
			code = cmd.ProcessState.ExitCode()
		}
		return &ProcessError{Code: code, Err: e}
	}
	return nil
}

// HostMain is an internal local child entrypoint, with its descriptor arriving
// through an anonymous pipe. It is not part of the structured API/CLI surface.
func HostMain() int {
	if e := containHost(); e != nil {
		fmt.Fprintln(os.Stderr, "PROCESS_CONTAINMENT_FAILED")
		return 125
	}
	d := json.NewDecoder(io.LimitReader(os.Stdin, 2<<20))
	var s ProcessSpec
	if e := d.Decode(&s); e != nil {
		return 125
	}
	// EOF means the owning engine died. Windows closes the host's job handle on exit.
	go func() { var b [1]byte; _, _ = os.Stdin.Read(b[:]); os.Exit(125) }()
	cmd := exec.Command(s.Program, s.Args...)
	cmd.Dir = s.Dir
	cmd.Env = s.Env
	cmd.Stdin = strings.NewReader(s.Input)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if e := cmd.Run(); e != nil {
		if cmd.ProcessState != nil {
			return cmd.ProcessState.ExitCode()
		}
		fmt.Fprintln(os.Stderr, "PROCESS_START_FAILED")
		return 126
	}
	return 0
}
func minimalEnv() []string {
	// Credentials and connection strings are not copied out of the parent environment.
	names := []string{"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "HOME", "LANG"}
	env := []string{}
	for _, n := range names {
		if v, ok := os.LookupEnv(n); ok {
			env = append(env, n+"="+v)
		}
	}
	return env
}
func policyArgs() []string {
	return []string{"-c", `approval_policy="never"`, "-c", `sandbox_mode="workspace-write"`, "-c", "sandbox_workspace_write.network_access=false", "-c", `windows.sandbox="unelevated"`}
}

type outputBudget struct {
	mu       sync.Mutex
	left     int
	cancel   context.CancelFunc
	exceeded bool
}
type cappedOutput struct {
	budget *outputBudget
	dest   io.Writer
}

func (w cappedOutput) Write(b []byte) (int, error) {
	w.budget.mu.Lock()
	defer w.budget.mu.Unlock()
	if len(b) > w.budget.left {
		w.budget.exceeded = true
		w.budget.cancel()
		return 0, errors.New("PROCESS_OUTPUT_LIMIT")
	}
	n, e := w.dest.Write(b)
	w.budget.left -= n
	return n, e
}
