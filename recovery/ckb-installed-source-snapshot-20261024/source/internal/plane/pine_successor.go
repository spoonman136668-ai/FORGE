package plane

import (
	"context"
	"database/sql"
	_ "embed"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"gopkg.in/yaml.v3"
)

const roadmapSuccessorCatalogSchema = "ckb-plane.roadmap-successor-catalog.v1"

//go:embed roadmap_successors.json
var roadmapSuccessorCatalogRaw []byte

type roadmapSuccessorCatalog struct {
	Schema              string                  `json:"schema"`
	SourceRoadmap       string                  `json:"source_roadmap"`
	SourceRoadmapSHA256 string                  `json:"source_roadmap_sha256"`
	Policy              string                  `json:"policy"`
	Entries             []roadmapSuccessorEntry `json:"entries"`
}

type roadmapSuccessorEntry struct {
	Key                         string             `json:"key"`
	ID                          string             `json:"id"`
	Title                       string             `json:"title"`
	ParentID                    string             `json:"parent_id"`
	AutoAuthorized              bool               `json:"auto_authorized"`
	OperatorReason              string             `json:"operator_reason"`
	AllowAcceptedTestOnlyParent bool               `json:"allow_accepted_test_only_parent"`
	WorkerBranch                string             `json:"worker_branch"`
	Instructions                []string           `json:"instructions"`
	AllowedPaths                []string           `json:"allowed_paths"`
	ForbiddenPaths              []string           `json:"forbidden_paths"`
	RequiredPaths               []string           `json:"required_paths"`
	Preserve                    []string           `json:"preserve"`
	FocusedGo                   []string           `json:"focused_go"`
	GoPackages                  []string           `json:"go_packages"`
	RunGoTestAll                bool               `json:"run_go_test_all"`
	RunPlaywright               bool               `json:"run_playwright"`
	UI                          roadmapSuccessorUI `json:"ui"`
	Forbidden                   []string           `json:"forbidden"`
}

type roadmapSuccessorUI struct {
	Root    string                   `json:"root"`
	Pages   []roadmapSuccessorUIPage `json:"pages"`
	Markers map[string][]string      `json:"markers"`
}

type roadmapSuccessorUIPage struct {
	Path        string   `json:"path"`
	CriticalIDs []string `json:"critical_ids"`
	ChartID     string   `json:"chart_id"`
}

func loadRoadmapSuccessorCatalog() (roadmapSuccessorCatalog, error) {
	var c roadmapSuccessorCatalog
	if len(roadmapSuccessorCatalogRaw) == 0 || len(roadmapSuccessorCatalogRaw) > 256<<10 {
		return c, errors.New("ROADMAP_SUCCESSOR_CATALOG_SIZE_INVALID")
	}
	if err := json.Unmarshal(roadmapSuccessorCatalogRaw, &c); err != nil {
		return c, errors.New("ROADMAP_SUCCESSOR_CATALOG_JSON_INVALID")
	}
	if c.Schema != roadmapSuccessorCatalogSchema || len(c.Entries) == 0 || len(c.Entries) > 64 {
		return c, errors.New("ROADMAP_SUCCESSOR_CATALOG_CONTRACT_INVALID")
	}
	if len(c.SourceRoadmapSHA256) != 64 || strings.Trim(c.SourceRoadmapSHA256, "0123456789abcdef") != "" {
		return c, errors.New("ROADMAP_SUCCESSOR_SOURCE_HASH_INVALID")
	}
	seen := map[string]bool{}
	for i, e := range c.Entries {
		if e.Key == "" || !safeID.MatchString(e.ID) || !safeID.MatchString(e.ParentID) || e.Title == "" {
			return c, errors.New("ROADMAP_SUCCESSOR_ENTRY_ID_INVALID")
		}
		if seen[e.ID] {
			return c, errors.New("ROADMAP_SUCCESSOR_DUPLICATE_ID")
		}
		seen[e.ID] = true
		if i > 0 && e.ParentID != c.Entries[i-1].ID {
			return c, errors.New("ROADMAP_SUCCESSOR_CHAIN_NOT_LINEAR")
		}
		if e.AutoAuthorized {
			if !strings.HasPrefix(e.WorkerBranch, "codex/") || len(e.AllowedPaths) == 0 || len(e.FocusedGo) != 1 {
				return c, errors.New("ROADMAP_SUCCESSOR_AUTOMATIC_ENTRY_INVALID")
			}
			if e.RunPlaywright && (e.UI.Root == "" || len(e.UI.Pages) == 0 || len(e.Preserve) == 0) {
				return c, errors.New("ROADMAP_SUCCESSOR_UI_CONTRACT_INVALID")
			}
		} else if e.OperatorReason == "" {
			return c, errors.New("ROADMAP_SUCCESSOR_OPERATOR_BOUNDARY_INVALID")
		}
		if e.AllowAcceptedTestOnlyParent && (i != 0 || !e.AutoAuthorized) {
			return c, errors.New("ROADMAP_SUCCESSOR_TEST_ONLY_PARENT_POLICY_INVALID")
		}
	}
	return c, nil
}

