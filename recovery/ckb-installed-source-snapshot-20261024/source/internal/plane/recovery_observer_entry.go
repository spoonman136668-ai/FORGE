package plane

// ObserveBlockedWork performs the complete Stage-3 observer transaction:
//
// blocked durable evidence
//   -> identity-bound read-only snapshot
//   -> RECOVERY_PENDING recovery-owned record
//   -> deterministic classification
//
// It deliberately has no scheduler/retry/resume/model/repair side effects.
// No production loop calls this function in Stage 3.
func (p *Engine) ObserveBlockedWork(cfg RecoveryObserverConfig, id string) (BlockerRecoveryTransaction, error) {
	if !cfg.Enabled {
		return BlockerRecoveryTransaction{}, errRecoveryObserverDisabled
	}
	snapshot, err := p.BuildRecoveryEvidenceSnapshot(id)
	if err != nil {
		return BlockerRecoveryTransaction{}, err
	}
	if err = initBlockerRecoveryObserverStore(p.Store.DB); err != nil {
		return BlockerRecoveryTransaction{}, err
	}
	pending, err := createBlockerRecoveryPending(cfg, p.Store.DB, snapshot)
	if err != nil {
		return BlockerRecoveryTransaction{}, err
	}
	return classifyBlockerRecoveryPending(cfg, p.Store.DB, pending.RecoveryID)
}
