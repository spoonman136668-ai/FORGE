package plane

import (
	"bytes"
	"context"
	"embed"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"golang.org/x/net/html"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

//go:embed harness/browser.cjs
var browserHarness embed.FS

func htmlContract(b []byte) (map[string]int, error) {
	out := map[string]int{}
	inScript := false
	z := html.NewTokenizer(bytes.NewReader(b))
	for {
		tt := z.Next()
		if tt == html.ErrorToken {
			if errors.Is(z.Err(), io.EOF) {
				return out, nil
			}
			return nil, z.Err()
		}
		if tt == html.TextToken && inScript {
			out["script-body:"+digest(z.Text())]++
			continue
		}
		if tt == html.EndTagToken {
			tag, _ := z.TagName()
			if string(tag) == "script" {
				inScript = false
			}
			continue
		}
		if tt != html.StartTagToken && tt != html.SelfClosingTagToken {
			continue
		}
		t := z.Token()
		if t.Data == "script" {
			inScript = true
			attrs := []string{}
			for _, a := range t.Attr {
				attrs = append(attrs, a.Key+"="+a.Val)
			}
			sort.Strings(attrs)
			out["script-tag:"+strings.Join(attrs, "|")]++
		}
		id := ""
		for _, a := range t.Attr {
			if a.Key == "id" {
				id = a.Val
				out["id:"+id]++
			}
		}
		for _, a := range t.Attr {
			if strings.HasPrefix(a.Key, "data-") {
				out["data:"+t.Data+":"+id+":"+a.Key+"="+a.Val]++
			}
		}
	}
}
func (p *Engine) uiChecks(j Job, base string) []Check {
	checks := []Check{}
	add := func(name string, ok bool, msg string) { checks = append(checks, Check{name, ok, msg}) }
	w := j.Order
	if len(w.Preserve) == 0 && !w.Acceptance.Browser {
		return checks
	}
	if w.UI.Root == "" || len(w.UI.Pages) == 0 {
		return []Check{{"UI_CONTRACT_MISSING", false, "Explicit UI root, pages, critical IDs and preservation markers are required"}}
	}
	before, e := treeInventory(base)
	if e != nil {
		return []Check{{"UI_BASELINE_UNAVAILABLE", false, e.Error()}}
	}
	after, e := treeInventory(j.Workspace)
	if e != nil {
		return []Check{{"UI_CANDIDATE_UNAVAILABLE", false, e.Error()}}
	}
	// JavaScript preservation is scope-aware. Earlier acceptance treated every UI
	// preservation contract as byte-for-byte JavaScript parity, which made any
	// explicitly authorized UI/source stage that touches app.js impossible to
	// accept. Preserve behavior by requiring existing JS files to remain present,
	// by rejecting unscoped JS additions/changes, and by letting the explicit
	// marker contract below carry behavior-preservation intent.
	for _, name := range sortedKeys(before) {
		if strings.HasSuffix(strings.ToLower(name), ".js") {
			afterHash, exists := after[name]
			allowed := w.Allows(filepath.ToSlash(name))
			add("UI_BEHAVIOR_PARITY", exists && (before[name] == afterHash || allowed), name+": JavaScript preserved or explicitly scoped by work order")
		}
	}
	for name := range after {
		if strings.HasSuffix(strings.ToLower(name), ".js") {
			_, existed := before[name]
			add("UI_BEHAVIOR_PARITY", existed || w.Allows(filepath.ToSlash(name)), name+": new JavaScript requires explicit work-order scope")
		}
	}
	for _, page := range w.UI.Pages {
		file := filepath.Join(w.UI.Root, page.Path)
		a, ae := os.ReadFile(filepath.Join(base, file))
		b, be := os.ReadFile(filepath.Join(j.Workspace, file))
		if ae != nil || be != nil {
			add("UI_PAGE_MISSING", false, file)
			continue
		}
		ac, ae := htmlContract(a)
		bc, be := htmlContract(b)
		good := ae == nil && be == nil
		for k, n := range ac {
			if bc[k] < n {
				good = false
			}
		}
		for k, n := range bc {
			if strings.HasPrefix(k, "script-") && ac[k] != n {
				good = false
			}
		}
		add("UI_ID_DATA_PARITY", good, file)
		for _, id := range page.CriticalIDs {
			add("UI_CRITICAL_ID", ac["id:"+id] == 1 && bc["id:"+id] == 1, file+": "+id)
		}
		if page.ChartID != "" {
			add("UI_CHART_ID", ac["id:"+page.ChartID] == 1 && bc["id:"+page.ChartID] == 1, file+": "+page.ChartID)
		}
	}
	// Preserve names are contracts, not inferred semantic promises. Each must be
	// covered by explicit source markers, except IDs/data handled by parsing.
	for _, name := range w.Preserve {
		if name == "element_ids" || name == "data_attributes" {
			continue
		}
		markers := w.UI.Markers[name]
		if len(markers) == 0 {
			add("UI_CONTRACT_MISSING", false, "Missing explicit markers for "+name)
			continue
		}
		for _, marker := range markers {
			foundBefore, foundAfter := false, false
			for _, file := range sortedKeys(before) {
				if strings.HasPrefix(file, w.UI.Root+"/") {
					a, _ := os.ReadFile(filepath.Join(base, filepath.FromSlash(file)))
					b, _ := os.ReadFile(filepath.Join(j.Workspace, filepath.FromSlash(file)))
					if bytes.Contains(a, []byte(marker)) {
						foundBefore = true
					}
					if bytes.Contains(b, []byte(marker)) {
						foundAfter = true
					}
				}
			}
			add("UI_REQUIRED_MARKER", marker != "" && foundBefore && foundAfter, name+": "+marker)
		}
	}
	return checks
}

type BrowserResult struct {
	Pass        bool              `json:"pass"`
	Checks      []Check           `json:"checks"`
	Screenshots map[string]string `json:"screenshots"`
}

func playwrightProcessEnv(root string) []string {
	root = filepath.Clean(root)
	nodePath := strings.Join([]string{
		filepath.Join(root, "playwright", "node_modules"),
		filepath.Join(root, "node_modules"),
		root,
	}, string(os.PathListSeparator))
	return []string{
		"NODE_PATH=" + nodePath,
		"PLAYWRIGHT_BROWSERS_PATH=" + filepath.Join(root, "playwright-browsers"),
	}
}

func browserAcceptanceProcessSpec(node, workspace, script, input string, env []string) ProcessSpec {
	return ProcessSpec{
		Program: filepath.Clean(node),
		Args:    []string{"-e", script},
		Dir:     workspace,
		Input:   input,
		Env:     append([]string(nil), env...),
	}
}
func (p *Engine) browserCheck(parent context.Context, j Job) ([]Check, error) {
	return p.browserCheckWithBaseline(parent, j, "")
}
func (p *Engine) browserCheckWithBaseline(parent context.Context, j Job, baseline string) ([]Check, error) {
	if p.Config.Tools.Node == "" || p.Config.Tools.PlaywrightRoot == "" {
		return nil, errors.New("PLAYWRIGHT_UNAVAILABLE")
	}
	if !filepath.IsAbs(p.Config.Tools.Node) {
		return nil, errors.New("PLAYWRIGHT_UNAVAILABLE: absolute Node executable required")
	}
	// Harness code is embedded in the controller, never loaded from candidate source.
	script, e := browserHarness.ReadFile("harness/browser.cjs")
	if e != nil {
		return nil, e
	}
	ctx, cancel := context.WithTimeout(parent, 2*time.Minute)
	defer cancel()
	browserInput := map[string]any{"root": filepath.Join(j.Workspace, j.Order.UI.Root), "pages": j.Order.UI.Pages, "moduleRoot": p.Config.Tools.PlaywrightRoot}
	if baseline != "" {
		browserInput["baselineRoot"] = filepath.Join(baseline, j.Order.UI.Root)
	}
	input := jsonText(browserInput)
	// Browser acceptance executes trusted embedded harness code, never candidate-provided
	// process metadata. Native-Windows Codex sandbox builds can deny Node child-process
	// creation with spawn EPERM, so run this harness directly under the plane's existing
	// supervised kill-on-close Job Object. The embedded harness retains static-only
	// request routing, closes WebSockets, blocks service workers and enables Chromium's
	// own sandbox.
	var out, stderr bytes.Buffer
	browserEnv := append(minimalEnv(), playwrightProcessEnv(p.Config.Tools.PlaywrightRoot)...)
	spec := browserAcceptanceProcessSpec(p.Config.Tools.Node, j.Workspace, string(script), input, browserEnv)
	e = p.supervisedRunnerFor(j).Run(ctx, spec, &out, &stderr)
	if er := os.WriteFile(filepath.Join(j.Evidence, "browser_stderr.log"), stderr.Bytes(), 0600); er != nil {
		return nil, er
	}
	if e != nil {
		return nil, errors.New("PLAYWRIGHT_FAILED: supervised browser harness exited nonzero")
	}
	var result BrowserResult
	if e = json.Unmarshal(out.Bytes(), &result); e != nil {
		return nil, errors.New("PLAYWRIGHT_FAILED: invalid harness result")
	}
	if len(result.Checks) == 0 {
		return nil, errors.New("PLAYWRIGHT_FAILED: no checks")
	}
	for name, data := range result.Screenshots {
		if !safeID.MatchString(strings.TrimSuffix(name, ".png")) || !strings.HasSuffix(name, ".png") {
			return nil, errors.New("invalid screenshot name")
		}
		b, e := base64.StdEncoding.DecodeString(data)
		if e != nil || len(b) > 8<<20 {
			return nil, errors.New("invalid screenshot bytes")
		}
		dir := filepath.Join(j.Evidence, "screenshots")
		if e = os.MkdirAll(dir, 0700); e != nil {
			return nil, e
		}
		if e = os.WriteFile(filepath.Join(dir, name), b, 0600); e != nil {
			return nil, e
		}
	}
	if e = writeJSON(filepath.Join(j.Evidence, "browser_result.json"), map[string]any{"pass": result.Pass, "checks": result.Checks}); e != nil {
		return nil, e
	}
	if !result.Pass {
		return result.Checks, fmt.Errorf("PLAYWRIGHT_FAILED")
	}
	return result.Checks, nil
}