func roadmapSuccessorWorkOrder(e roadmapSuccessorEntry, candidateSHA string) (WorkOrder, string, error) {
	var w WorkOrder
	w.ID = e.ID
	w.Title = e.Title
	w.Instructions = append([]string{}, e.Instructions...)
	w.Repo = "ckb"
	w.Baseline.Ref = localCandidateBaselinePrefix + e.ParentID
	w.Baseline.SHA = candidateSHA
	w.Worker.Branch = e.WorkerBranch
	w.Worker.Preferred = "codex"
	w.Scope.Allowed = append([]string{}, e.AllowedPaths...)
	w.Scope.Forbidden = append([]string{}, e.ForbiddenPaths...)
	w.RequiredPaths = append([]string{}, e.RequiredPaths...)
	w.RequiredTests.FocusedGo = append([]string{}, e.FocusedGo...)
	w.RequiredTests.Packages = append([]string{}, e.GoPackages...)
	w.Acceptance.All = e.RunGoTestAll
	w.Acceptance.Browser = e.RunPlaywright
	w.Acceptance.ProtectRefs = true
	w.Acceptance.Clean = true
	w.Forbidden = append([]string{}, e.Forbidden...)

	// yaml.v3 encodes nil slices/maps as explicit empty collections for this
	// struct shape. Normalize zero-value collections before marshaling so the
	// strict semantic round-trip comparison is stable without weakening it.
	w.ContextFiles = []ContextFile{}
	w.Preserve = append([]string{}, e.Preserve...)
	w.RequiredTests.PowerShellScripts = []string{}
	w.UI.Pages = []UIPage{}
	w.UI.Markers = map[string][]string{}
	if e.RunPlaywright {
		w.UI.Root = e.UI.Root
		w.UI.Markers = map[string][]string{}
		for k, values := range e.UI.Markers {
			w.UI.Markers[k] = append([]string{}, values...)
		}
		for _, page := range e.UI.Pages {
			w.UI.Pages = append(w.UI.Pages, UIPage{
				Path:        page.Path,
				CriticalIDs: append([]string{}, page.CriticalIDs...),
				ChartID:     page.ChartID,
			})
		}
	}
	if err := w.Validate(); err != nil {
		return WorkOrder{}, "", fmt.Errorf("ROADMAP_SUCCESSOR_RENDERED_WORK_ORDER_INVALID: %w", err)
	}
	raw, err := yaml.Marshal(&w)
	if err != nil {
		return WorkOrder{}, "", errors.New("ROADMAP_SUCCESSOR_YAML_ENCODE_FAILED")
	}
	parsed, err := ParseOrder(raw)
	if err != nil {
		return WorkOrder{}, "", err
	}
	if jsonText(parsed) != jsonText(w) {
		return WorkOrder{}, "", errors.New("ROADMAP_SUCCESSOR_YAML_ROUNDTRIP_MISMATCH")
	}
	return parsed, string(raw), nil
}

const roadmapSourceHygieneRetryReason = "ROADMAP_SOURCE_HYGIENE_RETRY_AUTHORIZED"

