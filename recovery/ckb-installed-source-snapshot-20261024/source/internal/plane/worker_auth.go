package plane

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

const workerAuthRetryAuthorizedReason = "OPERATOR_WORKER_AUTH_RETRY_AUTHORIZED"
const workerAuthEvidenceLimit = 1 << 20

// Fail closed on missing, oversized, non-regular or externally aliased evidence.
func authEvidence(root, dir, name string) ([]byte, error) {
	p := filepath.Join(dir, name)
	if e := bridgeContained(root, p); e != nil {
		return nil, e
	}
	f, e := os.Open(p)
	if e != nil {
		return nil, e
	}
	defer f.Close()
	s, e := f.Stat()
	if e != nil {
		return nil, e
	}
	if !s.Mode().IsRegular() || s.Size() > workerAuthEvidenceLimit {
		return nil, fmt.Errorf("AUTH_EVIDENCE_INVALID")
	}
	b, e := io.ReadAll(io.LimitReader(f, workerAuthEvidenceLimit+1))
	if len(b) > workerAuthEvidenceLimit {
		return nil, fmt.Errorf("AUTH_EVIDENCE_TOO_LARGE")
	}
	return b, e
}

func revokedWorkerAuth(root, evidence string) bool {
	for _, name := range []string{"worker_stdout.log", "worker_stderr.log"} {
		b, e := authEvidence(root, evidence, name)
		if e != nil {
			continue
		}
		s := strings.ToLower(string(b))
		for _, marker := range []string{"token_revoked", "refresh_token_invalidated", "refresh token was revoked"} {
			if strings.Contains(s, marker) {
				return true
			}
		}
	}
	return false
}

func workerExitFailure(worker, root, evidence string) string {
	if worker == "codex" && revokedWorkerAuth(root, evidence) {
		return "WORKER_AUTH_UNAVAILABLE"
	}
	return "WORKER_EXIT_NONZERO"
}

func (p *Engine) workerAuthRetryEscapeAllowed(tx *sql.Tx, id, inputHash string) (bool, error) {
	var attempt int
	var evidence string
	var native []byte
	if e := tx.QueryRow("SELECT attempt,evidence,yaml FROM work_orders WHERE id=?", id).Scan(&attempt, &evidence, &native); e != nil {
		return false, e
	}
	// The engine assigns this path from the monotonically increasing lease number.
	expected := filepath.Join(p.Root, "evidence", id, fmt.Sprint(attempt))
	if attempt < 1 || filepath.Clean(evidence) != filepath.Clean(expected) {
		return false, nil
	}
	var latest int
	var worker string
	var recordedExit sql.NullInt64
	e := tx.QueryRow("SELECT attempt,worker,exit_code FROM worker_attempts WHERE work_order_id=? ORDER BY attempt DESC LIMIT 1", id).Scan(&latest, &worker, &recordedExit)
	if e == sql.ErrNoRows {
		return false, nil
	}
	if e != nil {
		return false, e
	}
	if latest != attempt || worker != "codex" || !recordedExit.Valid || recordedExit.Int64 == 0 {
		return false, nil
	}
	read := func(name string, v any) bool {
		b, e := authEvidence(p.Root, evidence, name)
		return e == nil && json.Unmarshal(b, v) == nil
	}
	var exit struct {
		Code  *int   `json:"exit_code"`
		Class string `json:"failure_class"`
	}
	if !read("worker_exit.json", &exit) || exit.Code == nil || *exit.Code == 0 || (exit.Class != "WORKER_AUTH_UNAVAILABLE" && exit.Class != "WORKER_EXIT_NONZERO") {
		return false, nil
	}
	var acceptance struct {
		Ran      *bool `json:"acceptance_ran"`
		Accepted bool  `json:"production_accepted"`
	}
	if !read("acceptance_result.json", &acceptance) || acceptance.Ran == nil || *acceptance.Ran || acceptance.Accepted {
		return false, nil
	}
	for _, name := range []string{"candidate.diff", "changed_files.txt"} {
		b, e := authEvidence(p.Root, evidence, name)
		if e != nil || len(bytes.TrimSpace(b)) != 0 {
			return false, nil
		}
	}
	b, e := authEvidence(p.Root, evidence, "work_order.yaml")
	if e != nil || !bytes.Equal(b, native) {
		return false, nil
	}
	order, e := ParseOrder(native)
	if e != nil || order.ID != id || order.Worker.Preferred != "codex" {
		return false, nil
	}
	var receiptHash string
	var receiptRaw []byte
	e = tx.QueryRow("SELECT hash,raw FROM queue_receipts WHERE work_order_id=?", id).Scan(&receiptHash, &receiptRaw)
	if e == sql.ErrNoRows {
		return false, nil
	}
	if e != nil {
		return false, e
	}
	var result QueueResult
	if digest(receiptRaw) != receiptHash || json.Unmarshal(receiptRaw, &result) != nil || result.WorkOrderID != id || result.InputSHA256 != inputHash || result.ProductionAccepted {
		return false, nil
	}
	return revokedWorkerAuth(p.Root, evidence), nil
}
