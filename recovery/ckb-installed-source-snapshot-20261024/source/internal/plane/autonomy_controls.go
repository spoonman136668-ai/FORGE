package plane

import (
	"bytes"
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"gopkg.in/yaml.v3"
)

func ConfigureAutonomy(destination, base, source, home string, remote bool) error {
	if source == "" || home == "" || !filepath.IsAbs(source) || !filepath.IsAbs(home) {
		return errors.New("ABSOLUTE_SOURCE_AND_CODEX_HOME_REQUIRED")
	}
	if filepath.Base(source) != "ckb-codex-r4a-clean" {
		return errors.New("SETUP_REQUIRES_CLEAN_SOURCE_CLONE")
	}
	var c Config
	var e error
	if base == "" {
		return errors.New("BASE_CONFIG_REQUIRED: use --file config/toy-codex.yaml for previously qualified native tool paths")
	}
	c, e = LoadConfig(base)
	if e != nil {
		return e
	}
	c.Profile.Name = ""
	c.Server.Bind = "127.0.0.1"
	c.Server.Port = 8791
	c.State.SQLitePath = "state/autonomy.db"
	for name, r := range c.Repos {
		if r.Mode == "engineering" || r.Mode == "demo" {
			delete(c.Repos, name)
		}
	}
	if c.Repos == nil {
		c.Repos = map[string]Repo{}
	}
	c.Repos["ckb"] = Repo{LocalPath: source, Mode: "engineering"}
	referenceConfig := filepath.Join(filepath.Dir(destination), "local.yaml")
	if refs, e := LoadConfig(referenceConfig); e == nil {
		for name, r := range refs.Repos {
			if r.Mode == "knowledge" || r.Mode == "reference" {
				c.Repos[name] = r
			}
		}
	}
	c.Execution.CodexHome = home
	c.Execution.Enabled = true
	c.Policy.AcceptedRefMutation = false
	c.Policy.RuntimeLaunchAllowed = false
	c.Policy.ArbitraryShell = false
	c.Policy.MaxAttempts = 3
	c.Autonomy = AutonomyConfig{RemoteControl: remote, Enabled: true, PollSeconds: 5, RetrySeconds: 60, MaxNoProgressSeconds: 900, Repository: "spoonman136668-ai/ckb", RepositoryID: 1349639063, OriginalWorkflows: []string{"ckb-codex-worker.yml", "ckb-fast-continuation-poller.yml", "ckb-dh-candidate-hygiene-repair.yml"}}
	for name, tool := range map[string]string{"git": c.Tools.Git, "go": c.Tools.Go, "codex": c.Tools.Codex} {
		if !filepath.IsAbs(tool) || !strings.EqualFold(filepath.Ext(tool), ".exe") {
			return fmt.Errorf("SETUP_NATIVE_TOOL_REQUIRED: %s", name)
		}
		if i, e := os.Stat(tool); e != nil || !i.Mode().IsRegular() {
			return fmt.Errorf("SETUP_TOOL_MISSING: %s", name)
		}
	}
	c.Execution.SandboxSyntax, e = detectSandboxSyntax(c.Tools.Codex, home)
	if e != nil {
		return e
	}
	raw, e := yaml.Marshal(c)
	if e != nil {
		return e
	}
	if e = durableNew(destination, raw); e != nil {
		return e
	}
	fmt.Println("Configured. Original architecture remains authority; no source work is authorized. Start controller in observation mode.")
	return nil
}

