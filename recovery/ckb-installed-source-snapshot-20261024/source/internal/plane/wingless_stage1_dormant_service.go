package plane

import (
	"bytes"
	"context"
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"
)

const (
	winglessStage1DormantReadySchema     = "wingless.stage1-ar2-ready.v1"
	winglessStage1DormantReadyLimit      = 4096
	winglessStage1DormantRequestLimit    = 512 << 10
	winglessStage1DormantResponseLimit   = 512 << 10
	winglessStage1DormantExchangeTimeout = 15 * time.Minute

	winglessStage1DormantStateRunning = "running"
	winglessStage1DormantStateClosing = "closing"
	winglessStage1DormantStateClosed  = "closed"
	winglessStage1DormantStateDead    = "dead"
)

type WinglessStage1DormantLauncher struct {
	Runner         ProcessRunner
	StartupTimeout time.Duration
}

type winglessStage1DormantProcess struct {
	done   chan struct{}
	mu     sync.Mutex
	err    error
	finish sync.Once
}

func newWinglessStage1DormantProcess() *winglessStage1DormantProcess {
	return &winglessStage1DormantProcess{done: make(chan struct{})}
}

func (p *winglessStage1DormantProcess) complete(err error) {
	p.finish.Do(func() {
		p.mu.Lock()
		p.err = err
		p.mu.Unlock()
		close(p.done)
	})
}

func (p *winglessStage1DormantProcess) result() error {
	if p == nil {
		return errors.New("WINGLESS_STAGE1_DORMANT_PROCESS_UNAVAILABLE")
	}
	p.mu.Lock()
	defer p.mu.Unlock()
	return p.err
}

type WinglessStage1DormantHandle struct {
	endpoint string
	secret   string
	cancel   context.CancelFunc
	proc     *winglessStage1DormantProcess

	mu       sync.Mutex
	state    string
	closeErr error
	used     bool
}

type winglessStage1DormantReady struct {
	Schema   string `json:"schema"`
	Endpoint string `json:"endpoint"`
	PID      int    `json:"pid"`
}

type winglessStage1DormantReadyCapture struct {
	mu   sync.Mutex
	buf  bytes.Buffer
	line chan []byte
	sent bool
}

func newWinglessStage1DormantReadyCapture() *winglessStage1DormantReadyCapture {
	return &winglessStage1DormantReadyCapture{line: make(chan []byte, 1)}
}

func (w *winglessStage1DormantReadyCapture) Write(p []byte) (int, error) {
	w.mu.Lock()
	defer w.mu.Unlock()
	if w.sent {
		return len(p), nil
	}
	if w.buf.Len()+len(p) > winglessStage1DormantReadyLimit {
		return 0, errors.New("WINGLESS_STAGE1_DORMANT_READY_LIMIT")
	}
	_, _ = w.buf.Write(p)
	data := w.buf.Bytes()
	if i := bytes.IndexByte(data, '\n'); i >= 0 {
		line := append([]byte(nil), data[:i]...)
		w.sent = true
		w.line <- line
	}
	return len(p), nil
}

type winglessStage1DormantLockedBuffer struct {
	mu  sync.Mutex
	buf bytes.Buffer
}

func (b *winglessStage1DormantLockedBuffer) Write(p []byte) (int, error) {
	b.mu.Lock()
	defer b.mu.Unlock()
	return b.buf.Write(p)
}

func (b *winglessStage1DormantLockedBuffer) String() string {
	b.mu.Lock()
	defer b.mu.Unlock()
	return b.buf.String()
}

func winglessStage1DormantRandomSecret() (string, error) {
	var raw [32]byte
	if _, err := rand.Read(raw[:]); err != nil {
		return "", err
	}
	return hex.EncodeToString(raw[:]), nil
}

func winglessStage1DormantValidSHA256(v string) bool {
	return len(v) == 64 && strings.Trim(v, "0123456789abcdef") == ""
}

