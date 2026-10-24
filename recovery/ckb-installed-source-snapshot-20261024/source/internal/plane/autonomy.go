package plane

import (
	"context"
	"crypto/rand"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

const AutonomyVersion = "ckb-plane-autonomy-r1"
const queueSchema = "ckb-plane.queue-workorder.v1"

type AutonomyConfig struct {
	MindPalaceAutoDiscovery            bool     `yaml:"mind_palace_auto_discovery"`
	MindPalaceDiscoveryIntervalSeconds int      `yaml:"mind_palace_discovery_interval_seconds"`
	ObjectiveController                bool     `yaml:"objective_controller"`
	PineSuccessorController            bool     `yaml:"pine_successor_controller"`
	Enabled                            bool     `yaml:"enabled"`
	PollSeconds                        int      `yaml:"poll_seconds"`
	RetrySeconds                       int      `yaml:"retry_seconds"`
	MaxNoProgressSeconds               int      `yaml:"max_no_progress_seconds"`
	RemoteControl                      bool     `yaml:"remote_control"`
	Repository                         string   `yaml:"repository"`
	RepositoryID                       int64    `yaml:"repository_id"`
	OriginalWorkflows                  []string `yaml:"original_workflows"`
}

type QueueOrder struct {
	Schema        string   `json:"schema"`
	ID            string   `json:"id"`
	LogicalStage  string   `json:"logical_stage"`
	Kind          string   `json:"kind"` // source or proof; proposal imports are always proof
	WorkOrderYAML string   `json:"work_order_yaml,omitempty"`
	Dependencies  []string `json:"dependencies,omitempty"`
	SourceRepo    string   `json:"source_repo,omitempty"`
	BaselineRef   string   `json:"baseline_ref,omitempty"`
	BaselineSHA   string   `json:"baseline_sha,omitempty"`
}

type QueueItem struct {
	ID            string `json:"id"`
	Hash          string `json:"sha256"`
	Kind          string `json:"kind"`
	State         string `json:"state"`
	Mode          string `json:"mode"`
	Authorization string `json:"authorization"`
	Reason        string `json:"reason"`
	Updated       string `json:"updated_at"`
	NextRetry     string `json:"next_retry_at,omitempty"`
	Receipt       string `json:"receipt,omitempty"`
}

type QueueResult struct {
	QueueStateBefore      string `json:"queue_state_before"`
	QueueStateAfter       string `json:"queue_state_after"`
	WorkOrderStateBefore  string `json:"work_order_state_before"`
	WorkOrderStateAfter   string `json:"work_order_state_after"`
	Blocker               string `json:"blocker"`
	WorkerLaunchAttempted bool   `json:"worker_launch_attempted"`
	SourceHygieneRan      bool   `json:"source_hygiene_ran"`
	Schema                string `json:"schema"`
	RunID                 string `json:"run_id"`
	WorkOrderID           string `json:"work_order_id"`
	InputSHA256           string `json:"input_sha256"`
	Mode                  string `json:"mode"`
	Authorization         string `json:"authorization"`
	Disposition           string `json:"disposition"`
	Reason                string `json:"reason"`
	BaselineRef           string `json:"baseline_ref,omitempty"`
	BaselineSHA           string `json:"baseline_sha,omitempty"`
	Workspace             string `json:"workspace,omitempty"`
	Evidence              string `json:"evidence"`
	ObservedAt            string `json:"observed_at"`
	ProductionAccepted    bool   `json:"production_accepted"`
}

func (p *Engine) initAutonomy() error {
	_, e := p.Store.DB.Exec(`
CREATE TABLE IF NOT EXISTS plane_schema(version INTEGER PRIMARY KEY,created TEXT NOT NULL);
INSERT OR IGNORE INTO plane_schema VALUES(1,datetime('now'));
CREATE TABLE IF NOT EXISTS queue_items(id TEXT PRIMARY KEY,hash TEXT NOT NULL,raw BLOB NOT NULL,kind TEXT NOT NULL,state TEXT NOT NULL,mode TEXT NOT NULL DEFAULT '',authorization TEXT NOT NULL DEFAULT 'none',reason TEXT NOT NULL DEFAULT '',updated TEXT NOT NULL,next_retry TEXT NOT NULL DEFAULT '',receipt TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS queue_receipts(work_order_id TEXT PRIMARY KEY,hash TEXT NOT NULL,raw BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS recovery_decisions(work_order_id TEXT,attempt INTEGER,action TEXT,reason TEXT,created TEXT,PRIMARY KEY(work_order_id,attempt));
CREATE TABLE IF NOT EXISTS worker_progress(work_order_id TEXT PRIMARY KEY,observed TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS control_requests(id TEXT PRIMARY KEY,hash TEXT NOT NULL,result BLOB,state TEXT NOT NULL);
INSERT OR IGNORE INTO settings VALUES('autonomy_authority','original');
INSERT OR IGNORE INTO settings VALUES('autonomy_generation','0');
INSERT OR IGNORE INTO settings VALUES('autonomy_heartbeat','');
INSERT OR IGNORE INTO settings VALUES('autonomy_status','NOT_STARTED');
`)
	if e == nil {
		_, e = p.Store.DB.Exec("INSERT OR IGNORE INTO settings VALUES('installation_id',?)", randomID())
	}
	return e
}

func randomID() string {
	b := make([]byte, 16)
	if _, e := rand.Read(b); e != nil {
		panic(e)
	}
	return hex.EncodeToString(b)
}
func (p *Engine) setting(key string) string {
	var v string
	_ = p.Store.DB.QueryRow("SELECT value FROM settings WHERE key=?", key).Scan(&v)
	return v
}
func (p *Engine) setSetting(key, value string) error {
	_, e := p.Store.DB.Exec("INSERT OR REPLACE INTO settings VALUES(?,?)", key, value)
	return e
}

func durableNew(path string, raw []byte) error {
	if e := os.MkdirAll(filepath.Dir(path), 0700); e != nil {
		return e
	}
	f, e := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if e != nil {
		return e
	}
	_, e = f.Write(raw)
	if e == nil {
		e = f.Sync()
	}
	ce := f.Close()
	if e != nil {
		return e
	}
	return ce
}

func (p *Engine) queuePath(folder, id string) (string, error) {
	if !safeID.MatchString(id) {
		return "", errors.New("WORK_ORDER_ID_INVALID")
	}
	path := filepath.Join(p.Root, "workorders", folder, id+".json")
	if e := bridgeContained(p.Root, path); e != nil {
		return "", e
	}
	return path, nil
}

func (p *Engine) parseQueue(raw []byte, id string) (QueueOrder, error) {
	var h struct {
		Schema string `json:"schema"`
	}
	if e := json.Unmarshal(raw, &h); e != nil {
		return QueueOrder{}, errors.New("WORK_ORDER_JSON_INVALID")
	}
	var q QueueOrder
	if h.Schema == "ckb-plane.operator.work_order_proposal.v2" {
		// Legacy proposals are proof inputs only. Never infer a source authorization
		// or adopt a baseline from embedded roadmap prose.
		var v map[string]json.RawMessage
		if e := bridgeDecode(raw, &v); e != nil {
			return q, e
		}
		var schemaID, ref, sha, source, status string
		for k, dst := range map[string]*string{"stage_id": &schemaID, "required_baseline_ref": &ref, "required_baseline_sha": &sha, "worker_source_clone": &source, "status": &status} {
			if e := json.Unmarshal(v[k], dst); e != nil {
				return q, fmt.Errorf("PROPOSAL_FIELD_INVALID: %s", k)
			}
		}
		for _, k := range []string{"worker_launch_authorized", "candidate_acceptance_authorized", "runtime_launch_allowed", "deployment_allowed", "accepted_ref_promotion_allowed"} {
			var b bool
			if e := json.Unmarshal(v[k], &b); e != nil || b {
				return q, errors.New("PROPOSAL_POLICY_INVALID")
			}
		}
		if status != "SAFE_TO_PROPOSE" || schemaID != id {
			return q, errors.New("PROPOSAL_ID_OR_STATUS_INVALID")
		}
		repo := ""
		for name, r := range p.Config.Repos {
			if r.Mode == "engineering" && strings.EqualFold(filepath.Clean(r.LocalPath), filepath.Clean(source)) {
				if repo != "" {
					return q, errors.New("SOURCE_REGISTRY_AMBIGUOUS")
				}
				repo = name
			}
		}
		if repo == "" {
			return q, errors.New("PROPOSAL_SOURCE_NOT_REGISTERED")
		}
		q = QueueOrder{Schema: queueSchema, ID: id, LogicalStage: id, Kind: "proof", SourceRepo: repo, BaselineRef: ref, BaselineSHA: sha}
	} else {
		if e := bridgeDecode(raw, &q); e != nil {
			return q, e
		}
	}
	if q.Schema != queueSchema || q.ID != id || !safeID.MatchString(q.LogicalStage) {
		return q, errors.New("QUEUE_CONTRACT_INVALID")
	}
	seen := map[string]bool{}
	for _, dep := range q.Dependencies {
		if !safeID.MatchString(dep) || dep == id || seen[dep] {
			return q, errors.New("DEPENDENCY_INVALID")
		}
		seen[dep] = true
	}
	if q.Kind == "source" {
		w, e := ParseOrder([]byte(q.WorkOrderYAML))
		if e != nil {
			return q, e
		}
		if err := validateWorkOrderPreflight(w); err != nil {
			return q, err
		}
		if w.ID != q.ID || len(w.RequiredTests.FocusedGo) == 0 {
			return q, errors.New("SOURCE_ID_AND_FOCUSED_TEST_REQUIRED")
		}
		if q.SourceRepo != "" || q.BaselineRef != "" || q.BaselineSHA != "" {
			return q, errors.New("DUPLICATE_SOURCE_CONTRACT")
		}
	} else if q.Kind == "proof" {
		if q.WorkOrderYAML != "" || !safeID.MatchString(q.SourceRepo) || !safePath(q.BaselineRef) || !strings.HasPrefix(q.BaselineRef, "accepted/") || !shaRE.MatchString(q.BaselineSHA) {
			return q, errors.New("PROOF_CONTRACT_INVALID")
		}
	} else {
		return q, errors.New("QUEUE_KIND_INVALID")
	}
	return q, nil
}

func (p *Engine) QueueValidate(id string) (QueueOrder, error) {
	path, e := p.queuePath("pending", id)
	if e != nil {
		return QueueOrder{}, e
	}
	if e = regularPath(filepath.Dir(path), filepath.Base(path)); e != nil {
		return QueueOrder{}, e
	}
	raw, e := os.ReadFile(path)
	if e != nil {
		return QueueOrder{}, e
	}
	return p.parseQueue(raw, id)
}

func (p *Engine) QueueList() ([]QueueItem, error) {
	rows, e := p.Store.DB.Query("SELECT id,hash,kind,state,mode,authorization,reason,updated,next_retry,receipt FROM queue_items ORDER BY id")
	if e != nil {
		return nil, e
	}
	out := []QueueItem{}
	seen := map[string]bool{}
	for rows.Next() {
		var q QueueItem
		if e = rows.Scan(&q.ID, &q.Hash, &q.Kind, &q.State, &q.Mode, &q.Authorization, &q.Reason, &q.Updated, &q.NextRetry, &q.Receipt); e != nil {
			rows.Close()
			return nil, e
		}
		out = append(out, q)
		seen[q.ID] = true
	}
	e = rows.Err()
	rows.Close()
	if e != nil {
		return nil, e
	}
	entries, e := os.ReadDir(filepath.Join(p.Root, "workorders", "pending"))
	if os.IsNotExist(e) {
		return out, nil
	}
	if e != nil {
		return nil, e
	}
	for _, f := range entries {
		if !strings.HasSuffix(f.Name(), ".json") {
			continue
		}
		id := strings.TrimSuffix(f.Name(), ".json")
		if seen[id] {
			continue
		}
		item := QueueItem{ID: id, State: "PENDING", Authorization: "none"}
		q, er := p.QueueValidate(id)
		if er != nil {
			item.State = "INVALID"
			item.Reason = er.Error()
		} else {
			item.Kind = q.Kind
			if raw, er := os.ReadFile(filepath.Join(p.Root, "workorders", "pending", id+".json")); er == nil {
				item.Hash = digest(raw)
			}
		}
		out = append(out, item)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out, nil
}

func (p *Engine) QueueSubmit(raw []byte) error {
	var h struct {
		ID string `json:"id"`
	}
	if e := json.Unmarshal(raw, &h); e != nil {
		return e
	}
	if _, e := p.parseQueue(raw, h.ID); e != nil {
		return e
	}
	p.queueMu.Lock()
	defer p.queueMu.Unlock()
	path, e := p.queuePath("pending", h.ID)
	if e != nil {
		return e
	}
	if old, e := os.ReadFile(path); e == nil {
		if digest(old) == digest(raw) {
			return nil
		}
		return errors.New("WORK_ORDER_ID_CONTENT_CONFLICT")
	}
	if p.Config.Autonomy.ObjectiveController {
		var reserved int
		if e = p.Store.DB.QueryRow(
			"SELECT count(*) FROM objective_stages WHERE work_id=?", h.ID,
		).Scan(&reserved); e != nil {
			return e
		}
		if reserved != 0 {
			return errors.New(
				"OBJECTIVE_WORK_ID_RESERVED",
			)
		}
	}

	var n int
	if e = p.Store.DB.QueryRow("SELECT (SELECT count(*) FROM queue_items WHERE id=?) + (SELECT count(*) FROM work_orders WHERE id=?)", h.ID, h.ID).Scan(&n); e != nil {
		return e
	}
	if n != 0 {
		return errors.New("WORK_ORDER_ID_ALREADY_RECORDED")
	}
	for _, dir := range []string{"completed", "failed"} {
		dst, er := p.queuePath(dir, h.ID)
		if er != nil {
			return er
		}
		if _, er = os.Lstat(dst); !os.IsNotExist(er) {
			return errors.New("QUEUE_DESTINATION_CONFLICT")
		}
	}
	return durableNew(path, raw)
}

func (p *Engine) queueClaim(id, auth, mode string, expected ...string) (QueueOrder, []byte, error) {
	path, e := p.queuePath("pending", id)
	if e != nil {
		return QueueOrder{}, nil, e
	}
	if e = regularPath(filepath.Dir(path), filepath.Base(path)); e != nil {
		return QueueOrder{}, nil, e
	}
	raw, e := os.ReadFile(path)
	if e != nil {
		return QueueOrder{}, nil, e
	}
	if len(expected) > 0 && expected[0] != "" && digest(raw) != expected[0] {
		return QueueOrder{}, nil, errors.New("WORK_ORDER_CONTENT_CHANGED")
	}
	q, e := p.parseQueue(raw, id)
	if e != nil {
		return q, raw, e
	}
	if auth != "none" && ((mode == "source") != (q.Kind == "source")) {
		return q, raw, errors.New("QUEUE_KIND_MODE_MISMATCH")
	}
	for _, dir := range []string{"completed", "failed"} {
		dst, er := p.queuePath(dir, id)
		if er != nil {
			return q, raw, er
		}
		if _, er = os.Lstat(dst); !os.IsNotExist(er) {
			return q, raw, errors.New("QUEUE_DESTINATION_CONFLICT")
		}
	}
	var hash, oldAuth, oldMode, state string
	e = p.Store.DB.QueryRow("SELECT hash,authorization,mode,state FROM queue_items WHERE id=?", id).Scan(&hash, &oldAuth, &oldMode, &state)
	if e == nil {
		if hash != digest(raw) {
			return q, raw, errors.New("WORK_ORDER_ID_CONTENT_CONFLICT")
		}
		if oldAuth != auth || oldMode != mode {
			return q, raw, errors.New("QUEUE_AUTHORIZATION_CONFLICT")
		}
		if state == "BLOCKED" && q.Kind == "proof" {
			_, e = p.Store.DB.Exec("UPDATE queue_items SET state='QUEUED',updated=? WHERE id=?", now(), id)
			return q, raw, e
		}
		if state != "QUEUED" {
			return q, raw, fmt.Errorf("QUEUE_ALREADY_%s", state)
		}
		return q, raw, nil
	}
	if !errors.Is(e, sql.ErrNoRows) {
		return q, raw, e
	}
	_, e = p.Store.DB.Exec("INSERT INTO queue_items(id,hash,raw,kind,state,authorization,mode,updated) VALUES(?,?,?,?,'QUEUED',?,?,?)", id, digest(raw), raw, q.Kind, auth, mode, now())
	return q, raw, e
}

func (p *Engine) refusal(id, auth, mode, reason string, consume bool) (QueueResult, error) {
	r := QueueResult{Schema: "ckb-plane.queue-result.v1", RunID: randomID(), WorkOrderID: id, Mode: mode, Authorization: auth, Disposition: "pending", Reason: reason, ObservedAt: now()}
	r.Blocker = reason
	r.QueueStateBefore, r.WorkOrderStateBefore = p.queueStates(id)
	r.QueueStateAfter, r.WorkOrderStateAfter = r.QueueStateBefore, r.WorkOrderStateBefore
	path, e := p.queuePath("pending", id)
	if e != nil {
		return r, e
	}
	raw, e := os.ReadFile(path)
	if e != nil {
		return r, e
	}
	r.InputSHA256 = digest(raw)
	r.Evidence = filepath.Join(p.Root, "evidence", "queue", id, r.RunID)
	if consume {
		r.Disposition = "failed"
		r.QueueStateAfter = "FAILED"
	}
	b, _ := json.MarshalIndent(r, "", "  ")
	if e = durableNew(filepath.Join(r.Evidence, "status.json"), b); e != nil {
		return r, e
	}
	if consume {
		if _, _, e = p.queueClaim(id, auth, mode); e != nil {
			return r, e
		}
		if e = p.queueFinish(id, r); e != nil {
			return r, e
		}
	}
	return r, errors.New(reason)
}

func (p *Engine) QueueRun(ctx context.Context, id, auth, mode string, consume bool, expected ...string) (QueueResult, error) {
	p.queueMu.Lock()
	defer p.queueMu.Unlock()
	if auth != "none" && auth != "test" && auth != "operator" {
		return p.refusal(id, auth, mode, "AUTHORIZATION_INVALID", false)
	}
	if mode != "dry-run" && mode != "controlled-proof" && mode != "source" {
		return p.refusal(id, auth, mode, "MODE_INVALID", false)
	}
	// No baseline/repository access precedes unauthorized refusal.
	if auth == "none" {
		return p.refusal(id, auth, mode, "REFUSED_WITHOUT_AUTHORIZATION", consume)
	}
	if auth == "test" && mode == "source" || auth == "operator" && mode != "source" {
		return p.refusal(id, auth, mode, "AUTHORIZATION_MODE_MISMATCH", false)
	}
	if mode == "source" {
		if e := p.sourceAuthority(ctx); e != nil {
			return p.refusal(id, auth, mode, e.Error(), false)
		}
	}
	q, raw, e := p.queueClaim(id, auth, mode, expected...)
	if e != nil {
		return p.refusal(id, auth, mode, e.Error(), false)
	}
	if mode == "source" {
		if q.Kind != "source" {
			return p.refusal(id, auth, mode, "PROPOSAL_IS_NOT_EXECUTABLE_SOURCE", false)
		}
		if e = p.sourceAuthority(ctx); e != nil {
			return p.refusal(id, auth, mode, e.Error(), false)
		}
		return QueueResult{WorkOrderID: id, Disposition: "queued", Mode: mode, Authorization: auth}, nil
	}
	if q.Kind != "proof" {
		return p.refusal(id, auth, mode, "PROOF_CONTRACT_REQUIRED", false)
	}
	return p.runProof(ctx, q, raw, auth, mode)
}

func (p *Engine) runProof(ctx context.Context, q QueueOrder, raw []byte, auth, mode string) (QueueResult, error) {
	r := QueueResult{Schema: "ckb-plane.queue-result.v1", RunID: randomID(), WorkOrderID: q.ID, InputSHA256: digest(raw), Mode: mode, Authorization: auth, Disposition: "pending", ObservedAt: now(), BaselineRef: q.BaselineRef, BaselineSHA: q.BaselineSHA}
	r.Evidence = filepath.Join(p.Root, "evidence", "queue", q.ID, r.RunID)
	r.QueueStateBefore, r.WorkOrderStateBefore = p.queueStates(q.ID)
	r.QueueStateAfter, r.WorkOrderStateAfter = r.QueueStateBefore, r.WorkOrderStateBefore
	fail := func(reason string) (QueueResult, error) {
		r.Reason = reason
		r.Blocker = reason
		r.QueueStateAfter = "BLOCKED"
		b, _ := json.MarshalIndent(r, "", "  ")
		if e := durableNew(filepath.Join(r.Evidence, "status.json"), b); e != nil {
			return r, e
		}
		_, _ = p.Store.DB.Exec("UPDATE queue_items SET state='BLOCKED',reason=?,updated=?,receipt=? WHERE id=?", reason, now(), r.Evidence, q.ID)
		return r, errors.New(reason)
	}
	seed, ok := p.Config.Repos[q.SourceRepo]
	if !ok {
		return fail("SOURCE_NOT_REGISTERED")
	}
	if pathWithin(seed.LocalPath, p.Root) || pathWithin(p.Root, seed.LocalPath) {
		return fail("SOURCE_WORKSPACE_OVERLAP")
	}
	w := WorkOrder{}
	w.ID = q.ID
	w.Baseline.Ref = q.BaselineRef
	w.Baseline.SHA = q.BaselineSHA
	w.Worker.Branch = "codex/plane-proof"
	if e := checkRepo(p.Config.Tools.Git, seed, w); e != nil {
		return fail(e.Error())
	}
	before, e := p.profileWorkspaceRepoState(ctx, seed.LocalPath)
	if e != nil {
		return fail("SOURCE_STATE_UNAVAILABLE")
	}
	beforeJSON, _ := json.MarshalIndent(before, "", "  ")
	if e = durableNew(filepath.Join(r.Evidence, "source-before.json"), beforeJSON); e != nil {
		return fail("EVIDENCE_WRITE_FAILED")
	}
	// Private repository uniqueness is supplied by the full random run ID.
	// Avoid repeating the work-order ID in Windows Git metadata paths.
	root := filepath.Join(p.Root, "workspaces", "q", r.RunID)
	if e = bridgeContained(p.Root, root); e != nil {
		return fail(e.Error())
	}
	if mode == "controlled-proof" {
		r.Workspace, _, e = prepare(ctx, p.Config.Tools.Git, seed.LocalPath, root, w)
	} else {
		r.Workspace = root
		e = os.MkdirAll(root, 0700)
	}
	if e != nil {
		detail := map[string]any{"error": e.Error(), "workspace_root": root, "baseline_ref": q.BaselineRef, "baseline_sha": q.BaselineSHA}
		var gitFailure *gitCommandError
		if errors.As(e, &gitFailure) {
			detail["git_operation"] = gitFailure.operation
			detail["git_output"] = gitFailure.output
		}
		diagnostic, _ := json.MarshalIndent(detail, "", "  ")
		if er := durableNew(filepath.Join(r.Evidence, "materialization-error.json"), diagnostic); er != nil {
			return fail("EVIDENCE_WRITE_FAILED")
		}
		return fail("WORKSPACE_MATERIALIZATION_FAILED: " + e.Error())
	}
	if e = durableNew(filepath.Join(r.Workspace, "CKB_PLANE_QUEUE_PROOF.txt"), []byte("Queue plumbing proof only. No production stage accepted.\n")); e != nil {
		return fail("PROOF_WRITE_FAILED")
	}
	after, e := p.profileWorkspaceRepoState(ctx, seed.LocalPath)
	if e != nil || jsonText(before) != jsonText(after) {
		return fail("SOURCE_CHANGED_DURING_PROOF")
	}
	afterJSON, _ := json.MarshalIndent(after, "", "  ")
	if e = durableNew(filepath.Join(r.Evidence, "source-after.json"), afterJSON); e != nil {
		return fail("EVIDENCE_WRITE_FAILED")
	}
	r.Disposition = "completed"
	r.Reason = "TEST_PROOF_PASSED"
	if e = p.queueFinish(q.ID, r); e != nil {
		return r, e
	}
	return r, nil
}

// Journal terminal intent before filesystem delivery. Recovery repeats delivery,
// never worker execution. Destination contents must match the original bytes.
func (p *Engine) queueFinish(id string, r QueueResult) error {
	var raw []byte
	var hash string
	if e := p.Store.DB.QueryRow("SELECT raw,hash FROM queue_items WHERE id=?", id).Scan(&raw, &hash); e != nil {
		return e
	}
	if r.InputSHA256 == "" {
		r.InputSHA256 = hash
	}
	if hash != r.InputSHA256 {
		return errors.New("QUEUE_RESULT_HASH_MISMATCH")
	}
	if digest(raw) != hash {
		return errors.New("QUEUE_RAW_HASH_MISMATCH")
	}
	if r.QueueStateBefore == "" {
		r.QueueStateBefore, r.WorkOrderStateBefore = p.queueStates(id)
	}
	r.QueueStateAfter = strings.ToUpper(r.Disposition)
	_, r.WorkOrderStateAfter = p.queueStates(id)
	if r.Disposition == "failed" {
		r.Blocker = r.Reason
	}
	var launched int
	if e := p.Store.DB.QueryRow("SELECT count(*) FROM events WHERE work_order_id=? AND attempt_id=(SELECT attempt FROM work_orders WHERE id=?) AND type='WORKER_LAUNCH_ATTEMPTED'", id, id).Scan(&launched); e != nil {
		return e
	}
	r.WorkerLaunchAttempted = launched > 0
	if r.RunID == "" {
		r.RunID = randomID()
	}
	if r.ObservedAt == "" {
		r.ObservedAt = now()
	}
	if r.Schema == "" {
		r.Schema = "ckb-plane.queue-result.v1"
	}
	if r.Evidence == "" {
		r.Evidence = filepath.Join(p.Root, "evidence", "queue", id, r.RunID)
	}
	data, e := json.MarshalIndent(r, "", "  ")
	if e != nil {
		return e
	}
	receipt := filepath.Join(r.Evidence, "queue-result.json")
	if e = bridgeContained(p.Root, receipt); e != nil {
		return e
	}
	if e = durableNew(receipt, data); e != nil {
		if old, er := os.ReadFile(receipt); er != nil || string(old) != string(data) {
			return e
		}
	}
	tx, e := p.Store.DB.Begin()
	if e != nil {
		return e
	}
	defer tx.Rollback()
	if _, e = tx.Exec("INSERT OR REPLACE INTO queue_receipts VALUES(?,?,?)", id, digest(data), data); e != nil {
		return e
	}
	if _, e = tx.Exec("UPDATE queue_items SET state='FINALIZING',reason=?,receipt=?,updated=? WHERE id=?", r.Disposition, receipt, now(), id); e != nil {
		return e
	}
	if e = tx.Commit(); e != nil {
		return e
	}
	return p.deliverQueue(id, raw, hash, r.Disposition, receipt)
}

func (p *Engine) deliverQueue(id string, raw []byte, hash, disposition, receipt string) error {
	if disposition != "completed" && disposition != "failed" {
		return errors.New("QUEUE_DISPOSITION_INVALID")
	}
	var receiptRaw []byte
	var receiptHash string
	if e := p.Store.DB.QueryRow("SELECT hash,raw FROM queue_receipts WHERE work_order_id=?", id).Scan(&receiptHash, &receiptRaw); e != nil {
		return errors.New("QUEUE_RECEIPT_MISSING")
	}
	if digest(receiptRaw) != receiptHash {
		return errors.New("QUEUE_RECEIPT_CORRUPT")
	}
	var result QueueResult
	if e := json.Unmarshal(receiptRaw, &result); e != nil || result.InputSHA256 != hash || result.Disposition != disposition {
		return errors.New("QUEUE_RECEIPT_MISMATCH")
	}
	if e := bridgeContained(p.Root, receipt); e != nil {
		return e
	}
	if old, e := os.ReadFile(receipt); os.IsNotExist(e) {
		if e = durableNew(receipt, receiptRaw); e != nil {
			return e
		}
	} else if e != nil || digest(old) != receiptHash {
		return errors.New("QUEUE_RECEIPT_CHANGED")
	}
	src, e := p.queuePath("pending", id)
	if e != nil {
		return e
	}
	dst, e := p.queuePath(disposition, id)
	if e != nil {
		return e
	}
	if b, er := os.ReadFile(src); er == nil && digest(b) != hash {
		return errors.New("QUEUE_INPUT_CHANGED_DURING_RUN")
	} else if er != nil && !os.IsNotExist(er) {
		return er
	}
	if e = durableNew(dst, raw); e != nil {
		b, er := os.ReadFile(dst)
		if er != nil || digest(b) != hash {
			return errors.New("QUEUE_DESTINATION_CONFLICT")
		}
	}
	if e = os.Remove(src); e != nil && !os.IsNotExist(e) {
		return e
	}
	_, e = p.Store.DB.Exec("UPDATE queue_items SET state=?,reason=?,receipt=?,updated=? WHERE id=? AND state='FINALIZING'", strings.ToUpper(disposition), result.Reason, receipt, now(), id)
	return e
}

func (p *Engine) AutonomyStatus() (map[string]any, error) {
	queue, e := p.QueueList()
	if e != nil {
		return nil, e
	}
	jobs, e := p.Store.List()
	if e != nil {
		return nil, e
	}
	type jobView struct {
		ID                     string `json:"id"`
		State                  string `json:"state"`
		Attempt                int    `json:"attempt"`
		WorkerLaunches         int    `json:"worker_launches"`
		AttemptBudget          int    `json:"attempt_budget"`
		AttemptBudgetRemaining int    `json:"attempt_budget_remaining"`
		Reason                 string `json:"reason"`
		Workspace              string `json:"workspace,omitempty"`
		Evidence               string `json:"evidence,omitempty"`
		LastEvent              string `json:"last_event,omitempty"`
	}
	summaries := []jobView{}
	for _, j := range jobs {
		consumed, er := p.consumedWorkerAttempts(j.ID)
		if er != nil {
			return nil, er
		}
		remaining := p.retryEffectiveBudgetNow() - consumed
		if remaining < 0 {
			remaining = 0
		}
		var lastEvent string
		_ = p.Store.DB.QueryRow("SELECT type FROM events WHERE work_order_id=? ORDER BY id DESC LIMIT 1", j.ID).Scan(&lastEvent)
		summaries = append(summaries, jobView{ID: j.ID, State: j.State, Attempt: j.Attempt, WorkerLaunches: consumed, AttemptBudget: p.retryEffectiveBudgetNow(), AttemptBudgetRemaining: remaining, Reason: j.Reason, Workspace: j.Workspace, Evidence: j.Evidence, LastEvent: lastEvent})
	}
	blockers, e := p.queueBlockers(queue)
	if e != nil {
		return nil, e
	}
	heartbeat := p.setting("autonomy_heartbeat")
	heartbeatStale := autonomyHeartbeatStale(heartbeat, p.Config.Autonomy.PollSeconds)
	status := p.observedControllerStatus(p.setting("autonomy_status"), queue, jobs, blockers)
	return map[string]any{"version": AutonomyVersion, "authority": p.setting("autonomy_authority"), "generation": p.setting("autonomy_generation"), "paused": p.setting("paused") == "true", "controller_status": status, "blockers": blockers, "heartbeat_at": heartbeat, "heartbeat_stale": heartbeatStale, "observed_at": now(), "queue": queue, "jobs": summaries, "mind_palace_discovery": p.mindPalaceAutoDiscoveryStatus(), "accepted_ref_mutation_allowed": p.Config.Policy.AcceptedRefMutation, "blocker_resolver_mode": blockerResolverMode(p), "blocker_resolver_status": p.setting(blockerResolverStatusSetting)}, nil
}

func autonomyHeartbeatStale(raw string, pollSeconds int) bool {
	if strings.TrimSpace(raw) == "" {
		return true
	}
	observed, err := time.Parse(time.RFC3339Nano, raw)
	if err != nil {
		return true
	}
	budget := time.Duration(pollSeconds*3) * time.Second
	if budget < 30*time.Second {
		budget = 30 * time.Second
	}
	if budget > 5*time.Minute {
		budget = 5 * time.Minute
	}
	return time.Since(observed) > budget
}

func (p *Engine) observedControllerStatus(stored string, queue []QueueItem, jobs []Job, blockers []string) string {
	if len(blockers) > 0 {
		return strings.Join(blockers, "; ")
	}
	jobState := map[string]Job{}
	for _, j := range jobs {
		jobState[j.ID] = j
		switch j.State {
		case "DISPATCHED", "ENGINEERING", "ACCEPTING":
			if j.Reason != "" {
				return "RUNNING: " + j.ID + " ΓÇö " + j.Reason
			}
			return "RUNNING: " + j.ID
		}
	}
	for _, item := range queue {
		switch item.State {
		case "RUNNING":
			if j, ok := jobState[item.ID]; ok && j.State == "ACCEPTED" {
				return "FINALIZING: " + item.ID + " accepted candidate awaits queue receipt"
			}
			if item.Reason != "" {
				return "RUNNING: " + item.ID + " ΓÇö " + item.Reason
			}
			return "RUNNING: " + item.ID
		case "RETRY_WAIT":
			return "RECOVERY_WAIT: " + item.ID
		}
	}
	if p.setting("paused") == "true" {
		return "PAUSED"
	}
	for _, item := range queue {
		if item.State == "QUEUED" && item.Authorization == "operator" && item.Mode == "source" {
			return "IDLE: " + item.ID + " queued for explicit controller run"
		}
	}
	if strings.HasPrefix(stored, "OPERATOR_BLOCKED:") || strings.HasPrefix(stored, "QUEUE_") {
		return stored
	}
	return "IDLE: no authorized eligible work"
}

func (p *Engine) SetAutonomyAuthority(ctx context.Context, authority string) error {
	p.queueMu.Lock()
	defer p.queueMu.Unlock()
	if authority != "original" && authority != "test" && authority != "plane" {
		return errors.New("AUTHORITY_INVALID")
	}
	var n int
	if e := p.Store.DB.QueryRow("SELECT count(*) FROM worker_leases").Scan(&n); e != nil {
		return e
	}
	if n != 0 {
		return errors.New("AUTHORITY_CHANGE_REQUIRES_DRAIN")
	}
	if authority == "plane" {
		if e := p.CheckAutonomyHandoff(ctx); e != nil {
			return e
		}
		if !p.Config.Execution.Enabled {
			return errors.New("EXECUTION_NOT_CONFIGURED")
		}
		if e := p.verifyOriginalInactive(ctx); e != nil {
			return e
		}
	}
	tx, e := p.Store.DB.Begin()
	if e != nil {
		return e
	}
	defer tx.Rollback()
	if _, e = tx.Exec("UPDATE settings SET value=? WHERE key='autonomy_authority'", authority); e != nil {
		return e
	}
	if _, e = tx.Exec("UPDATE settings SET value=CAST(value AS INTEGER)+1 WHERE key='autonomy_generation'"); e != nil {
		return e
	}
	if _, e = tx.Exec("UPDATE settings SET value='true' WHERE key='paused'"); e != nil {
		return e
	}
	if e = event(tx, "", 0, "AUTHORITY_CHANGED", authority+"; dispatch paused"); e != nil {
		return e
	}
	return tx.Commit()
}

func (p *Engine) sourceAuthority(ctx context.Context) error {
	return retryTransientAuthority(ctx, func() error {
		return p.sourceAuthorityOnce(ctx)
	})
}

func (p *Engine) sourceAuthorityOnce(ctx context.Context) error {
	if p.Config.Policy.AcceptedRefMutation {
		return errors.New("ACCEPTED_REF_MUTATION_FORBIDDEN")
	}
	if !p.Config.Autonomy.Enabled {
		return errors.New("AUTONOMY_NOT_CONFIGURED")
	}
	if p.setting("autonomy_authority") != "plane" {
		return errors.New("ORIGINAL_ARCHITECTURE_REMAINS_AUTHORITY")
	}
	if p.authorityVerifier == nil {
		if e := p.verifyQualification(); e != nil {
			return e
		}
	}
	if e := p.verifyOriginalInactive(ctx); e != nil {
		return e
	}
	if p.authorityVerifier != nil {
		return nil
	}
	if os.Getenv("CKB_PLANE_GITHUB_TOKEN") == "" {
		return p.setSetting("authority_verified_at", now())
	}
	return p.renewPlaneLease(ctx)
}

func (p *Engine) verifyOriginalInactive(ctx context.Context) error {
	if p.authorityVerifier != nil {
		return p.authorityVerifier(ctx)
	}
	c := p.Config.Autonomy
	if !bridgeRepo.MatchString(c.Repository) || c.RepositoryID <= 0 || len(c.OriginalWorkflows) < 2 {
		return errors.New("ORIGINAL_AUTHORITY_GUARD_NOT_CONFIGURED")
	}
	token := os.Getenv("CKB_PLANE_GITHUB_TOKEN")
	if token == "" {
		return originalAuthorityInactiveLocalProofR6()
	}
	m := newGitHubMailbox(BridgeConfig{Repository: c.Repository}, token)
	var repo struct {
		ID      int64 `json:"id"`
		Private bool  `json:"private"`
	}
	if _, e := m.api(ctx, "GET", "", nil, &repo); e != nil {
		return e
	}
	if repo.ID != c.RepositoryID || !repo.Private {
		return errors.New("AUTHORITY_REPOSITORY_MISMATCH")
	}
	for _, name := range c.OriginalWorkflows {
		if !safePath(name) || strings.Contains(name, "/") {
			return errors.New("AUTHORITY_WORKFLOW_INVALID")
		}
		var w struct {
			State string `json:"state"`
		}
		if _, e := m.api(ctx, "GET", "/actions/workflows/"+name, nil, &w); e != nil {
			return e
		}
		if w.State != "disabled_manually" {
			return errors.New("ORIGINAL_WORKFLOW_NOT_DISABLED: " + name)
		}
	}
	for _, status := range []string{"queued", "in_progress", "waiting", "pending", "requested"} {
		var runs struct {
			Count int `json:"total_count"`
		}
		if _, e := m.api(ctx, "GET", "/actions/runs?per_page=1&status="+status, nil, &runs); e != nil {
			return e
		}
		if runs.Count > 0 {
			return errors.New("ORIGINAL_REPOSITORY_HAS_ACTIVE_RUNS")
		}
	}
	return nil
}

// Serialize scheduler and command handlers. Existing Engine ownership remains
// in force through acceptance/evidence sealing; only one queue job is active.
func (p *Engine) AutonomyTick(ctx context.Context) error {
	p.queueMu.Lock()
	defer p.queueMu.Unlock()
	if e := p.reconcileObjectives(ctx); e != nil {
		return e
	}
	if e := p.reconcilePineSuccessor(ctx); e != nil {
		return e
	}
	if e := p.reconcileExternalOrchestratorHandoffs(ctx); e != nil {
		return e
	}
	if e := p.setSetting("autonomy_heartbeat", now()); e != nil {
		return e
	}
	if e := p.maybeStartMindPalaceAutoDiscovery(ctx); e != nil {
		p.recordMindPalaceAutoDiscoverySchedulerError(e)
	}
	items, e := p.QueueList()
	if e != nil {
		return e
	}
	blockers, e := p.queueBlockers(items)
	if e != nil {
		return e
	}
	for _, blocker := range blockers {
		if strings.HasPrefix(blocker, "QUEUE_JOB_STATE_MISMATCH:") {
			return p.setSetting("autonomy_status", strings.Join(blockers, "; "))
		}
	}
	for _, item := range items {
		if item.State == "FINALIZING" {
			var raw []byte
			var disposition string
			if e = p.Store.DB.QueryRow("SELECT raw,reason FROM queue_items WHERE id=?", item.ID).Scan(&raw, &disposition); e != nil {
				return e
			}
			if e = p.deliverQueue(item.ID, raw, item.Hash, disposition, item.Receipt); e != nil {
				return e
			}
			return nil
		}
	}
	if p.blockerRecoveryShadowTick(ctx, items) {
		return nil
	}
	for _, item := range items {
		if item.State != "RUNNING" && item.State != "RETRY_WAIT" {
			continue
		}
		j, er := p.Store.Get(item.ID)
		if er != nil {
			return er
		}
		if j.State == "ACCEPTING" {
			return p.setSetting("autonomy_status", "ACCEPTING: "+item.ID)
		}
		p.mu.Lock()
		_, owned := p.cancels[item.ID]
		p.mu.Unlock()
		if owned {
			if p.authorityVerifier == nil {
				last, _ := time.Parse(time.RFC3339Nano, p.setting("authority_verified_at"))
				if time.Since(last) > time.Minute {
					if e = p.sourceAuthority(ctx); e != nil {
						_ = p.cancelAttempt(item.ID, "AUTHORITY_REVERIFY_FAILED: "+e.Error())
						return e
					}
				}
			}
			if e = p.monitorProgress(item.ID); e != nil {
				return e
			}
			return p.setSetting("autonomy_status", "RUNNING: "+item.ID)
		}
		if p.Config.Autonomy.ObjectiveController && failureClass(j.Reason) == "CODEX_QUOTA_EXHAUSTED" {
			return p.holdCodexExhaustion(j)
		}
		if j.State == "ACCEPTED" {
			if er = p.sourceAuthority(ctx); er != nil {
				return er
			}
			if er = p.VerifyEvidence(j); er != nil {
				return er
			}
			return p.queueFinish(item.ID, QueueResult{WorkOrderID: item.ID, InputSHA256: item.Hash, Disposition: "completed", Mode: item.Mode, Authorization: item.Authorization, Reason: "LOCAL_CANDIDATE_ACCEPTED", Evidence: filepath.Join(p.Root, "evidence", "queue", item.ID, randomID())})
		}
		operatorBlocked := strings.HasPrefix(j.Reason, "OPERATOR_DECISION_REQUIRED")
		if j.State == "BLOCKED" || j.State == "FAILED" {
			var action string
			er = p.Store.DB.QueryRow("SELECT action FROM recovery_decisions WHERE work_order_id=? AND attempt=?", j.ID, j.Attempt).Scan(&action)
			if er != nil && !errors.Is(er, sql.ErrNoRows) {
				return er
			}
			operatorBlocked = operatorBlocked || action == "operator-blocked"
		}
		if (j.State == "BLOCKED" || j.State == "FAILED") && operatorBlocked {
			return p.blockOperatorDecision(j)
		}
		if j.State == "BLOCKED" && j.Attempt == 0 {
			return p.preWorkerFailure(item, item.State, j.State, j.Reason)
		}
		if j.State == "BLOCKED" || j.State == "FAILED" {
			return p.queueFinish(item.ID, QueueResult{WorkOrderID: item.ID, InputSHA256: item.Hash, Disposition: "failed", Mode: item.Mode, Authorization: item.Authorization, Reason: j.Reason})
		}
		if j.State == "REJECTED_RETRYABLE" {
			var action string
			er = p.Store.DB.QueryRow("SELECT action FROM recovery_decisions WHERE work_order_id=? AND attempt=?", j.ID, j.Attempt).Scan(&action)
			if errors.Is(er, sql.ErrNoRows) {
				action, _ = p.retryRecoveryAction(j.ID, j.Attempt, j.Reason, item.Reason)
				tx, er := p.Store.DB.Begin()
				if er != nil {
					return er
				}
				defer tx.Rollback()
				if _, er = tx.Exec("INSERT INTO recovery_decisions VALUES(?,?,?,?,?)", j.ID, j.Attempt, action, j.Reason, now()); er != nil {
					return er
				}
				delay := p.Config.Autonomy.RetrySeconds
				if delay < 1 {
					delay = 60
				}
				due := time.Now().UTC().Add(time.Duration(delay*j.Attempt) * time.Second).Format(time.RFC3339Nano)
				if _, er = tx.Exec("UPDATE queue_items SET state='RETRY_WAIT',reason=?,next_retry=?,updated=? WHERE id=?", action, due, now(), j.ID); er != nil {
					return er
				}
				return tx.Commit()
			}
			if er != nil {
				return er
			}
			if action == "operator-blocked" {
				return p.blockOperatorDecision(j)
			}
			due, er := time.Parse(time.RFC3339Nano, item.NextRetry)
			if er != nil {
				return er
			}
			if time.Now().Before(due) {
				return p.setSetting("autonomy_status", "RECOVERY_WAIT: "+item.ID)
			}
			if p.setting("paused") == "true" {
				return p.setSetting("autonomy_status", "PAUSED")
			}
			if er = p.sourceAuthority(ctx); er != nil {
				return er
			}
			return p.startQueued(ctx, item)
		}
		if j.State == "READY" || j.State == "AUTHORIZED" || j.State == "DRAFT" {
			return p.startQueued(ctx, item)
		}
		return fmt.Errorf("QUEUE_JOB_STATE_AMBIGUOUS: %s", j.State)
	}
	if p.setting("paused") == "true" {
		return p.setSetting("autonomy_status", "PAUSED")
	}
	if len(blockers) > 0 {
		return p.setSetting("autonomy_status", strings.Join(blockers, "; "))
	}
	waiting := false
	for _, item := range items {
		if item.State != "QUEUED" || item.Mode != "source" || item.Authorization != "operator" {
			continue
		}
		eligible, er := p.queueEligible(item.ID)
		if er != nil {
			return er
		}
		if !eligible {
			waiting = true
			continue
		}
		if e = p.startQueued(ctx, item); e != nil {
			return e
		}
		return nil
	}
	if waiting {
		return p.setSetting("autonomy_status", "WAITING_FOR_DEPENDENCIES: inspect queued work order dependencies")
	}
	return p.setSetting("autonomy_status", "IDLE: no authorized eligible work")
}

func (p *Engine) startQueued(ctx context.Context, item QueueItem) (resultErr error) {
	if allowed, e := p.objectiveMayStart(ctx, item.ID); e != nil {
		return e
	} else if !allowed {
		return p.setSetting("autonomy_status", "OBJECTIVE_HELD: "+item.ID)
	}
	queueBefore, jobBefore := p.queueStates(item.ID)
	defer func() {
		if resultErr != nil {
			if e := p.preWorkerFailure(item, queueBefore, jobBefore, resultErr.Error()); e != nil {
				resultErr = errors.Join(resultErr, e)
			}
		}
	}()
	if e := ctx.Err(); e != nil {
		return e
	}
	if p.setting("paused") == "true" {
		return p.setSetting("autonomy_status", "PAUSED")
	}
	if e := p.sourceAuthority(ctx); e != nil {
		return e
	}
	var raw []byte
	if e := p.Store.DB.QueryRow("SELECT raw FROM queue_items WHERE id=?", item.ID).Scan(&raw); e != nil {
		return e
	}
	if digest(raw) != item.Hash {
		return errors.New("QUEUE_RAW_HASH_MISMATCH")
	}
	path, e := p.queuePath("pending", item.ID)
	if e != nil {
		return e
	}
	disk, e := os.ReadFile(path)
	if e != nil || digest(disk) != item.Hash {
		return errors.New("QUEUE_INPUT_CHANGED")
	}
	q, e := p.parseQueue(raw, item.ID)
	if e != nil {
		return e
	}
	for _, dep := range q.Dependencies {
		var state, kind string
		if e = p.Store.DB.QueryRow("SELECT state,kind FROM queue_items WHERE id=?", dep).Scan(&state, &kind); e != nil || state != "COMPLETED" || kind != "source" {
			return p.setSetting("autonomy_status", "WAITING_FOR_DEPENDENCY: "+dep)
		}
	}
	j, e := p.Store.Get(item.ID)
	if errors.Is(e, sql.ErrNoRows) {
		if e = p.Store.Load([]byte(q.WorkOrderYAML)); e != nil {
			return e
		}
		j, e = p.Store.Get(item.ID)
	}
	if e != nil {
		return e
	}
	expected, er := ParseOrder([]byte(q.WorkOrderYAML))
	if er != nil {
		return er
	}
	if jsonText(expected) != jsonText(j.Order) {
		return errors.New("QUEUE_NATIVE_ORDER_MISMATCH")
	}
	if j.State == "DRAFT" {
		if e = p.Authorize(item.ID); e != nil {
			return e
		}
		j, e = p.Store.Get(item.ID)
		if e != nil {
			return e
		}
	}
	if j.State == "AUTHORIZED" || j.State == "REJECTED_RETRYABLE" {
		if e = p.Ready(item.ID); e != nil {
			return e
		}
	}
	j, e = p.Store.Get(item.ID)
	if e != nil {
		return e
	}
	if j.State != "READY" {
		if j.Reason != "" && (j.State == "BLOCKED" || j.State == "FAILED" || j.State == "REJECTED_RETRYABLE") {
			return errors.New(j.Reason)
		}
		if j.Reason != "" {
			return fmt.Errorf("%s: work_order_state=%s", j.Reason, j.State)
		}
		return fmt.Errorf("WORK_ORDER_NOT_READY: work_order_state=%s", j.State)
	}
	// Durable intent precedes launch; startup reconciles the engine's job state.
	if _, e = p.Store.DB.Exec("UPDATE queue_items SET state='RUNNING',updated=? WHERE id=?", now(), item.ID); e != nil {
		return e
	}
	return p.Dispatch(item.ID)
}

func (p *Engine) AutonomyLoop(ctx context.Context) {
	seconds := p.Config.Autonomy.PollSeconds
	if seconds < 1 {
		seconds = 5
	}
	tick := time.NewTicker(time.Duration(seconds) * time.Second)
	defer tick.Stop()
	for {
		if e := p.AutonomyTick(ctx); e != nil {
			_ = p.setSetting("autonomy_status", "OPERATOR_BLOCKED: "+e.Error())
			_ = p.Store.Pause(true)
		}
		select {
		case <-ctx.Done():
			return
		case <-tick.C:
		}
	}
}

// Kept separate from the worker mutex; no scheduler holds it while waiting for
// a model/process. Every durable decision precedes its corresponding side effect.

func (p *Engine) queueEligible(id string) (bool, error) {
	var raw []byte
	if e := p.Store.DB.QueryRow("SELECT raw FROM queue_items WHERE id=?", id).Scan(&raw); e != nil {
		return false, e
	}
	q, e := p.parseQueue(raw, id)
	if e != nil {
		return false, e
	}
	for _, dep := range q.Dependencies {
		var state, kind string
		e := p.Store.DB.QueryRow("SELECT state,kind FROM queue_items WHERE id=?", dep).Scan(&state, &kind)
		if errors.Is(e, sql.ErrNoRows) {
			return false, nil
		}
		if e != nil {
			return false, e
		}
		if state != "COMPLETED" || kind != "source" {
			return false, nil
		}
	}
	return true, nil
}
