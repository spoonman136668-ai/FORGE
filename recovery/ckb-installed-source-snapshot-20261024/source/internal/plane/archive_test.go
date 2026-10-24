package plane

import (
	"archive/tar"
	"bytes"
	"context"
	"errors"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
	"time"
)

// A real producer writes padding substantially larger than Windows and Linux
// anonymous pipe buffers. tar.Reader reaches its end marker before this padding.
func runArchiveFixture() bool {
	archive := false
	mode := ""
	for _, arg := range os.Args[1:] {
		if arg == "archive" {
			archive = true
		}
		if arg == "plane-test-padding" || arg == "plane-test-hang" {
			mode = arg
		}
	}
	if !archive || mode == "" {
		return false
	}
	if mode == "plane-test-hang" {
		time.Sleep(30 * time.Second)
		return true
	}
	tw := tar.NewWriter(os.Stdout)
	data := []byte("baseline\n")
	if tw.WriteHeader(&tar.Header{Name: "demo.txt", Mode: 0600, Size: int64(len(data))}) != nil {
		return true
	}
	_, _ = tw.Write(data)
	_ = tw.Close()
	_, _ = os.Stdout.Write(make([]byte, 2<<20))
	return true
}
func TestArchivePaddingRequiresPipeDrain(t *testing.T) {
	exe, _ := os.Executable()
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, exe, "-c", "core.hooksPath=", "archive", "--format=tar", "plane-test-padding")
	pipe, e := cmd.StdoutPipe()
	if e != nil {
		t.Fatal(e)
	}
	if e = cmd.Start(); e != nil {
		t.Fatal(e)
	}
	defer pipe.Close()
	tr := tar.NewReader(pipe)
	if _, e = tr.Next(); e != nil {
		t.Fatal(e)
	}
	_, _ = io.Copy(io.Discard, tr)
	if _, e = tr.Next(); e != io.EOF {
		t.Fatal(e)
	}
	// This is the previous consumer sequence: Wait while padding remains unread.
	// The deadline must terminate the blocked producer, demonstrating the defect.
	e = cmd.Wait()
	if e == nil || ctx.Err() != context.DeadlineExceeded {
		t.Fatalf("expected unread-padding deadlock, got %v (%v)", e, ctx.Err())
	}
}
func TestExportBaselineDrainsArchivePadding(t *testing.T) {
	exe, _ := os.Executable()
	p := &Engine{}
	p.Config.Tools.Git = exe
	dir := t.TempDir()
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if e := p.exportBaseline(ctx, dir, "plane-test-padding", dir); e != nil {
		t.Fatal(e)
	}
	b, e := os.ReadFile(filepath.Join(dir, "demo.txt"))
	if e != nil || !bytes.Equal(b, []byte("baseline\n")) {
		t.Fatal("exported content mismatch", e)
	}
}
func TestExportBaselineHonorsAttemptCancellation(t *testing.T) {
	exe, _ := os.Executable()
	p := &Engine{}
	p.Config.Tools.Git = exe
	dir := t.TempDir()
	ctx, cancel := context.WithTimeout(context.Background(), 200*time.Millisecond)
	defer cancel()
	start := time.Now()
	e := p.exportBaseline(ctx, dir, "plane-test-hang", dir)
	if e == nil || time.Since(start) > 5*time.Second {
		t.Fatalf("cancel did not reap exporter: %v", e)
	}
	if !errors.Is(ctx.Err(), context.DeadlineExceeded) {
		t.Fatal(ctx.Err())
	}
	// On Windows this also catches the lingering cwd handle seen in the report.
	if e = os.RemoveAll(dir); e != nil {
		t.Fatalf("exporter retained directory: %v", e)
	}
}
