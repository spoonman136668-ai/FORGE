package plane

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"
)

const (
	mindPalaceAutoDiscoveryOperationID     = "mind-palace-project-discovery"
	mindPalaceAutoDiscoveryDefaultInterval = 6 * time.Hour
	mindPalaceAutoDiscoveryMinimumInterval = time.Hour
	mindPalaceAutoDiscoveryMaximumInterval = 24 * time.Hour
	mindPalaceAutoDiscoveryFailureBackoff  = time.Hour
	mindPalaceAutoDiscoveryErrorLimit      = 512
)

func (p *Engine) mindPalaceAutoDiscoveryInterval() time.Duration {
	seconds := p.Config.Autonomy.MindPalaceDiscoveryIntervalSeconds
	if seconds == 0 {
		return mindPalaceAutoDiscoveryDefaultInterval
	}
	return time.Duration(seconds) * time.Second
}

func (p *Engine) validateMindPalaceAutoDiscovery() error {
	if !p.Config.Autonomy.MindPalaceAutoDiscovery {
		return nil
	}
	interval := p.mindPalaceAutoDiscoveryInterval()
	if interval < mindPalaceAutoDiscoveryMinimumInterval || interval > mindPalaceAutoDiscoveryMaximumInterval {
		return errors.New("MIND_PALACE_AUTO_DISCOVERY_INTERVAL_INVALID")
	}
	if p.localOperations == nil {
		return errors.New("MIND_PALACE_AUTO_DISCOVERY_LOCAL_EXEC_DISABLED")
	}
	op, ok := p.localOperations.byID[mindPalaceAutoDiscoveryOperationID]
	if !ok {
		return errors.New("MIND_PALACE_AUTO_DISCOVERY_OPERATION_NOT_REGISTERED")
	}
	if op.Class != "diagnostic" || len(op.Arguments) != 0 || op.TimeoutSeconds < 1 || op.TimeoutSeconds > 120 {
		return errors.New("MIND_PALACE_AUTO_DISCOVERY_OPERATION_CONTRACT_INVALID")
	}
	return nil
}

func (p *Engine) mindPalaceAutoDiscoveryStatus() map[string]any {
	return map[string]any{
		"enabled":                  p.Config.Autonomy.MindPalaceAutoDiscovery,
		"interval_seconds":         int(p.mindPalaceAutoDiscoveryInterval() / time.Second),
		"state":                    p.setting("mind_palace_discovery_state"),
		"last_attempt_at":          p.setting("mind_palace_discovery_last_attempt_at"),
		"last_finished_at":         p.setting("mind_palace_discovery_last_finished_at"),
		"last_success_at":          p.setting("mind_palace_discovery_last_success_at"),
		"last_request_id":          p.setting("mind_palace_discovery_last_request_id"),
		"last_result_status":       p.setting("mind_palace_discovery_last_result_status"),
		"last_error":               p.setting("mind_palace_discovery_last_error"),
		"evidence_manifest_sha256": p.setting("mind_palace_discovery_evidence_manifest_sha256"),
	}
}

func mindPalaceAutoDiscoveryError(err error) string {
	if err == nil {
		return ""
	}
	s := strings.TrimSpace(err.Error())
	if len(s) > mindPalaceAutoDiscoveryErrorLimit {
		s = s[:mindPalaceAutoDiscoveryErrorLimit]
	}
	return s
}

func parseMindPalaceAutoDiscoveryTime(raw string) (time.Time, error) {
	if strings.TrimSpace(raw) == "" {
		return time.Time{}, nil
	}
	t, err := time.Parse(time.RFC3339Nano, raw)
	if err != nil {
		return time.Time{}, errors.New("MIND_PALACE_AUTO_DISCOVERY_STATE_INVALID")
	}
	return t, nil
}

func (p *Engine) mindPalaceAutoDiscoveryDue(now time.Time, op LocalOperation) (bool, error) {
	state := p.setting("mind_palace_discovery_state")
	lastAttempt, err := parseMindPalaceAutoDiscoveryTime(p.setting("mind_palace_discovery_last_attempt_at"))
	if err != nil {
		return false, err
	}
	if state == "RUNNING" {
		if lastAttempt.IsZero() {
			return false, errors.New("MIND_PALACE_AUTO_DISCOVERY_RUNNING_WITHOUT_ATTEMPT")
		}
		staleAfter := time.Duration(op.TimeoutSeconds+60) * time.Second
		if now.Sub(lastAttempt) < staleAfter {
			return false, nil
		}
		_ = p.setSetting("mind_palace_discovery_state", "STALE")
		_ = p.setSetting("mind_palace_discovery_last_error", "MIND_PALACE_AUTO_DISCOVERY_STALE_RUN_RECOVERED")
		state = "STALE"
	}
	if lastAttempt.IsZero() {
		return true, nil
	}
	wait := p.mindPalaceAutoDiscoveryInterval()
	switch state {
	case "FAILED", "STALE", "ERROR":
		if wait > mindPalaceAutoDiscoveryFailureBackoff {
			wait = mindPalaceAutoDiscoveryFailureBackoff
		}
	}
	return now.Sub(lastAttempt) >= wait, nil
}

