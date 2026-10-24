package plane

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"
)

func (p *Engine) blockerRecoveryShadowTick(ctx context.Context, items []QueueItem) bool {
	mode := blockerResolverMode(p)
	if mode != blockerResolverModeShadow && mode != blockerResolverModeActive {
		return false
	}
	for _, item := range items {
		if item.State != "FAILED" && item.State != "BLOCKED" {
			continue
		}
		j, err := p.Store.Get(item.ID)
		if err != nil || j.State != "BLOCKED" || j.Attempt < 1 {
			continue
		}
		if err = p.advanceBlockerRecoveryShadow(ctx, item.ID); err != nil {
			_ = p.setSetting(blockerResolverStatusSetting, "SHADOW_ERROR: "+item.ID+": "+errorText(err))
			return false
		}
		run, runErr := blockerRecoveryShadowRunForWorkOrder(p.Store.DB, item.ID)
		if runErr == nil {
			if mode == blockerResolverModeActive && run.Phase == recoveryActiveRetryQueued {
				return true
			}
			if shadowTerminal(run.Phase) {
				return false
			}
		}
		return true
	}
	return false
}

func blockerRecoveryShadowRunForWorkOrder(db *sql.DB, workOrderID string) (BlockerRecoveryShadowRun, error) {
	var recoveryID string
	if err := db.QueryRow(
		"SELECT recovery_id FROM blocker_recovery_shadow_runs WHERE work_order_id=? ORDER BY updated DESC LIMIT 1",
		workOrderID,
	).Scan(&recoveryID); err != nil {
		return BlockerRecoveryShadowRun{}, err
	}
	return getBlockerRecoveryShadowRun(db, recoveryID)
}

func (p *Engine) advanceBlockerRecoveryShadow(ctx context.Context, id string) error {
	txState, err := p.ObserveBlockedWork(RecoveryObserverConfig{Enabled: true}, id)
	if err != nil {
		return err
	}
	plan, err := PrepareRecoveryPlan(RecoveryPlannerConfig{Enabled: true}, p.Store.DB, txState.RecoveryID)
	if err != nil {
		return err
	}
	run, err := ensureBlockerRecoveryShadowRun(p.Store.DB, txState, plan)
	if err != nil {
		return err
	}

	if blockerResolverMode(p) == blockerResolverModeActive && boundedActiveRetryPlan(plan) {
		return p.advanceBoundedActiveRetry(ctx, run, id)
	}

	if plan.Disposition != "SOURCE_REPAIR_CANDIDATE" || plan.RepairDomain != "APPLICATION_SOURCE" ||
		plan.RequiresAuthorityChange || plan.OuterQualificationRequired || plan.AutomaticMutation {
		if !shadowTerminal(run.Phase) {
			run, err = moveBlockerRecoveryShadowRun(
				p.Store.DB, run, run.Phase, recoveryShadowEscalated, 0, 0,
				"RECOVERY_SHADOW_PLAN_REQUIRES_NON_SOURCE_AUTHORITY",
			)
			if err != nil {
				return err
			}
		}
		return p.setSetting(blockerResolverStatusSetting, recoveryShadowStatus(run))
	}

	switch run.Phase {
	case recoveryShadowPlanned:
		run, err = moveBlockerRecoveryShadowRun(
			p.Store.DB, run, recoveryShadowPlanned, recoveryShadowCandidateRunning, 0, 0, "",
		)
		if err != nil {
			return err
		}
		var candidate RecoveryCandidateResult
		err = p.withBlockerRecoveryHeartbeat(ctx, func(runCtx context.Context) error {
			var inner error
			candidate, inner = p.PrepareRecoveryCandidate(
				runCtx,
				RecoveryRepairConfig{
					Enabled:           true,
					MaxRepairAttempts: 1,
					TimeoutSeconds:    blockerRecoveryTimeoutSeconds(p),
				},
				txState.RecoveryID,
			)
			return inner
		})
		if candidate.RepairAttempt > 0 && candidate.Status == "CANDIDATE_PREPARED" && err == nil {
			run, moveErr := moveBlockerRecoveryShadowRun(
				p.Store.DB, run, recoveryShadowCandidateRunning, recoveryShadowCandidateReady,
				candidate.RepairAttempt, 0, "",
			)
			if moveErr != nil {
				return moveErr
			}
			return p.setSetting(blockerResolverStatusSetting, recoveryShadowStatus(run))
		}
		detail := errorText(err)
		if detail == "" {
			detail = "RECOVERY_SHADOW_CANDIDATE_NOT_PREPARED"
		}
		run, moveErr := moveBlockerRecoveryShadowRun(
			p.Store.DB, run, recoveryShadowCandidateRunning, recoveryShadowRejected,
			candidate.RepairAttempt, 0, detail,
		)
		if moveErr != nil {
			return moveErr
		}
		return p.setSetting(blockerResolverStatusSetting, recoveryShadowStatus(run))

	case recoveryShadowCandidateRunning:
		return p.reconcileInterruptedShadowCandidate(run)

	case recoveryShadowCandidateReady:
		run, err = moveBlockerRecoveryShadowRun(
			p.Store.DB, run, recoveryShadowCandidateReady, recoveryShadowValidationRunning,
			run.CandidateAttempt, 0, "",
		)
		if err != nil {
			return err
		}
		var validation RecoveryValidationResult
		err = p.withBlockerRecoveryHeartbeat(ctx, func(runCtx context.Context) error {
			var inner error
			validation, inner = p.ValidateRecoveryCandidate(
				runCtx,
				RecoveryValidationConfig{Enabled: true, MaxValidationAttempts: 1},
				run.RecoveryID,
				run.CandidateAttempt,
			)
			return inner
		})
		target := recoveryShadowValidated
		detail := ""
		if err != nil || validation.Status != "VALIDATED" {
			target = recoveryShadowRejected
			detail = errorText(err)
			if detail == "" {
				detail = validation.FirstFailedCheck
			}
			if detail == "" {
				detail = "RECOVERY_SHADOW_VALIDATION_REJECTED"
			}
		}
		run, moveErr := moveBlockerRecoveryShadowRun(
			p.Store.DB, run, recoveryShadowValidationRunning, target,
			run.CandidateAttempt, validation.ValidationAttempt, detail,
		)
		if moveErr != nil {
			return moveErr
		}
		return p.setSetting(blockerResolverStatusSetting, recoveryShadowStatus(run))

	case recoveryShadowValidationRunning:
		return p.reconcileInterruptedShadowValidation(run)

	case recoveryShadowRejected:
		return p.revalidateHygieneRejectedShadow(ctx, run)

	case recoveryShadowValidated, recoveryShadowEscalated, recoveryShadowFailed:
		return p.setSetting(blockerResolverStatusSetting, recoveryShadowStatus(run))
	default:
		return errors.New("RECOVERY_SHADOW_PHASE_INVALID")
	}
}