func roadmapCatalogAutoRecoveryIDs(c roadmapSuccessorCatalog) []string {
	if len(c.Entries) == 0 {
		return nil
	}
	ids := []string{}
	seen := map[string]bool{}
	// The first automatic child binds the already-existing accepted frontier
	// parent. Installing this catalog explicitly authorizes bounded repair of
	// that one source-only parent so the chain can actually enter the catalog.
	if c.Entries[0].AutoAuthorized {
		ids = append(ids, c.Entries[0].ParentID)
		seen[c.Entries[0].ParentID] = true
	}
	for _, e := range c.Entries {
		if e.AutoAuthorized && !seen[e.ID] {
			ids = append(ids, e.ID)
			seen[e.ID] = true
		}
	}
	return ids
}

// recoverRoadmapSourceHygieneLocked is intentionally narrower than the global
// retry policy. SOURCE_HYGIENE_FAILED remains a hard blocker everywhere else.
// Only catalog-preauthorized source stages may be requeued, with the existing
// attempt budget, immutable queue bytes, operator/source mode, and no leases.
func (p *Engine) recoverRoadmapSourceHygieneLocked(ctx context.Context, c roadmapSuccessorCatalog) (bool, error) {
	allowed := roadmapCatalogAutoRecoveryIDs(c)
	for _, id := range allowed {
		var raw []byte
		var hash, queueState, auth, mode, kind string
		err := p.Store.DB.QueryRow(
			"SELECT raw,hash,state,authorization,mode,kind FROM queue_items WHERE id=?",
			id,
		).Scan(&raw, &hash, &queueState, &auth, &mode, &kind)
		if errors.Is(err, sql.ErrNoRows) {
			continue
		}
		if err != nil {
			return false, err
		}
		if queueState != "FAILED" && queueState != "BLOCKED" {
			continue
		}
		if auth != "operator" || mode != "source" || kind != "source" || digest(raw) != hash {
			continue
		}

		var jobState, reason string
		var attempt, leases int
		if err = p.Store.DB.QueryRow(
			"SELECT state,reason,attempt FROM work_orders WHERE id=?",
			id,
		).Scan(&jobState, &reason, &attempt); err != nil {
			return false, err
		}
		if jobState != "BLOCKED" || reason != "SOURCE_HYGIENE_FAILED" {
			continue
		}
		if p.retryDecisionNow(id, attempt, reason).HardStop {
			continue
		}
		if err = p.Store.DB.QueryRow(
			"SELECT count(*) FROM worker_leases WHERE work_order_id=?",
			id,
		).Scan(&leases); err != nil {
			return false, err
		}
		if leases != 0 {
			return false, errors.New("ROADMAP_SOURCE_HYGIENE_ATTEMPT_STILL_OWNED")
		}
		q, err := p.parseQueue(raw, id)
		if err != nil {
			return false, err
		}
		if q.Kind != "source" || q.ID != id {
			return false, errors.New("ROADMAP_SOURCE_HYGIENE_QUEUE_CONTRACT_INVALID")
		}
		if err = p.sourceAuthority(ctx); err != nil {
			return false, err
		}

		for _, dir := range []string{"pending", "failed", "completed"} {
			path, er := p.queuePath(dir, id)
			if er != nil {
				return false, er
			}
			b, er := os.ReadFile(path)
			if er == nil {
				if digest(b) != hash {
					return false, errors.New("ROADMAP_SOURCE_HYGIENE_QUEUE_INPUT_CHANGED")
				}
				if dir == "completed" {
					return false, errors.New("ROADMAP_SOURCE_HYGIENE_ALREADY_COMPLETED")
				}
			} else if !os.IsNotExist(er) {
				return false, er
			}
		}
		pending, err := p.queuePath("pending", id)
		if err != nil {
			return false, err
		}
		if _, err = os.Stat(pending); os.IsNotExist(err) {
			if err = durableNew(pending, raw); err != nil {
				return false, err
			}
		} else if err != nil {
			return false, err
		}

		tx, err := p.Store.DB.Begin()
		if err != nil {
			return false, err
		}
		defer tx.Rollback()
		if _, err = tx.Exec(
			"UPDATE work_orders SET state='DRAFT',reason=? WHERE id=?",
			roadmapSourceHygieneRetryReason, id,
		); err != nil {
			return false, err
		}
		if _, err = tx.Exec(
			"DELETE FROM authorization_contracts WHERE work_order_id=?",
			id,
		); err != nil {
			return false, err
		}
		if _, err = tx.Exec(
			"UPDATE queue_items SET state='QUEUED',authorization='operator',mode='source',reason=?,next_retry='',receipt='',updated=? WHERE id=?",
			roadmapSourceHygieneRetryReason, now(), id,
		); err != nil {
			return false, err
		}
		message := fmt.Sprintf(
			"catalog-scoped source-hygiene repair; queue=%s -> QUEUED; work_order=%s -> DRAFT; sha256=%s",
			queueState, jobState, hash,
		)
		if err = event(tx, id, attempt, roadmapSourceHygieneRetryReason, message); err != nil {
			return false, err
		}
		if err = tx.Commit(); err != nil {
			return false, err
		}
		if err = p.setSetting("autonomy_status", "ROADMAP_SOURCE_HYGIENE_REQUEUED: "+id); err != nil {
			return false, err
		}
		return true, nil
	}
	return false, nil
}

