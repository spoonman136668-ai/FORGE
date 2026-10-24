package plane

// Objective state belongs to the existing controller and SQLite store. There
// is no goroutine, worker launcher, alternate queue, or planner in this file.
import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

const objectiveSchema = "ckb-plane.objective.v1"

type ObjectivePlan struct {
	Schema   string       `json:"schema"`
	ID       string       `json:"objective_id"`
	Goal     string       `json:"goal"`
	Envelope string       `json:"authorization_envelope_ref"`
	Priority int          `json:"priority"`
	Orders   []QueueOrder `json:"orders"`
}

type Objective struct {
	HandoffSHA256        string            `json:"handoff_sha256,omitempty"`
	Schema               string            `json:"schema"`
	ID                   string            `json:"objective_id"`
	Goal                 string            `json:"goal"`
	Envelope             string            `json:"authorization_envelope_ref"`
	Generation           int64             `json:"authority_generation"`
	Status               string            `json:"status"`
	Priority             int               `json:"priority"`
	Revision             int64             `json:"revision"`
	LastSteeringRevision int64             `json:"last_steering_revision"`
	Next                 int               `json:"next_stage"`
	Total                int               `json:"stage_count"`
	Current              string            `json:"current_work_order_id,omitempty"`
	Paused               bool              `json:"paused"`
	StopAfterCurrent     bool              `json:"stop_after_current"`
	Blocker              string            `json:"blocker,omitempty"`
	Created              string            `json:"created_at"`
	Updated              string            `json:"updated_at"`
	LastProgress         string            `json:"last_progress_at"`
	LastEvaluated        string            `json:"last_evaluated_state"`
	Handoff              *ObjectiveHandoff `json:"external_handoff,omitempty"`
}

type ObjectiveRequest struct {
	HandoffSHA256    string         `json:"handoff_sha256,omitempty"`
	Action           string         `json:"action"`
	ID               string         `json:"objective_id"`
	ExpectedRevision int64          `json:"expected_revision,omitempty"`
	Priority         *int           `json:"priority,omitempty"`
	Plan             *ObjectivePlan `json:"plan,omitempty"`
}

func (r ObjectiveRequest) validate() error {
	if (r.Action != "continue" && r.HandoffSHA256 != "") || (r.Action == "continue" && (len(r.HandoffSHA256) != 64 || strings.Trim(r.HandoffSHA256, "0123456789abcdef") != "")) {
		return errors.New("OBJECTIVE_HANDOFF_HASH_REQUIRED")
	}
	if !safeID.MatchString(r.ID) {
		return errors.New("OBJECTIVE_ID_INVALID")
	}
	switch r.Action {
	case "create":
		if r.Plan == nil || r.Plan.ID != r.ID || r.ExpectedRevision != 0 || r.Priority != nil {
			return errors.New("OBJECTIVE_ARGUMENTS_INVALID")
		}
	case "status", "decisions":
		if r.Plan != nil || r.Priority != nil || r.ExpectedRevision != 0 {
			return errors.New("OBJECTIVE_ARGUMENTS_INVALID")
		}
	case "pause", "resume", "cancel", "stop-after-current", "continue", "abandon-blocked":
		if r.Plan != nil || r.Priority != nil || r.ExpectedRevision < 1 {
			return errors.New("OBJECTIVE_ARGUMENTS_INVALID")
		}
	case "priority":
		if r.Plan != nil || r.Priority == nil || *r.Priority < -100 || *r.Priority > 100 || r.ExpectedRevision < 1 {
			return errors.New("OBJECTIVE_ARGUMENTS_INVALID")
		}
	default:
		return errors.New("OBJECTIVE_ACTION_INVALID")
	}
	return nil
}

