// Package promptlineage generates a bounded, deterministic, non-executing
// Promptbreeder-style candidate lineage from an independently pinned plan.
// Its outputs are untested proposals, NEVER scientific admissions.
package promptlineage

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"strconv"
	"strings"
)

const Schema = "forge.promptlineage.frozen.v1"
const ResultSchema = "forge.promptlineage.advisory.v1"

var ErrFrozen = errors.New("FORGE_PROMPTLINEAGE_FROZEN_PLAN_INVALID")

type Operation struct {
	Kind        string `json:"kind"`
	Position    int    `json:"position"`
	Replacement string `json:"replacement,omitempty"`
}

type Frozen struct {
	Schema        string      `json:"schema"`
	Lane          string      `json:"lane"`
	Epoch         uint64      `json:"epoch"`
	SourceSHA     string      `json:"source_sha"`
	Parent        string      `json:"parent"`
	Vocabulary    []string    `json:"vocabulary"`
	MaxOperations int         `json:"max_operations"`
	Operations    []Operation `json:"operations"`
}

type Candidate struct {
	ParentSHA256    string    `json:"parent_sha256"`
	CandidateSHA256 string    `json:"candidate_sha256"`
	Prompt          string    `json:"prompt"`
	Operation       Operation `json:"operation"`
	Classification  string    `json:"classification"`
}

type Result struct {
	Schema                       string      `json:"schema"`
	Lane                         string      `json:"lane"`
	FrozenSHA256                 string      `json:"frozen_sha256"`
	ParentSHA256                 string      `json:"parent_sha256"`
	OperationsUsed               int         `json:"operations_used"`
	Candidates                   []Candidate `json:"candidates"`
	ScientificAccepted           bool        `json:"scientific_accepted"`
	DispatchAuthorized           bool        `json:"dispatch_authorized"`
	SealedEvaluationConsumed     bool        `json:"sealed_evaluation_consumed"`
}

func hash(s string) string {
	h := sha256.Sum256([]byte(s))
	return hex.EncodeToString(h[:])
}

func Digest(f Frozen) string {
	raw, _ := json.Marshal(f)
	return hash("FORGE-PROMPTLINEAGE-FROZEN-V1\n" + string(raw))
}

func hexLower(s string, n int) bool {
	if len(s) != n {
		return false
	}
	for _, c := range s {
		if !((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')) {
			return false
		}
	}
	return true
}

func word(s string) bool {
	if len(s) == 0 || len(s) > 24 {
		return false
	}
	for _, c := range s {
		if !((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-') {
			return false
		}
	}
	return true
}

func prompt(s string) ([]string, bool) {
	if len(s) < 3 || len(s) > 512 {
		return nil, false
	}
	parts := strings.Split(s, " ")
	if len(parts) < 2 || len(parts) > 24 {
		return nil, false
	}
	for _, p := range parts {
		if !word(p) {
			return nil, false
		}
	}
	return parts, true
}

// Generate never reads scientific results or private sealed material, makes
// no model/network/process calls, and refuses any unpinned source or budget.
func Generate(f Frozen, independentPin string) (Result, error) {
	var empty Result
	if f.Schema != Schema ||
		(f.Lane != "Wingless" && f.Lane != "Yggdrasil") ||
		f.Epoch == 0 || !hexLower(f.SourceSHA, 40) ||
		!hexLower(independentPin, 64) || Digest(f) != independentPin ||
		f.MaxOperations < 1 || f.MaxOperations > 32 ||
		len(f.Operations) == 0 || len(f.Operations) > f.MaxOperations {
		return empty, ErrFrozen
	}
	parent, ok := prompt(f.Parent)
	if !ok || len(f.Vocabulary) == 0 || len(f.Vocabulary) > 24 {
		return empty, ErrFrozen
	}
	vocabulary := make(map[string]bool, len(f.Vocabulary))
	for _, v := range f.Vocabulary {
		if !word(v) || vocabulary[v] {
			return empty, ErrFrozen
		}
		vocabulary[v] = true
	}
	parentHash := hash("FORGE-PROMPTLINEAGE-PARENT-V1\n" + f.Lane + "\n" + f.SourceSHA + "\n" + f.Parent)
	out := Result{
		Schema: ResultSchema, Lane: f.Lane,
		FrozenSHA256: independentPin, ParentSHA256: parentHash,
		Candidates: make([]Candidate, 0, len(f.Operations)),
	}
	seen := make(map[string]bool, len(f.Operations))
	for i, op := range f.Operations {
		if op.Position < 0 || op.Position >= len(parent) {
			return empty, ErrFrozen
		}
		words := append([]string(nil), parent...)
		switch op.Kind {
		case "replace":
			if !vocabulary[op.Replacement] || words[op.Position] == op.Replacement {
				return empty, ErrFrozen
			}
			words[op.Position] = op.Replacement
		case "swap-next":
			if op.Replacement != "" || op.Position+1 >= len(words) ||
				words[op.Position] == words[op.Position+1] {
				return empty, ErrFrozen
			}
			words[op.Position], words[op.Position+1] = words[op.Position+1], words[op.Position]
		default:
			return empty, ErrFrozen
		}
		modified := strings.Join(words, " ")
		if seen[modified] || modified == f.Parent {
			return empty, ErrFrozen
		}
		seen[modified] = true
		childHash := hash("FORGE-PROMPTLINEAGE-CHILD-V1\n" +
			independentPin + "\n" + parentHash + "\n" +
			strconv.Itoa(i) + "\n" + modified)
		out.Candidates = append(out.Candidates, Candidate{
			ParentSHA256: parentHash, CandidateSHA256: childHash,
			Prompt: modified, Operation: op, Classification: "UNTESTED",
		})
	}
	out.OperationsUsed = len(out.Candidates)
	return out, nil
}
