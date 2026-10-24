package plane

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"io"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

type winglessStage1DormantCountingRunner struct {
	calls int
	run   func(context.Context, ProcessSpec, io.Writer, io.Writer) error
}

func (r *winglessStage1DormantCountingRunner) Run(ctx context.Context, spec ProcessSpec, stdout, stderr io.Writer) error {
	r.calls++
	if r.run != nil {
		return r.run(ctx, spec, stdout, stderr)
	}
	return nil
}

func TestWinglessStage1DormantRejectsProgramHashMismatchBeforeLaunch(t *testing.T) {
	program := filepath.Join(t.TempDir(), "service.exe")
	if err := os.WriteFile(program, []byte("fixture"), 0700); err != nil {
		t.Fatal(err)
	}
	runner := &winglessStage1DormantCountingRunner{}
	_, err := (WinglessStage1DormantLauncher{Runner: runner}).Start(context.Background(), program, strings.Repeat("0", 64))
	if err == nil || !strings.Contains(err.Error(), "PROGRAM_HASH_MISMATCH") {
		t.Fatalf("got %v", err)
	}
	if runner.calls != 0 {
		t.Fatalf("runner invoked %d times before program identity passed", runner.calls)
	}
}

func TestWinglessStage1DormantRejectsInvalidEndpointForms(t *testing.T) {
	bad := []string{
		"http://localhost:1234",
		"http://[::1]:1234",
		"http://127.0.0.2:1234",
		"http://127.0.0.1:1234/stage1",
		"http://127.0.0.1:1234/?x=1",
		"https://127.0.0.1:1234",
	}
	for _, raw := range bad {
		if _, err := winglessStage1ValidateDormantEndpoint(raw); err == nil {
			t.Fatalf("accepted %q", raw)
		}
	}
	got, err := winglessStage1ValidateDormantEndpoint("http://127.0.0.1:32123")
	if err != nil || got != "http://127.0.0.1:32123" {
		t.Fatalf("got=%q err=%v", got, err)
	}
}

func TestWinglessStage1DormantExchangeFenceIsSingleUse(t *testing.T) {
	proc := newWinglessStage1DormantProcess()
	h := &WinglessStage1DormantHandle{
		endpoint: "http://127.0.0.1:1",
		secret:   strings.Repeat("a", 64),
		cancel:   func() {},
		proc:     proc,
		state:    winglessStage1DormantStateRunning,
		used:     true,
	}
	_, err := h.Exchange(context.Background(), []byte(`{"schema":"fixture"}`))
	if err == nil || !strings.Contains(err.Error(), "EXCHANGE_ALREADY_USED") {
		t.Fatalf("got %v", err)
	}
}

func TestWinglessStage1DormantExchangeAuthenticatesRequestAndResponse(t *testing.T) {
	listener, err := net.Listen("tcp4", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer listener.Close()
	secret := strings.Repeat("a", 64)
	requestBody := []byte(`{"schema":"fixture"}`)
	responseBody := []byte(`{"schema":"fixture-response"}`)
	server := &http.Server{Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		body, readErr := io.ReadAll(r.Body)
		if readErr != nil {
			t.Errorf("read: %v", readErr)
			w.WriteHeader(http.StatusBadRequest)
			return
		}
		mac := hmac.New(sha256.New, []byte(secret))
		_, _ = mac.Write(body)
		got, decodeErr := hex.DecodeString(r.Header.Get("X-CKB-Wingless-Signature"))
		if decodeErr != nil || !hmac.Equal(got, mac.Sum(nil)) || string(body) != string(requestBody) {
			t.Errorf("request authentication mismatch")
			w.WriteHeader(http.StatusUnauthorized)
			return
		}
		responseMAC := hmac.New(sha256.New, []byte(secret))
		_, _ = responseMAC.Write(responseBody)
		w.Header().Set("X-CKB-Wingless-Response-Signature", hex.EncodeToString(responseMAC.Sum(nil)))
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write(responseBody)
	})}
	go func() { _ = server.Serve(listener) }()
	defer server.Close()

	proc := newWinglessStage1DormantProcess()
	h := &WinglessStage1DormantHandle{
		endpoint: "http://" + listener.Addr().String(),
		secret:   secret,
		cancel:   func() {},
		proc:     proc,
		state:    winglessStage1DormantStateRunning,
	}
	got, err := h.Exchange(context.Background(), requestBody)
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != string(responseBody) {
		t.Fatalf("response=%q", got)
	}
	if _, err := h.Exchange(context.Background(), requestBody); err == nil || !strings.Contains(err.Error(), "EXCHANGE_ALREADY_USED") {
		t.Fatalf("second exchange got %v", err)
	}
}