func (p *Engine) initObjectives() error {
	if !p.Config.Autonomy.ObjectiveController {
		return nil
	}
	_, e := p.Store.DB.Exec(`
CREATE TABLE IF NOT EXISTS objectives(id TEXT PRIMARY KEY,raw BLOB NOT NULL,priority INTEGER NOT NULL,revision INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS objective_stages(objective_id TEXT NOT NULL,stage INTEGER NOT NULL,work_id TEXT NOT NULL UNIQUE,raw BLOB NOT NULL,hash TEXT NOT NULL,contract TEXT NOT NULL,state TEXT NOT NULL,PRIMARY KEY(objective_id,stage));
CREATE TABLE IF NOT EXISTS objective_continuations(work_id TEXT NOT NULL,next_attempt INTEGER NOT NULL,handoff BLOB NOT NULL,PRIMARY KEY(work_id,next_attempt));
CREATE TABLE IF NOT EXISTS objective_decisions(objective_id TEXT NOT NULL,revision INTEGER NOT NULL,created TEXT NOT NULL,decision TEXT NOT NULL,PRIMARY KEY(objective_id,revision));
`)
	return e
}

func (p *Engine) objectiveGet(id string) (Objective, error) {
	var o Objective
	var raw []byte
	var rev int64
	var priority int
	e := p.Store.DB.QueryRow("SELECT raw,revision,priority FROM objectives WHERE id=?", id).Scan(&raw, &rev, &priority)
	if e != nil {
		return o, e
	}
	if e = json.Unmarshal(raw, &o); e != nil {
		return o, e
	}
	if o.ID != id || o.Schema != objectiveSchema || o.Revision != rev || o.Priority != priority || o.Next < 0 || o.Next > o.Total || o.Total < 1 {
		return o, errors.New("OBJECTIVE_STATE_CORRUPT")
	}
	switch o.Status {
	case "PENDING", "RUNNING", "PAUSED", "WAITING_FOR_EXTERNAL_ORCHESTRATOR", "BLOCKED", "COMPLETED", "CANCELLED":
	default:
		return o, errors.New("OBJECTIVE_UNKNOWN_STATE")
	}
	return o, nil
}

func saveObjective(tx *sql.Tx, o *Objective, decision string, progress bool) error {
	if o.Handoff != nil {
		o.HandoffSHA256 = digest([]byte(jsonText(o.Handoff)))
	}
	previous := o.Revision
	o.Revision++
	if strings.HasPrefix(decision, "OPERATOR_") {
		o.LastSteeringRevision = o.Revision
	}
	o.Updated = now()
	o.LastEvaluated = decision
	if progress {
		o.LastProgress = o.Updated
	}
	r, e := tx.Exec("UPDATE objectives SET raw=?,priority=?,revision=? WHERE id=? AND revision=?", jsonText(o), o.Priority, o.Revision, o.ID, previous)
	if e != nil {
		return e
	}
	n, e := r.RowsAffected()
	if e != nil {
		return e
	}
	if n != 1 {
		return errors.New("OBJECTIVE_REVISION_CONFLICT")
	}
	_, e = tx.Exec("INSERT INTO objective_decisions VALUES(?,?,?,?)", o.ID, o.Revision, o.Updated, decision)
	return e
}

func (p *Engine) objectiveSave(o *Objective, decision string, progress bool) error {
	if decision == o.LastEvaluated && !progress {
		return nil
	}
	tx, e := p.Store.DB.Begin()
	if e != nil {
		return e
	}
	defer tx.Rollback()
	if e = saveObjective(tx, o, decision, progress); e != nil {
		return e
	}
	return tx.Commit()
}

func (p *Engine) objectiveAuthority(ctx context.Context, generation int64) error {
	if !p.Config.Autonomy.ObjectiveController {
		return errors.New("OBJECTIVE_CONTROLLER_DISABLED")
	}
	g, e := strconv.ParseInt(p.setting("autonomy_generation"), 10, 64)
	if e != nil || generation < 1 || g != generation {
		return errors.New("AUTHORITY_GENERATION_CHANGED")
	}
	if p.Config.Policy.RuntimeLaunchAllowed || p.Config.Policy.ArbitraryShell || p.Config.Policy.AcceptedRefMutation {
		return errors.New("OBJECTIVE_POLICY_REJECTED")
	}
	return p.sourceAuthority(ctx)
}

