package plane

import (
	"context"
	"crypto/rand"
	"crypto/subtle"
	"embed"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"
)

//go:embed web/*
var web embed.FS

func (p *Engine) Token() (string, error) {
	file := filepath.Join(p.Root, "state", "operator.token")
	if b, e := os.ReadFile(file); e == nil {
		v := strings.TrimSpace(string(b))
		if len(v) != 64 {
			return "", errors.New("invalid operator token file")
		}
		return v, nil
	}
	if e := os.MkdirAll(filepath.Dir(file), 0700); e != nil {
		return "", e
	}
	var b [32]byte
	if _, e := rand.Read(b[:]); e != nil {
		return "", e
	}
	v := hex.EncodeToString(b[:])
	f, e := os.OpenFile(file, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	if e != nil {
		return "", e
	}
	_, e = f.WriteString(v)
	ce := f.Close()
	if e == nil {
		e = ce
	}
	return v, e
}
func respond(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}
func (p *Engine) Handler(token string) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			http.Error(w, "method not allowed", 405)
			return
		}
		name := strings.TrimPrefix(r.URL.Path, "/")
		if name == "" {
			name = "index.html"
		}
		if name != "index.html" && name != "app.js" && name != "app.css" {
			http.NotFound(w, r)
			return
		}
		b, e := web.ReadFile("web/" + name)
		if e != nil {
			http.NotFound(w, r)
			return
		}
		switch name {
		case "app.js":
			w.Header().Set("Content-Type", "text/javascript")
		case "app.css":
			w.Header().Set("Content-Type", "text/css")
		default:
			w.Header().Set("Content-Type", "text/html")
		}
		w.Write(b)
	})
	mux.HandleFunc("/api/", func(w http.ResponseWriter, r *http.Request) {
		if subtle.ConstantTimeCompare([]byte(r.Header.Get("Authorization")), []byte("Bearer "+token)) != 1 {
			respond(w, 401, map[string]string{"error": "Operator token required"})
			return
		}
		if r.Header.Get("Origin") != "" && r.Header.Get("Origin") != "http://"+r.Host {
			respond(w, 403, map[string]string{"error": "Origin rejected"})
			return
		}
		if r.Method != "GET" && r.Method != "POST" {
			respond(w, 405, map[string]string{"error": "Method not allowed"})
			return
		}
		r.Body = http.MaxBytesReader(w, r.Body, 256<<10)
		path := strings.TrimPrefix(r.URL.Path, "/api/")
		var result any
		var err error
		if r.Method == "GET" {
			switch path {
			case "native":
				result, err = p.AutonomyStatus()
			case "state":
				jobs, e := p.Store.List()
				err = e
				for i := range jobs {
					jobs[i].Checks, _ = p.Checks(jobs[i].ID)
				}
				result = map[string]any{"why": p.Why(), "jobs": jobs, "authority": p.Authority(), "policy": p.Config.Policy}
			case "workorders":
				result, err = p.Store.List()
			case "tools/doctor":
				result = p.Doctor()
			case "repos":
				result = p.Config.Repos
			case "events":
				p.sse(w, r)
				return
			default:
				parts := strings.Split(path, "/")
				if len(parts) < 2 || parts[0] != "workorders" {
					respond(w, 404, map[string]string{"error": "Unknown endpoint"})
					return
				}
				j, e := p.Store.Get(parts[1])
				err = e
				if e == nil {
					if len(parts) == 2 {
						j.Checks, _ = p.Checks(j.ID)
						result = j
					} else if len(parts) == 3 && parts[2] == "diff" {
						var b []byte
						b, err = os.ReadFile(filepath.Join(j.Evidence, "candidate.diff"))
						result = map[string]string{"diff": string(b), "note": "Tracked patch; untracked file contents are in evidence/candidate_files"}
					} else if len(parts) == 3 && parts[2] == "logs" {
						var b []byte
						b, err = readLogTail(filepath.Join(j.Evidence, "worker_stdout.log"))
						result = map[string]string{"stdout": string(b)}
					} else if len(parts) == 3 && parts[2] == "evidence" {
						var m map[string]string
						m, err = Manifest(j.Evidence)
						if err == nil {
							err = p.VerifyEvidence(j)
						}
						result = map[string]any{"directory": j.Evidence, "manifest": m}
					} else {
						err = errors.New("Unknown endpoint")
					}
				}
			}
		} else {
			switch path {
			case "native":
				var raw []byte
				raw, err = io.ReadAll(r.Body)
				var command NativeRequest
				if err == nil {
					err = bridgeDecode(raw, &command)
				}
				if err == nil {
					result, err = p.HandleNative(r.Context(), command)
				}
			case "workorders/load":
				var b []byte
				b, err = io.ReadAll(r.Body)
				if err == nil {
					err = p.Store.Load(b)
				}
				result = map[string]string{"status": "loaded as DRAFT"}
			case "chat":
				var q struct {
					Text string `json:"text"`
				}
				err = json.NewDecoder(r.Body).Decode(&q)
				if err == nil {
					var a Action
					a, err = p.ParseChat(q.Text)
					if err == nil {
						result, err = p.Action(a)
					}
				}
			case "pause":
				err = p.Store.Pause(true)
				result = map[string]bool{"paused": true}
			case "resume":
				err = p.Store.Pause(false)
				result = map[string]bool{"paused": false}
			default:
				parts := strings.Split(path, "/")
				if len(parts) != 3 || parts[0] != "workorders" {
					respond(w, 404, map[string]string{"error": "Unknown endpoint"})
					return
				}
				result, err = p.Action(Action{parts[2], parts[1], ""})
			}
		}
		if err != nil {
			respond(w, 409, map[string]string{"error": err.Error()})
			return
		}
		respond(w, 200, result)
	})
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		host, _, e := net.SplitHostPort(r.Host)
		if e != nil {
			host = r.Host
		}
		ip := net.ParseIP(host)
		if host != "localhost" && (ip == nil || !ip.IsLoopback()) {
			http.Error(w, "Loopback host required", 403)
			return
		}
		w.Header().Set("Cache-Control", "no-store")
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'")
		mux.ServeHTTP(w, r)
	})
}
func (p *Engine) sse(w http.ResponseWriter, r *http.Request) {
	f, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "stream unavailable", 500)
		return
	}
	w.Header().Set("Content-Type", "text/event-stream")
	after, _ := strconv.ParseInt(r.Header.Get("Last-Event-ID"), 10, 64)
	if q := r.URL.Query().Get("after"); q != "" {
		after, _ = strconv.ParseInt(q, 10, 64)
	}
	tick := time.NewTicker(time.Second)
	defer tick.Stop()
	for {
		events, e := p.Store.Events(after)
		if e != nil {
			return
		}
		for _, ev := range events {
			fmt.Fprintf(w, "id: %d\ndata: %s\n\n", ev.ID, jsonText(ev))
			after = ev.ID
		}
		fmt.Fprint(w, ": heartbeat\n\n")
		f.Flush()
		select {
		case <-r.Context().Done():
			return
		case <-tick.C:
		}
	}
}
func (p *Engine) Serve() error {
	if !p.Config.Autonomy.Enabled {
		if e := p.guardLegacyExecution(); e != nil {
			return e
		}
	}
	ip := net.ParseIP(p.Config.Server.Bind)
	if ip == nil || !ip.IsLoopback() {
		return errors.New("CONFIG_INVALID: milestone 1 only supports loopback bind")
	}
	lock, e := p.controllerLock()
	if e != nil {
		return e
	}
	defer lock.Close()
	if e = p.recoverInterrupted(); e != nil {
		return e
	}

	token, e := p.Token()
	if e != nil {
		return e
	}
	server := http.Server{Addr: net.JoinHostPort(p.Config.Server.Bind, strconv.Itoa(p.Config.Server.Port)), Handler: p.Handler(token), ReadHeaderTimeout: 5 * time.Second, IdleTimeout: 60 * time.Second}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	p.mu.Lock()
	p.shutdown = stop
	p.mu.Unlock()
	var background sync.WaitGroup
	if p.shouldRunAutonomyLoop() {
		background.Add(1)
		go func() { defer background.Done(); p.AutonomyLoop(ctx) }()
	}
	if p.bridge != nil {
		background.Add(1)
		go func() {
			defer background.Done()
			_ = p.bridge.Watch(ctx, func(e error) { _ = p.setSetting("bridge_status", e.Error()) })
		}()
	}
	defer func() { stop(); background.Wait() }()
	done := make(chan struct{})
	go func() {
		select {
		case <-ctx.Done():
			shutdown, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()
			_ = server.Shutdown(shutdown)
			p.mu.Lock()
			p.shuttingDown = true
			p.mu.Unlock()
			p.cancelAllAttempts("CONTROLLER_SHUTDOWN")
		case <-done:
		}
	}()
	err := server.ListenAndServe()
	stop()
	p.mu.Lock()
	p.shuttingDown = true
	p.mu.Unlock()
	p.cancelAllAttempts("CONTROLLER_EXIT")
	close(done)
	deadline := time.Now().Add(5 * time.Second)
	for time.Now().Before(deadline) {
		p.mu.Lock()
		n := len(p.cancels)
		p.mu.Unlock()
		if n == 0 {
			break
		}
		time.Sleep(10 * time.Millisecond)
	}
	if errors.Is(err, http.ErrServerClosed) {
		return nil
	}
	return err
}