func TestWinglessStage1DormantExchangeRejectsUnauthenticatedResponse(t *testing.T) {
	listener, err := net.Listen("tcp4", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer listener.Close()
	server := &http.Server{Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"schema":"unsigned"}`))
	})}
	go func() { _ = server.Serve(listener) }()
	defer server.Close()

	proc := newWinglessStage1DormantProcess()
	h := &WinglessStage1DormantHandle{
		endpoint: "http://" + listener.Addr().String(),
		secret:   strings.Repeat("b", 64),
		cancel:   func() {},
		proc:     proc,
		state:    winglessStage1DormantStateRunning,
	}
	_, err = h.Exchange(context.Background(), []byte(`{"schema":"fixture"}`))
	if err == nil || !strings.Contains(err.Error(), "RESPONSE_AUTH_MISSING") {
		t.Fatalf("got %v", err)
	}
}

func TestWinglessStage1DormantLauncherUsesMinimalEnvironmentAndOneProcess(t *testing.T) {
	program := filepath.Join(t.TempDir(), "service.exe")
	content := []byte("fixture-service")
	if err := os.WriteFile(program, content, 0700); err != nil {
		t.Fatal(err)
	}
	sum := sha256.Sum256(content)
	hash := hex.EncodeToString(sum[:])
	runner := &winglessStage1DormantCountingRunner{}
	runner.run = func(ctx context.Context, spec ProcessSpec, stdout, stderr io.Writer) error {
		if spec.Program != program || spec.Dir != filepath.Dir(program) || len(spec.Args) != 0 || spec.Input != "" {
			return errors.New("unexpected process spec")
		}
		allowed := map[string]bool{
			"PATH": true, "SYSTEMROOT": true, "WINDIR": true, "COMSPEC": true, "TEMP": true, "TMP": true,
			"USERPROFILE": true, "APPDATA": true, "LOCALAPPDATA": true, "HOME": true, "LANG": true,
			"CKB_WINGLESS_STAGE1_INSTANCE_SECRET": true,
		}
		secretCount := 0
		for _, entry := range spec.Env {
			name, value, ok := strings.Cut(entry, "=")
			if !ok || !allowed[name] {
				return errors.New("unexpected inherited environment name")
			}
			if name == "CKB_WINGLESS_STAGE1_INSTANCE_SECRET" {
				secretCount++
				if !winglessStage1DormantValidSHA256(value) {
					return errors.New("invalid instance secret")
				}
			}
		}
		if secretCount != 1 {
			return errors.New("instance secret count mismatch")
		}
		_, _ = io.WriteString(stdout, `{"schema":"wingless.stage1-ar2-ready.v1","endpoint":"http://127.0.0.1:32124","pid":123}`+"\n")
		<-ctx.Done()
		return ctx.Err()
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	h, err := (WinglessStage1DormantLauncher{Runner: runner, StartupTimeout: time.Second}).Start(ctx, program, hash)
	if err != nil {
		t.Fatal(err)
	}
	if runner.calls != 1 {
		t.Fatalf("runner calls=%d", runner.calls)
	}
	if h.State() != winglessStage1DormantStateRunning {
		t.Fatalf("state=%s", h.State())
	}
	if err := h.Close(); err != nil {
		t.Fatal(err)
	}
	if h.State() != winglessStage1DormantStateClosed {
		t.Fatalf("state after close=%s", h.State())
	}
}

func TestWinglessStage1DormantNotRegisteredByDefault(t *testing.T) {
	p, _ := setup(t)
	if p.workers["wingless"] != nil || p.workers["wingless-stage1"] != nil || p.workers["wingless-stage1-ar2"] != nil {
		t.Fatal("dormant Stage-1 process composition unexpectedly registered a worker")
	}
}