func roadmapSuccessorChildRecorded(p *Engine, id string) (bool, error) {
	var n int
	if err := p.Store.DB.QueryRow(
		"SELECT (SELECT count(*) FROM queue_items WHERE id=?)+(SELECT count(*) FROM work_orders WHERE id=?)",
		id, id,
	).Scan(&n); err != nil {
		return false, err
	}
	if n != 0 {
		return true, nil
	}
	for _, dir := range []string{"completed", "failed"} {
		path, err := p.queuePath(dir, id)
		if err != nil {
			return false, err
		}
		if _, err = os.Lstat(path); err == nil {
			return true, nil
		} else if !os.IsNotExist(err) {
			return false, err
		}
	}
	return false, nil
}

type roadmapSemanticDisposition string

const (
	roadmapSemanticAcceptedImplementation roadmapSemanticDisposition = "ACCEPTED_IMPLEMENTATION"
	roadmapSemanticBlockedPrerequisite    roadmapSemanticDisposition = "BLOCKED_PREREQUISITE"
	roadmapSemanticInvestigationComplete  roadmapSemanticDisposition = "INVESTIGATION_COMPLETE"
)

func roadmapSemanticStatusTextPath(normalized string) bool {
	return strings.HasPrefix(normalized, "docs/")
}
func (p *Engine) roadmapParentSemanticDisposition(parent Job) (roadmapSemanticDisposition, string, error) {
	if parent.Evidence == "" {
		return "", "", errors.New("ROADMAP_PARENT_EVIDENCE_MISSING")
	}
	if err := bridgeContained(p.Root, parent.Evidence); err != nil {
		return "", "", err
	}
	if err := regularPath(parent.Evidence, "candidate_inventory.json"); err != nil {
		return "", "", errors.New("ROADMAP_PARENT_INVENTORY_INVALID")
	}
	raw, err := os.ReadFile(filepath.Join(parent.Evidence, "candidate_inventory.json"))
	if err != nil {
		return "", "", err
	}
	var entries []CandidateEntry
	if err = json.Unmarshal(raw, &entries); err != nil {
		return "", "", errors.New("ROADMAP_PARENT_INVENTORY_JSON_INVALID")
	}

	production := []string{}
	for _, entry := range entries {
		if !parent.Order.Allows(entry.Path) {
			return "", "", errors.New("ROADMAP_PARENT_INVENTORY_SCOPE_INVALID")
		}
		normalized := strings.ToLower(filepath.ToSlash(entry.Path))
		isEvidenceText := roadmapSemanticStatusTextPath(normalized)
		isProduction := !strings.HasPrefix(normalized, "docs/") &&
			!strings.HasPrefix(normalized, "testdata/") &&
			!strings.Contains(normalized, "/testdata/") &&
			!strings.HasSuffix(normalized, "_test.go")
		if isProduction {
			production = append(production, entry.Path)
		}
		if entry.Deleted || !isEvidenceText {
			continue
		}

		candidateRoot := filepath.Join(parent.Evidence, "candidate_files")
		if err = regularPath(candidateRoot, entry.Path); err != nil {
			return "", "", errors.New("ROADMAP_PARENT_CANDIDATE_EVIDENCE_INVALID")
		}
		data, readErr := os.ReadFile(filepath.Join(candidateRoot, filepath.FromSlash(entry.Path)))
		if readErr != nil {
			return "", "", readErr
		}
		if len(data) > 512<<10 {
			return "", "", errors.New("ROADMAP_PARENT_SEMANTIC_EVIDENCE_TOO_LARGE")
		}
		upper := strings.ToUpper(string(data))
		markers := []string{
			"STATUS: NOT READY",
			"DOES NOT ESTABLISH",
			"MANDATORY SEMANTIC IMPLEMENTATION REMAINS",
			"MANDATORY IMPLEMENTATION REMAINS",
			"REMAIN UNFINISHED",
			"REMAINS UNFINISHED",
		}
		for _, marker := range markers {
			if strings.Contains(upper, marker) {
				return roadmapSemanticBlockedPrerequisite, entry.Path + ": " + marker, nil
			}
		}
	}
	if len(production) == 0 {
		return roadmapSemanticInvestigationComplete, "accepted candidate changed only documentation/tests; no implementation delta was proven", nil
	}
	return roadmapSemanticAcceptedImplementation, strings.Join(production, ","), nil
}

