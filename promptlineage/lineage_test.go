package promptlineage

import (
	"reflect"
	"strings"
	"testing"
)

func fixture() Frozen {
	return Frozen{
		Schema: Schema, Lane: "Wingless", Epoch: 1,
		SourceSHA: strings.Repeat("a", 40),
		Parent: "reason with bounded evidence",
		Vocabulary: []string{"verified", "strict"},
		MaxOperations: 3,
		Operations: []Operation{
			{Kind: "replace", Position: 2, Replacement: "verified"},
			{Kind: "swap-next", Position: 0},
			{Kind: "replace", Position: 1, Replacement: "strict"},
		},
	}
}

func TestGeneratePinnedBoundedLineage(t *testing.T) {
	f := fixture()
	pin := Digest(f)
	a, err := Generate(f, pin)
	if err != nil {
		t.Fatal(err)
	}
	b, err := Generate(f, pin)
	if err != nil || !reflect.DeepEqual(a, b) {
		t.Fatal("deterministic replay failed", err)
	}
	if a.Schema != ResultSchema || a.OperationsUsed != 3 ||
		len(a.Candidates) != 3 || a.FrozenSHA256 != pin ||
		a.ScientificAccepted || a.DispatchAuthorized || a.SealedEvaluationConsumed {
		t.Fatalf("unsafe status or accounting: %+v", a)
	}
	for _, c := range a.Candidates {
		if c.Classification != "UNTESTED" || c.ParentSHA256 != a.ParentSHA256 ||
			!hexLower(c.CandidateSHA256, 64) || c.Prompt == f.Parent {
			t.Fatalf("unsafe candidate: %+v", c)
		}
	}
}

func TestGenerateRejectsPinDriftAndBadPlans(t *testing.T) {
	base := fixture()
	pin := Digest(base)
	tests := map[string]func(*Frozen){
		"lane": func(f *Frozen) { f.Lane = "KTRADE" },
		"epoch": func(f *Frozen) { f.Epoch = 0 },
		"source": func(f *Frozen) { f.SourceSHA = strings.Repeat("A", 40) },
		"parent": func(f *Frozen) { f.Parent = "reason  with bounded evidence" },
		"budget": func(f *Frozen) { f.MaxOperations = 2 },
		"huge-budget": func(f *Frozen) { f.MaxOperations = 33 },
		"duplicate-vocabulary": func(f *Frozen) { f.Vocabulary = []string{"strict", "strict"} },
		"unknown-vocabulary": func(f *Frozen) { f.Operations[0].Replacement = "unverified" },
		"no-op": func(f *Frozen) { f.Operations[0].Replacement = "bounded" },
		"unknown-operator": func(f *Frozen) { f.Operations[0].Kind = "model-call" },
		"out-of-range": func(f *Frozen) { f.Operations[0].Position = 10 },
		"hidden-swap-replacement": func(f *Frozen) { f.Operations[1].Replacement = "strict" },
		"duplicate-candidate": func(f *Frozen) { f.Operations[2] = f.Operations[0] },
	}
	for name, mutate := range tests {
		t.Run(name, func(t *testing.T) {
			f := fixture()
			mutate(&f)
			if _, err := Generate(f, Digest(f)); err == nil {
				t.Fatal("accepted unsafe frozen plan")
			}
		})
	}
	drift := fixture()
	drift.Operations[0].Replacement = "strict"
	if _, err := Generate(drift, pin); err == nil {
		t.Fatal("accepted plan drift after independent pin")
	}
	if _, err := Generate(base, strings.Repeat("0", 64)); err == nil {
		t.Fatal("accepted forged independent pin")
	}
}

func TestDistinctSourceAndLaneProduceDistinctIdentity(t *testing.T) {
	a := fixture()
	b := fixture()
	b.Lane = "Yggdrasil"
	ra, errA := Generate(a, Digest(a))
	rb, errB := Generate(b, Digest(b))
	if errA != nil || errB != nil || ra.ParentSHA256 == rb.ParentSHA256 ||
		ra.Candidates[0].CandidateSHA256 == rb.Candidates[0].CandidateSHA256 {
		t.Fatal("cross-lane identity collision", errA, errB)
	}
}