func (p *Engine) ChangeAuthorityOffline(ctx context.Context, owner string) error {
	f, e := p.controllerLock()
	if e != nil {
		return e
	}
	defer f.Close()
	if e = p.recoverInterrupted(); e != nil {
		return e
	}
	return p.SetAutonomyAuthority(ctx, owner)
}
func (p *Engine) SubmitOffline(raw []byte) error {
	f, e := p.controllerLock()
	if e != nil {
		_, er := p.callLocalController(context.Background(), NativeRequest{Action: "submit", QueueJSON: raw})
		return er
	}
	defer f.Close()
	return p.QueueSubmit(raw)
}
func (p *Engine) RunQueueOffline(ctx context.Context, id, auth, mode string, consume bool) (QueueResult, error) {
	f, e := p.controllerLock()
	if e != nil {
		v, er := p.callLocalController(ctx, NativeRequest{Action: "run", ID: id, Authorization: auth, Mode: mode, Consume: consume})
		var result QueueResult
		if er == nil {
			b, _ := json.Marshal(v)
			er = json.Unmarshal(b, &result)
		}
		return result, er
	}
	defer f.Close()
	return p.QueueRun(ctx, id, auth, mode, consume)
}

func (p *Engine) LocalControl(ctx context.Context, action, id string) (any, error) {
	switch action {
	case "pause":
		return map[string]bool{"paused": true}, p.Store.Pause(true)
	case "resume":
		if e := p.sourceAuthority(ctx); e != nil {
			return nil, e
		}
		return map[string]bool{"paused": false}, p.Store.Pause(false)
	case "quota-restored":
		return p.rearmCodexQuotaRestored(ctx, id)
	case "acknowledge":
		if !safeID.MatchString(id) {
			return nil, errors.New("WORK_ORDER_ID_INVALID")
		}
		if reviewed, handled, e := p.acknowledgeExternalWaiting(id); handled || e != nil {
			return reviewed, e
		}
		r, e := p.Store.DB.Exec("UPDATE queue_items SET state='REVIEWED',updated=? WHERE id=? AND state IN ('FAILED','BLOCKED')", now(), id)
		if e != nil {
		return nil, e
		}
		n, e := r.RowsAffected()
		if e != nil {
		return nil, e
		}
		if n == 1 {
		return map[string]string{"id": id, "state": "REVIEWED", "note": "Not accepted; dependent stages remain ineligible."}, nil
		}

		// A diagnosed retryable work order may be retired without consuming another
		// attempt, but only while dispatch is paused and no attempt is active.
		p.queueMu.Lock()
		defer p.queueMu.Unlock()

		var paused string
		if e = p.Store.DB.QueryRow("SELECT value FROM settings WHERE key='paused'").Scan(&paused); e != nil {
		return nil, e
		}
		if paused != "true" {
		return nil, errors.New("ACKNOWLEDGE_REQUIRES_BLOCKED_OR_FAILED")
		}

		p.mu.Lock()
		_, active := p.cancels[id]
		p.mu.Unlock()

		if active {
		return nil, errors.New("ACKNOWLEDGE_RETRY_WAIT_ACTIVE_ATTEMPT")
		}

		r, e = p.Store.DB.Exec(`
		UPDATE queue_items
		SET state='REVIEWED', updated=?
		WHERE id=?
		  AND state='RETRY_WAIT'
		  AND EXISTS (
		SELECT 1 FROM work_orders
		WHERE id=? AND state='REJECTED_RETRYABLE'
		  )`,
		now(), id, id,
		)
		if e != nil {
		return nil, e
		}

		n, e = r.RowsAffected()
		if e != nil {
		return nil, e
		}
		if n != 1 {
		return nil, errors.New("ACKNOWLEDGE_REQUIRES_BLOCKED_OR_FAILED")
		}

		return map[string]string{"id": id, "state": "REVIEWED", "note": "Not accepted; dependent stages remain ineligible."}, nil
	}
	return nil, errors.New("ACTION_NOT_ALLOWED")
}