func roadmapSuccessorParentDispositionAllowed(
	e roadmapSuccessorEntry,
	disposition roadmapSemanticDisposition,
) bool {
	if disposition == roadmapSemanticAcceptedImplementation {
		return true
	}
	if !e.AutoAuthorized && disposition == roadmapSemanticInvestigationComplete {
		return true
	}
	return e.AllowAcceptedTestOnlyParent &&
		disposition == roadmapSemanticInvestigationComplete
}
func roadmapSuccessorOperatorBoundaryAcknowledged(p *Engine, e roadmapSuccessorEntry) (bool, error) {
	if e.AutoAuthorized {
		return false, nil
	}
	type operatorQueueEvidence struct {
		id   string
		hash string
		raw  []byte
	}
	rows, err := p.Store.DB.Query(
		"SELECT id,hash,raw FROM queue_items WHERE id<>? AND kind='source' AND authorization='operator' AND mode='source' ORDER BY updated,id",
		e.ID,
	)
	if err != nil {
		return false, err
	}
	var evidence []operatorQueueEvidence
	for rows.Next() {
		var item operatorQueueEvidence
		if err = rows.Scan(&item.id, &item.hash, &item.raw); err != nil {
			_ = rows.Close()
			return false, err
		}
		item.raw = append([]byte(nil), item.raw...)
		evidence = append(evidence, item)
	}
	if err = rows.Err(); err != nil {
		_ = rows.Close()
		return false, err
	}
	if err = rows.Close(); err != nil {
		return false, err
	}

	for _, item := range evidence {
		var q QueueOrder
		if json.Unmarshal(item.raw, &q) != nil {
			continue
		}
		if q.Schema != queueSchema || q.ID != item.id || q.Kind != "source" ||
			len(q.Dependencies) != 1 || q.Dependencies[0] != e.ParentID {
			continue
		}
		if digest(item.raw) != item.hash {
			return false, errors.New("ROADMAP_OPERATOR_BOUNDARY_QUEUE_HASH_INVALID")
		}
		parsed, parseErr := p.parseQueue(item.raw, item.id)
		if parseErr != nil {
			return false, fmt.Errorf("ROADMAP_OPERATOR_BOUNDARY_EVIDENCE_INVALID: %w", parseErr)
		}
		w, parseErr := ParseOrder([]byte(parsed.WorkOrderYAML))
		if parseErr != nil {
			return false, fmt.Errorf("ROADMAP_OPERATOR_BOUNDARY_EVIDENCE_INVALID: %w", parseErr)
		}
		if w.ID != item.id ||
			w.Baseline.Ref != localCandidateBaselinePrefix+e.ParentID ||
			!shaRE.MatchString(w.Baseline.SHA) {
			return false, errors.New("ROADMAP_OPERATOR_BOUNDARY_EVIDENCE_INVALID")
		}

		parent, parentErr := p.Store.Get(e.ParentID)
		if parentErr != nil || parent.State != "ACCEPTED" {
			return false, errors.New("ROADMAP_OPERATOR_BOUNDARY_PARENT_ACCEPTANCE_INVALID")
		}
		if parentErr = p.VerifyEvidence(parent); parentErr != nil {
			return false, errors.New("ROADMAP_OPERATOR_BOUNDARY_PARENT_EVIDENCE_INVALID")
		}
		exportRoot := filepath.Join(p.Root, "exports", e.ParentID, fmt.Sprint(parent.Attempt))
		if parentErr = bridgeContained(p.Root, exportRoot); parentErr != nil {
			return false, parentErr
		}
		manifestPath := filepath.Join(exportRoot, "candidate.json")
		manifestRaw, parentErr := os.ReadFile(manifestPath)
		if parentErr != nil {
			return false, errors.New("ROADMAP_OPERATOR_BOUNDARY_PARENT_EXPORT_REQUIRED")
		}
		var manifest localCandidateExport
		if parentErr = json.Unmarshal(manifestRaw, &manifest); parentErr != nil {
			return false, errors.New("ROADMAP_OPERATOR_BOUNDARY_PARENT_EXPORT_INVALID")
		}
		expectedBundle := filepath.Join(exportRoot, "candidate.bundle")
		if manifest.Schema != "ckb-plane.candidate-export.v1" ||
			manifest.WorkOrderID != e.ParentID ||
			manifest.Attempt != parent.Attempt ||
			manifest.CandidateSHA != w.Baseline.SHA ||
			manifest.Bundle != expectedBundle ||
			manifest.Published ||
			manifest.AcceptedRefMutated ||
			!strings.HasPrefix(manifest.WorkerBranch, "codex/") {
			return false, errors.New("ROADMAP_OPERATOR_BOUNDARY_PARENT_BINDING_INVALID")
		}
		bundleRaw, parentErr := os.ReadFile(expectedBundle)
		if parentErr != nil || digest(bundleRaw) != manifest.BundleSHA256 {
			return false, errors.New("ROADMAP_OPERATOR_BOUNDARY_PARENT_EXPORT_INTEGRITY_FAILED")
		}
		return true, nil
	}
	return false, nil
}
func (p *Engine) materializeRoadmapSuccessor(ctx context.Context, e roadmapSuccessorEntry) error {
	recorded, err := roadmapSuccessorChildRecorded(p, e.ID)
	if err != nil || recorded {
		return err
	}

	var parentQueueState, parentKind string
	err = p.Store.DB.QueryRow(
		"SELECT state,kind FROM queue_items WHERE id=?",
		e.ParentID,
	).Scan(&parentQueueState, &parentKind)
	if errors.Is(err, sql.ErrNoRows) {
		return nil
	}
	if err != nil {
		return err
	}
	if parentQueueState != "COMPLETED" || parentKind != "source" {
		return nil
	}

	parent, err := p.Store.Get(e.ParentID)
	if err != nil {
		return err
	}
	if parent.State != "ACCEPTED" {
		return errors.New("ROADMAP_SUCCESSOR_PARENT_ACCEPTANCE_REQUIRED")
	}
	if err = p.VerifyEvidence(parent); err != nil {
		return errors.New("ROADMAP_SUCCESSOR_PARENT_EVIDENCE_INVALID")
	}

	disposition, detail, err := p.roadmapParentSemanticDisposition(parent)
	if err != nil {
		return err
	}
	if !roadmapSuccessorParentDispositionAllowed(e, disposition) {
		_ = p.setSetting("autonomy_status", "ROADMAP_SEMANTIC_HOLD: "+e.ParentID+": "+string(disposition))
		return fmt.Errorf("ROADMAP_PARENT_SEMANTIC_COMPLETION_REQUIRED: %s: %s", disposition, detail)
	}
	if !e.AutoAuthorized {
		acknowledged, ackErr := roadmapSuccessorOperatorBoundaryAcknowledged(p, e)
		if ackErr != nil {
			return ackErr
		}
		if acknowledged {
			return nil
		}
		return fmt.Errorf("ROADMAP_OPERATOR_REQUIRED: %s: %s", e.Key, e.OperatorReason)
	}

	if err = p.sourceAuthority(ctx); err != nil {
		return err
	}
	exported, err := p.exportCandidateLocked(ctx, e.ParentID)
	if err != nil {
		return err
	}
	candidateSHA, _ := exported["candidate_sha"].(string)
	if !shaRE.MatchString(candidateSHA) {
		return errors.New("ROADMAP_SUCCESSOR_PARENT_EXPORT_INVALID")
	}

	w, yamlText, err := roadmapSuccessorWorkOrderWithParent(e, parent.Order, candidateSHA)
	if err != nil {
		return err
	}
	if w.ID != e.ID ||
		w.Baseline.Ref != localCandidateBaselinePrefix+e.ParentID ||
		w.Baseline.SHA != candidateSHA {
		return errors.New("ROADMAP_SUCCESSOR_RENDERED_CONTRACT_INVALID")
	}

	q := QueueOrder{
		Schema:        queueSchema,
		ID:            e.ID,
		LogicalStage:  e.ID,
		Kind:          "source",
		WorkOrderYAML: yamlText,
		Dependencies:  []string{e.ParentID},
	}
	raw, err := json.Marshal(q)
	if err != nil {
		return err
	}
	parsedQueue, err := p.parseQueue(raw, e.ID)
	if err != nil {
		return err
	}
	if parsedQueue.ID != e.ID {
		return errors.New("ROADMAP_SUCCESSOR_QUEUE_CONTRACT_INVALID")
	}

	path, err := p.queuePath("pending", e.ID)
	if err != nil {
		return err
	}
	if err = durableNew(path, raw); err != nil {
		if !os.IsExist(err) {
			return err
		}
		existing, readErr := os.ReadFile(path)
		if readErr != nil || digest(existing) != digest(raw) {
			return errors.New("ROADMAP_SUCCESSOR_PENDING_CONFLICT")
		}
	}

	claimed, claimedRaw, err := p.queueClaim(e.ID, "operator", "source")
	if err != nil {
		return err
	}
	if claimed.ID != e.ID || digest(claimedRaw) != digest(raw) {
		return errors.New("ROADMAP_SUCCESSOR_QUEUE_CLAIM_MISMATCH")
	}

	tx, err := p.Store.DB.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()
	message := strings.Join([]string{
		e.Key,
		e.ParentID,
		"->",
		e.ID,
		"baseline_sha=" + candidateSHA,
	}, " ")
	if err = event(tx, e.ID, 0, "ROADMAP_SUCCESSOR_MATERIALIZED", message); err != nil {
		return err
	}
	if err = tx.Commit(); err != nil {
		return err
	}
	return p.setSetting("autonomy_status", "ROADMAP_SUCCESSOR_MATERIALIZED: "+e.ID)
}

