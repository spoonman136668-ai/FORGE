package plane

// The WebUI bridge is deliberately independent of Engine.Dispatch and Serve.
// Its mailbox is transport, never an execution authority or a worker queue.
import (
	"bytes"
	"context"
	"crypto/sha1"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"
)

const BridgeVersion = "webui-bridge-r2"
const bridgeCommandSchema = "ckb-plane.webui-command.v1"
const bridgeResultSchema = "ckb-plane.webui-result.v1"
const bridgeMaxBytes = 128 * 1024

var bridgeSegment = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$`)
var bridgeRepo = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$`)

type BridgeConfig struct {
	Schema           string `json:"schema"`
	Repository       string `json:"repository"`
	RepositoryID     int64  `json:"repository_id"`
	Branch           string `json:"branch"`
	MailboxID        string `json:"mailbox_id"`
	PlaneID          string `json:"plane_id"`
	TokenEnv         string `json:"token_env"`
	PollSeconds      int    `json:"poll_seconds"`
	HeartbeatSeconds int    `json:"heartbeat_seconds"`
	ControlEnabled   bool   `json:"control_enabled,omitempty"`
}

func LoadBridgeConfig(file string) (BridgeConfig, error) {
	var c BridgeConfig
	b, e := os.ReadFile(file)
	if e != nil {
		return c, e
	}
	if e = bridgeDecode(b, &c); e != nil {
		return c, e
	}
	return c, c.Validate()
}

func (c BridgeConfig) Validate() error {
	if c.Schema != "ckb-plane.webui-bridge.v1" || !bridgeRepo.MatchString(c.Repository) || c.RepositoryID <= 0 {
		return errors.New("BRIDGE_CONFIG_INVALID")
	}
	// Dedicated fixed branch namespace; never main, orchestration, or accepted refs.
	if !strings.HasPrefix(c.Branch, "ckb-plane/webui-") || !safePath(c.Branch) || strings.ContainsAny(c.Branch, " ~^?*[@{") || strings.Contains(c.Branch, "..") {
		return errors.New("BRIDGE_BRANCH_INVALID")
	}
	if !bridgeSegment.MatchString(c.PlaneID) || !bridgeSegment.MatchString(c.MailboxID) || c.TokenEnv != "CKB_PLANE_GITHUB_TOKEN" {
		return errors.New("BRIDGE_IDENTITY_INVALID")
	}
	if c.PollSeconds < 5 || c.PollSeconds > 900 || c.HeartbeatSeconds < 300 || c.HeartbeatSeconds > 3600 {
		return errors.New("BRIDGE_INTERVAL_INVALID")
	}
	return nil
}

// Decode explicitly rejects duplicate keys: authorization fields cannot have two interpretations.
func bridgeDecode(b []byte, v any) error {
	if len(b) > bridgeMaxBytes {
		return errors.New("BRIDGE_MESSAGE_TOO_LARGE")
	}
	b = bytes.TrimPrefix(b, []byte{0xef, 0xbb, 0xbf})
	d := json.NewDecoder(bytes.NewReader(b))
	var walk func() error
	walk = func() error {
		t, e := d.Token()
		if e != nil {
			return e
		}
		if delim, ok := t.(json.Delim); ok {
			switch delim {
			case '{':
				seen := map[string]bool{}
				for d.More() {
					k, e := d.Token()
					if e != nil {
						return e
					}
					key, ok := k.(string)
					if !ok || seen[key] {
						return errors.New("BRIDGE_DUPLICATE_KEY")
					}
					seen[key] = true
					if e = walk(); e != nil {
						return e
					}
				}
			case '[':
				for d.More() {
					if e := walk(); e != nil {
						return e
					}
				}
			default:
				return errors.New("BRIDGE_JSON_INVALID")
			}
			_, e = d.Token()
			return e
		}
		return nil
	}
	if e := walk(); e != nil {
		return e
	}
	if _, e := d.Token(); e != io.EOF {
		return errors.New("BRIDGE_TRAILING_JSON")
	}
	d = json.NewDecoder(bytes.NewReader(b))
	d.DisallowUnknownFields()
	return d.Decode(v)
}

