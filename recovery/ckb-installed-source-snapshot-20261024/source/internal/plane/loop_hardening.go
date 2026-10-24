package plane

import (
	"bytes"
	"database/sql"
	"errors"
	"fmt"
	"path"
	"strings"
)

// consumedWorkerAttempts is the retry-budget authority. A lease/workspace attempt
// is bookkeeping; only a durable WORKER_LAUNCH_ATTEMPTED event consumes model
// execution budget. This prevents deterministic pre-worker failures from
// exhausting the work order before a worker is actually invoked.
func (p *Engine) consumedWorkerAttempts(id string) (int, error) {
	var n int
	e := p.Store.DB.QueryRow("SELECT count(DISTINCT attempt_id) FROM events WHERE work_order_id=? AND type='WORKER_LAUNCH_ATTEMPTED'", id).Scan(&n)
	return n, e
}

func consumedWorkerAttemptsTx(tx *sql.Tx, id string) (int, error) {
	var n int
	e := tx.QueryRow("SELECT count(DISTINCT attempt_id) FROM events WHERE work_order_id=? AND type='WORKER_LAUNCH_ATTEMPTED'", id).Scan(&n)
	return n, e
}

// validateBaselineAcceptanceContract rejects deterministic acceptance-contract
// defects before a worker lease is acquired. It reads only the exact pinned
// baseline object from the registered source repository; it never reads the
// mutable source working tree as candidate input.
//
// RequiredPaths are candidate acceptance outputs. They are validated after
// engineering in the candidate workspace and therefore must not be required to
// exist in the baseline. Baseline preflight is limited to preservation/browser
// inputs that necessarily must already exist before the worker runs.
func (p *Engine) validateBaselineAcceptanceContract(r Repo, w WorkOrder) error {
	if len(w.Preserve) == 0 && !w.Acceptance.Browser {
		return nil
	}
	if w.UI.Root == "" || len(w.UI.Pages) == 0 {
		return errors.New("UI_CONTRACT_INVALID: explicit UI root and pages required for preserve/browser acceptance")
	}

	for _, pageContract := range w.UI.Pages {
		name := path.Join(w.UI.Root, pageContract.Path)
		raw, e := git(p.Config.Tools.Git, r.LocalPath, "show", w.Baseline.SHA+":"+name)
		if e != nil {
			return fmt.Errorf("BASELINE_UI_PAGE_MISSING: %s", name)
		}
		contract, e := htmlContract([]byte(raw))
		if e != nil {
			return fmt.Errorf("BASELINE_UI_PAGE_INVALID: %s", name)
		}
		for _, id := range pageContract.CriticalIDs {
			if contract["id:"+id] != 1 {
				return fmt.Errorf("BROWSER_CRITICAL_CONTROL: %s:%s", name, id)
			}
		}
		if pageContract.ChartID != "" && contract["id:"+pageContract.ChartID] != 1 {
			return fmt.Errorf("BROWSER_CRITICAL_CONTROL: %s:%s", name, pageContract.ChartID)
		}
	}

	if len(w.Preserve) == 0 {
		return nil
	}

	tree, e := git(p.Config.Tools.Git, r.LocalPath, "ls-tree", "-r", "--name-only", "-z", w.Baseline.SHA, "--", w.UI.Root)
	if e != nil {
		return errors.New("BASELINE_UI_TREE_UNAVAILABLE")
	}
	files := []string{}
	for _, name := range strings.Split(tree, "\x00") {
		if name != "" {
			files = append(files, name)
		}
	}

	for _, preserveName := range w.Preserve {
		if preserveName == "element_ids" || preserveName == "data_attributes" {
			continue
		}
		markers := w.UI.Markers[preserveName]
		if len(markers) == 0 {
			return fmt.Errorf("UI_CONTRACT_INVALID: missing explicit markers for %s", preserveName)
		}
		for _, marker := range markers {
			if strings.TrimSpace(marker) == "" {
				return fmt.Errorf("UI_CONTRACT_INVALID: empty marker for %s", preserveName)
			}
			found := false
			for _, name := range files {
				raw, er := git(p.Config.Tools.Git, r.LocalPath, "show", w.Baseline.SHA+":"+name)
				if er == nil && bytes.Contains([]byte(raw), []byte(marker)) {
					found = true
					break
				}
			}
			if !found {
				return fmt.Errorf("BASELINE_UI_MARKER_MISSING: %s:%s", preserveName, marker)
			}
		}
	}
	return nil
}