func boundedActiveRetryPlan(plan RecoveryPlan) bool {
	return plan.Disposition == "DETERMINISTIC_RETRY" &&
		plan.RepairDomain == "INFRASTRUCTURE" &&
		!plan.RequiresAuthorityChange &&
		!plan.OuterQualificationRequired &&
		!plan.AutomaticMutation
}

func boundedActiveRetryRefusal(err error) bool {
	if err == nil {
		return false
	}
	s := err.Error()
	for _, prefix := range []string{
		"RETRY_LIMIT_REACHED",
		"EXTERNAL_ORCHESTRATOR_REQUIRED",
		"ATTEMPT_STILL_OWNED",
		"QUEUE_RETRY_STATE_INVALID",
		"WORK_ORDER_RETRY_STATE_INVALID",
		"QUEUE_ALREADY_COMPLETED",
	} {
		if strings.HasPrefix(s, prefix) {
			return true
		}
	}
	return false
}

func (p *Engine) advanceBoundedActiveRetry(ctx context.Context, run BlockerRecoveryShadowRun, id string) error {
	if run.Phase != recoveryShadowPlanned && run.Phase != recoveryShadowEscalated {
		return p.setSetting(blockerResolverStatusSetting, recoveryShadowStatus(run))
	}
	result, err := p.queueRetryLocked(ctx, id, "operator", "source")
	if err != nil {
		if !boundedActiveRetryRefusal(err) {
			return err
		}
		next, moveErr := moveBlockerRecoveryShadowRun(
			p.Store.DB, run, run.Phase, recoveryActiveRetryRefused,
			run.CandidateAttempt, run.ValidationAttempt, err.Error(),
		)
		if moveErr != nil {
			return moveErr
		}
		return p.setSetting(blockerResolverStatusSetting, recoveryShadowStatus(next))
	}
	out, ok := result.(map[string]any)
	if !ok || out["production_accepted"] != false || out["retry_budget_override"] != false {
		return errors.New("ACTIVE_RECOVERY_RETRY_RESULT_INVALID")
	}
	next, moveErr := moveBlockerRecoveryShadowRun(
		p.Store.DB, run, run.Phase, recoveryActiveRetryQueued,
		run.CandidateAttempt, run.ValidationAttempt, "",
	)
	if moveErr != nil {
		return moveErr
	}
	return p.setSetting(blockerResolverStatusSetting, recoveryShadowStatus(next))
}
func (p *Engine) revalidateHygieneRejectedShadow(ctx context.Context, run BlockerRecoveryShadowRun) error {
	if run.CandidateAttempt != 1 || (run.ValidationAttempt != 1 && run.ValidationAttempt != 2) ||
		run.LastError != "REJECTED: SOURCE_HYGIENE_FAILED" {
		return p.setSetting(blockerResolverStatusSetting, recoveryShadowStatus(run))
	}
	previous, err := p.RecoveryValidationAttempt(run.RecoveryID, run.CandidateAttempt, run.ValidationAttempt)
	if err != nil {
		return err
	}
	if previous.Status != "REJECTED" || previous.FirstFailedCheck != "SOURCE_HYGIENE_FAILED" {
		return p.setSetting(blockerResolverStatusSetting, recoveryShadowStatus(run))
	}
	run, err = moveBlockerRecoveryShadowRun(
		p.Store.DB, run, recoveryShadowRejected, recoveryShadowValidationRunning,
		run.CandidateAttempt, run.ValidationAttempt, "",
	)
	if err != nil {
		return err
	}
	var validation RecoveryValidationResult
	err = p.withBlockerRecoveryHeartbeat(ctx, func(runCtx context.Context) error {
		var inner error
		validation, inner = p.RevalidateRecoveryCandidate(
			runCtx,
			RecoveryValidationConfig{Enabled: true, MaxValidationAttempts: 3},
			run.RecoveryID,
			run.CandidateAttempt,
		)
		return inner
	})
	target := recoveryShadowValidated
	detail := ""
	if err != nil || validation.Status != "VALIDATED" {
		target = recoveryShadowRejected
		detail = errorText(err)
		if detail == "" {
			detail = validation.FirstFailedCheck
		}
		if detail == "" {
			detail = "RECOVERY_SHADOW_REVALIDATION_REJECTED"
		}
	}
	run, moveErr := moveBlockerRecoveryShadowRun(
		p.Store.DB, run, recoveryShadowValidationRunning, target,
		run.CandidateAttempt, validation.ValidationAttempt, detail,
	)
	if moveErr != nil {
		return moveErr
	}
	return p.setSetting(blockerResolverStatusSetting, recoveryShadowStatus(run))
}