// This entry point is invoked only from the authenticated native/bridge control
// path. Generation and optimistic revision are checked again under queueMu.
func (p *Engine) ObjectiveControl(ctx context.Context, generation int64, r ObjectiveRequest) (any, error) {
	p.queueMu.Lock()
	defer p.queueMu.Unlock()
	if !p.Config.Autonomy.ObjectiveController {
		return nil, errors.New("OBJECTIVE_CONTROLLER_DISABLED")
	}
	if e := r.validate(); e != nil {
		return nil, e
	}
	if r.Action == "status" {
		return p.objectiveGet(r.ID)
	}
	if r.Action == "decisions" {
		rows, e := p.Store.DB.Query("SELECT revision,created,decision FROM objective_decisions WHERE objective_id=? ORDER BY revision DESC LIMIT 50", r.ID)
		if e != nil {
			return nil, e
		}
		defer rows.Close()
		out := []map[string]any{}
		for rows.Next() {
			var rev int64
			var at, d string
			if e = rows.Scan(&rev, &at, &d); e != nil {
				return nil, e
			}
			out = append(out, map[string]any{"revision": rev, "created_at": at, "decision": d})
		}
		return out, rows.Err()
	}
	// Stop controls must remain available if qualification/provider verification
	// is unavailable. They still require the current authority generation.
	g, e := strconv.ParseInt(p.setting("autonomy_generation"), 10, 64)
	if e != nil || generation < 1 || g != generation {
		return nil, errors.New("AUTHORITY_GENERATION_CHANGED")
	}
	if r.Action == "create" {
		return p.objectiveCreate(ctx, generation, *r.Plan)
	}
	o, e := p.objectiveGet(r.ID)
	if e != nil {
		return nil, e
	}
	if r.ExpectedRevision < o.LastSteeringRevision || r.ExpectedRevision > o.Revision {
		return nil, errors.New("OBJECTIVE_REVISION_CONFLICT")
	}
	if o.Status == "COMPLETED" || o.Status == "CANCELLED" {
		return nil, errors.New("OBJECTIVE_TERMINAL")
	}
	switch r.Action {
	case "pause":
		o.Paused = true
		if o.Status == "RUNNING" || o.Status == "PENDING" {
			o.Status = "PAUSED"
		}
	case "stop-after-current":
		o.StopAfterCurrent = true
	case "cancel":
		o.Status = "CANCELLED"
		o.Paused = true
	case "abandon-blocked":
		if e = p.objectiveAbandonBlocked(&o); e != nil {
			return nil, e
		}
		return o, nil
	case "priority":
		o.Priority = *r.Priority
	case "resume", "continue":
		if e = p.objectiveAuthority(ctx, o.Generation); e != nil {
			return nil, e
		}
		if r.Action == "continue" {
			if o.Status != "WAITING_FOR_EXTERNAL_ORCHESTRATOR" {
				return nil, errors.New("OBJECTIVE_NOT_WAITING")
			}
			// An external proposer cannot declare a stage accepted. Resume only
			// after the existing plane has accepted the same retained work order.
			if o.Handoff == nil || digest([]byte(jsonText(o.Handoff))) != r.HandoffSHA256 {
				return nil, errors.New("OBJECTIVE_HANDOFF_CHANGED")
			}
			return p.objectiveContinueLocked(ctx, &o, r.HandoffSHA256)
		} else if o.Status == "BLOCKED" {
			reconciled, er := p.objectiveBlockedRetryReconciled(o)
			if er != nil {
				return nil, er
			}
			if !reconciled {
				return nil, errors.New("OBJECTIVE_BLOCKER_REQUIRES_RECONCILIATION")
			}
		} else if o.Status != "PAUSED" && o.Status != "PENDING" && o.Status != "RUNNING" {
			return nil, errors.New("OBJECTIVE_BLOCKER_REQUIRES_RECONCILIATION")
		}
		o.Paused = false
		o.StopAfterCurrent = false
		o.Status = "RUNNING"
		o.Blocker = ""
	}
	decision := "OPERATOR_" + r.Action
	if r.Action == "priority" {
		decision += ":" + strconv.Itoa(*r.Priority)
	}
	if e = p.objectiveSave(&o, decision, false); e != nil {
		return nil, e
	}
	// Cancellation desired state is durable before touching the owned process.
	// Reconciliation repeats the cancellation if the controller crashes here.
	if r.Action == "cancel" && o.Current != "" {
		p.mu.Lock()
		_, active := p.cancels[o.Current]
		p.mu.Unlock()
		if active {
			if e = p.Cancel(o.Current); e != nil {
				return o, e
			}
		}
	}
	return o, nil
}