func (p *Engine) recordMindPalaceAutoDiscoverySchedulerError(err error) {
	_ = p.setSetting("mind_palace_discovery_last_attempt_at", time.Now().UTC().Format(time.RFC3339Nano))
	_ = p.setSetting("mind_palace_discovery_last_error", mindPalaceAutoDiscoveryError(err))
	_ = p.setSetting("mind_palace_discovery_last_result_status", "scheduler-error")
	_ = p.setSetting("mind_palace_discovery_state", "ERROR")
}

func (p *Engine) maybeStartMindPalaceAutoDiscovery(ctx context.Context) error {
	if !p.Config.Autonomy.MindPalaceAutoDiscovery {
		return nil
	}
	if p.setting("autonomy_authority") != "plane" {
		return nil
	}
	if p.localOperations == nil {
		return errors.New("MIND_PALACE_AUTO_DISCOVERY_LOCAL_EXEC_DISABLED")
	}
	op, ok := p.localOperations.byID[mindPalaceAutoDiscoveryOperationID]
	if !ok {
		return errors.New("MIND_PALACE_AUTO_DISCOVERY_OPERATION_NOT_REGISTERED")
	}
	var leases int
	if err := p.Store.DB.QueryRow("SELECT count(*) FROM worker_leases").Scan(&leases); err != nil {
		return err
	}
	if leases != 0 {
		return nil
	}
	nowUTC := time.Now().UTC()
	due, err := p.mindPalaceAutoDiscoveryDue(nowUTC, op)
	if err != nil || !due {
		return err
	}
	generation := strings.TrimSpace(p.setting("autonomy_generation"))
	if generation == "" {
		return errors.New("MIND_PALACE_AUTO_DISCOVERY_GENERATION_UNAVAILABLE")
	}
	requestID := fmt.Sprintf("mpdisc-auto-g%s-%s-%s", generation, nowUTC.Format("20060102T150405"), randomID()[:8])
	if !safeID.MatchString(requestID) {
		return errors.New("MIND_PALACE_AUTO_DISCOVERY_REQUEST_ID_INVALID")
	}
	if err = p.setSetting("mind_palace_discovery_last_attempt_at", nowUTC.Format(time.RFC3339Nano)); err != nil {
		return err
	}
	if err = p.setSetting("mind_palace_discovery_last_request_id", requestID); err != nil {
		return err
	}
	if err = p.setSetting("mind_palace_discovery_last_result_status", "running"); err != nil {
		return err
	}
	if err = p.setSetting("mind_palace_discovery_last_error", ""); err != nil {
		return err
	}
	if err = p.setSetting("mind_palace_discovery_state", "RUNNING"); err != nil {
		return err
	}
	req := LocalExecutionRequest{RequestID: requestID, OperationID: op.ID, ScriptSHA256: op.ScriptSHA256}
	go p.runMindPalaceAutoDiscovery(ctx, req)
	return nil
}

func (p *Engine) runMindPalaceAutoDiscovery(ctx context.Context, req LocalExecutionRequest) {
	result, runErr := p.RunLocalOperation(ctx, req)
	finished := time.Now().UTC().Format(time.RFC3339Nano)
	_ = p.setSetting("mind_palace_discovery_last_finished_at", finished)
	_ = p.setSetting("mind_palace_discovery_last_result_status", result.Status)
	_ = p.setSetting("mind_palace_discovery_evidence_manifest_sha256", result.EvidenceManifestSHA256)
	if runErr != nil || result.Status != "succeeded" || result.ExitCode != 0 {
		if runErr == nil {
			runErr = fmt.Errorf("MIND_PALACE_AUTO_DISCOVERY_RESULT_INVALID status=%s exit=%d", result.Status, result.ExitCode)
		}
		_ = p.setSetting("mind_palace_discovery_last_error", mindPalaceAutoDiscoveryError(runErr))
		_ = p.setSetting("mind_palace_discovery_state", "FAILED")
		return
	}
	_ = p.setSetting("mind_palace_discovery_last_success_at", finished)
	_ = p.setSetting("mind_palace_discovery_last_error", "")
	_ = p.setSetting("mind_palace_discovery_state", "SUCCEEDED")
}
