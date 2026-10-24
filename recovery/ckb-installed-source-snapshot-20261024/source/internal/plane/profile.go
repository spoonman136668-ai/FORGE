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
	"regexp"
	"sort"
	"strings"
	"time"

	"github.com/bmatcuk/doublestar/v4"
)

type DispatchProfile struct {
	ProfileName                string                     `json:"profile_name"`
	Mode                       string                     `json:"mode"`
	RepoPath                   string                     `json:"repo_path"`
	WorkOrderID                string                     `json:"work_order_id"`
	WorkOrderTitle             string                     `json:"work_order_title,omitempty"`
	Instructions               []string                   `json:"instructions,omitempty"`
	WorkerBranch               string                     `json:"worker_branch"`
	RequiredBaselineRef        string                     `json:"required_baseline_ref"`
	RequiredBaselineSHA        string                     `json:"required_baseline_sha"`
	BaselineResolutionObserved *ProfileBaselineResolution `json:"baseline_resolution_observed,omitempty"`
	AcceptanceAuthority        string                     `json:"acceptance_authority"`
	FocusedTests               []string                   `json:"focused_tests"`
	RunGoTestAll               *bool                      `json:"run_go_test_all,omitempty"`
	GoPackages                 []string                   `json:"go_packages,omitempty"`
	AllowedPaths               []string                   `json:"allowed_paths"`
	ForbiddenPaths             []string                   `json:"forbidden_paths"`
	AcceptedRefsPolicy         string                     `json:"accepted_refs_policy"`
	RuntimeForbidden           bool                       `json:"runtime_forbidden"`
	WorkerLaunchAllowed        bool                       `json:"worker_launch_allowed"`
	CandidateAcceptanceAllowed bool                       `json:"candidate_acceptance_allowed"`
	CodexProfilePath           string                     `json:"codex_profile_path"`
	ScrubDenylist              []string                   `json:"scrub_denylist"`
	AllowSHAFallback           bool                       `json:"allow_sha_fallback"`
	FetchMissingRefAllowed     bool                       `json:"fetch_missing_ref_allowed"`
}

type ProfileBaselineResolution struct {
	ResolvedRef string `json:"resolved_ref"`
	ResolvedSHA string `json:"resolved_sha"`
	Mode        string `json:"mode"`
	RefPresent  bool   `json:"ref_present"`
}

func (r *ProfileBaselineResolution) UnmarshalJSON(b []byte) error {
	type baselineResolutionJSON struct {
		ResolvedRef       string `json:"resolved_ref"`
		ResolvedSHA       string `json:"resolved_sha"`
		Mode              string `json:"mode"`
		RefPresent        bool   `json:"ref_present"`
		LegacyResolvedRef string `json:"ResolvedRef"`
		LegacyResolvedSha string `json:"ResolvedSha"`
		LegacyResolvedSHA string `json:"ResolvedSHA"`
		LegacyMode        string `json:"Mode"`
		LegacyRefPresent  *bool  `json:"RefPresent"`
	}
	var v baselineResolutionJSON
	if err := json.Unmarshal(b, &v); err != nil {
		return err
	}
	if v.ResolvedRef == "" {
		v.ResolvedRef = v.LegacyResolvedRef
	}
	if v.ResolvedSHA == "" {
		v.ResolvedSHA = v.LegacyResolvedSHA
	}
	if v.ResolvedSHA == "" {
		v.ResolvedSHA = v.LegacyResolvedSha
	}
	if v.Mode == "" {
		v.Mode = v.LegacyMode
	}
	if v.LegacyRefPresent != nil {
		v.RefPresent = *v.LegacyRefPresent
	}
	*r = ProfileBaselineResolution{
		ResolvedRef: v.ResolvedRef,
		ResolvedSHA: v.ResolvedSHA,
		Mode:        v.Mode,
		RefPresent:  v.RefPresent,
	}
	return nil
}

type ProfileScrubEvidence struct {
	CodexProfilePath string   `json:"codex_profile_path"`
	Denylist         []string `json:"denylist"`
	Removed          []string `json:"removed"`
	PresentAfter     []string `json:"present_after"`
	Status           string   `json:"status"`
}