// reconcilePineSuccessor retains the already-live R1 call/config seam for
// backward compatibility. Its behavior is now catalog-driven and not Pine
// specific. Future roadmap expansion changes the catalog, not the scheduler.
func (p *Engine) reconcilePineSuccessor(ctx context.Context) error {
	if !p.Config.Autonomy.PineSuccessorController {
		return nil
	}
	if p.setting("paused") == "true" {
		return nil
	}
	if p.Config.Policy.AcceptedRefMutation || p.Config.Policy.RuntimeLaunchAllowed || p.Config.Policy.ArbitraryShell {
		return errors.New("ROADMAP_SUCCESSOR_POLICY_REJECTED")
	}

	catalog, err := loadRoadmapSuccessorCatalog()
	if err != nil {
		return err
	}
	recovered, err := p.recoverRoadmapSourceHygieneLocked(ctx, catalog)
	if err != nil {
		return err
	}
	if recovered {
		return nil
	}
	for _, entry := range catalog.Entries {
		recorded, err := roadmapSuccessorChildRecorded(p, entry.ID)
		if err != nil {
			return err
		}
		if recorded {
			continue
		}
		var state, kind string
		err = p.Store.DB.QueryRow(
			"SELECT state,kind FROM queue_items WHERE id=?",
			entry.ParentID,
		).Scan(&state, &kind)
		if errors.Is(err, sql.ErrNoRows) {
			return nil
		}
		if err != nil {
			return err
		}
		if state != "COMPLETED" || kind != "source" {
			return nil
		}
		return p.materializeRoadmapSuccessor(ctx, entry)
	}
	return p.setSetting("autonomy_status", "ROADMAP_CATALOG_COMPLETE")
}

