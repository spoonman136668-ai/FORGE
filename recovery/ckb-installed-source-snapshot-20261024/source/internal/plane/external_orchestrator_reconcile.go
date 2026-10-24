package plane

import (
	"context"
	"database/sql"
	"errors"
)

// reconcileExternalOrchestratorHandoffs makes handoff publication eventual.
// The authoritative held state and local handoff already exist before this
// runs; this only queues an immutable WebUI outbox record if the bridge is
// attached. Repeated calls are idempotent.
func (p *Engine) reconcileExternalOrchestratorHandoffs(ctx context.Context) error {
	if !p.Config.Autonomy.ObjectiveController || p.bridge == nil {
		return nil
	}
	rows, err := p.Store.DB.QueryContext(ctx, `
SELECT q.id
FROM queue_items q
WHERE q.state='WAITING_FOR_EXTERNAL_ORCHESTRATOR'
ORDER BY q.updated, q.id
LIMIT 20`)
	if err != nil {
		return err
	}
	var ids []string
	for rows.Next() {
		var id string
		if err = rows.Scan(&id); err != nil {
			rows.Close()
			return err
		}
		ids = append(ids, id)
	}
	if err = rows.Err(); err != nil {
		rows.Close()
		return err
	}
	rows.Close()

	for _, id := range ids {
		j, getErr := p.Store.Get(id)
		if errors.Is(getErr, sql.ErrNoRows) {
			continue
		}
		if getErr != nil {
			return getErr
		}
		// Only the original quota hold has a canonical external handoff. Later
		// acceptance failures reuse that exact handoff binding rather than
		// generating a new authority document.
		if failureClass(j.Reason) != "CODEX_QUOTA_EXHAUSTED" {
			continue
		}
		h, handoffErr := p.objectiveHandoff(j)
		if handoffErr != nil {
			return handoffErr
		}
		if handoffErr = p.bridge.queueExternalHandoff(h); handoffErr != nil {
			return handoffErr
		}
	}
	return nil
}