func (p *Engine) reconcileInterruptedShadowCandidate(run BlockerRecoveryShadowRun) error {
	if err := initBlockerRecoveryCandidateStore(p.Store.DB); err != nil {
		return err
	}
	attempt, candidate, err := latestRecoveryCandidateShadow(p, run.RecoveryID)
	if errors.Is(err, sql.ErrNoRows) {
		next, moveErr := moveBlockerRecoveryShadowRun(
			p.Store.DB, run, recoveryShadowCandidateRunning, recoveryShadowFailed, 0, 0,
			"RECOVERY_SHADOW_INTERRUPTED_BEFORE_CANDIDATE_CLAIM",
		)
		if moveErr != nil {
			return moveErr
		}
		return p.setSetting(blockerResolverStatusSetting, recoveryShadowStatus(next))
	}
	if err != nil {
		return err
	}
	if candidate.Status == "RUNNING" {
		candidate.Status = "EVIDENCE_FAILED"
		candidate.ProductionAccepted = false
		candidate.ResumeAuthorized = false
		if _, err = finishRecoveryCandidate(p.Store.DB, candidate); err != nil {
			return err
		}
	}
	target := recoveryShadowRejected
	detail := candidate.Status
	if candidate.Status == "CANDIDATE_PREPARED" {
		target = recoveryShadowCandidateReady
		detail = ""
	}
	next, err := moveBlockerRecoveryShadowRun(
		p.Store.DB, run, recoveryShadowCandidateRunning, target, attempt, 0, detail,
	)
	if err != nil {
		return err
	}
	return p.setSetting(blockerResolverStatusSetting, recoveryShadowStatus(next))
}

