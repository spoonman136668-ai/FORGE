package plane

import (
	"fmt"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
)

type Health struct {
	Name   string `json:"name"`
	Status string `json:"status"`
	Detail string `json:"detail"`
}

func (p *Engine) Doctor() []Health {
	out := []Health{{"Execution configuration", "INFO", fmt.Sprintf("enabled=%v; real dispatch requires Windows, native tools, dedicated profile and a matching authorization contract", p.Config.Execution.Enabled)}}
	add := func(name string, ok bool, detail string) {
		s := "PASS"
		if !ok {
			s = "MISSING"
		}
		out = append(out, Health{name, s, detail})
	}
	for _, t := range []struct{ name, path string }{{"Go", p.Config.Tools.Go}, {"Git", p.Config.Tools.Git}, {"PowerShell", p.Config.Tools.Powershell}, {"Codex", p.Config.Tools.Codex}, {"Node", p.Config.Tools.Node}} {
		_, e := exec.LookPath(t.path)
		add(t.name, e == nil, t.path)
	}
	add("Windows authority", runtime.GOOS == "windows" && runtime.GOARCH == "amd64" && runtime.Version() == "go1.25.5", runtime.Version()+" "+runtime.GOOS+"/"+runtime.GOARCH)
	for name, r := range p.Config.Repos {
		status := "UNVERIFIED"
		detail := r.LocalPath
		if r.LocalPath == "" {
			status = "REMOTE_ONLY"
		} else if _, e := os.Stat(r.LocalPath); e != nil {
			status = "MISSING"
		} else if _, e := git(p.Config.Tools.Git, r.LocalPath, "rev-parse", "--git-dir"); e != nil {
			status = "UNVERIFIED"
		} else {
			status = "LOCAL"
			s, e := git(p.Config.Tools.Git, r.LocalPath, "status", "--porcelain")
			if e != nil {
				status = "UNVERIFIED"
			} else if s != "" {
				status = "DIRTY"
			}
			if r.Remote != "" {
				s, e = git(p.Config.Tools.Git, r.LocalPath, "remote", "get-url", "origin")
				if e != nil || s != r.Remote {
					status = "UNVERIFIED"
					detail += " (origin mismatch)"
				}
			}
		}
		out = append(out, Health{"repo: " + name, status, detail})
	}
	for _, dir := range []string{filepath.Dir(p.Config.State.SQLitePath), "workspaces", "evidence"} {
		d := dir
		if !filepath.IsAbs(d) {
			d = filepath.Join(p.Root, d)
		}
		e := os.MkdirAll(d, 0700)
		if e == nil {
			var f *os.File
			f, e = os.CreateTemp(d, "doctor-")
			if e == nil {
				f.Close()
				os.Remove(f.Name())
			}
		}
		add("writable: "+dir, e == nil, d)
	}
	info, e := os.Stat(p.Config.Tools.PlaywrightRoot)
	add("Playwright root", e == nil && info.IsDir(), p.Config.Tools.PlaywrightRoot+" (presence only, static harness requires Node + Playwright + qualified sandbox)")
	ln, e := net.Listen("tcp", net.JoinHostPort(p.Config.Server.Bind, strconv.Itoa(p.Config.Server.Port)))
	if e == nil {
		ln.Close()
	}
	add("server port available", e == nil, fmt.Sprint(p.Config.Server.Port)+" (in use is expected while serving)")
	add("SQLite", p.Store.DB.Ping() == nil, p.Config.State.SQLitePath)
	return out
}