type Action struct {
	Action string `json:"action"`
	ID     string `json:"work_order_id"`
	Worker string `json:"worker,omitempty"`
}

func (p *Engine) ParseChat(text string) (Action, error) {
	s := strings.ToLower(strings.TrimSpace(text))
	switch s {
	case "why idle", "why blocked", "show current job":
		return Action{Action: "status"}, nil
	case "pause dispatch":
		return Action{Action: "pause"}, nil
	case "resume dispatch":
		return Action{Action: "resume"}, nil
	case "cancel current attempt":
		jobs, _ := p.Store.List()
		var ids []string
		for _, j := range jobs {
			if j.State == "ENGINEERING" || j.State == "DISPATCHED" {
				ids = append(ids, j.ID)
			}
		}
		if len(ids) == 1 {
			return Action{"cancel", ids[0], ""}, nil
		}
		return Action{}, errors.New("No unique active attempt")
	}
	var action, alias, worker string
	for _, prefix := range []string{"run acceptance for ", "show evidence for ", "show diff for ", "authorize ", "dispatch ", "retry "} {
		if strings.HasPrefix(s, prefix) {
			alias = strings.TrimPrefix(s, prefix)
			switch prefix {
			case "run acceptance for ":
				action = "accept"
			case "show evidence for ":
				action = "evidence"
			case "show diff for ":
				action = "diff"
			default:
				action = strings.TrimSpace(prefix)
			}
			break
		}
	}
	if action == "retry" && strings.HasSuffix(alias, " with codex") {
		alias = strings.TrimSuffix(alias, " with codex")
		worker = "codex"
	}
	if action == "" || alias == "" || strings.ContainsAny(alias, " ;\r\n") {
		return Action{}, errors.New("Unsupported command. Only structured execution-plane actions are accepted. Arbitrary shell commands are disabled.")
	}
	jobs, e := p.Store.List()
	if e != nil {
		return Action{}, e
	}
	var matches []string
	for _, j := range jobs {
		low := strings.ToLower(j.ID)
		if low == alias || strings.Contains(low, "_stage_"+alias+"_") {
			matches = append(matches, j.ID)
		}
	}
	if len(matches) != 1 {
		return Action{}, errors.New("Work order alias missing or ambiguous; use exact ID")
	}
	return Action{action, matches[0], worker}, nil
}
func (p *Engine) Action(a Action) (any, error) {
	var err error
	if a.Worker != "" {
		j, e := p.Store.Get(a.ID)
		if e != nil {
			return nil, e
		}
		if a.Worker != j.Order.Worker.Preferred {
			return nil, errors.New("WORKER_CONTRACT_CHANGED: load a new explicitly authorized work order to change adapter")
		}
	}
	switch a.Action {
	case "status":
		return map[string]string{"why": p.Why()}, nil
	case "pause":
		err = p.Store.Pause(true)
	case "resume":
		err = p.Store.Pause(false)
	case "authorize":
		err = p.Authorize(a.ID)
		if err == nil {
			err = p.Ready(a.ID)
		}
	case "dispatch":
		err = p.Dispatch(a.ID)
	case "retry":
		err = p.Retry(a.ID)
	case "cancel":
		err = p.Cancel(a.ID)
	case "accept":
		err = p.Accept(a.ID)
	case "diff", "evidence":
		j, e := p.Store.Get(a.ID)
		if e != nil {
			return nil, e
		}
		if a.Action == "evidence" {
			if e = p.VerifyEvidence(j); e != nil {
				return nil, e
			}
			return Manifest(j.Evidence)
		}
		b, e := os.ReadFile(filepath.Join(j.Evidence, "candidate.diff"))
		return map[string]string{"diff": string(b)}, e
	default:
		err = errors.New("Unsupported structured action")
	}
	return map[string]string{"action": a.Action, "work_order_id": a.ID}, err
}

func readLogTail(file string) ([]byte, error) {
	f, e := os.Open(file)
	if e != nil {
		return nil, e
	}
	defer f.Close()
	info, e := f.Stat()
	if e != nil {
		return nil, e
	}
	start := info.Size() - 64*1024
	if start < 0 {
		start = 0
	}
	if _, e = f.Seek(start, 0); e != nil {
		return nil, e
	}
	return io.ReadAll(io.LimitReader(f, 64*1024))
}
