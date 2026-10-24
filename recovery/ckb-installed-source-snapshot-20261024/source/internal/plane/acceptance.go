package plane

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"runtime"
	"strings"
	"time"
)

func (p *Engine) Accept(id string) error {
	p.mu.Lock()
	if _, ok := p.cancels[id]; ok {
		p.mu.Unlock()
		return errors.New("ATTEMPT_STILL_OWNED")
	}
	ctx, cancel := context.WithTimeout(context.Background(), p.attemptTimeout())
	p.cancels[id] = cancel
	p.mu.Unlock()
	defer func() { cancel(); p.mu.Lock(); delete(p.cancels, id); p.mu.Unlock() }()
	return p.acceptContext(ctx, id)
}
func (p *Engine) acceptContext(ctx context.Context, id string) error {
	if e := p.Store.Move(id, "ACCEPTING", "Running deterministic gates"); e != nil {
		return e
	}
	j, e := p.Store.Get(id)
	if e != nil {
		return e
	}
	checks := []Check{}
	authority := "demo"
	if p.Config.Repos[j.Order.Repo].Mode != "demo" {
		authority = "windows-source"
	}
	failed := ""
	add := func(name string, pass bool, detail string) {
		checks = append(checks, Check{name, pass, detail})
		if !pass && (failed == "" || retryable(failed) && !retryable(name)) {
			failed = name
		}
	}
	if p.Config.Autonomy.Enabled {
		err := p.sourceAuthority(ctx)
		detail := "Recorded plane authority and repository lease verified"
		if err != nil {
			detail = err.Error()
		}
		add("PLANE_AUTHORITY_LOST", err == nil, detail)
	}
	if e = p.verifyContract(j.Order); e != nil {
		add("AUTHORIZATION_CONTRACT_CHANGED", false, e.Error())
	}
	var before RepoState
	b, e := os.ReadFile(filepath.Join(j.Evidence, "repo_state_before.json"))
	if e == nil {
		e = json.Unmarshal(b, &before)
	}
	if e != nil {
		add("EVIDENCE_READ_FAILED", false, "Missing pre-attempt evidence")
	} else {
		r := p.Config.Repos[j.Order.Repo]
		e = baseline(p.Config.Tools.Git, r.LocalPath, j.Order)
		add("BASELINE_MISMATCH", e == nil, "Exact authoritative baseline SHA")
		_, e = git(p.Config.Tools.Git, j.Workspace, "merge-base", "--is-ancestor", j.Order.Baseline.SHA, "HEAD")
		add("BRANCH_ANCESTRY_INVALID", e == nil, "Candidate descends from pinned baseline")
		branch, be := git(p.Config.Tools.Git, j.Workspace, "symbolic-ref", "--short", "HEAD")
		add("WORKER_BRANCH_CHANGED", be == nil && branch == j.Order.Worker.Branch, "Exact worker branch")
		sr, se := refs(p.Config.Tools.Git, r.LocalPath)
		ar, ae := refs(p.Config.Tools.Git, j.Workspace)
		add("ACCEPTED_REF_MUTATION_DETECTED", se == nil && ae == nil && sr == before.SourceRefs && ar == before.AttemptRefs, "Source and private accepted refs unchanged")
	}
	for _, name := range j.Order.RequiredPaths {
		add("REQUIRED_FILE_MISSING", regularPath(j.Workspace, name) == nil, name)
	}
	files, e := changed(p.Config.Tools.Git, j.Workspace, j.Order.Baseline.SHA)
	add("CANDIDATE_READ_FAILED", e == nil, "Complete tracked and untracked inventory")
	add("NO_DIFF_PRODUCED", len(files) > 0, "Candidate must change source")
	for _, f := range files {
		add("FORBIDDEN_PATH_MODIFIED", j.Order.Allows(f), f)
	}
	_, e = git(p.Config.Tools.Git, j.Workspace, "diff", "--check", j.Order.Baseline.SHA, "--")
	add("SOURCE_HYGIENE_FAILED", e == nil, "Git whitespace/conflict check")
	for _, f := range files {
		info, err := os.Lstat(filepath.Join(j.Workspace, filepath.FromSlash(f)))
		if os.IsNotExist(err) {
			continue
		}
		good := err == nil && info.Mode().IsRegular()
		if good {
			data, er := os.ReadFile(filepath.Join(j.Workspace, filepath.FromSlash(f)))
			good = er == nil && !bytes.Contains(data, []byte("<<<<<<< ")) && !bytes.ContainsRune(data, 0)
		}
		add("SOURCE_HYGIENE_FAILED", good, f+": regular text file without merge markers")
	}

	if p.Config.Repos[j.Order.Repo].Mode != "demo" {
		add("WINDOWS_AUTHORITY_REQUIRED", runtime.GOOS == "windows" && runtime.GOARCH == "amd64" && runtime.Version() == "go1.25.5", "Requires Go 1.25.5 windows/amd64")
	}
	testJob := j
	var frozen map[string]string
	uiBaseline := ""
	if failed == "" {
		dir, inv, err := p.freeze(ctx, j)
		detail := "Fresh baseline plus hash-verified candidate overlay"
		if err != nil {
			detail = err.Error()
		}
		add("CANDIDATE_FREEZE_FAILED", err == nil, detail)
		if err == nil {
			testJob.Workspace = dir
			frozen = inv
		}
	}
	if failed == "" && (len(j.Order.Preserve) > 0 || j.Order.Acceptance.Browser) {
		base := filepath.Join(p.Root, "acceptance", j.ID, fmt.Sprintf("%d-baseline", j.Attempt))
		uiBaseline = base
		err := os.Mkdir(base, 0700)
		if err == nil {
			err = p.exportBaseline(ctx, p.Config.Repos[j.Order.Repo].LocalPath, j.Order.Baseline.SHA, base)
		}
		add("UI_BASELINE_EXPORT", err == nil, "Independent baseline for UI preservation")
		if err == nil {
			for _, c := range p.uiChecks(testJob, base) {
				add(c.Name, c.Pass, c.Detail)
			}
		}
	}
	if failed == "" && p.Config.Autonomy.Enabled {
		pass, detail := p.powershellCheck(ctx, testJob, files)
		add("POWERSHELL_ACCEPTANCE_FAILED", pass, detail)
	}
	if failed == "" {
		for i, pattern := range j.Order.RequiredTests.FocusedGo {
			pass, detail := p.goTest(ctx, testJob, pattern, false, i)
			add("FOCUSED_TEST_FAILED", pass, detail)
		}
		if j.Order.Acceptance.All {
			pass, detail := p.goTest(ctx, testJob, "", true, 0)
			add(goAcceptanceCheckName(pass, detail), pass, detail)
		}
	}
	if failed == "" && j.Order.Acceptance.Browser {
		cs, er := p.browserCheckWithBaseline(ctx, testJob, uiBaseline)
		for _, c := range cs {
			add(c.Name, c.Pass, c.Detail)
		}
		code := "PLAYWRIGHT_FAILED"
		if er != nil && strings.HasPrefix(er.Error(), "PLAYWRIGHT_UNAVAILABLE") {
			code = "PLAYWRIGHT_UNAVAILABLE"
		}
		detail := "Static source browser checks at 1024 and 1440"
		if er != nil {
			detail = er.Error()
		}
		add(code, er == nil, detail)
	}
	if frozen != nil {
		after, er := treeInventory(testJob.Workspace)
		add("ACCEPTANCE_INPUT_MUTATED", er == nil && sameInventory(frozen, after), "Full acceptance input tree is unchanged after tests")
	}
	if er := ctx.Err(); er != nil {
		add("ACCEPTANCE_CANCELLED", false, er.Error())
	}
	sourceRefs, sre := refs(p.Config.Tools.Git, p.Config.Repos[j.Order.Repo].LocalPath)
	attemptRefs, are := refs(p.Config.Tools.Git, j.Workspace)
	add("ACCEPTED_REF_MUTATION_DETECTED", sre == nil && are == nil && sourceRefs == before.SourceRefs && attemptRefs == before.AttemptRefs, "Accepted refs rechecked after acceptance")

	if failed == "" && p.Config.Autonomy.Enabled {
		err := p.sourceAuthority(ctx)
		detail := "Authority rechecked before sealing candidate"
		if err != nil {
			detail = err.Error()
		}
		add("PLANE_AUTHORITY_LOST", err == nil, detail)
	}

	state, reason := "ACCEPTED", "All required deterministic gates passed ("+authority+")"
	if failed != "" {
		state = "BLOCKED"
		reason = failed
		retryDecision := p.retryDecisionNow(id, j.Attempt, failed)
		if retryDecision.FailureRetryable && retryDecision.MayRetry {
			state = "REJECTED_RETRYABLE"
		}
		if retryDecision.HardStop && retryDecision.FailureRetryable && !retryDecision.ExternalHandoff {
			reason = "RETRY_LIMIT_REACHED: " + failed
		}
	}
	if e = writeJSON(filepath.Join(j.Evidence, "acceptance_checks.json"), checks); e != nil {
		return p.Store.Move(id, "BLOCKED", "EVIDENCE_WRITE_FAILED")
	}
	if e = writeJSON(filepath.Join(j.Evidence, "acceptance_result.json"), map[string]any{"state": state, "reason": reason, "authority": authority, "attempt": j.Attempt}); e != nil {
		return p.Store.Move(id, "BLOCKED", "EVIDENCE_WRITE_FAILED")
	}
	tx, e := p.Store.DB.Begin()
	if e != nil {
		return e
	}
	defer tx.Rollback()
	res, e := tx.Exec("INSERT INTO acceptance_runs(work_order_id,attempt,result,created) VALUES(?,?,?,?)", id, j.Attempt, "SEALING", now())
	if e != nil {
		return e
	}
	rid, e := res.LastInsertId()
	if e != nil {
		return e
	}
	for _, c := range checks {
		if _, e = tx.Exec("INSERT INTO acceptance_checks(run_id,name,pass,detail) VALUES(?,?,?,?)", rid, c.Name, c.Pass, c.Detail); e != nil {
			return e
		}
	}
	if e = tx.Commit(); e != nil {
		return e
	}
	// Seal all candidate evidence before publishing a terminal state. The final state
	// transition is recorded in SQLite after the immutable evidence snapshot.
	j.State = state
	j.Reason = reason
	if e = p.Seal(j); e != nil {
		return p.Store.Move(id, "BLOCKED", "EVIDENCE_HASH_FAILED")
	}
	txFinal, e := p.Store.DB.Begin()
	if e != nil {
		return e
	}
	defer txFinal.Rollback()
	r, e := txFinal.Exec("UPDATE work_orders SET state=?,reason=? WHERE id=? AND attempt=? AND state='ACCEPTING'", state, reason, id, j.Attempt)
	if e != nil {
		return e
	}
	n, _ := r.RowsAffected()
	if n != 1 {
		return errors.New("ACCEPTANCE_OWNERSHIP_LOST")
	}
	if _, e = txFinal.Exec("UPDATE acceptance_runs SET result=? WHERE id=?", state, rid); e != nil {
		return e
	}
	if e = event(txFinal, id, j.Attempt, state, reason); e != nil {
		return e
	}
	return txFinal.Commit()
}
func (p *Engine) goTest(parent context.Context, j Job, pattern string, all bool, index int) (bool, string) {
	ctx, cancel := context.WithTimeout(parent, goAcceptanceSupervisorTimeout(all))
	defer cancel()
	packages := j.Order.RequiredTests.Packages
	if len(packages) == 0 {
		packages = []string{"./..."}
	}
	args := append([]string{"test"}, packages...)
	args = append(args, "-json", "-count=1", goAcceptanceTimeoutArg(all))
	if !all {
		args = append(args, "-run", pattern)
	}
	name := fmt.Sprintf("go-focused-%d.jsonl", index)
	if all {
		name = "go-all.jsonl"
	}
	env := append(minimalEnv(), "GOFLAGS=-buildvcs=false", "GOENV=off", "GOWORK=off", "GOTOOLCHAIN=local", "GOPROXY=off", "GOSUMDB=off")
	var err error
	var out []byte
	var stderrOut []byte
	if p.Config.Repos[j.Order.Repo].Mode == "demo" {
		cmd := exec.CommandContext(ctx, p.Config.Tools.Go, args...)
		cmd.Dir = j.Workspace
		cmd.Env = env
		cmd.WaitDelay = 3 * time.Second
		out, err = cmd.CombinedOutput()
	} else {
		var scratch string
		env, scratch, err = acceptanceEnv()
		if err != nil {
			return false, "GO_ENVIRONMENT_FAILED: " + err.Error()
		}
		defer os.RemoveAll(scratch)

		tool := filepath.Clean(p.Config.Tools.Go)
		if info, e := os.Stat(tool); e != nil || !info.Mode().IsRegular() {
			return false, "GO_EXECUTABLE_UNAVAILABLE: " + tool
		}

		// Probe the pinned native tool independently. The actual acceptance command
		// remains supervised and uses the configured sandbox for autonomy jobs.
		probeCtx, probeCancel := context.WithTimeout(ctx, 20*time.Second)
		probeCmd := exec.CommandContext(probeCtx, tool, "version")
		probeCmd.Dir = j.Workspace
		probeCmd.Env = env
		probeCmd.WaitDelay = 3 * time.Second
		version, probeErr := probeCmd.CombinedOutput()
		probeCancel()
		probeFile := name + ".launch.json"
		probe := map[string]any{"program": tool, "directory": j.Workspace, "version": strings.TrimSpace(string(version)), "output": string(version)}
		if probeErr != nil {
			probe["error"] = probeErr.Error()
		}
		if e := writeJSON(filepath.Join(j.Evidence, probeFile), probe); e != nil {
			return false, "Evidence write failed"
		}
		if probeErr != nil {
			return false, "GO_NATIVE_LAUNCH_FAILED: see " + probeFile
		}
		if strings.TrimSpace(string(version)) != "go version go1.25.5 windows/amd64" {
			return false, "WINDOWS_TOOLCHAIN_MISMATCH: see " + probeFile
		}

		var stdout, stderr bytes.Buffer
		runner := p.supervisedRunnerFor(j)
		// The deterministic sandbox adds filesystem/network restrictions; the
		// supervisor separately owns descendants and caps their output.
		program := tool
		commandArgs := args
		if p.Config.Autonomy.Enabled {
			program = p.Config.Tools.Codex
			commandArgs = p.sandboxArgs(acceptanceSandboxArgs(tool, scratch, args))
			env = replaceEnv(env, map[string]string{"CODEX_HOME": p.Config.Execution.CodexHome})
		}
		err = runner.Run(ctx, ProcessSpec{Program: program, Args: commandArgs, Dir: j.Workspace, Env: env}, &stdout, &stderr)
		out = stdout.Bytes()
		stderrOut = append([]byte(nil), stderr.Bytes()...)
		if e := os.WriteFile(filepath.Join(j.Evidence, name+".stderr.log"), stderr.Bytes(), 0600); e != nil {
			return false, "EVIDENCE_WRITE_FAILED"
		}
	}
	if e := os.WriteFile(filepath.Join(j.Evidence, name), out, 0600); e != nil {
		return false, "Evidence write failed"
	}
	if err != nil {
		code := classifyGoAcceptanceExecutionFailure(ctx.Err(), err, out, stderrOut)
		return false, fmt.Sprintf("%s: Go test failed: %v; see %s and sandbox launch/stderr evidence", code, err, name)
	}
	re := regexp.MustCompile(".*")
	if !all {
		re = regexp.MustCompile(pattern)
	}
	passes := 0
	scanner := bufio.NewScanner(bytes.NewReader(out))
	scanner.Buffer(make([]byte, 4096), 1<<20)
	for scanner.Scan() {
		var v struct{ Action, Test string }
		if json.Unmarshal(scanner.Bytes(), &v) == nil && v.Action == "pass" && v.Test != "" && re.MatchString(v.Test) {
			passes++
		}
	}
	if scanner.Err() != nil {
		return false, "Test JSON read failed"
	}
	return passes > 0, fmt.Sprintf("%d matching tests passed; %s", passes, name)
}
func (p *Engine) Checks(id string) ([]Check, error) {
	rows, e := p.Store.DB.Query("SELECT name,pass,detail FROM acceptance_checks WHERE run_id=(SELECT max(id) FROM acceptance_runs WHERE work_order_id=?) ORDER BY id", id)
	if e != nil {
		return nil, e
	}
	defer rows.Close()
	out := []Check{}
	for rows.Next() {
		var c Check
		if e = rows.Scan(&c.Name, &c.Pass, &c.Detail); e != nil {
			return nil, e
		}
		out = append(out, c)
	}
	return out, rows.Err()
}