func (p *Engine) AttachBridge(b *WebUIBridge) {
	p.bridge = b
	b.objectiveControl = p.Config.Autonomy.ObjectiveController
	b.localExecutionEnabled = p.localOperations != nil
	b.mindPalaceContextEnabled = mindPalaceWebUIContextAvailable(p.localOperations)
	b.mindPalaceContextScriptSHA256 = mindPalaceWebUIContextRegisteredSHA256(p.localOperations)
	previous := b.snapshot
	b.snapshot = func(ctx context.Context, c BridgeCommand) (any, error) {
		switch c.Action {
		case "external-repair", "objective":
			return p.controlRequest(ctx, c)
		case "ping":
			capabilities := append([]string{"ping", "status", "queue-list", "workorder", "events", "evidence", "queue-submit", "queue-run", "retry", "export"}, localExecutionCapability(p.localOperations != nil)...)
			if p.Config.Autonomy.ObjectiveController {
				capabilities = append(capabilities, "objective", "external-repair")
			}
			result := map[string]any{"connected": true, "version": AutonomyVersion, "authority": p.setting("autonomy_authority"), "authority_generation": p.setting("autonomy_generation"), "remote_control_enabled": p.Config.Autonomy.RemoteControl && b.Config.ControlEnabled, "capabilities": capabilities}
			if mindPalaceWebUIContextAvailable(p.localOperations) {
				capabilities = append(capabilities, "mind-palace-context")
				result["capabilities"] = capabilities
				result["mind_palace_context"] = mindPalaceWebUIContextDescriptor(mindPalaceWebUIContextRegisteredSHA256(p.localOperations))
			}
			result["capabilities"] = append(result["capabilities"].([]string), "quota-restored")
			return result, nil
		case "status", "queue-list":
			return p.AutonomyStatus()
		case "evidence":
			j, e := p.Store.Get(c.WorkOrderID)
			if errors.Is(e, sql.ErrNoRows) {
				return p.QueueReceiptEvidence(c.WorkOrderID)
			}
			if e != nil {
				return nil, e
			}
			if e = p.VerifyEvidence(j); e != nil {
				return nil, e
			}
			view, e := previous(ctx, c)
			if e != nil {
				return nil, e
			}
			projection, ok := view.(map[string]any)
			if !ok {
				return nil, errors.New("EVIDENCE_PROJECTION_INVALID")
			}
			projection["verified_now"] = true
			return projection, nil
		case "queue-submit", "queue-run", "retry", "export", "local-exec", "pause", "resume", "cancel", "acknowledge", "blocker-resolver":
			return p.controlRequest(ctx, c)
		default:
			return previous(ctx, c)
		}
	}
}