// objectiveAbandonBlocked retires a queue row that is permanently held by a
// hard-blocked objective. It never accepts work and it refuses any active or
// accepted native job. ObjectiveControl already owns queueMu and generation
// validation when this helper is called.
func (p *Engine) objectiveAbandonBlocked(o *Objective) error {
	if o.Status != "BLOCKED" || o.Current == "" {
		return errors.New("OBJECTIVE_ABANDON_REQUIRES_BLOCKED")
	}

	tx, e := p.Store.DB.Begin()
	if e != nil {
		return e
	}
	defer tx.Rollback()

	var owner, stageState, stageHash string
	if e = tx.QueryRow("SELECT objective_id,state,hash FROM objective_stages WHERE work_id=?", o.Current).Scan(&owner, &stageState, &stageHash); e != nil {
		return e
	}
	if owner != o.ID || stageState != "QUEUED" {
		return errors.New("OBJECTIVE_ABANDON_STAGE_MISMATCH")
	}

	var queueState, queueHash string
	if e = tx.QueryRow("SELECT state,hash FROM queue_items WHERE id=?", o.Current).Scan(&queueState, &queueHash); e != nil {
		return e
	}
	if queueState != "QUEUED" || queueHash != stageHash {
		return errors.New("OBJECTIVE_ABANDON_QUEUE_MISMATCH")
	}

	var active int
	if e = tx.QueryRow("SELECT (SELECT count(*) FROM worker_leases WHERE work_order_id=?)+(SELECT count(*) FROM process_records WHERE work_order_id=? AND finished=0)", o.Current, o.Current).Scan(&active); e != nil {
		return e
	}
	if active != 0 {
		return errors.New("OBJECTIVE_ABANDON_WORK_ACTIVE")
	}

	var jobState string
	e = tx.QueryRow("SELECT state FROM work_orders WHERE id=?", o.Current).Scan(&jobState)
	if e != nil && !errors.Is(e, sql.ErrNoRows) {
		return e
	}
	if e == nil {
		switch jobState {
		case "DRAFT", "READY", "AUTHORIZED", "REJECTED_RETRYABLE":
		default:
			return errors.New("OBJECTIVE_ABANDON_WORK_STATE_INVALID")
		}
	}

	reason := "OBJECTIVE_BLOCKED_RECONCILED: " + o.Blocker
	r, e := tx.Exec("UPDATE queue_items SET state='REVIEWED',reason=?,updated=? WHERE id=? AND state='QUEUED' AND hash=?", reason, now(), o.Current, stageHash)
	if e != nil {
		return e
	}
	n, e := r.RowsAffected()
	if e != nil {
		return e
	}
	if n != 1 {
		return errors.New("OBJECTIVE_ABANDON_QUEUE_CHANGED")
	}

	o.Status = "CANCELLED"
	o.Paused = true
	o.Blocker = reason
	if e = saveObjective(tx, o, "OPERATOR_abandon-blocked", false); e != nil {
		return e
	}
	return tx.Commit()
}
func (p *Engine) objectiveCreate(ctx context.Context, generation int64, plan ObjectivePlan) (Objective, error) {
	var o Objective
	if e := p.objectiveAuthority(ctx, generation); e != nil {
		return o, e
	}
	if plan.Schema != objectiveSchema || !safeID.MatchString(plan.ID) || len(plan.Goal) < 1 || len(plan.Goal) > 4096 || !safeID.MatchString(plan.Envelope) || plan.Priority < -100 || plan.Priority > 100 || len(plan.Orders) < 1 || len(plan.Orders) > 64 || len(jsonText(plan)) > bridgeMaxBytes {
		return o, errors.New("OBJECTIVE_PLAN_INVALID")
	}
	raws := make([][]byte, len(plan.Orders))
	contracts := make([]string, len(plan.Orders))
	seen := map[string]bool{}
	for i, q := range plan.Orders {
		raw, _ := json.Marshal(q)
		parsed, e := p.parseQueue(raw, q.ID)
		if e != nil {
			return o, e
		}
		if parsed.Kind != "source" || seen[q.ID] {
			return o, errors.New("OBJECTIVE_SOURCE_SEQUENCE_REQUIRED")
		}
		// V1 is a bounded ordered DAG. Dependencies can only refer to prior
		// stages in this exact immutable plan; no inferred roadmap edges.
		for _, dep := range q.Dependencies {
			if !seen[dep] {
				return o, errors.New("OBJECTIVE_DEPENDENCY_NOT_PRIOR_STAGE")
			}
		}
		w, e := ParseOrder([]byte(q.WorkOrderYAML))
		if e != nil {
			return o, e
		}
		var n int
		if e = p.Store.DB.QueryRow("SELECT (SELECT count(*) FROM queue_items WHERE id=?)+(SELECT count(*) FROM work_orders WHERE id=?)", q.ID, q.ID).Scan(&n); e != nil {
			return o, e
		}
		if n != 0 {
			return o, errors.New("OBJECTIVE_WORK_ALREADY_EXISTS")
		}
		for _, dir := range []string{"pending", "completed", "failed"} {
			path, e := p.queuePath(dir, q.ID)
			if e != nil {
				return o, e
			}
			if _, e = os.Lstat(path); !os.IsNotExist(e) {
				return o, errors.New("OBJECTIVE_QUEUE_PATH_EXISTS")
			}
		}
		raws[i] = raw
		contracts[i] = p.contract(w)
		seen[q.ID] = true
	}
	o = Objective{Schema: objectiveSchema, ID: plan.ID, Goal: plan.Goal, Envelope: plan.Envelope, Generation: generation, Status: "PENDING", Priority: plan.Priority, Revision: 1, LastSteeringRevision: 1, Total: len(plan.Orders), Created: now(), Updated: now(), LastProgress: now(), LastEvaluated: "OPERATOR_CREATE"}
	tx, e := p.Store.DB.Begin()
	if e != nil {
		return o, e
	}
	defer tx.Rollback()
	if _, e = tx.Exec("INSERT INTO objectives VALUES(?,?,?,?)", o.ID, jsonText(o), o.Priority, o.Revision); e != nil {
		return o, e
	}
	for i, q := range plan.Orders {
		if _, e = tx.Exec("INSERT INTO objective_stages VALUES(?,?,?,?,?,?, 'PLANNED')", o.ID, i, q.ID, raws[i], digest(raws[i]), contracts[i]); e != nil {
			return o, e
		}
	}
	if _, e = tx.Exec("INSERT INTO objective_decisions VALUES(?,?,?,?)", o.ID, o.Revision, o.Updated, o.LastEvaluated); e != nil {
		return o, e
	}
	return o, tx.Commit()
}