type BridgeCommand struct {
	Objective      *ObjectiveRequest                  `json:"objective,omitempty"`
	ExternalRepair *ExternalOrchestratorRepairRequest `json:"external_repair,omitempty"`
	Schema         string                             `json:"schema"`
	ID             string                             `json:"id"`
	PlaneID        string                             `json:"plane_id"`
	MailboxID      string                             `json:"mailbox_id"`
	CreatedAt      time.Time                          `json:"created_at"`
	ExpiresAt      time.Time                          `json:"expires_at"`
	Action         string                             `json:"action"`
	WorkOrderID    string                             `json:"work_order_id,omitempty"`
	AfterEvent     int64                              `json:"after_event,omitempty"`
	Generation     int64                              `json:"authority_generation,omitempty"`
	InputSHA256    string                             `json:"input_sha256,omitempty"`
	QueueJSON      json.RawMessage                    `json:"queue_json,omitempty"`
	Authorization  string                             `json:"authorization,omitempty"`
	Mode           string                             `json:"mode,omitempty"`
	OperationID    string                             `json:"operation_id,omitempty"`
	Parameters     map[string]json.RawMessage         `json:"parameters,omitempty"`
}

func (c BridgeCommand) validate(cfg BridgeConfig, at time.Time) error {
	if c.Schema != bridgeCommandSchema || !bridgeSegment.MatchString(c.ID) || c.PlaneID != cfg.PlaneID || c.MailboxID != cfg.MailboxID {
		return errors.New("COMMAND_IDENTITY_INVALID")
	}
	if c.CreatedAt.IsZero() || c.ExpiresAt.IsZero() || c.CreatedAt.After(at.Add(2*time.Minute)) || !c.ExpiresAt.After(at) || !c.ExpiresAt.After(c.CreatedAt) || c.ExpiresAt.Sub(c.CreatedAt) > 24*time.Hour {
		return errors.New("COMMAND_EXPIRED_OR_CLOCK_INVALID")
	}
	if c.Action != "local-exec" && (c.OperationID != "" || len(c.Parameters) != 0) {
		return errors.New("COMMAND_ARGUMENTS_INVALID")
	}
	if c.Action != "objective" && c.Objective != nil {
		return errors.New("COMMAND_ARGUMENTS_INVALID")
	}
	if c.Action != "external-repair" && c.ExternalRepair != nil {
		return errors.New("COMMAND_ARGUMENTS_INVALID")
	}
	control := c.Action == "external-repair" || c.Action == "objective" || c.Action == "queue-submit" || c.Action == "queue-run" || c.Action == "retry" || c.Action == "export" || c.Action == "local-exec" || c.Action == "pause" || c.Action == "resume" || c.Action == "cancel" || c.Action == "acknowledge" || c.Action == "blocker-resolver" || c.Action == "quota-restored"
	if control {
		if !cfg.ControlEnabled {
			return errors.New("ACTION_NOT_ALLOWED_READ_ONLY_BRIDGE")
		}
		if c.Generation < 1 || c.AfterEvent != 0 {
			return errors.New("CONTROL_ARGUMENTS_INVALID")
		}
		switch c.Action {
		case "external-repair":
			if c.ExternalRepair == nil || c.ExternalRepair.RequestID != c.ID || c.WorkOrderID != "" || len(c.QueueJSON) != 0 || c.Mode != "" || c.Authorization != "" || c.InputSHA256 != "" {
				return errors.New("CONTROL_ARGUMENTS_INVALID")
			}
			if e := c.ExternalRepair.validate(); e != nil {
				return e
			}
		case "objective":
			if c.Objective == nil || c.WorkOrderID != "" || len(c.QueueJSON) != 0 || c.Mode != "" || c.Authorization != "" || c.InputSHA256 != "" {
				return errors.New("CONTROL_ARGUMENTS_INVALID")
			}
			if e := c.Objective.validate(); e != nil {
				return e
			}
		case "queue-submit":
			if len(c.QueueJSON) == 0 || c.WorkOrderID != "" || c.Authorization != "" || c.Mode != "" || c.InputSHA256 != "" {
				return errors.New("CONTROL_ARGUMENTS_INVALID")
			}
		case "queue-run":
			if !safeID.MatchString(c.WorkOrderID) || len(c.InputSHA256) != 64 || strings.Trim(c.InputSHA256, "0123456789abcdef") != "" || len(c.QueueJSON) != 0 || (c.Authorization != "none" && c.Authorization != "test" && c.Authorization != "operator") || (c.Mode != "dry-run" && c.Mode != "controlled-proof" && c.Mode != "source") {
				return errors.New("CONTROL_ARGUMENTS_INVALID")
			}
		case "blocker-resolver":
			if c.WorkOrderID != "" || len(c.QueueJSON) != 0 || (c.Mode != blockerResolverModeOff && c.Mode != blockerResolverModeShadow && c.Mode != blockerResolverModeActive) || c.Authorization != "" || c.InputSHA256 != "" {
				return errors.New("CONTROL_ARGUMENTS_INVALID")
			}
		case "local-exec":
			if !safeID.MatchString(c.OperationID) || len(c.InputSHA256) != 64 || strings.Trim(c.InputSHA256, "0123456789abcdef") != "" || len(c.Parameters) > 16 || c.WorkOrderID != "" || len(c.QueueJSON) != 0 || c.Authorization != "" || c.Mode != "" {
				return errors.New("CONTROL_ARGUMENTS_INVALID")
			}
		case "retry":
			if !safeID.MatchString(c.WorkOrderID) || len(c.QueueJSON) != 0 || c.InputSHA256 != "" || c.Authorization != "operator" || c.Mode != "source" {
				return errors.New("CONTROL_ARGUMENTS_INVALID")
			}
		case "quota-restored":
			if !safeID.MatchString(c.WorkOrderID) || len(c.QueueJSON) != 0 || c.Mode != "" || c.Authorization != "" || c.InputSHA256 != "" {
				return errors.New("CONTROL_ARGUMENTS_INVALID")
			}
		case "cancel", "acknowledge", "export":
			if !safeID.MatchString(c.WorkOrderID) || len(c.QueueJSON) != 0 || c.Mode != "" || c.Authorization != "" || c.InputSHA256 != "" {
				return errors.New("CONTROL_ARGUMENTS_INVALID")
			}
		default:
			if c.WorkOrderID != "" || len(c.QueueJSON) != 0 || c.Mode != "" || c.Authorization != "" || c.InputSHA256 != "" {
				return errors.New("CONTROL_ARGUMENTS_INVALID")
			}
		}
		return nil
	}
	if c.Generation != 0 || c.InputSHA256 != "" || len(c.QueueJSON) != 0 || c.Authorization != "" || c.Mode != "" {
		return errors.New("COMMAND_ARGUMENTS_INVALID")
	}
	switch c.Action {
	case "ping", "status", "queue-list":
		if c.WorkOrderID != "" || c.AfterEvent != 0 {
			return errors.New("COMMAND_ARGUMENTS_INVALID")
		}
	case "workorder", "evidence":
		if !safeID.MatchString(c.WorkOrderID) || c.AfterEvent != 0 {
			return errors.New("COMMAND_ARGUMENTS_INVALID")
		}
	case "events":
		if c.WorkOrderID != "" || c.AfterEvent < 0 {
			return errors.New("COMMAND_ARGUMENTS_INVALID")
		}
	default:
		return errors.New("ACTION_NOT_ALLOWED_READ_ONLY_BRIDGE")
	}
	return nil
}

