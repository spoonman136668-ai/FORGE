package plane

import (
	"context"
	"database/sql"
	"errors"
	"io"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
)

func recoveryCandidateTestPreflight(t *testing.T, p *Engine, w WorkOrder) recoveryCandidatePreflight {
	t.Helper()
	recoveryID := strings.Repeat("a", 64)
	planID := strings.Repeat("b", 64)
	raw, err := os.ReadFile(filepath.Join(p.Root, "workorder.yaml"))
	if err != nil {
		t.Fatal(err)
	}
	repo, ok := p.Config.Repos[w.Repo]
	if !ok {
		t.Fatal("fixture repo missing")
	}
	return recoveryCandidatePreflight{
		Transaction: BlockerRecoveryTransaction{
			RecoveryID:  recoveryID,
			WorkOrderID: w.ID,
		},
		Plan: RecoveryPlan{
			PlanID:     planID,
			RecoveryID: recoveryID,
		},
		Order:      w,
		OrderYAML:  raw,
		SourceRepo: repo,
	}
}

func recoveryAuthoritativeCounts(t *testing.T, db *sql.DB) (work, leases, queue int) {
	t.Helper()
	for query, dst := range map[string]*int{
		"SELECT count(*) FROM work_orders":   &work,
		"SELECT count(*) FROM worker_leases": &leases,
		"SELECT count(*) FROM queue_items":    &queue,
	} {
		if err := db.QueryRow(query).Scan(dst); err != nil {
			t.Fatal(err)
		}
	}
	return
}

type recoveryFixtureWorker struct {
	kind  string
	calls int
	mu    sync.Mutex
}

func (w *recoveryFixtureWorker) Name() string { return "fake" }

func (w *recoveryFixtureWorker) Run(ctx context.Context, dir string, order WorkOrder, out, errout io.Writer) error {
	w.mu.Lock()
	w.calls++
	w.mu.Unlock()
	switch w.kind {
	case "fail":
		return errors.New("fixture worker failure")
	case "forbidden":
		return os.WriteFile(filepath.Join(dir, "outside.txt"), []byte("forbidden\n"), 0600)
	case "ref":
		_, err := git("git", dir, "tag", "accepted/recovery-fixture")
		return err
	case "nodiff":
		return nil
	default:
		return os.WriteFile(filepath.Join(dir, "demo.txt"), []byte("recovery candidate\n"), 0600)
	}
}

func (w *recoveryFixtureWorker) Calls() int {
	w.mu.Lock()
	defer w.mu.Unlock()
	return w.calls
}