// Called only while AutonomyTick owns queueMu. Intent and publication are
// separate durable phases; both replay against the same globally unique ID.
func (p *Engine) reconcileObjectives(ctx context.Context) error {
	if !p.Config.Autonomy.ObjectiveController {
		return nil
	}
	rows, e := p.Store.DB.Query("SELECT id FROM objectives ORDER BY priority DESC,id")
	if e != nil {
		return e
	}
	var ids []string
	for rows.Next() {
		var id string
		if e = rows.Scan(&id); e != nil {
			rows.Close()
			return e
		}
		ids = append(ids, id)
	}
	e = rows.Err()
	rows.Close()
	if e != nil {
		return e
	}
	for _, id := range ids {
		o, e := p.objectiveGet(id)
		if e != nil {
			return e
		}
		if e = p.reconcileObjective(ctx, &o); e != nil {
			return e
		}
	}
	return nil
}

func (p *Engine) objectiveCompleted(id string) error {
	var state string
	if e := p.Store.DB.QueryRow("SELECT state FROM queue_items WHERE id=?", id).Scan(&state); e != nil {
		return e
	}
	if state != "COMPLETED" {
		return errors.New("OBJECTIVE_STAGE_NOT_COMPLETED")
	}
	j, e := p.Store.Get(id)
	if e != nil {
		return e
	}
	if j.State != "ACCEPTED" {
		return errors.New("OBJECTIVE_ACCEPTANCE_REQUIRED")
	}
	if e = p.VerifyEvidence(j); e != nil {
		return e
	}
	_, e = p.QueueReceiptEvidence(id)
	return e
}