type ProfilePreflightEvidence struct {
	ProfileName                string                    `json:"profile_name"`
	Mode                       string                    `json:"mode"`
	RepoPath                   string                    `json:"repo_path"`
	WorkOrderID                string                    `json:"work_order_id"`
	RequestedBaselineRef       string                    `json:"requested_baseline_ref"`
	RequiredBaselineSHA        string                    `json:"required_baseline_sha"`
	Baseline                   ProfileBaselineResolution `json:"baseline"`
	AcceptanceAuthority        string                    `json:"acceptance_authority"`
	FocusedTests               []string                  `json:"focused_tests"`
	AllowedPaths               []string                  `json:"allowed_paths"`
	ForbiddenPaths             []string                  `json:"forbidden_paths"`
	AcceptedRefsPolicy         string                    `json:"accepted_refs_policy"`
	WorkerLaunchAllowed        bool                      `json:"worker_launch_allowed"`
	CandidateAcceptanceAllowed bool                      `json:"candidate_acceptance_allowed"`
	RuntimeForbidden           bool                      `json:"runtime_forbidden"`
	Scrub                      ProfileScrubEvidence      `json:"scrub"`
	EvidencePath               string                    `json:"evidence_path,omitempty"`
	Status                     string                    `json:"status"`
	Created                    string                    `json:"created"`
}

var profileTestName = regexp.MustCompile(`^\^?Test[A-Za-z0-9_]*\$?$`)

func LoadDispatchProfile(root, name string) (DispatchProfile, error) {
	var p DispatchProfile
	if !safeID.MatchString(name) {
		return p, errors.New("CONFIG_INVALID: safe profile name required")
	}
	file := filepath.Join(root, "profiles", name+".json")
	b, err := os.ReadFile(file)
	if err != nil {
		return p, err
	}
	b = bytes.TrimPrefix(b, []byte{0xef, 0xbb, 0xbf})
	if err = jsonUnmarshalStrict(b, &p); err != nil {
		return p, err
	}
	if p.ProfileName == "" {
		p.ProfileName = name
	}
	if p.ProfileName != name {
		return p, errors.New("CONFIG_INVALID: profile name/file name mismatch")
	}
	return p, p.Validate()
}

func jsonUnmarshalStrict(b []byte, v any) error {
	d := json.NewDecoder(bytes.NewReader(b))
	d.DisallowUnknownFields()
	if err := d.Decode(v); err != nil {
		return err
	}
	var extra any
	if err := d.Decode(&extra); err != io.EOF {
		return errors.New("exactly one JSON document required")
	}
	return nil
}