func TestRecoveryCandidateStoreDefaultOffAndBudgetAreSeparate(t *testing.T) {
	p, w := setup(t)
	pre := recoveryCandidateTestPreflight(t, p, w)

	if _, err := p.prepareRecoveryCandidateWithWorker(
		context.Background(),
		RecoveryRepairConfig{},
		pre,
		&recoveryFixtureWorker{},
	); !errors.Is(err, errRecoveryRepairDisabled) {
		t.Fatal(err)
	}
	var tables int
	if err := p.Store.DB.QueryRow(
		"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='blocker_recovery_candidates'",
	).Scan(&tables); err != nil || tables != 0 {
		t.Fatal(tables, err)
	}

	beforeWork, beforeLeases, beforeQueue := recoveryAuthoritativeCounts(t, p.Store.DB)
	if err := initBlockerRecoveryCandidateStore(p.Store.DB); err != nil {
		t.Fatal(err)
	}
	cfg := RecoveryRepairConfig{Enabled: true, MaxRepairAttempts: 2, TimeoutSeconds: 30}
	for attempt := 1; attempt <= 2; attempt++ {
		claim, err := claimRecoveryCandidate(
			p.Store.DB,
			pre.Transaction.RecoveryID,
			pre.Plan.PlanID,
			filepath.Join(p.Root, "workspaces", "r", pre.Transaction.RecoveryID),
			filepath.Join(p.Root, "evidence", "recovery", pre.Transaction.RecoveryID),
			cfg.MaxRepairAttempts,
		)
		if err != nil {
			t.Fatal(err)
		}
		if claim.RepairAttempt != attempt {
			t.Fatalf("attempt=%d want=%d", claim.RepairAttempt, attempt)
		}
		claim.Status = "WORKER_FAILED"
		if _, err = finishRecoveryCandidate(p.Store.DB, claim); err != nil {
			t.Fatal(err)
		}
	}
	if _, err := claimRecoveryCandidate(
		p.Store.DB,
		pre.Transaction.RecoveryID,
		pre.Plan.PlanID,
		filepath.Join(p.Root, "workspaces", "r", pre.Transaction.RecoveryID),
		filepath.Join(p.Root, "evidence", "recovery", pre.Transaction.RecoveryID),
		cfg.MaxRepairAttempts,
	); err == nil || err.Error() != "RECOVERY_REPAIR_BUDGET_EXHAUSTED" {
		t.Fatal(err)
	}
	afterWork, afterLeases, afterQueue := recoveryAuthoritativeCounts(t, p.Store.DB)
	if beforeWork != afterWork || beforeLeases != afterLeases || beforeQueue != afterQueue {
		t.Fatalf("recovery budget mutated authoritative execution tables: before=%d/%d/%d after=%d/%d/%d",
			beforeWork, beforeLeases, beforeQueue, afterWork, afterLeases, afterQueue)
	}
}

func TestRecoveryCandidateClaimIsExclusive(t *testing.T) {
	p, w := setup(t)
	pre := recoveryCandidateTestPreflight(t, p, w)
	if err := initBlockerRecoveryCandidateStore(p.Store.DB); err != nil {
		t.Fatal(err)
	}

	var wg sync.WaitGroup
	var mu sync.Mutex
	success := 0
	owned := 0
	for i := 0; i < 8; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			_, err := claimRecoveryCandidate(
				p.Store.DB,
				pre.Transaction.RecoveryID,
				pre.Plan.PlanID,
				filepath.Join(p.Root, "workspaces", "r", pre.Transaction.RecoveryID),
				filepath.Join(p.Root, "evidence", "recovery", pre.Transaction.RecoveryID),
				3,
			)
			mu.Lock()
			defer mu.Unlock()
			if err == nil {
				success++
			} else if err.Error() == "RECOVERY_REPAIR_ALREADY_OWNED" {
				owned++
			}
		}()
	}
	wg.Wait()
	if success != 1 || owned != 7 {
		t.Fatalf("success=%d owned=%d", success, owned)
	}
}

func TestRecoveryCandidateTerminalStateCannotGrantAuthority(t *testing.T) {
	p, w := setup(t)
	pre := recoveryCandidateTestPreflight(t, p, w)
	if err := initBlockerRecoveryCandidateStore(p.Store.DB); err != nil {
		t.Fatal(err)
	}
	claim, err := claimRecoveryCandidate(
		p.Store.DB,
		pre.Transaction.RecoveryID,
		pre.Plan.PlanID,
		filepath.Join(p.Root, "workspaces", "r", pre.Transaction.RecoveryID),
		filepath.Join(p.Root, "evidence", "recovery", pre.Transaction.RecoveryID),
		1,
	)
	if err != nil {
		t.Fatal(err)
	}
	claim.Status = "CANDIDATE_PREPARED"
	claim.ProductionAccepted = true
	if _, err = finishRecoveryCandidate(p.Store.DB, claim); err == nil || err.Error() != "RECOVERY_CANDIDATE_AUTHORITY_INVALID" {
		t.Fatal(err)
	}
	claim.ProductionAccepted = false
	claim.ResumeAuthorized = true
	if _, err = finishRecoveryCandidate(p.Store.DB, claim); err == nil || err.Error() != "RECOVERY_CANDIDATE_AUTHORITY_INVALID" {
		t.Fatal(err)
	}
}