func (p *Engine) objectiveBlock(o *Objective, reason string) error {
	o.Status = "BLOCKED"
	o.Blocker = reason
	return p.objectiveSave(o, "BLOCKED: "+reason, false)
}

func (p *Engine) reconcileObjective(ctx context.Context, o *Objective) error {
	if o.Status == "CANCELLED" {
		if o.Current != "" {
			p.mu.Lock()
			_, active := p.cancels[o.Current]
			p.mu.Unlock()
			if active {
				return p.Cancel(o.Current)
			}
		}
		return nil
	}
	if o.Status == "COMPLETED" || o.Status == "BLOCKED" || o.Status == "WAITING_FOR_EXTERNAL_ORCHESTRATOR" {
		return nil
	}
	if o.Current != "" {
		var state, reason string
		e := p.Store.DB.QueryRow("SELECT state,reason FROM queue_items WHERE id=?", o.Current).Scan(&state, &reason)
		if e != nil {
			return e
		}
		j, je := p.Store.Get(o.Current)
		if je != nil && !errors.Is(je, sql.ErrNoRows) {
			return je
		}
		if je == nil && j.State != "ACCEPTED" && failureClass(j.Reason) == "CODEX_QUOTA_EXHAUSTED" {
			if e = p.holdCodexExhaustion(j); e != nil {
				return e
			}
			h, e := p.objectiveHandoff(j)
			if e != nil {
				return e
			}
			o.Handoff = &h
			o.Status = "WAITING_FOR_EXTERNAL_ORCHESTRATOR"
			o.Blocker = "CODEX_QUOTA_EXHAUSTED"
			return p.objectiveSave(o, "CODEX_QUOTA_EXHAUSTED: external handoff retained", false)
		}
		switch state {
		case "COMPLETED":
			if e = p.objectiveCompleted(o.Current); e != nil {
				return p.objectiveBlock(o, e.Error())
			}
			tx, e := p.Store.DB.Begin()
			if e != nil {
				return e
			}
			defer tx.Rollback()
			if _, e = tx.Exec("UPDATE objective_stages SET state='COMPLETE' WHERE objective_id=? AND stage=? AND work_id=? AND state='QUEUED'", o.ID, o.Next, o.Current); e != nil {
				return e
			}
			o.Next++
			o.Current = ""
			if o.Next == o.Total {
				o.Status = "COMPLETED"
			} else if o.StopAfterCurrent || o.Paused {
				o.Status = "PAUSED"
				o.Paused = true
			}
			if e = saveObjective(tx, o, "STAGE_COMPLETED", true); e != nil {
				return e
			}
			return tx.Commit()
		case "QUEUED", "RUNNING", "RETRY_WAIT", "FINALIZING":
			// Existing repair classification/attempt limits own this work. Never
			// synthesize a repair or advance from a worker's claimed PASS.
			return nil
		case "FAILED", "BLOCKED", "REVIEWED":
			return p.objectiveBlock(o, reason)
		case "WAITING_FOR_EXTERNAL_ORCHESTRATOR":
			return p.objectiveBlock(o, "EXHAUSTION_EVIDENCE_MISMATCH")
		default:
			return p.objectiveBlock(o, "UNKNOWN_QUEUE_STATE: "+state)
		}
	}
	if o.Paused || o.StopAfterCurrent || o.Status == "PAUSED" || o.Status == "PENDING" || p.setting("paused") == "true" {
		return nil
	}
	if e := p.objectiveAuthority(ctx, o.Generation); e != nil {
		return p.objectiveBlock(o, e.Error())
	}
	busy, e := p.objectiveBusy()
	if e != nil {
		return e
	}
	if busy {
		return nil
	}
	var raw []byte
	var id, hash, contract, state string
	if e = p.Store.DB.QueryRow("SELECT work_id,raw,hash,contract,state FROM objective_stages WHERE objective_id=? AND stage=?", o.ID, o.Next).Scan(&id, &raw, &hash, &contract, &state); e != nil {
		return e
	}
	q, e := p.parseQueue(raw, id)
	if e != nil {
		return p.objectiveBlock(o, e.Error())
	}
	w, e := ParseOrder([]byte(q.WorkOrderYAML))
	if e != nil {
		return e
	}
	if digest(raw) != hash || p.contract(w) != contract {
		return p.objectiveBlock(o, "OBJECTIVE_AUTHORIZATION_CONTRACT_CHANGED")
	}
	if state == "PLANNED" {
		tx, e := p.Store.DB.Begin()
		if e != nil {
			return e
		}
		defer tx.Rollback()
		if _, e = tx.Exec("UPDATE objective_stages SET state='INTENT' WHERE objective_id=? AND stage=? AND state='PLANNED'", o.ID, o.Next); e != nil {
			return e
		}
		if e = saveObjective(tx, o, "SUCCESSOR_INTENT: "+id, false); e != nil {
			return e
		}
		return tx.Commit()
	}
	if state != "INTENT" {
		return p.objectiveBlock(o, "UNKNOWN_SUCCESSOR_INTENT_STATE: "+state)
	}
	// File publication is non-authoritative. No worker can consume it until
	// the existing queue row and objective pointer commit together below.
	path, e := p.queuePath("pending", id)
	if e != nil {
		return e
	}
	if old, er := os.ReadFile(path); er == nil {
		if regularPath(filepath.Dir(path), filepath.Base(path)) != nil || digest(old) != hash {
			return p.objectiveBlock(o, "OBJECTIVE_QUEUE_INPUT_CHANGED")
		}
	} else if os.IsNotExist(er) {
		if e = durableNew(path, raw); e != nil {
			return e
		}
	} else {
		return er
	}
	if e = p.objectiveAuthority(ctx, o.Generation); e != nil {
		return p.objectiveBlock(o, e.Error())
	}
	tx, e := p.Store.DB.Begin()
	if e != nil {
		return e
	}
	defer tx.Rollback()
	if e = p.objectiveBindQueue(tx, id, hash, raw); e != nil {
		return e
	}
	if _, e = tx.Exec("UPDATE objective_stages SET state='QUEUED' WHERE objective_id=? AND stage=? AND state='INTENT'", o.ID, o.Next); e != nil {
		return e
	}
	o.Current = id
	if e = saveObjective(tx, o, "SUCCESSOR_QUEUED: "+id, true); e != nil {
		return e
	}
	return tx.Commit()
}