type BridgeResult struct {
	Schema        string    `json:"schema"`
	Version       string    `json:"bridge_version"`
	ID            string    `json:"id"`
	PlaneID       string    `json:"plane_id"`
	MailboxID     string    `json:"mailbox_id"`
	CommandSHA256 string    `json:"command_sha256"`
	ObservedAt    time.Time `json:"observed_at"`
	Status        string    `json:"status"`
	Code          string    `json:"code"`
	ReadOnly      bool      `json:"read_only"`
	Data          any       `json:"data,omitempty"`
}

type bridgeEntry struct {
	Name string
	SHA  string
}
type bridgeMailbox interface {
	Verify(context.Context, BridgeConfig) error
	List(context.Context) ([]bridgeEntry, error)
	Read(context.Context, bridgeEntry) ([]byte, error)
	Publish(context.Context, string, []byte, bool) error
}

type WebUIBridge struct {
	mindPalaceContextEnabled      bool
	mindPalaceContextScriptSHA256 string
	objectiveControl              bool
	Config                        BridgeConfig
	Root                          string
	PlaneState                    string
	mailbox                       bridgeMailbox
	db                            *sql.DB
	lock                          *os.File
	clock                         func() time.Time
	snapshot                      func(context.Context, BridgeCommand) (any, error)
	lastHeartbeat                 time.Time
	localExecutionEnabled         bool
}

func NewWebUIBridge(root, planeState string, c BridgeConfig) (*WebUIBridge, error) {
	if e := c.Validate(); e != nil {
		return nil, e
	}
	token := os.Getenv(c.TokenEnv)
	if strings.TrimSpace(token) == "" {
		return nil, errors.New("BRIDGE_TOKEN_MISSING: set CKB_PLANE_GITHUB_TOKEN locally")
	}
	m := newGitHubMailbox(c, token)
	return openWebUIBridge(root, planeState, c, m)
}