func winglessStage1DormantFileSHA256(path string) (string, error) {
	f, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer f.Close()
	h := sha256.New()
	if _, err := io.Copy(h, f); err != nil {
		return "", err
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}

func winglessStage1ValidateDormantEndpoint(raw string) (string, error) {
	u, err := url.Parse(raw)
	if err != nil || u.Scheme != "http" || u.User != nil || u.RawQuery != "" || u.Fragment != "" {
		return "", errors.New("WINGLESS_STAGE1_DORMANT_ENDPOINT_INVALID")
	}
	if u.Path != "" && u.Path != "/" {
		return "", errors.New("WINGLESS_STAGE1_DORMANT_ENDPOINT_INVALID")
	}
	host := u.Hostname()
	if host != "127.0.0.1" {
		return "", errors.New("WINGLESS_STAGE1_DORMANT_ENDPOINT_NOT_NUMERIC_IPV4_LOOPBACK")
	}
	ip := net.ParseIP(host)
	if ip == nil || ip.To4() == nil || !ip.IsLoopback() {
		return "", errors.New("WINGLESS_STAGE1_DORMANT_ENDPOINT_NOT_NUMERIC_IPV4_LOOPBACK")
	}
	port, err := strconv.Atoi(u.Port())
	if err != nil || port < 1 || port > 65535 {
		return "", errors.New("WINGLESS_STAGE1_DORMANT_ENDPOINT_INVALID_PORT")
	}
	return fmt.Sprintf("http://127.0.0.1:%d", port), nil
}

func (l WinglessStage1DormantLauncher) Start(ctx context.Context, program, expectedSHA256 string) (*WinglessStage1DormantHandle, error) {
	if ctx == nil {
		return nil, errors.New("WINGLESS_STAGE1_DORMANT_CONTEXT_REQUIRED")
	}
	if program == "" || !filepath.IsAbs(program) || filepath.Clean(program) != program || strings.ContainsAny(program, "\x00\r\n") {
		return nil, errors.New("WINGLESS_STAGE1_DORMANT_PROGRAM_INVALID")
	}
	if !winglessStage1DormantValidSHA256(expectedSHA256) {
		return nil, errors.New("WINGLESS_STAGE1_DORMANT_PROGRAM_HASH_INVALID")
	}
	info, err := os.Lstat(program)
	if err != nil || !info.Mode().IsRegular() {
		return nil, errors.New("WINGLESS_STAGE1_DORMANT_PROGRAM_UNAVAILABLE")
	}
	if rp, err := winglessStage1IsReparse(program); err != nil || rp {
		return nil, errors.New("WINGLESS_STAGE1_DORMANT_PROGRAM_REPARSE_PROHIBITED")
	}
	observed, err := winglessStage1DormantFileSHA256(program)
	if err != nil {
		return nil, fmt.Errorf("WINGLESS_STAGE1_DORMANT_PROGRAM_HASH_READ_FAILED: %w", err)
	}
	if observed != expectedSHA256 {
		return nil, errors.New("WINGLESS_STAGE1_DORMANT_PROGRAM_HASH_MISMATCH")
	}

	secret, err := winglessStage1DormantRandomSecret()
	if err != nil {
		return nil, fmt.Errorf("WINGLESS_STAGE1_DORMANT_SECRET_FAILED: %w", err)
	}

	timeout := l.StartupTimeout
	if timeout <= 0 {
		timeout = 10 * time.Second
	}
	if timeout > 30*time.Second {
		return nil, errors.New("WINGLESS_STAGE1_DORMANT_STARTUP_TIMEOUT_INVALID")
	}

	runner := l.Runner
	if runner == nil {
		runner = SupervisedRunner{}
	}
	runCtx, cancel := context.WithCancel(ctx)
	capture := newWinglessStage1DormantReadyCapture()
	var stderr winglessStage1DormantLockedBuffer
	proc := newWinglessStage1DormantProcess()

	spec := ProcessSpec{
		Program: program,
		Dir:     filepath.Dir(program),
		Env: append(minimalEnv(),
			"CKB_WINGLESS_STAGE1_INSTANCE_SECRET="+secret,
		),
	}
	go func() {
		proc.complete(runner.Run(runCtx, spec, capture, &stderr))
	}()

	fail := func(startErr error) (*WinglessStage1DormantHandle, error) {
		cancel()
		select {
		case <-proc.done:
			if text := strings.TrimSpace(stderr.String()); text != "" {
				return nil, fmt.Errorf("%w: %s", startErr, text)
			}
			return nil, startErr
		case <-time.After(5 * time.Second):
			return &WinglessStage1DormantHandle{
				secret: secret,
				cancel: cancel,
				proc:   proc,
				state:  winglessStage1DormantStateClosing,
			}, fmt.Errorf("WINGLESS_STAGE1_DORMANT_SHUTDOWN_UNCONFIRMED: %w", startErr)
		}
	}

	timer := time.NewTimer(timeout)
	defer timer.Stop()

	var line []byte
	select {
	case line = <-capture.line:
	case <-proc.done:
		err := proc.result()
		if err == nil {
			err = errors.New("WINGLESS_STAGE1_DORMANT_EXITED_BEFORE_READY")
		}
		cancel()
		return nil, fmt.Errorf("WINGLESS_STAGE1_DORMANT_START_FAILED: %w", err)
	case <-ctx.Done():
		return fail(ctx.Err())
	case <-timer.C:
		return fail(errors.New("WINGLESS_STAGE1_DORMANT_STARTUP_TIMEOUT"))
	}

	var ready winglessStage1DormantReady
	d := json.NewDecoder(bytes.NewReader(line))
	d.DisallowUnknownFields()
	if err := d.Decode(&ready); err != nil {
		return fail(fmt.Errorf("WINGLESS_STAGE1_DORMANT_READY_INVALID: %w", err))
	}
	var extra any
	if err := d.Decode(&extra); err != io.EOF {
		return fail(errors.New("WINGLESS_STAGE1_DORMANT_READY_INVALID"))
	}
	if ready.Schema != winglessStage1DormantReadySchema || ready.PID <= 0 {
		return fail(errors.New("WINGLESS_STAGE1_DORMANT_READY_INVALID"))
	}
	endpoint, err := winglessStage1ValidateDormantEndpoint(ready.Endpoint)
	if err != nil {
		return fail(err)
	}
	select {
	case <-proc.done:
		return fail(errors.New("WINGLESS_STAGE1_DORMANT_EXITED_AFTER_READY"))
	default:
	}

	return &WinglessStage1DormantHandle{
		endpoint: endpoint,
		secret:   secret,
		cancel:   cancel,
		proc:     proc,
		state:    winglessStage1DormantStateRunning,
	}, nil
}

func (h *WinglessStage1DormantHandle) refreshStateLocked() {
	if h == nil || h.proc == nil {
		return
	}
	select {
	case <-h.proc.done:
		switch h.state {
		case winglessStage1DormantStateRunning:
			h.state = winglessStage1DormantStateDead
		case winglessStage1DormantStateClosing:
			h.state = winglessStage1DormantStateClosed
		}
	default:
	}
}

func (h *WinglessStage1DormantHandle) State() string {
	if h == nil {
		return winglessStage1DormantStateClosed
	}
	h.mu.Lock()
	defer h.mu.Unlock()
	h.refreshStateLocked()
	return h.state
}

func (h *WinglessStage1DormantHandle) Exchange(ctx context.Context, request []byte) ([]byte, error) {
	if h == nil || h.proc == nil || h.cancel == nil {
		return nil, errors.New("WINGLESS_STAGE1_DORMANT_HANDLE_INVALID")
	}
	if ctx == nil {
		return nil, errors.New("WINGLESS_STAGE1_DORMANT_CONTEXT_REQUIRED")
	}
	if len(request) == 0 || len(request) > winglessStage1DormantRequestLimit {
		return nil, errors.New("WINGLESS_STAGE1_DORMANT_REQUEST_LIMIT")
	}

	h.mu.Lock()
	h.refreshStateLocked()
	if h.used {
		h.mu.Unlock()
		return nil, errors.New("WINGLESS_STAGE1_DORMANT_EXCHANGE_ALREADY_USED")
	}
	if h.state != winglessStage1DormantStateRunning {
		state := h.state
		h.mu.Unlock()
		return nil, fmt.Errorf("WINGLESS_STAGE1_DORMANT_NOT_RUNNING: %s", state)
	}
	endpoint := h.endpoint
	secret := h.secret
	h.used = true
	h.mu.Unlock()

	mac := hmac.New(sha256.New, []byte(secret))
	_, _ = mac.Write(request)
	signature := hex.EncodeToString(mac.Sum(nil))

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint+"/stage1", bytes.NewReader(request))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-CKB-Wingless-Signature", signature)

	client := &http.Client{
		Timeout: winglessStage1DormantExchangeTimeout,
		Transport: &http.Transport{
			Proxy: nil,
			DialContext: (&net.Dialer{
				Timeout: 10 * time.Second,
			}).DialContext,
		},
		CheckRedirect: func(_ *http.Request, _ []*http.Request) error {
			return errors.New("WINGLESS_STAGE1_DORMANT_REDIRECT_REFUSED")
		},
	}
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("WINGLESS_STAGE1_DORMANT_EXCHANGE_FAILED: %w", err)
	}
	defer resp.Body.Close()

	limited := io.LimitReader(resp.Body, winglessStage1DormantResponseLimit+1)
	body, err := io.ReadAll(limited)
	if err != nil {
		return nil, fmt.Errorf("WINGLESS_STAGE1_DORMANT_RESPONSE_READ_FAILED: %w", err)
	}
	if len(body) > winglessStage1DormantResponseLimit {
		return nil, errors.New("WINGLESS_STAGE1_DORMANT_RESPONSE_LIMIT")
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("WINGLESS_STAGE1_DORMANT_REMOTE_STATUS_%d", resp.StatusCode)
	}

	responseSignature := resp.Header.Get("X-CKB-Wingless-Response-Signature")
	if len(responseSignature) != 64 {
		return nil, errors.New("WINGLESS_STAGE1_DORMANT_RESPONSE_AUTH_MISSING")
	}
	expectedMAC := hmac.New(sha256.New, []byte(secret))
	_, _ = expectedMAC.Write(body)
	expectedSig, err := hex.DecodeString(responseSignature)
	if err != nil || !hmac.Equal(expectedSig, expectedMAC.Sum(nil)) {
		return nil, errors.New("WINGLESS_STAGE1_DORMANT_RESPONSE_AUTH_INVALID")
	}
	return body, nil
}

