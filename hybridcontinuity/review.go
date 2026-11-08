// Package hybridcontinuity validates claimed Hybrid checkpoint lineage for
// offline FORGE review. It cannot authenticate private checkpoint bytes,
// execute a trainer, certify science, or promote an accepted model.
package hybridcontinuity

import (
	"errors"
	"fmt"
)

const (
	Schema         = "forge.hybrid.checkpoint-continuity-review.v1"
	Repository     = "spoonman136668-ai/TTT-Hybrid-Lab"
	Disposition    = "REVIEW_ONLY_UNAUTHENTICATED_NO_TRAINING_OR_PROMOTION"
	MaxCheckpoints = 256
)

var ErrBlocked = errors.New("FORGE_HYBRID_CONTINUITY_BLOCKED")

type Checkpoint struct {
	ManifestSHA256        string `json:"manifest_sha256"`
	ParentManifestSHA256  string `json:"parent_manifest_sha256"`
	PayloadSHA256         string `json:"payload_sha256"`
	SourceSHA             string `json:"source_sha"`
	ArchitectureSHA256    string `json:"architecture_sha256"`
	InterfaceSHA256       string `json:"interface_sha256"`
	ProtocolSHA256        string `json:"protocol_sha256"`
	DataSplitSHA256       string `json:"data_split_sha256"`
	HarnessSHA256         string `json:"harness_sha256"`
	EnvironmentSHA256     string `json:"environment_sha256"`
	OptimizerStatePresent bool   `json:"optimizer_state_present"`
	RNGStatePresent       bool   `json:"rng_state_present"`
	NativeMemoryPresent   bool   `json:"native_memory_present"`
	SamplerCursorPresent  bool   `json:"sampler_cursor_present"`
	Steps                 uint64 `json:"steps"`
	ConsumedExamples      uint64 `json:"consumed_examples"`
}

type Review struct {
	Schema                       string `json:"schema"`
	Repository                   string `json:"repository"`
	CheckpointCount              int    `json:"checkpoint_count"`
	InitialManifestSHA256        string `json:"initial_manifest_sha256"`
	CandidateManifestSHA256      string `json:"candidate_manifest_sha256"`
	CumulativeSteps              uint64 `json:"cumulative_steps"`
	CumulativeExamples           uint64 `json:"cumulative_examples"`
	Disposition                  string `json:"disposition"`
	CheckpointBytesAuthenticated bool   `json:"checkpoint_bytes_authenticated"`
	OwnerVerified                bool   `json:"owner_verified"`
	ScientificAccepted           bool   `json:"scientific_accepted"`
	ExecutionAuthorized          bool   `json:"execution_authorized"`
	TrainingResumed              bool   `json:"training_resumed"`
	ModelPromoted                bool   `json:"model_promoted"`
}

func hex(s string, n int) bool {
	if len(s) != n {
		return false
	}
	for _, c := range s {
		if !(c >= '0' && c <= '9' || c >= 'a' && c <= 'f') {
			return false
		}
	}
	return true
}
func sameIdentity(a, b Checkpoint) bool {
	return a.SourceSHA == b.SourceSHA && a.ArchitectureSHA256 == b.ArchitectureSHA256 &&
		a.InterfaceSHA256 == b.InterfaceSHA256 && a.ProtocolSHA256 == b.ProtocolSHA256 &&
		a.DataSplitSHA256 == b.DataSplitSHA256 && a.HarnessSHA256 == b.HarnessSHA256 &&
		a.EnvironmentSHA256 == b.EnvironmentSHA256
}
func valid(c Checkpoint) bool {
	return hex(c.ManifestSHA256, 64) && hex(c.PayloadSHA256, 64) &&
		hex(c.SourceSHA, 40) && hex(c.ArchitectureSHA256, 64) && hex(c.InterfaceSHA256, 64) &&
		hex(c.ProtocolSHA256, 64) && hex(c.DataSplitSHA256, 64) && hex(c.HarnessSHA256, 64) &&
		hex(c.EnvironmentSHA256, 64) && c.OptimizerStatePresent && c.RNGStatePresent &&
		c.NativeMemoryPresent && c.SamplerCursorPresent
}

// Inspect only compares caller-supplied claimed digests. It does not independently
// fetch or authenticate private blobs. A source/model/protocol change requires a
// separate qualified migration, not a silent continuation or fake reset.
func Inspect(chain []Checkpoint) (Review, error) {
	var zero Review
	if len(chain) < 2 || len(chain) > MaxCheckpoints {
		return zero, ErrBlocked
	}
	seen := make(map[string]bool, len(chain))
	for i, c := range chain {
		if !valid(c) || seen[c.ManifestSHA256] {
			return zero, fmt.Errorf("%w: INVALID_OR_DUPLICATE_CHECKPOINT", ErrBlocked)
		}
		seen[c.ManifestSHA256] = true
		if i == 0 {
			if c.ParentManifestSHA256 != "" || c.Steps != 0 || c.ConsumedExamples != 0 {
				return zero, fmt.Errorf("%w: ROOT_NOT_ZERO", ErrBlocked)
			}
			continue
		}
		parent := chain[i-1]
		if c.ParentManifestSHA256 != parent.ManifestSHA256 ||
			c.ManifestSHA256 == parent.ManifestSHA256 || c.PayloadSHA256 == parent.PayloadSHA256 ||
			c.Steps <= parent.Steps || c.ConsumedExamples <= parent.ConsumedExamples ||
			!sameIdentity(c, parent) {
			return zero, fmt.Errorf("%w: RESTART_OR_DRIFT", ErrBlocked)
		}
	}
	tip := chain[len(chain)-1]
	return Review{Schema: Schema, Repository: Repository, CheckpointCount: len(chain),
		InitialManifestSHA256:   chain[0].ManifestSHA256,
		CandidateManifestSHA256: tip.ManifestSHA256,
		CumulativeSteps:         tip.Steps, CumulativeExamples: tip.ConsumedExamples,
		Disposition: Disposition}, nil
}

// VerifyResult rejects any caller-side elevation to training, authentic
// first-use, scientific acceptance, or model promotion.
func VerifyResult(r Review) error {
	if r.Schema != Schema || r.Repository != Repository || r.CheckpointCount < 2 ||
		r.CheckpointCount > MaxCheckpoints || !hex(r.InitialManifestSHA256, 64) ||
		!hex(r.CandidateManifestSHA256, 64) || r.CumulativeSteps == 0 ||
		r.CumulativeExamples == 0 || r.Disposition != Disposition ||
		r.CheckpointBytesAuthenticated || r.OwnerVerified || r.ScientificAccepted ||
		r.ExecutionAuthorized || r.TrainingResumed || r.ModelPromoted {
		return ErrBlocked
	}
	return nil
}
