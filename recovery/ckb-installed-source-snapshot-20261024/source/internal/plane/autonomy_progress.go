package plane

import (
	"database/sql"
	"errors"
	"io"
	"time"
)

type progressWriter struct {
	p    *Engine
	id   string
	dest io.Writer
	last time.Time
}

func (w *progressWriter) Write(b []byte) (int, error) {
	n, e := w.dest.Write(b)
	if n > 0 && time.Since(w.last) > time.Second {
		_, _ = w.p.Store.DB.Exec("INSERT OR REPLACE INTO worker_progress VALUES(?,?)", w.id, now())
		w.last = time.Now()
	}
	return n, e
}

func (p *Engine) monitorProgress(id string) error {
	if active, e := p.activeProcessRecord(id); e != nil {
		return e
	} else if active {
		return nil
	}
	if ok, e := p.workerStartupGraceActive(id); e != nil {
		return e
	} else if ok {
		return nil
	}

	var at string
	e := p.Store.DB.QueryRow("SELECT observed FROM worker_progress WHERE work_order_id=?", id).Scan(&at)
	if e != nil {
		e = p.Store.DB.QueryRow("SELECT started FROM worker_attempts WHERE work_order_id=? ORDER BY attempt DESC LIMIT 1", id).Scan(&at)
	}
	if e != nil {
		return e
	}
	t, e := time.Parse(time.RFC3339Nano, at)
	if e != nil {
		return e
	}
	limit := p.Config.Autonomy.MaxNoProgressSeconds
	if limit < 1 {
		limit = 900
	}
	if time.Since(t) > time.Duration(limit)*time.Second {
		if _, e = p.Store.DB.Exec("UPDATE queue_items SET reason='NO_PROGRESS_TIMEOUT',updated=? WHERE id=?", now(), id); e != nil {
			return e
		}
		return p.cancelAttempt(id, "NO_PROGRESS_TIMEOUT")
	}
	return nil
}

func (p *Engine) workerStartupGraceActive(id string) (bool, error) {
	grace := p.workerStartupGrace()
	for _, query := range []string{
		"SELECT timestamp FROM events WHERE work_order_id=? AND type='WORKER_LAUNCH_ATTEMPTED' ORDER BY id DESC LIMIT 1",
		"SELECT started FROM worker_attempts WHERE work_order_id=? ORDER BY attempt DESC LIMIT 1",
	} {
		var at string
		e := p.Store.DB.QueryRow(query, id).Scan(&at)
		if errors.Is(e, sql.ErrNoRows) {
			continue
		}
		if e != nil {
			return false, e
		}
		t, e := time.Parse(time.RFC3339Nano, at)
		if e != nil {
			return false, e
		}
		if time.Since(t) <= grace {
			return true, nil
		}
	}
	return false, nil
}

func (p *Engine) workerStartupGrace() time.Duration {
	seconds := p.Config.Autonomy.PollSeconds * 4
	if seconds < 60 {
		seconds = 60
	}
	if seconds > 300 {
		seconds = 300
	}
	return time.Duration(seconds) * time.Second
}

func (p *Engine) activeProcessRecord(id string) (bool, error) {
	var count int
	if e := p.Store.DB.QueryRow("SELECT count(*) FROM process_records WHERE work_order_id=? AND finished=0", id).Scan(&count); e != nil {
		return false, e
	}
	return count > 0, nil
}
