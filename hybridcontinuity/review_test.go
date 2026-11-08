package hybridcontinuity

import (
	"strings"
	"testing"
)

func cp(id, parent, payload string, steps, examples uint64) Checkpoint {
	return Checkpoint{ManifestSHA256: strings.Repeat(id, 64),
		ParentManifestSHA256: parent, PayloadSHA256: strings.Repeat(payload, 64),
		SourceSHA: strings.Repeat("a", 40), ArchitectureSHA256: strings.Repeat("b", 64),
		InterfaceSHA256: strings.Repeat("c", 64), ProtocolSHA256: strings.Repeat("d", 64),
		DataSplitSHA256: strings.Repeat("e", 64), HarnessSHA256: strings.Repeat("f", 64),
		EnvironmentSHA256: strings.Repeat("0", 64), OptimizerStatePresent: true,
		RNGStatePresent: true, NativeMemoryPresent: true, SamplerCursorPresent: true,
		Steps: steps, ConsumedExamples: examples}
}
func pair() []Checkpoint {
	a := cp("1", "", "2", 0, 0)
	b := cp("3", a.ManifestSHA256, "4", 100, 900)
	return []Checkpoint{a, b}
}
func TestReadOnlyValidResume(t *testing.T) {
	r, err := Inspect(pair())
	if err != nil {
		t.Fatal(err)
	}
	if err = VerifyResult(r); err != nil {
		t.Fatal(err)
	}
	if r.CumulativeSteps != 100 || r.TrainingResumed || r.ModelPromoted || r.ScientificAccepted {
		t.Fatal(r)
	}
}
func TestRejectRestartWithoutParent(t *testing.T) {
	c := pair()
	c[1].ParentManifestSHA256 = ""
	if _, err := Inspect(c); err == nil {
		t.Fatal("accepted reset")
	}
}
func TestRejectForkOrSourceAndStateDrift(t *testing.T) {
	cases := []func(*Checkpoint){
		func(c *Checkpoint) { c.ParentManifestSHA256 = strings.Repeat("5", 64) },
		func(c *Checkpoint) { c.SourceSHA = strings.Repeat("6", 40) },
		func(c *Checkpoint) { c.ArchitectureSHA256 = strings.Repeat("7", 64) },
		func(c *Checkpoint) { c.DataSplitSHA256 = strings.Repeat("8", 64) },
		func(c *Checkpoint) { c.OptimizerStatePresent = false },
		func(c *Checkpoint) { c.RNGStatePresent = false },
		func(c *Checkpoint) { c.NativeMemoryPresent = false },
		func(c *Checkpoint) { c.SamplerCursorPresent = false },
		func(c *Checkpoint) { c.PayloadSHA256 = strings.Repeat("2", 64) },
	}
	for i, f := range cases {
		c := pair()
		f(&c[1])
		if _, err := Inspect(c); err == nil {
			t.Fatalf("accepted drift %d", i)
		}
	}
}
func TestRejectRepeatedStepOrCursor(t *testing.T) {
	c := pair()
	c[1].Steps = 0
	if _, err := Inspect(c); err == nil {
		t.Fatal("accepted unchanged training step")
	}
	c = pair()
	c[1].ConsumedExamples = 0
	if _, err := Inspect(c); err == nil {
		t.Fatal("accepted replay cursor")
	}
}
func TestRejectDuplicateAndMissingOrigin(t *testing.T) {
	c := pair()
	c[1].ManifestSHA256 = c[0].ManifestSHA256
	if _, err := Inspect(c); err == nil {
		t.Fatal("accepted duplicate")
	}
	c = pair()
	c[0].Steps = 5
	if _, err := Inspect(c); err == nil {
		t.Fatal("accepted training without root")
	}
}
func TestRejectForgedPromotion(t *testing.T) {
	r, _ := Inspect(pair())
	r.ScientificAccepted = true
	if err := VerifyResult(r); err == nil {
		t.Fatal("accepted science escalation")
	}
	r, _ = Inspect(pair())
	r.TrainingResumed = true
	if err := VerifyResult(r); err == nil {
		t.Fatal("accepted resume escalation")
	}
	r, _ = Inspect(pair())
	r.CheckpointBytesAuthenticated = true
	if err := VerifyResult(r); err == nil {
		t.Fatal("accepted fake authenticity")
	}
}
