package branchpolicy

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

type f139RefPattern struct {
	Include []string `json:"include"`
	Exclude []string `json:"exclude"`
}

type f139ReleaseRuleset struct {
	Name string `json:"name"`
	Target string `json:"target"`
	Enforcement string `json:"enforcement"`
	BypassActors []json.RawMessage `json:"bypass_actors"`
	Conditions struct {
		RefName f139RefPattern `json:"ref_name"`
	} `json:"conditions"`
	Rules []struct {
		Type string `json:"type"`
	} `json:"rules"`
}

func checkF139ReleaseRuleset(src []byte) error {
	dec := json.NewDecoder(bytes.NewReader(src))
	dec.DisallowUnknownFields()
	var p f139ReleaseRuleset
	if err := dec.Decode(&p); err != nil {
		return fmt.Errorf("decode ruleset: %w", err)
	}
	var tail any
	if err := dec.Decode(&tail); err != io.EOF {
		return fmt.Errorf("trailing or duplicate document: %v", err)
	}
	// Require exactly the documented GitHub API payload: no duplicate
	// fields, ambiguous overwrites, unknown permissions, or silent additions.
	canonical, err := json.MarshalIndent(p, "", "  ")
	if err != nil {
		return err
	}
	if !bytes.Equal(src, append(canonical, '\n')) {
		return fmt.Errorf("noncanonical JSON or duplicate key")
	}
	if p.Name != "FORGE F139 immutable owner release refs" ||
		p.Target != "branch" || p.Enforcement != "active" ||
		len(p.BypassActors) != 0 ||
		!reflect.DeepEqual(p.Conditions.RefName.Include,
			[]string{"refs/heads/f139-owner-release-*"}) ||
		!reflect.DeepEqual(p.Conditions.RefName.Exclude, []string{}) {
		return fmt.Errorf("release ruleset scope or enforcement drift")
	}
	if len(p.Rules) != 2 ||
		p.Rules[0].Type != "update" ||
		p.Rules[1].Type != "deletion" {
		return fmt.Errorf("unlocked or additional release rules")
	}
	return nil
}

func TestF139OwnerReleaseRulesetExactNoBypassLock(t *testing.T) {
	path := filepath.Join("..", "reference", "governance",
		"f139-owner-release-ref-ruleset-proposal.json")
	b, err := os.ReadFile(path)
	if err != nil { t.Fatal(err) }
	if err := checkF139ReleaseRuleset(b); err != nil { t.Fatal(err) }
}

func TestF139OwnerReleaseRulesetRejectsWeakenings(t *testing.T) {
	path := filepath.Join("..", "reference", "governance",
		"f139-owner-release-ref-ruleset-proposal.json")
	b, err := os.ReadFile(path)
	if err != nil { t.Fatal(err) }
	tests := map[string]func([]byte) []byte{
		"disabled": func(p []byte) []byte {
			return bytes.Replace(p, []byte(`"active"`), []byte(`"disabled"`), 1)
		},
		"main_target": func(p []byte) []byte {
			return bytes.Replace(p, []byte("refs/heads/f139-owner-release-*"),
				[]byte("refs/heads/main"), 1)
		},
		"new_bypass": func(p []byte) []byte {
			return bytes.Replace(p, []byte(`"bypass_actors": []`),
				[]byte(`"bypass_actors": [{"actor_id":1,"actor_type":"OrganizationAdmin","bypass_mode":"always"}]`), 1)
		},
		"omit_update_lock": func(p []byte) []byte {
			return bytes.Replace(p, []byte(`"update"`), []byte(`"non_fast_forward"`), 1)
		},
		"omit_deletion_lock": func(p []byte) []byte {
			return bytes.Replace(p, []byte(`"deletion"`), []byte(`"creation"`), 1)
		},
		"duplicate_name": func(p []byte) []byte {
			return bytes.Replace(p, []byte(`"target": "branch",`),
				[]byte(`"name": "override", "target": "branch",`), 1)
		},
		"add_unknown_rule": func(p []byte) []byte {
			return bytes.Replace(p, []byte(`"type": "update"`),
				[]byte(`"type": "update", "parameters": {}`), 1)
		},
		"extra_document": func(p []byte) []byte {
			return append(p, []byte("{}")...)
		},
	}
	for name, mutate := range tests {
		t.Run(name, func(t *testing.T) {
			if err := checkF139ReleaseRuleset(mutate(bytes.Clone(b))); err == nil {
				t.Fatal("weakened or ambiguous release ruleset accepted")
			}
		})
	}
}
