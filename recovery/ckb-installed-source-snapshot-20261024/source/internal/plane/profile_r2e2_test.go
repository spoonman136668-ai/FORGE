package plane

import (
	"os"
	"path/filepath"
	"strconv"
	"testing"
)

func TestR2e2DispatchProfileAcceptsLegacyPowerShellObservedBaseline(t *testing.T) {
	root := t.TempDir()
	profileDir := filepath.Join(root, "profiles")
	if err := os.MkdirAll(profileDir, 0o755); err != nil {
		t.Fatal(err)
	}
	repoPath := filepath.Join(root, "repo")
	sha := "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	body := `{
  "profile_name": "toy",
  "mode": "toy-proof-profile",
  "repo_path": ` + strconv.Quote(repoPath) + `,
  "work_order_id": "TOY_CODEX_FIXTURE_R1",
  "worker_branch": "codex/toy-fixture-r1",
  "required_baseline_ref": "accepted/toy",
  "required_baseline_sha": "` + sha + `",
  "baseline_resolution_observed": {
    "ResolvedRef": "accepted/toy",
    "ResolvedSha": "` + sha + `",
    "Mode": "ref",
    "RefPresent": true
  },
  "acceptance_authority": "windows-source",
  "focused_tests": ["TestMessage"],
  "allowed_paths": ["toy.go"],
  "forbidden_paths": ["go.mod", "toy_test.go"],
  "accepted_refs_policy": "toy proof only; never create or move accepted CKB refs",
  "runtime_forbidden": true,
  "worker_launch_allowed": true,
  "candidate_acceptance_allowed": true,
  "scrub_denylist": ["config.toml", "skills", "plugins"],
  "allow_sha_fallback": true,
  "fetch_missing_ref_allowed": false
}`
	if err := os.WriteFile(filepath.Join(profileDir, "toy.json"), []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
	p, err := LoadDispatchProfile(root, "toy")
	if err != nil {
		t.Fatalf("LoadDispatchProfile failed on legacy observed baseline: %v", err)
	}
	if p.BaselineResolutionObserved == nil {
		t.Fatalf("expected observed baseline to decode")
	}
	if p.BaselineResolutionObserved.ResolvedRef != "accepted/toy" || p.BaselineResolutionObserved.ResolvedSHA != sha || !p.BaselineResolutionObserved.RefPresent {
		t.Fatalf("unexpected observed baseline: %+v", *p.BaselineResolutionObserved)
	}
}

func TestR2e2DispatchProfileDoesNotRequireObservedBaseline(t *testing.T) {
	root := t.TempDir()
	profileDir := filepath.Join(root, "profiles")
	if err := os.MkdirAll(profileDir, 0o755); err != nil {
		t.Fatal(err)
	}
	repoPath := filepath.Join(root, "repo")
	body := `{
  "profile_name": "ckb-readonly",
  "mode": "readonly-baseline-verification",
  "repo_path": ` + strconv.Quote(repoPath) + `,
  "work_order_id": "CKB_READONLY_BASELINE_VERIFY_R1",
  "worker_branch": "none-readonly",
  "required_baseline_ref": "accepted/v1.11.10-stage-bq-ktrade-execution-visibility-r1",
  "required_baseline_sha": "01260dda4bdebc454921cdf0c5d3d0eeafef7629",
  "acceptance_authority": "windows-source",
  "focused_tests": [],
  "allowed_paths": [],
  "forbidden_paths": ["**"],
  "accepted_refs_policy": "never create, move, update, checkout, reset, or push accepted CKB refs",
  "runtime_forbidden": true,
  "worker_launch_allowed": false,
  "candidate_acceptance_allowed": false,
  "scrub_denylist": ["config.toml", "skills", "plugins"],
  "allow_sha_fallback": false,
  "fetch_missing_ref_allowed": true
}`
	if err := os.WriteFile(filepath.Join(profileDir, "ckb-readonly.json"), []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
	p, err := LoadDispatchProfile(root, "ckb-readonly")
	if err != nil {
		t.Fatalf("LoadDispatchProfile without observed baseline failed: %v", err)
	}
	if p.BaselineResolutionObserved != nil {
		t.Fatalf("did not expect observed baseline in config-only profile")
	}
}