func (p *Engine) objectiveBindQueue(tx *sql.Tx, id, hash string, raw []byte) error {
	var existingHash, kind, state, mode, authorization string
	var existingRaw []byte

	e := tx.QueryRow(
		"SELECT hash,raw,kind,state,mode,authorization FROM queue_items WHERE id=?",
		id,
	).Scan(
		&existingHash,
		&existingRaw,
		&kind,
		&state,
		&mode,
		&authorization,
	)

	if errors.Is(e, sql.ErrNoRows) {
		_, e = tx.Exec(
			"INSERT INTO queue_items(id,hash,raw,kind,state,mode,authorization,updated) VALUES(?,?,?,'source','QUEUED','source','operator',?)",
			id,
			hash,
			raw,
			now(),
		)
		return e
	}
	if e != nil {
		return e
	}

	if existingHash != hash ||
		string(existingRaw) != string(raw) ||
		kind != "source" ||
		state != "QUEUED" ||
		mode != "source" ||
		authorization != "operator" {
		return errors.New("OBJECTIVE_QUEUE_IDENTITY_CONFLICT")
	}

	return nil
}
func (p *Engine) objectiveBusy() (bool, error) {
	var n int
	e := p.Store.DB.QueryRow("SELECT (SELECT count(*) FROM queue_items WHERE state NOT IN ('COMPLETED','REVIEWED'))+(SELECT count(*) FROM worker_leases)+(SELECT count(*) FROM process_records WHERE finished=0)+(SELECT count(*) FROM work_orders WHERE state IN ('DISPATCHED','ENGINEERING','CANDIDATE','ACCEPTING'))").Scan(&n)
	return n != 0, e
}

