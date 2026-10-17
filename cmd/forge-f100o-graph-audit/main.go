// forge-f100o-graph-audit audits a pinned third-party PUBLIC development
// graph only. No question/answer data, F95 evaluation, scientific admission,
// optimizer training, policy selection, or controlled external mutation.
package main

import (
	"crypto/sha1"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"os"
	"strconv"

	"github.com/spoonman136668-ai/forge/noveltymechanisms/largegraph"
)

const (
	sourceRepo = "tiantiangao7/kalm-qa"
	sourceCommit = "826ee617e4da5b087584b0e03c70fe76642c6188"
	sourceBlob = "a43fa7ca5e6894236556f2984764070c4ca5562b"
	sourceSHA256 = "9b4d3b3066266075ad1577b4beed68e6e112e76e1a29ed2cb00a2896d2b792af"
)

type Audit struct {
	Schema string `json:"schema"`
	Status string `json:"status"`
	SourceRepository string `json:"source_repository"`
	SourceCommit string `json:"source_commit"`
	SourceBlob string `json:"source_blob"`
	SourceBytesSHA256 string `json:"source_bytes_sha256"`
	Stats largegraph.Stats `json:"whole_graph"`
	SourceIdentityPinned bool `json:"source_identity_pinned"`
	QueryRolesProvidedByIndependentCallerOnly bool `json:"typed_roles_caller_supplied_only"`
	NaturalLanguageAdapterExists bool `json:"natural_language_adapter_exists"`
	F95QuestionAccuracyComputed bool `json:"f95_question_accuracy_computed"`
	PublicDevelopmentOnly bool `json:"public_development_only"`
	IndependentFirstUse bool `json:"independent_scientific_firstuse"`
	ScientificAcceptance bool `json:"scientific_acceptance"`
	DreamParetoPromotion bool `json:"dream_pareto_promotion"`
	ThetaAcceptedTraining bool `json:"thetaevolve_accepted_training"`
	ScienceDispatchAuthorized bool `json:"science_dispatch_authorized"`
	AcceptedRefMutation bool `json:"accepted_ref_mutation"`
	ModelCalls int `json:"model_calls"`
	CodexCalls int `json:"codex_calls"`
	CloudflareWrites int `json:"cloudflare_writes"`
}

func AuditBytes(raw []byte) (Audit, error) {
	var zero Audit
	if len(raw) == 0 || len(raw) > largegraph.MaxSourceBytes {
		return zero, largegraph.ErrBudget
	}
	// Git blob checksum is of the original immutable Git object, not OS-text.
	prefix := []byte("blob " + strconv.Itoa(len(raw)) + "\x00")
	sourceHash := sha1.New()
	_, _ = sourceHash.Write(prefix)
	_, _ = sourceHash.Write(raw)
	if hex.EncodeToString(sourceHash.Sum(nil)) != sourceBlob {
		return zero, errors.New("FORGE_F100O_UNAUTHENTICATED_GIT_BLOB")
	}
	sum := sha256.Sum256(raw)
	if hex.EncodeToString(sum[:]) != sourceSHA256 {
		return zero, errors.New("FORGE_F100O_UNAUTHENTICATED_SOURCE_SHA256")
	}
	graph, err := largegraph.Compile(raw)
	if err != nil {
		return zero, err
	}
	stats := graph.Statistics()
	if stats.SourceRows != 134741 || stats.DistinctTriples != 133582 ||
		stats.DuplicateRows != 1159 || stats.SelfRelations != 11 ||
		stats.DistinctEntities != 43234 {
		return zero, errors.New("FORGE_F100O_REAL_SOURCE_DENOMINATORS_DRIFT")
	}
	return Audit{
		Schema: "forge.optimizer.f100o.public-external-large-graph-index.v1",
		Status: "PUBLIC_EXTERNAL_GRAPH_INDEX_ENGINEERING_ONLY",
		SourceRepository: sourceRepo, SourceCommit: sourceCommit,
		SourceBlob: sourceBlob, SourceBytesSHA256: sourceSHA256,
		Stats: stats, SourceIdentityPinned: true,
		QueryRolesProvidedByIndependentCallerOnly: true,
		PublicDevelopmentOnly: true,
	}, nil
}

func main() {
	input := flag.String("pinned-raw-kb", "", "Immutable Git-object KB path")
	output := flag.String("output", "", "Create-new aggregate evidence path")
	flag.Parse()
	if *input == "" || *output == "" || len(flag.Args()) != 0 {
		fmt.Fprintln(os.Stderr, "FORGE_F100O_REQUIRES_EXACT_READ_ONLY_SOURCE_AND_OUTPUT")
		os.Exit(2)
	}
	info, err := os.Lstat(*input)
	if err != nil || !info.Mode().IsRegular() || info.Size() > largegraph.MaxSourceBytes {
		fmt.Fprintln(os.Stderr, "FORGE_F100O_INVALID_SOURCE_PATH")
		os.Exit(1)
	}
	b, err := os.ReadFile(*input)
	if err != nil {
		fmt.Fprintln(os.Stderr, "FORGE_F100O_SOURCE_READ_FAILED")
		os.Exit(1)
	}
	report, err := AuditBytes(b)
	if err != nil {
		fmt.Fprintln(os.Stderr, "FORGE_F100O_GRAPH_IDENTITY_OR_CAPACITY_DENIED:", err)
		os.Exit(1)
	}
	payload, err := json.MarshalIndent(report, "", "  ")
	if err != nil {
		panic(err)
	}
	f, err := os.OpenFile(*output, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {
		fmt.Fprintln(os.Stderr, "FORGE_F100O_OUTPUT_NOT_NEW")
		os.Exit(1)
	}
	defer f.Close()
	if _, err := f.Write(append(payload, '\n')); err != nil {
		fmt.Fprintln(os.Stderr, "FORGE_F100O_OUTPUT_WRITE_FAILED")
		os.Exit(1)
	}
	fmt.Println("F100O_REAL_PUBLIC_FULL_KB_READBACK=PASS")
	fmt.Println("F100O_ACCEPTED_SCIENCE_AND_MODEL_CALLS=ZERO")
}