func (p DispatchProfile) Validate() error {
	if !safeID.MatchString(p.ProfileName) || !safeID.MatchString(p.WorkOrderID) || p.Mode == "" {
		return errors.New("CONFIG_INVALID: profile_name, mode and work_order_id required")
	}
	if p.RepoPath == "" || !filepath.IsAbs(p.RepoPath) {
		return errors.New("CONFIG_INVALID: absolute repo_path required")
	}
	if !strings.HasPrefix(p.RequiredBaselineRef, "accepted/") || !safePath(p.RequiredBaselineRef) || !shaRE.MatchString(p.RequiredBaselineSHA) {
		return errors.New("CONFIG_INVALID: exact accepted baseline ref and SHA required")
	}
	if p.AcceptanceAuthority != "windows-source" && p.AcceptanceAuthority != "demo" {
		return errors.New("CONFIG_INVALID: known acceptance authority required")
	}
	if !p.RuntimeForbidden {
		return errors.New("CONFIG_INVALID: runtime_forbidden must be true")
	}
	if p.WorkerLaunchAllowed {
		if !p.CandidateAcceptanceAllowed {
			return errors.New("CONFIG_INVALID: launch profile must allow candidate acceptance")
		}
		if !strings.HasPrefix(p.WorkerBranch, "codex/") || !safePath(p.WorkerBranch) || strings.ContainsAny(p.WorkerBranch, " ~^?*[@{") {
			return errors.New("CONFIG_INVALID: launch profile requires valid codex worker_branch")
		}
		if len(p.AllowedPaths) == 0 {
			return errors.New("CONFIG_INVALID: launch profile requires allowed paths")
		}
	} else {
		if p.CandidateAcceptanceAllowed {
			return errors.New("CONFIG_INVALID: readonly profile cannot allow candidate acceptance")
		}
		if !strings.Contains(strings.ToLower(p.AcceptedRefsPolicy), "never") {
			return errors.New("CONFIG_INVALID: readonly profile must forbid accepted ref mutation")
		}
	}
	for _, pattern := range append(append([]string{}, p.AllowedPaths...), p.ForbiddenPaths...) {
		if !safePath(pattern) || !doublestar.ValidatePattern(pattern) {
			return fmt.Errorf("CONFIG_INVALID: invalid profile path pattern %q", pattern)
		}
	}
	for _, pattern := range p.FocusedTests {
		if !profileTestName.MatchString(pattern) {
			return errors.New("CONFIG_INVALID: focused_tests must name anchored Go tests")
		}
	}
	for _, name := range p.ScrubDenylist {
		if !safeProfileArtifactName(name) {
			return fmt.Errorf("CONFIG_INVALID: invalid codex profile denylist entry %q", name)
		}
	}
	if p.CodexProfilePath != "" && !filepath.IsAbs(p.CodexProfilePath) {
		return errors.New("CONFIG_INVALID: absolute codex_profile_path required")
	}
	return nil
}

func (p DispatchProfile) WorkOrder() (WorkOrder, error) {
	var w WorkOrder
	if err := p.Validate(); err != nil {
		return w, err
	}
	if !p.WorkerLaunchAllowed || !p.CandidateAcceptanceAllowed {
		return w, errors.New("PROFILE_READONLY: profile cannot be converted to an executable work order")
	}
	w.ID = p.WorkOrderID
	title := strings.TrimSpace(p.WorkOrderTitle)
	if title == "" {
		title = "Profile-driven work order: " + p.ProfileName
	}
	w.Title = title
	w.Repo = p.ProfileName
	w.Instructions = append([]string{}, p.Instructions...)
	w.Baseline.Ref = p.RequiredBaselineRef
	w.Baseline.SHA = p.RequiredBaselineSHA
	w.Worker.Branch = p.WorkerBranch
	w.Worker.Preferred = "codex"
	w.Scope.Allowed = append([]string{}, p.AllowedPaths...)
	w.Scope.Forbidden = append([]string{}, p.ForbiddenPaths...)
	for _, test := range p.FocusedTests {
		w.RequiredTests.FocusedGo = append(w.RequiredTests.FocusedGo, normalizeFocusedTest(test))
	}
	if len(p.GoPackages) > 0 {
		w.RequiredTests.Packages = append([]string{}, p.GoPackages...)
	} else {
		w.RequiredTests.Packages = []string{"./..."}
	}
	w.Acceptance.All = true
	if p.RunGoTestAll != nil {
		w.Acceptance.All = *p.RunGoTestAll
	}
	w.Acceptance.Browser = false
	w.Acceptance.ProtectRefs = true
	w.Acceptance.Clean = true
	w.Forbidden = []string{"runtime_launch", "credentials", "deployment", "accepted_ref_mutation"}
	return w, w.Validate()
}

func normalizeFocusedTest(s string) string {
	s = strings.TrimSpace(s)
	s = strings.TrimPrefix(s, "^")
	s = strings.TrimSuffix(s, "$")
	return "^" + s + "$"
}

func ApplyDispatchProfile(c Config, p DispatchProfile) (Config, error) {
	if err := p.Validate(); err != nil {
		return c, err
	}
	if c.Repos == nil {
		c.Repos = map[string]Repo{}
	}
	c.Repos[p.ProfileName] = Repo{LocalPath: p.RepoPath, Mode: "engineering"}
	c.Execution.Enabled = p.WorkerLaunchAllowed
	if p.CodexProfilePath != "" {
		c.Execution.CodexHome = p.CodexProfilePath
	}
	c.Profile.Name = p.ProfileName
	return c, nil
}

