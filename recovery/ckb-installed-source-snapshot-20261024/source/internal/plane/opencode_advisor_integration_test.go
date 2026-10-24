package plane

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func q2OpenCodeTool(t *testing.T) string {
	t.Helper()
	if os.Getenv("CKB_OPENCODE_Q2") != "1" {
		t.Skip("CKB_OPENCODE_Q2=1 required")
	}
	tool := os.Getenv("CKB_OPENCODE_EXE")
	if tool == "" || !filepath.IsAbs(tool) {
		t.Fatal("CKB_OPENCODE_EXE must be an absolute path")
	}
	info, err := os.Lstat(tool)
	if err != nil || !info.Mode().IsRegular() || info.Mode()&os.ModeSymlink != 0 {
		t.Fatalf("invalid OpenCode executable: %v", err)
	}
	if strings.TrimSpace(os.Getenv("OPENROUTER_API_KEY")) == "" {
		t.Fatal("OPENROUTER_API_KEY unavailable")
	}
	return tool
}

func q2HostExecutable(t *testing.T) string {
	t.Helper()
	host := os.Getenv("CKB_OPENCODE_Q2_PLANE_EXE")
	if host == "" || !filepath.IsAbs(host) {
		t.Fatal("CKB_OPENCODE_Q2_PLANE_EXE must be an absolute path")
	}
	info, err := os.Lstat(host)
	if err != nil || !info.Mode().IsRegular() || info.Mode()&os.ModeSymlink != 0 {
		t.Fatalf("invalid Q2 plane host executable: %v", err)
	}
	return host
}

func q2Advisor(t *testing.T, runner *SupervisedRunner) OpenCodeAdvisor {
	t.Helper()
	tool := q2OpenCodeTool(t)
	r := SupervisedRunner{HostExecutable: q2HostExecutable(t)}
	if runner != nil {
		r = *runner
		if r.HostExecutable == "" {
			r.HostExecutable = q2HostExecutable(t)
		}
	}
	return OpenCodeAdvisor{
		Config: OpenCodeAdvisorConfig{
			Enabled:   true,
			Tool:      tool,
			Model:     "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
			APIKeyEnv: "OPENROUTER_API_KEY",
		},
		Runner: r,
		Replay: NewOpenCodeReplayFence(t.TempDir()),
	}
}

func TestOpenCodeAdvisorQ2SupervisedProviderRoundTrip(t *testing.T) {
	a := q2Advisor(t, nil)
	packet := OpenCodeAdvisoryPacket{Schema: openCodeAdvisorPacketSchema, RequestID: "q2_supervised_roundtrip_001", Purpose: "Prove a synthetic advisory round trip through the plane-owned supervised process path.", DataClassification: "synthetic", Context: "Synthetic debugging exercise: a deterministic counter expected 8 but observed 7. State one plausible defect class and one verification step. Do not call tools."}
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()
	var stdout, stderr bytes.Buffer
	if err := a.Run(ctx, t.TempDir(), packet, &stdout, &stderr); err != nil { t.Fatalf("supervised provider round trip failed: %v; stderr=%s", err, stderr.String()) }
	key := os.Getenv("OPENROUTER_API_KEY")
	if strings.Contains(stdout.String(), key) || strings.Contains(stderr.String(), key) { t.Fatal("provider credential leaked into supervised output") }
	if strings.TrimSpace(stdout.String()) == "" { t.Fatal("supervised provider round trip returned empty stdout") }
	events := 0
	for _, line := range strings.Split(strings.ReplaceAll(stdout.String(), "\r\n", "\n"), "\n") {
		if strings.TrimSpace(line) == "" { continue }
		var v any
		if err := json.Unmarshal([]byte(line), &v); err != nil { t.Fatalf("non-JSON OpenCode event: %v", err) }
		events++
	}
	if events == 0 { t.Fatal("no OpenCode JSON events observed") }
}

func TestOpenCodeAdvisorQ2SupervisedCancellation(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	runner := &SupervisedRunner{OnStart: func(pid int) error {
		go func() { time.Sleep(750 * time.Millisecond); cancel() }()
		return nil
	}}
	a := q2Advisor(t, runner)
	packet := OpenCodeAdvisoryPacket{Schema: openCodeAdvisorPacketSchema, RequestID: "q2_supervised_cancel_001", Purpose: "Exercise cancellation of a real supervised OpenCode advisory request.", DataClassification: "synthetic", Context: "Synthetic stress response. Produce a detailed diagnostic taxonomy with many distinct categories and verification ideas. Do not call tools or mutate state."}
	var stdout, stderr bytes.Buffer
	err := a.Run(ctx, t.TempDir(), packet, &stdout, &stderr)
	if err == nil { t.Fatal("supervised OpenCode request completed before cancellation") }
	if !errors.Is(err, context.Canceled) { t.Fatalf("unexpected cancellation result: %v; stderr=%s", err, stderr.String()) }
	key := os.Getenv("OPENROUTER_API_KEY")
	if strings.Contains(stdout.String(), key) || strings.Contains(stderr.String(), key) { t.Fatal("provider credential leaked during cancellation") }
}

func TestOpenCodeAdvisorQ2OwnerDeathHarness(t *testing.T) {
	if os.Getenv("CKB_OPENCODE_Q2_OWNER_DEATH") != "1" { t.Skip("CKB_OPENCODE_Q2_OWNER_DEATH=1 required") }
	marker := os.Getenv("CKB_OPENCODE_Q2_HOST_MARKER")
	if marker == "" || !filepath.IsAbs(marker) { t.Fatal("CKB_OPENCODE_Q2_HOST_MARKER must be absolute") }
	runner := &SupervisedRunner{HostExecutable: q2HostExecutable(t), OnStart: func(pid int) error { return os.WriteFile(marker, []byte(fmt.Sprintf("%d", pid)), 0600) }}
	a := q2Advisor(t, runner)
	packet := OpenCodeAdvisoryPacket{Schema: openCodeAdvisorPacketSchema, RequestID: "q2_owner_death_001", Purpose: "Exercise owner-death lifecycle containment with a real OpenCode advisory process.", DataClassification: "synthetic", Context: "Synthetic stress response. Produce a detailed diagnostic taxonomy with many distinct categories and verification ideas. Do not call tools or mutate state."}
	var stdout, stderr bytes.Buffer
	if err := a.Run(context.Background(), t.TempDir(), packet, &stdout, &stderr); err != nil { t.Fatalf("owner-death harness returned before external termination: %v", err) }
	io.WriteString(io.Discard, stdout.String())
	t.Fatal("owner-death harness completed before external owner termination")
}
