package plane

import "strings"

func objectiveExplicitRetryReason(reason string) bool {
	switch strings.TrimSpace(reason) {
	case "OPERATOR_RETRY_AUTHORIZED",
		preWorkerRetryAuthorizedReason,
		workerCancelRetryAuthorizedReason,
		workerAuthRetryAuthorizedReason:
		return true
	default:
		return false
	}
}

// objectiveBlockedRetryReconciled proves that an explicit queue retry restored
// the exact immutable stage after an Objective had already latched BLOCKED.
// This does not retry work itself; it only permits the operator's separate
// Objective resume to clear the stale Objective-level blocker.
func (p *Engine) objectiveBlockedRetryReconciled(o Objective) (bool, error) {
	if o.Status != "BLOCKED" || o.Current == "" || o.Next < 0 || o.Next >= o.Total {
		return false, nil
	}

	var stageRaw []byte
	var stageHash, stageContract, stageState string
	if e := p.Store.DB.QueryRow(
		"SELECT raw,hash,contract,state FROM objective_stages WHERE objective_id=? AND stage=? AND work_id=?",
		o.ID, o.Next, o.Current,
	).Scan(&stageRaw, &stageHash, &stageContract, &stageState); e != nil {
		return false, e
	}
	if stageState != "QUEUED" || digest(stageRaw) != stageHash {
		return false, nil
	}

	var queueRaw []byte
	var queueHash, queueState, queueReason string
	if e := p.Store.DB.QueryRow(
		"SELECT raw,hash,state,reason FROM queue_items WHERE id=?",
		o.Current,
	).Scan(&queueRaw, &queueHash, &queueState, &queueReason); e != nil {
		return false, e
	}
	if queueState != "QUEUED" || !objectiveExplicitRetryReason(queueReason) ||
		queueHash != stageHash || digest(queueRaw) != stageHash {
		return false, nil
	}

	q, e := p.parseQueue(queueRaw, o.Current)
	if e != nil {
		return false, e
	}
	w, e := ParseOrder([]byte(q.WorkOrderYAML))
	if e != nil {
		return false, e
	}
	if p.contract(w) != stageContract {
		return false, nil
	}

	j, e := p.Store.Get(o.Current)
	if e != nil {
		return false, e
	}
	if j.State != "DRAFT" && j.State != "AUTHORIZED" && j.State != "READY" {
		return false, nil
	}
	if jsonText(j.Order) != jsonText(w) {
		return false, nil
	}

	var leases, liveProcesses int
	if e = p.Store.DB.QueryRow("SELECT count(*) FROM worker_leases WHERE work_order_id=?", o.Current).Scan(&leases); e != nil {
		return false, e
	}
	if e = p.Store.DB.QueryRow("SELECT count(*) FROM process_records WHERE work_order_id=? AND finished=0", o.Current).Scan(&liveProcesses); e != nil {
		return false, e
	}
	return leases == 0 && liveProcesses == 0, nil
}