func (p *Engine) PreflightSelectedProfile(ctx context.Context) (ProfilePreflightEvidence, error) {
	if p.Profile == nil {
		return ProfilePreflightEvidence{}, errors.New("PROFILE_REQUIRED: no dispatch profile selected")
	}
	return p.PreflightDispatchProfile(ctx, *p.Profile, filepath.Join(p.Root, "artifacts", "r2e"))
}

func (p *Engine) PreflightDispatchProfile(ctx context.Context, profile DispatchProfile, evidenceRoot string) (ProfilePreflightEvidence, error) {
	if err := profile.Validate(); err != nil {
		return ProfilePreflightEvidence{}, err
	}
	scrub, err := scrubCodexProfile(profile.CodexProfilePath, profileScrubDenylist(profile.ScrubDenylist))
	if err != nil {
		return ProfilePreflightEvidence{}, err
	}
	baseline, err := resolveAcceptedBaseline(ctx, p.Config.Tools.Git, profile.RepoPath, profile.RequiredBaselineRef, profile.RequiredBaselineSHA, profile.AllowSHAFallback, profile.FetchMissingRefAllowed)
	if err != nil {
		return ProfilePreflightEvidence{}, err
	}
	if profile.Mode == "readonly-baseline-verification" {
		if profile.WorkerLaunchAllowed || profile.CandidateAcceptanceAllowed {
			return ProfilePreflightEvidence{}, errors.New("PROFILE_POLICY_INVALID: readonly profile cannot launch or accept candidates")
		}
		if !strings.Contains(strings.ToLower(profile.AcceptedRefsPolicy), "never") {
			return ProfilePreflightEvidence{}, errors.New("PROFILE_POLICY_INVALID: readonly profile must forbid accepted refs")
		}
	}
	ev := ProfilePreflightEvidence{
		ProfileName:                profile.ProfileName,
		Mode:                       profile.Mode,
		RepoPath:                   profile.RepoPath,
		WorkOrderID:                profile.WorkOrderID,
		RequestedBaselineRef:       profile.RequiredBaselineRef,
		RequiredBaselineSHA:        profile.RequiredBaselineSHA,
		Baseline:                   baseline,
		AcceptanceAuthority:        profile.AcceptanceAuthority,
		FocusedTests:               append([]string{}, profile.FocusedTests...),
		AllowedPaths:               append([]string{}, profile.AllowedPaths...),
		ForbiddenPaths:             append([]string{}, profile.ForbiddenPaths...),
		AcceptedRefsPolicy:         profile.AcceptedRefsPolicy,
		WorkerLaunchAllowed:        profile.WorkerLaunchAllowed,
		CandidateAcceptanceAllowed: profile.CandidateAcceptanceAllowed,
		RuntimeForbidden:           profile.RuntimeForbidden,
		Scrub:                      scrub,
		Status:                     "DRY_DISPATCH_READY",
		Created:                    time.Now().UTC().Format(time.RFC3339Nano),
	}
	if evidenceRoot != "" {
		if err = os.MkdirAll(evidenceRoot, 0700); err != nil {
			return ev, err
		}
		ev.EvidencePath = filepath.Join(evidenceRoot, profile.ProfileName+"-engine-preflight.json")
		if err = writeJSON(ev.EvidencePath, ev); err != nil {
			return ev, err
		}
	}
	return ev, nil
}