func postBTVAppendUniqueStrings(dst []string, values ...string) []string {
	seen := map[string]bool{}
	for _, v := range dst {
		seen[v] = true
	}
	for _, v := range values {
		if v == "" || seen[v] {
			continue
		}
		dst = append(dst, v)
		seen[v] = true
	}
	return dst
}

func postBTVMergeUI(parent UIContract, child UIContract) (UIContract, error) {
	out := UIContract{Root: parent.Root, Pages: []UIPage{}, Markers: map[string][]string{}}
	for _, page := range parent.Pages {
		out.Pages = append(out.Pages, UIPage{Path: page.Path, CriticalIDs: append([]string{}, page.CriticalIDs...), ChartID: page.ChartID})
	}
	for key, values := range parent.Markers {
		out.Markers[key] = append([]string{}, values...)
	}
	if child.Root != "" {
		if out.Root != "" && out.Root != child.Root {
			return UIContract{}, errors.New("ROADMAP_SUCCESSOR_UI_ROOT_CONFLICT")
		}
		out.Root = child.Root
	}
	for _, cp := range child.Pages {
		found := false
		for i := range out.Pages {
			if out.Pages[i].Path != cp.Path {
				continue
			}
			found = true
			if cp.ChartID != "" && out.Pages[i].ChartID != "" && cp.ChartID != out.Pages[i].ChartID {
				return UIContract{}, errors.New("ROADMAP_SUCCESSOR_UI_CHART_ID_CONFLICT")
			}
			if out.Pages[i].ChartID == "" {
				out.Pages[i].ChartID = cp.ChartID
			}
			out.Pages[i].CriticalIDs = postBTVAppendUniqueStrings(out.Pages[i].CriticalIDs, cp.CriticalIDs...)
			break
		}
		if !found {
			out.Pages = append(out.Pages, UIPage{Path: cp.Path, CriticalIDs: append([]string{}, cp.CriticalIDs...), ChartID: cp.ChartID})
		}
	}
	for key, values := range child.Markers {
		if inherited, ok := out.Markers[key]; ok {
			if jsonText(inherited) != jsonText(values) {
				return UIContract{}, errors.New("ROADMAP_SUCCESSOR_UI_MARKER_CONFLICT")
			}
			continue
		}
		out.Markers[key] = append([]string{}, values...)
	}
	return out, nil
}