func openWebUIBridge(root, planeState string, c BridgeConfig, m bridgeMailbox) (*WebUIBridge, error) {
	if e := c.Validate(); e != nil {
		return nil, e
	}
	root, e := filepath.Abs(root)
	if e != nil {
		return nil, e
	}
	root, e = filepath.EvalSymlinks(root)
	if e != nil {
		return nil, e
	}
	if !filepath.IsAbs(planeState) {
		planeState = filepath.Join(root, planeState)
	}
	if e = bridgeContained(root, planeState); e != nil {
		return nil, e
	}
	dir := filepath.Join(root, "state", "webui-bridge", c.PlaneID)
	if e = bridgeContained(root, dir); e != nil {
		return nil, e
	}
	if e = os.MkdirAll(dir, 0700); e != nil {
		return nil, e
	}
	for _, name := range []string{"bridge.lock", "bridge.db", "bridge.db-wal", "bridge.db-shm"} {
		if e = bridgeContained(dir, filepath.Join(dir, name)); e != nil {
			return nil, e
		}
	}
	f, e := os.OpenFile(filepath.Join(dir, "bridge.lock"), os.O_CREATE|os.O_RDWR, 0600)
	if e != nil {
		return nil, e
	}
	if e = lockFile(f); e != nil {
		f.Close()
		return nil, errors.New("BRIDGE_ALREADY_RUNNING")
	}
	db, e := sql.Open("sqlite", filepath.Join(dir, "bridge.db"))
	if e != nil {
		f.Close()
		return nil, e
	}
	db.SetMaxOpenConns(1)
	_, e = db.Exec(`PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; PRAGMA busy_timeout=5000;
CREATE TABLE IF NOT EXISTS identity(value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS commands(id TEXT PRIMARY KEY, blob_sha TEXT NOT NULL, input_hash TEXT NOT NULL, result BLOB NOT NULL, delivered INTEGER NOT NULL DEFAULT 0);`)
	if e != nil {
		db.Close()
		f.Close()
		return nil, e
	}
	// A local ledger cannot be silently reused for a different remote mailbox.
	identity := fmt.Sprintf("%d/%s/%s/%s/%s", c.RepositoryID, c.Repository, c.Branch, c.MailboxID, c.PlaneID)
	var old string
	e = db.QueryRow("SELECT value FROM identity LIMIT 1").Scan(&old)
	if errors.Is(e, sql.ErrNoRows) {
		_, e = db.Exec("INSERT INTO identity(value) VALUES(?)", identity)
	} else if e == nil && old != identity {
		e = errors.New("BRIDGE_LEDGER_IDENTITY_CONFLICT")
	}
	if e != nil {
		db.Close()
		f.Close()
		return nil, e
	}
	b := &WebUIBridge{Config: c, Root: root, PlaneState: planeState, mailbox: m, db: db, lock: f, clock: func() time.Time { return time.Now().UTC() }}
	b.snapshot = b.observe
	return b, nil
}

func (b *WebUIBridge) Close() error {
	e := b.db.Close()
	le := b.lock.Close()
	if e != nil {
		return e
	}
	return le
}

// Check every existing ancestor; never traverse a link outside the allowed root.
func bridgeContained(root, target string) error {
	root, e := filepath.Abs(root)
	if e != nil {
		return e
	}
	if !pathIsWithinOrEqual(root, target) {
		return errors.New("BRIDGE_PATH_OUTSIDE_PLANE")
	}
	for p := target; ; p = filepath.Dir(p) {
		if _, e := os.Lstat(p); e == nil {
			real, e := filepath.EvalSymlinks(p)
			if e != nil || !pathIsWithinOrEqual(root, real) {
				return errors.New("BRIDGE_PATH_ALIAS_REJECTED")
			}
		} else if !os.IsNotExist(e) {
			return e
		}
		if p == root || filepath.Dir(p) == p {
			break
		}
	}
	return nil
}

func bridgeBlobSHA(raw []byte) string {
	h := sha1.New()
	fmt.Fprintf(h, "blob %d\x00", len(raw))
	h.Write(raw)
	return hex.EncodeToString(h.Sum(nil))
}