func (p *Engine) controlRequest(ctx context.Context, c BridgeCommand) (any, error) {
	if !p.Config.Autonomy.RemoteControl || p.bridge == nil || !p.bridge.Config.ControlEnabled {
		return nil, errors.New("REMOTE_CONTROL_DISABLED_LOCALLY")
	}
	generation, _ := strconv.ParseInt(p.setting("autonomy_generation"), 10, 64)
	if c.Generation != generation {
		return nil, errors.New("AUTHORITY_GENERATION_CHANGED")
	}
	raw, _ := json.Marshal(c)
	hash := digest(raw)
	var oldHash, state string
	var saved []byte
	e := p.Store.DB.QueryRow("SELECT hash,result,state FROM control_requests WHERE id=?", c.ID).Scan(&oldHash, &saved, &state)
	if e == nil {
		if oldHash != hash {
			return nil, errors.New("CONTROL_REQUEST_ID_REUSED")
		}
		if state != "DONE" {
			return nil, errors.New("CONTROL_OUTCOME_UNCERTAIN_REVIEW_STATE")
		}
		var v any
		e = json.Unmarshal(saved, &v)
		return v, e
	}
	if !errors.Is(e, sql.ErrNoRows) {
		return nil, e
	}
	if _, e = p.Store.DB.Exec("INSERT INTO control_requests(id,hash,state) VALUES(?,?,'PROCESSING')", c.ID, hash); e != nil {
		return nil, e
	}
	var result any
	switch c.Action {
	case "external-repair":
		if c.ExternalRepair == nil || c.ExternalRepair.RequestID != c.ID {
			e = errors.New("EXTERNAL_REPAIR_ARGUMENTS_INVALID")
		} else {
			result, e = p.ExternalOrchestratorRepair(ctx, *c.ExternalRepair)
		}
	case "objective":
		if c.Objective == nil {
			e = errors.New("OBJECTIVE_ARGUMENTS_INVALID")
		} else {
			result, e = p.ObjectiveControl(ctx, c.Generation, *c.Objective)
		}
	case "queue-submit":
		e = p.QueueSubmit(c.QueueJSON)
		result = map[string]bool{"submitted": e == nil, "authorized": false}
	case "queue-run":
		path, er := p.queuePath("pending", c.WorkOrderID)
		if er != nil {
			e = er
			break
		}
		b, er := os.ReadFile(path)
		if er != nil {
			e = er
			break
		}
		if digest(b) != c.InputSHA256 {
			e = errors.New("WORK_ORDER_CONTENT_CHANGED")
			break
		}
		result, e = p.QueueRun(ctx, c.WorkOrderID, c.Authorization, c.Mode, false, c.InputSHA256)
	case "retry":
		result, e = p.QueueRetry(ctx, c.WorkOrderID, c.Authorization, c.Mode)
	case "export":
		var exported map[string]any
		exported, e = p.ExportCandidate(ctx, c.WorkOrderID)
		if e == nil {
			delete(exported, "bundle")
			result = exported
		}
	case "local-exec":
		result, e = p.RunLocalOperation(ctx, LocalExecutionRequest{
			RequestID:    c.ID,
			OperationID:  c.OperationID,
			ScriptSHA256: c.InputSHA256,
			Parameters:   c.Parameters,
		})
	case "blocker-resolver":
		result, e = p.SetBlockerResolverMode(ctx, c.Mode)
	case "quota-restored":
		result, e = p.rearmCodexQuotaRestored(ctx, c.WorkOrderID)
	case "cancel":
		e = p.Cancel(c.WorkOrderID)
		result = map[string]bool{"cancellation_requested": e == nil}
	default:
		result, e = p.LocalControl(ctx, c.Action, c.WorkOrderID)
	}
	response := map[string]any{"result": result, "succeeded": e == nil}
	if e != nil {
		response["error"] = e.Error()
	}
	data, er := json.Marshal(response)
	if er != nil {
		return nil, er
	}
	if _, er = p.Store.DB.Exec("UPDATE control_requests SET result=?,state='DONE' WHERE id=?", data, c.ID); er != nil {
		return nil, er
	}
	return response, nil
}

type NativeRequest struct {
	Objective     *ObjectiveRequest `json:"objective,omitempty"`
	Generation    int64             `json:"authority_generation,omitempty"`
	InputSHA256   string            `json:"input_sha256,omitempty"`
	Action        string            `json:"action"`
	ID            string            `json:"id,omitempty"`
	QueueJSON     json.RawMessage   `json:"queue_json,omitempty"`
	Authorization string            `json:"authorization,omitempty"`
	Mode          string            `json:"mode,omitempty"`
	Consume       bool              `json:"consume_on_refusal,omitempty"`
}

func (p *Engine) HandleNative(ctx context.Context, r NativeRequest) (any, error) {
	if !p.Config.Autonomy.Enabled {
		return nil, errors.New("AUTONOMY_NOT_CONFIGURED")
	}
	if r.Action != "objective" && (r.Objective != nil || r.Generation != 0) {
		return nil, errors.New("NATIVE_ARGUMENTS_INVALID")
	}
	switch r.Action {
	case "objective":
		if r.Objective == nil || r.ID != "" || r.InputSHA256 != "" || len(r.QueueJSON) != 0 || r.Authorization != "" || r.Mode != "" || r.Consume {
			return nil, errors.New("OBJECTIVE_ARGUMENTS_INVALID")
		}
		return p.ObjectiveControl(ctx, r.Generation, *r.Objective)
	case "stop":
		p.mu.Lock()
		stop := p.shutdown
		p.mu.Unlock()
		if stop == nil {
			return nil, errors.New("CONTROLLER_NOT_RUNNING")
		}
		stop()
		return map[string]bool{"stopping": true}, nil
	case "status":
		return p.AutonomyStatus()
	case "submit":
		return map[string]bool{"submitted": true}, p.QueueSubmit(r.QueueJSON)
	case "run":
		return p.QueueRun(ctx, r.ID, r.Authorization, r.Mode, r.Consume, r.InputSHA256)
	case "retry":
		return p.QueueRetry(ctx, r.ID, r.Authorization, r.Mode)
	case "export":
		return p.ExportCandidate(ctx, r.ID)
	case "acceptance-replay":
		return p.AcceptanceReplay(ctx, r.ID)
	case "pause", "resume", "acknowledge", "quota-restored":
		return p.LocalControl(ctx, r.Action, r.ID)
	case "cancel":
		return map[string]bool{"cancellation_requested": true}, p.Cancel(r.ID)
	}
	return nil, errors.New("NATIVE_ACTION_NOT_ALLOWED")
}