// Gate every normal start/retry of objective work, including queue rows
// published before a pause arrived. Called under the same queue mutex.
func (p *Engine) objectiveMayStart(ctx context.Context, id string) (bool, error) {
	if !p.Config.Autonomy.ObjectiveController {
		var tables, managed int
		if e := p.Store.DB.QueryRow("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='objective_stages'").Scan(&tables); e != nil {
			return false, e
		}
		if tables == 0 {
			return true, nil
		}
		if e := p.Store.DB.QueryRow("SELECT count(*) FROM objective_stages WHERE work_id=?", id).Scan(&managed); e != nil {
			return false, e
		}
		return managed == 0, nil
	}
	var oid, hash, contract, state string
	var raw []byte
	e := p.Store.DB.QueryRow("SELECT objective_id,raw,hash,contract,state FROM objective_stages WHERE work_id=?", id).Scan(&oid, &raw, &hash, &contract, &state)
	if errors.Is(e, sql.ErrNoRows) {
		return true, nil
	}
	if e != nil {
		return false, e
	}
	o, e := p.objectiveGet(oid)
	if e != nil {
		return false, e
	}
	if o.Status != "RUNNING" || o.Paused || o.Current != id {
		return false, nil
	}
	if o.StopAfterCurrent {
		j, e := p.Store.Get(id)
		if errors.Is(e, sql.ErrNoRows) {
			return false, nil
		}
		if e != nil {
			return false, e
		}
		if j.Attempt == 0 {
			return false, nil
		}
	}
	if e = p.objectiveAuthority(ctx, o.Generation); e != nil {
		return false, e
	}
	q, e := p.parseQueue(raw, id)
	if e != nil {
		return false, e
	}
	w, e := ParseOrder([]byte(q.WorkOrderYAML))
	if e != nil {
		return false, e
	}
	var queueHash string
	if e = p.Store.DB.QueryRow("SELECT hash FROM queue_items WHERE id=?", id).Scan(&queueHash); e != nil {
		return false, e
	}
	if state != "QUEUED" || digest(raw) != hash || queueHash != hash || p.contract(w) != contract {
		return false, errors.New("OBJECTIVE_AUTHORIZATION_CONTRACT_CHANGED")
	}
	return true, nil
}