func (p *Engine) reconcileInterruptedShadowValidation(run BlockerRecoveryShadowRun) error {
	if err := initBlockerRecoveryValidationStore(p.Store.DB); err != nil {
		return err
	}
	attempt, validation, err := latestRecoveryValidationShadow(p, run.RecoveryID, run.CandidateAttempt)
	if errors.Is(err, sql.ErrNoRows) {
		next, moveErr := moveBlockerRecoveryShadowRun(
			p.Store.DB, run, recoveryShadowValidationRunning, recoveryShadowFailed,
			run.CandidateAttempt, 0, "RECOVERY_SHADOW_INTERRUPTED_BEFORE_VALIDATION_CLAIM",
		)
		if moveErr != nil {
			return moveErr
		}
		return p.setSetting(blockerResolverStatusSetting, recoveryShadowStatus(next))
	}
	if err != nil {
		return err
	}
	if validation.Status == "RUNNING" {
		validation.Status = "EVIDENCE_FAILED"
		validation.FirstFailedCheck = "CONTROLLER_INTERRUPTED"
		validation.ProductionAccepted = false
		validation.ResumeAuthorized = false
		if _, err = finishRecoveryValidation(p.Store.DB, validation); err != nil {
			return err
		}
	}
	target := recoveryShadowRejected
	detail := validation.FirstFailedCheck
	if validation.Status == "VALIDATED" {
		target = recoveryShadowValidated
		detail = ""
	}
	next, err := moveBlockerRecoveryShadowRun(
		p.Store.DB, run, recoveryShadowValidationRunning, target,
		run.CandidateAttempt, attempt, detail,
	)
	if err != nil {
		return err
	}
	return p.setSetting(blockerResolverStatusSetting, recoveryShadowStatus(next))
}

func latestRecoveryCandidateShadow(p *Engine, recoveryID string) (int, RecoveryCandidateResult, error) {
	var attempt sql.NullInt64
	if err := p.Store.DB.QueryRow(
		"SELECT max(repair_attempt) FROM blocker_recovery_candidates WHERE recovery_id=?",
		recoveryID,
	).Scan(&attempt); err != nil {
		return 0, RecoveryCandidateResult{}, err
	}
	if !attempt.Valid || attempt.Int64 < 1 {
		return 0, RecoveryCandidateResult{}, sql.ErrNoRows
	}
	out, err := p.RecoveryCandidate(recoveryID, int(attempt.Int64))
	return int(attempt.Int64), out, err
}

func latestRecoveryValidationShadow(p *Engine, recoveryID string, repairAttempt int) (int, RecoveryValidationResult, error) {
	var attempt sql.NullInt64
	if err := p.Store.DB.QueryRow(
		"SELECT max(validation_attempt) FROM blocker_recovery_validations WHERE recovery_id=? AND repair_attempt=?",
		recoveryID, repairAttempt,
	).Scan(&attempt); err != nil {
		return 0, RecoveryValidationResult{}, err
	}
	if !attempt.Valid || attempt.Int64 < 1 {
		return 0, RecoveryValidationResult{}, sql.ErrNoRows
	}
	out, err := p.RecoveryValidationAttempt(recoveryID, repairAttempt, int(attempt.Int64))
	return int(attempt.Int64), out, err
}

func (p *Engine) withBlockerRecoveryHeartbeat(ctx context.Context, fn func(context.Context) error) error {
	done := make(chan struct{})
	go func() {
		ticker := time.NewTicker(15 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-done:
				return
			case <-ctx.Done():
				return
			case <-ticker.C:
				_ = p.setSetting("autonomy_heartbeat", now())
			}
		}
	}()
	err := fn(ctx)
	close(done)
	_ = p.setSetting("autonomy_heartbeat", now())
	return err
}

func blockerRecoveryTimeoutSeconds(p *Engine) int {
	timeout := p.Config.Execution.TimeoutSeconds
	if timeout < 1 {
		return 1200
	}
	if timeout > 1200 {
		return 1200
	}
	return timeout
}

func shadowTerminal(phase string) bool {
	switch phase {
	case recoveryShadowValidated, recoveryShadowRejected, recoveryShadowEscalated, recoveryShadowFailed,
		recoveryActiveRetryQueued, recoveryActiveRetryRefused:
		return true
	default:
		return false
	}
}

func recoveryShadowStatus(run BlockerRecoveryShadowRun) string {
	status := run.Phase + ": " + run.WorkOrderID
	if run.LastError != "" {
		status += ": " + run.LastError
	}
	return fmt.Sprintf("%s recovery=%s", status, run.RecoveryID[:16])
}