func roadmapSuccessorWorkOrderWithParent(e roadmapSuccessorEntry, parent WorkOrder, candidateSHA string) (WorkOrder, string, error) {
	w, _, err := roadmapSuccessorWorkOrder(e, candidateSHA)
	if err != nil {
		return WorkOrder{}, "", err
	}
	w.Preserve = postBTVAppendUniqueStrings(append([]string{}, parent.Preserve...), w.Preserve...)
	w.UI, err = postBTVMergeUI(parent.UI, w.UI)
	if err != nil {
		return WorkOrder{}, "", err
	}
	if err = w.Validate(); err != nil {
		return WorkOrder{}, "", fmt.Errorf("ROADMAP_SUCCESSOR_RENDERED_WORK_ORDER_INVALID: %w", err)
	}
	raw, err := yaml.Marshal(&w)
	if err != nil {
		return WorkOrder{}, "", errors.New("ROADMAP_SUCCESSOR_YAML_ENCODE_FAILED")
	}
	parsed, err := ParseOrder(raw)
	if err != nil {
		return WorkOrder{}, "", err
	}
	if jsonText(parsed) != jsonText(w) {
		return WorkOrder{}, "", errors.New("ROADMAP_SUCCESSOR_YAML_ROUNDTRIP_MISMATCH")
	}
	return parsed, string(raw), nil
}