func (b *WebUIBridge) compactDeliveredMailboxEntries(ctx context.Context, entries []bridgeEntry) error {
	archiver, ok := b.mailbox.(interface {
		Archive(context.Context, bridgeEntry) error
	})
	if !ok {
		return nil
	}
	compacted := 0
	for _, entry := range entries {
		if compacted >= 10 {
			break
		}
		if !strings.HasSuffix(entry.Name, ".json") {
			continue
		}
		id := strings.TrimSuffix(entry.Name, ".json")
		if !bridgeSegment.MatchString(id) {
			return errors.New("BRIDGE_INBOX_NAME_INVALID")
		}
		var blobSHA string
		var delivered int
		e := b.db.QueryRowContext(ctx, "SELECT blob_sha,delivered FROM commands WHERE id=?", id).Scan(&blobSHA, &delivered)
		if errors.Is(e, sql.ErrNoRows) {
			continue
		}
		if e != nil {
			return e
		}
		if blobSHA != entry.SHA {
			return errors.New("BRIDGE_COMMAND_ID_REUSED")
		}
		if delivered == 0 {
			continue
		}
		if e = archiver.Archive(ctx, entry); e != nil {
			return e
		}
		compacted++
	}
	return nil
}
func (b *WebUIBridge) Once(ctx context.Context) error {
	if e := b.mailbox.Verify(ctx, b.Config); e != nil {
		return e
	}
	if e := b.deliverPlaneOutbox(ctx); e != nil {
		return e
	}
	// Resume durable delivery even if the sender has removed the inbox file.
	rows, e := b.db.QueryContext(ctx, "SELECT id,result FROM commands WHERE delivered=0 ORDER BY rowid LIMIT 20")
	if e != nil {
		return e
	}
	type delivery struct {
		id  string
		raw []byte
	}
	var pending []delivery
	for rows.Next() {
		var d delivery
		if e = rows.Scan(&d.id, &d.raw); e != nil {
			rows.Close()
			return e
		}
		pending = append(pending, d)
	}
	e = rows.Err()
	rows.Close()
	if e != nil {
		return e
	}
	for _, d := range pending {
		if e = b.mailbox.Publish(ctx, "outbox/"+d.id+".json", d.raw, false); e != nil {
			return e
		}
		if _, e = b.db.ExecContext(ctx, "UPDATE commands SET delivered=1 WHERE id=?", d.id); e != nil {
			return e
		}
	}
	entries, e := b.mailbox.List(ctx)
	if e != nil {
		return e
	}
	processed := 0
	for _, entry := range entries {
		if !strings.HasSuffix(entry.Name, ".json") {
			continue
		}
		id := strings.TrimSuffix(entry.Name, ".json")
		if !bridgeSegment.MatchString(id) {
			return errors.New("BRIDGE_INBOX_NAME_INVALID")
		}
		var oldSHA string
		var result []byte
		var delivered int
		e := b.db.QueryRow("SELECT blob_sha,result,delivered FROM commands WHERE id=?", id).Scan(&oldSHA, &result, &delivered)
		if e == nil {
			if oldSHA != entry.SHA {
				return errors.New("BRIDGE_COMMAND_ID_REUSED")
			}
			if delivered != 0 {
				continue
			}
		} else if !errors.Is(e, sql.ErrNoRows) {
			return e
		} else {
			raw, e := b.mailbox.Read(ctx, entry)
			if e != nil {
				return e
			}
			if bridgeBlobSHA(raw) != entry.SHA {
				return errors.New("BRIDGE_COMMAND_CONTENT_CHANGED")
			}
			var cmd BridgeCommand
			r := BridgeResult{Schema: bridgeResultSchema, Version: BridgeVersion, ID: id, PlaneID: b.Config.PlaneID, MailboxID: b.Config.MailboxID, CommandSHA256: digest(raw), ObservedAt: b.clock(), Status: "refused", ReadOnly: true}
			if e = bridgeDecode(raw, &cmd); e != nil {
				r.Code = "COMMAND_JSON_INVALID"
			} else if cmd.ID != id {
				r.Code = "COMMAND_FILENAME_MISMATCH"
			} else if e = cmd.validate(b.Config, b.clock()); e != nil {
				r.Code = e.Error()
			} else {
				r.ReadOnly = cmd.Action == "ping" || cmd.Action == "status" || cmd.Action == "events" || cmd.Action == "workorder" || cmd.Action == "evidence" || cmd.Action == "queue-list"
				r.Data, e = b.snapshot(ctx, cmd)
				if e != nil {
					r.Status = "blocked"
					r.Code = "PLANE_OBSERVATION_UNAVAILABLE"
					r.Data = nil
				} else {
					r.Status = "succeeded"
					r.Code = "READ_ONLY_RESULT"
					if !r.ReadOnly {
						r.Code = "CONTROL_RESULT"
						if data, ok := r.Data.(map[string]any); ok && data["succeeded"] == false {
							r.Status = "blocked"
							r.Code = "CONTROL_ACTION_REFUSED"
						}
					}
				}
			}
			result, e = json.MarshalIndent(r, "", "  ")
			if e != nil {
				return e
			}
			if len(result) > bridgeMaxBytes {
				if !r.ReadOnly {
					return errors.New("BRIDGE_RESULT_TOO_LARGE")
				}

				r.Status = "blocked"
				r.Code = "BRIDGE_RESULT_TOO_LARGE"
				r.Data = map[string]any{
					"action":      cmd.Action,
					"limit_bytes": bridgeMaxBytes,
					"truncated":   true,
				}

				result, e = json.MarshalIndent(r, "", "  ")
				if e != nil {
					return e
				}

				if len(result) > bridgeMaxBytes {
					return errors.New("BRIDGE_RESULT_TOO_LARGE")
				}
			}
			// Persist before delivery. Retry publishes identical bytes; it does not re-observe.
			if _, e = b.db.ExecContext(ctx, "INSERT INTO commands(id,blob_sha,input_hash,result) VALUES(?,?,?,?)", id, entry.SHA, digest(raw), result); e != nil {
				return e
			}
		}
		if e = b.mailbox.Publish(ctx, "outbox/"+id+".json", result, false); e != nil {
			return e
		}
		if _, e = b.db.ExecContext(ctx, "UPDATE commands SET delivered=1 WHERE id=?", id); e != nil {
			return e
		}
		processed++
		if processed >= 20 {
			break
		}
	}
	if e = b.compactDeliveredMailboxEntries(ctx, entries); e != nil {
		return e
	}

	if b.lastHeartbeat.IsZero() || b.clock().Sub(b.lastHeartbeat) >= time.Duration(b.Config.HeartbeatSeconds)*time.Second {
		capabilities := []string{"ping", "status", "workorder", "events", "evidence"}
		if b.Config.ControlEnabled {
			capabilities = append(capabilities, "queue-submit", "queue-run", "retry", "export")
			if b.localExecutionEnabled {
				capabilities = append(capabilities, "local-exec")
				if b.mindPalaceContextEnabled {
					capabilities = append(capabilities, "mind-palace-context")
				}
			}
			capabilities = append(capabilities, "pause", "resume", "cancel", "acknowledge", "quota-restored")
			if b.objectiveControl {
				capabilities = append(capabilities, "objective", "external-repair")
			}
		}
		r := map[string]any{"schema": "ckb-plane.webui-heartbeat.v1", "bridge_version": BridgeVersion, "plane_id": b.Config.PlaneID, "mailbox_id": b.Config.MailboxID, "observed_at": b.clock(), "read_only": !b.Config.ControlEnabled, "execution_authority": "local-record-required", "capabilities": capabilities}
		if b.mindPalaceContextEnabled {
			r["mind_palace_context"] = mindPalaceWebUIContextDescriptor(b.mindPalaceContextScriptSHA256)
		}
		raw, _ := json.MarshalIndent(r, "", "  ")
		if e = b.mailbox.Publish(ctx, "status/heartbeat.json", raw, true); e != nil {
			return e
		}
		b.lastHeartbeat = b.clock()
	}
	return nil
}

func bridgeRetryDelay(current, base time.Duration) time.Duration {
	if base <= 0 {
		base = time.Second
	}
	if current < base {
		current = base
	}
	next := current * 2
	capDelay := 2 * time.Minute
	if base > capDelay {
		capDelay = base
	}
	if next > capDelay {
		return capDelay
	}
	return next
}
func (b *WebUIBridge) Watch(ctx context.Context, report func(error)) error {
	delay := time.Duration(b.Config.PollSeconds) * time.Second
	for {
		e := b.Once(ctx)
		if ctx.Err() != nil {
			return nil
		}
		if e != nil {
			if report != nil {
				report(e)
			}
			delay = bridgeRetryDelay(delay, time.Duration(b.Config.PollSeconds)*time.Second)
		} else {
			delay = time.Duration(b.Config.PollSeconds) * time.Second
		}
		t := time.NewTimer(delay)
		select {
		case <-ctx.Done():
			t.Stop()
			return nil
		case <-t.C:
		}
	}
}