func resolveAcceptedBaseline(ctx context.Context, tool, dir, ref, requiredSHA string, allowSHAFallback, allowFetch bool) (ProfileBaselineResolution, error) {
	var zero ProfileBaselineResolution
	if !strings.HasPrefix(ref, "accepted/") || !safePath(ref) || !shaRE.MatchString(requiredSHA) {
		return zero, errors.New("BASELINE_MISMATCH")
	}
	candidates := []struct {
		label string
		spec  string
	}{
		{"refs/heads/" + ref, "refs/heads/" + ref},
		{"refs/tags/" + ref, "refs/tags/" + ref},
		{"origin/" + ref, "refs/remotes/origin/" + ref},
		{"refs/remotes/origin/" + ref, "refs/remotes/origin/" + ref},
	}
	matches := []ProfileBaselineResolution{}
	bad := []string{}
	seen := map[string]bool{}
	for _, c := range candidates {
		if seen[c.spec] {
			continue
		}
		seen[c.spec] = true
		sha, err := gitContext(ctx, tool, dir, "rev-parse", "--verify", c.spec+"^{commit}")
		if err != nil {
			continue
		}
		if sha != requiredSHA {
			bad = append(bad, c.label+"="+sha)
			continue
		}
		matches = append(matches, ProfileBaselineResolution{ResolvedRef: c.label, ResolvedSHA: sha, Mode: "ref", RefPresent: true})
	}
	if len(bad) > 0 {
		return zero, fmt.Errorf("BASELINE_MISMATCH: %s", strings.Join(bad, ", "))
	}
	if len(matches) > 0 {
		return matches[0], nil
	}
	if allowFetch {
		if _, err := gitContext(ctx, tool, dir, "remote", "get-url", "origin"); err == nil {
			_, _ = gitContext(ctx, tool, dir, "fetch", "--no-tags", "origin", "refs/heads/"+ref+":refs/remotes/origin/"+ref)
			return resolveAcceptedBaseline(ctx, tool, dir, ref, requiredSHA, allowSHAFallback, false)
		}
	}
	if allowSHAFallback {
		sha, err := gitContext(ctx, tool, dir, "rev-parse", "--verify", requiredSHA+"^{commit}")
		if err == nil && sha == requiredSHA {
			return ProfileBaselineResolution{ResolvedRef: requiredSHA, ResolvedSHA: sha, Mode: "sha-fallback", RefPresent: false}, nil
		}
	}
	return zero, errors.New("BASELINE_MISMATCH")
}

func defaultCodexProfileDenylist() []string {
	return []string{"config.toml", "config.json", "skills", "plugins", "rules", "AGENTS.md"}
}

func profileScrubDenylist(configured []string) []string {
	seen := map[string]bool{}
	out := []string{}
	for _, name := range append(defaultCodexProfileDenylist(), configured...) {
		if safeProfileArtifactName(name) && !seen[strings.ToLower(name)] {
			seen[strings.ToLower(name)] = true
			out = append(out, name)
		}
	}
	sort.Strings(out)
	return out
}

func safeProfileArtifactName(name string) bool {
	return name != "" && !strings.ContainsAny(name, "/\\:\x00\r\n") && filepath.Base(name) == name && name != "." && name != ".."
}

func scrubCodexProfile(home string, denylist []string) (ProfileScrubEvidence, error) {
	ev := ProfileScrubEvidence{CodexProfilePath: home, Denylist: append([]string{}, denylist...), Status: "SCRUBBED"}
	if home == "" {
		ev.Status = "NO_PROFILE_PATH"
		return ev, nil
	}
	if !filepath.IsAbs(home) {
		return ev, errors.New("CODEX_PROFILE_NOT_ISOLATED: absolute profile path required")
	}
	if err := os.MkdirAll(home, 0700); err != nil {
		return ev, err
	}
	for _, name := range denylist {
		if !safeProfileArtifactName(name) {
			return ev, fmt.Errorf("CODEX_PROFILE_NOT_ISOLATED: unsafe denylist entry %q", name)
		}
		full := filepath.Join(home, name)
		if _, err := os.Lstat(full); err == nil {
			if err = os.RemoveAll(full); err != nil {
				return ev, err
			}
			ev.Removed = append(ev.Removed, name)
		} else if !os.IsNotExist(err) {
			return ev, err
		}
	}
	for _, name := range denylist {
		if _, err := os.Lstat(filepath.Join(home, name)); err == nil {
			ev.PresentAfter = append(ev.PresentAfter, name)
		} else if !os.IsNotExist(err) {
			return ev, err
		}
	}
	if len(ev.PresentAfter) > 0 {
		ev.Status = "DENYLIST_PRESENT"
		return ev, errors.New("CODEX_PROFILE_NOT_ISOLATED: denylisted artifacts remain")
	}
	return ev, nil
}