func (p *Engine) callLocalController(ctx context.Context, r NativeRequest) (any, error) {
	token, e := p.Token()
	if e != nil {
		return nil, e
	}
	raw, e := json.Marshal(r)
	if e != nil {
		return nil, e
	}
	request, e := http.NewRequestWithContext(ctx, "POST", fmt.Sprintf("http://%s:%d/api/native", p.Config.Server.Bind, p.Config.Server.Port), bytes.NewReader(raw))
	if e != nil {
		return nil, e
	}
	request.Header.Set("Authorization", "Bearer "+token)
	request.Header.Set("Content-Type", "application/json")
	client := http.Client{Timeout: 10 * time.Minute, CheckRedirect: func(*http.Request, []*http.Request) error { return errors.New("LOCAL_REDIRECT_REFUSED") }}
	res, e := client.Do(request)
	if e != nil {
		return nil, errors.New("CONTROLLER_LOCKED_OR_UNAVAILABLE")
	}
	defer res.Body.Close()
	b, e := io.ReadAll(io.LimitReader(res.Body, 1<<20))
	if e != nil {
		return nil, e
	}
	var result any
	if e = json.Unmarshal(b, &result); e != nil {
		return nil, e
	}
	if res.StatusCode != 200 {
		return result, fmt.Errorf("NATIVE_COMMAND_REJECTED: %s", b)
	}
	return result, nil
}

func (p *Engine) StopLocalController(ctx context.Context) (any, error) {
	return p.callLocalController(ctx, NativeRequest{Action: "stop"})
}

// Queue proof receipts have no native worker job. Expose their integrity through
// the same read-only mailbox evidence action without publishing source contents.
func (p *Engine) QueueReceiptEvidence(id string) (map[string]any, error) {
	if !safeID.MatchString(id) {
		return nil, errors.New("WORK_ORDER_ID_INVALID")
	}
	var raw []byte
	var hash, path string
	if e := p.Store.DB.QueryRow("SELECT r.raw,r.hash,q.receipt FROM queue_receipts r JOIN queue_items q ON q.id=r.work_order_id WHERE q.id=?", id).Scan(&raw, &hash, &path); e != nil {
		return nil, e
	}
	if digest(raw) != hash {
		return nil, errors.New("QUEUE_RECEIPT_CORRUPT")
	}
	if e := bridgeContained(p.Root, path); e != nil {
		return nil, e
	}
	disk, e := os.ReadFile(path)
	if e != nil || digest(disk) != hash {
		return nil, errors.New("QUEUE_RECEIPT_CHANGED_OR_MISSING")
	}
	var result QueueResult
	if e = json.Unmarshal(raw, &result); e != nil {
		return nil, e
	}
	return map[string]any{"id": id, "kind": "queue-receipt", "verified_now": true, "receipt": result}, nil
}

func localExecutionCapability(enabled bool) []string {
	if enabled {
		return []string{"local-exec", "pause", "resume", "cancel", "acknowledge"}
	}
	return []string{"pause", "resume", "cancel", "acknowledge"}
}