func (h *WinglessStage1DormantHandle) Close() error {
	if h == nil {
		return nil
	}
	if h.proc == nil || h.cancel == nil {
		return errors.New("WINGLESS_STAGE1_DORMANT_HANDLE_INVALID")
	}

	h.mu.Lock()
	h.refreshStateLocked()
	if h.state == winglessStage1DormantStateClosed {
		err := h.closeErr
		h.mu.Unlock()
		return err
	}
	wasDead := h.state == winglessStage1DormantStateDead
	h.state = winglessStage1DormantStateClosing
	h.mu.Unlock()

	h.cancel()
	select {
	case <-h.proc.done:
		procErr := h.proc.result()
		h.mu.Lock()
		h.state = winglessStage1DormantStateClosed
		if wasDead && procErr != nil && !errors.Is(procErr, context.Canceled) {
			h.closeErr = fmt.Errorf("WINGLESS_STAGE1_DORMANT_PROCESS_EXITED: %w", procErr)
		} else if procErr != nil && !errors.Is(procErr, context.Canceled) {
			h.closeErr = procErr
		} else {
			h.closeErr = nil
		}
		h.secret = ""
		err := h.closeErr
		h.mu.Unlock()
		return err
	case <-time.After(5 * time.Second):
		h.mu.Lock()
		h.state = winglessStage1DormantStateClosing
		h.closeErr = errors.New("WINGLESS_STAGE1_DORMANT_STOP_UNCONFIRMED")
		err := h.closeErr
		h.mu.Unlock()
		return err
	}
}
