package nativediscovery

import (
	"bytes"
	"encoding/json"
	"reflect"
	"testing"
)

func TestF17FrozenThreeLawInterferenceAllControls(t *testing.T) {
	report, err := F17Development()
	if err != nil {
		t.Fatal(err)
	}
	if F17Validate(report) != nil {
		t.Fatal("F17 canonical source report invalid")
	}
	parent, err := F16Development()
	if err != nil || F16Validate(parent) != nil || parent.Classification != F16NO_GO ||
		report.ParentF16DigestSHA256 != parent.DigestSHA256 || !report.EarlierNegativesPreserved {
		t.Fatal("F16 and earlier original negative outcomes missing")
	}
	if report.Schema != F17Schema || report.Seeds != [2]uint32{71, 97} ||
		report.Policies != [2]string{"fixed", "random"} ||
		report.SwitchSteps != [3]int{16, 32, 48} || report.ActionsPerArm != 60 ||
		report.DelaySteps != 2 || report.ReturnPredictions != 10 ||
		report.MinimumStrongGain != 2 || report.MinimumLatencyGain != 1 ||
		report.MinimumAblationGain != 2 || report.MinimumAlwaysGain != 1 ||
		len(report.Arms) != 4 || report.TotalRuleWork <= 0 || !report.DevelopmentOnly ||
		report.IndependentFirstUseConsumed || report.ScientificAccepted ||
		report.WholeProcessCostMeasured || report.OwnerEligible ||
		report.DispatchAuthorized || report.ActiveResearchChanged || report.AgentCalls != 0 ||
		report.PaidAPICalls != 0 {
		t.Fatal("frozen experimental scope/authority changed")
	}
	passed, totalWork := 0, 0
	for i, arm := range report.Arms {
		if arm.Seed != report.Seeds[i/2] || arm.Policy != report.Policies[i%2] ||
			arm.G1Credited != 52 || arm.G2Credited != 58 || arm.G1Pending != 2 || arm.G2Pending != 2 ||
			!arm.ColdMatches || len(arm.G1SnapshotSHA256) != 64 || len(arm.G2SnapshotSHA256) != 64 {
			t.Fatal("missing development arm or credit/snapshot invariant")
		}
		stream, err := f17Generate(arm.Seed, arm.Policy)
		if err != nil || arm.TraceSHA256 != f8Digest("FORGE-EUREKA-F17-INTERFERENCE-OBSERVATIONS-V1\n", stream) {
			t.Fatal("provenance of precommitted world invalid")
		}
		for wi, w := range arm.Windows {
			locked := f17Windows()[wi]
			if w.Name != locked.Name || w.Start != locked.Start || w.End != locked.End || w.Predictions != locked.Predictions {
				t.Fatal("evaluation window moved after seeing results")
			}
			for k, kind := range f17Kinds() {
				m := f13New()
				for _, e := range stream[:w.Start] {
					if m.Observe(e) != nil {
						t.Fatal("source ingest failed")
					}
				}
				correct, work, trace := 0, 0, ""
				for step := w.Start; step <= w.End; step++ {
					if m.Observe(stream[step]) != nil {
						t.Fatal("source ingest failed")
					}
					before, err := m.Snapshot()
					if err != nil {
						t.Fatal(err)
					}
					guess, cost, err := f17Forecast(kind, m, stream[step-1], stream[step])
					if err != nil || cost < 1 {
						t.Fatal("forecast failed", kind, err)
					}
					target := stream[step+2].DelayedState // scorer exclusively
					if guess == target {
						correct++
						trace += "1"
					} else {
						trace += "0"
					}
					after, err := m.Snapshot()
					if err != nil || !bytes.Equal(before, after) {
						t.Fatal("evaluation label reached learned memory")
					}
					work += cost
				}
				if correct != w.Correct[k] || work != w.RuleWork[k] || trace != w.CorrectTrace[k] ||
					len(trace) != w.Predictions {
					t.Fatalf("model %s on %s differs from exact stream", kind, w.Name)
				}
				totalWork += work
			}
		}
		b, c, ret := arm.Windows[0], arm.Windows[1], arm.Windows[2]
		bestB, _, _ := f17Strongest(b)
		bestC, _, _ := f17Strongest(c)
		strong, name, fastest := f17Strongest(ret)
		offset := f17Recovery(ret.CorrectTrace[0])
		retained := b.Correct[0] >= bestB-1 && c.Correct[0] >= bestC-1
		passedArm := arm.ColdMatches && retained && arm.ArchiveCountAtG1 > 0 &&
			ret.Correct[0]-strong >= 2 && fastest-offset >= 1 &&
			ret.Correct[0]-ret.Correct[7] >= 2 && ret.Correct[0]-ret.Correct[8] >= 1 &&
			ret.Correct[0]-ret.Correct[9] >= 2
		if arm.ReturnStrongestCorrect != strong || arm.ReturnStrongestName != name ||
			arm.FastestControlRecoveryOffset != fastest || arm.CandidateRecoveryOffset != offset ||
			arm.AdvantageStrongest != ret.Correct[0]-strong || arm.AdvantageRecovery != fastest-offset ||
			arm.AdvantageNoArchive != ret.Correct[0]-ret.Correct[7] ||
			arm.AdvantageAlwaysArchive != ret.Correct[0]-ret.Correct[8] ||
			arm.AdvantageWrongLag != ret.Correct[0]-ret.Correct[9] ||
			arm.MiddleRetention != retained || arm.PassesThreshold != passedArm {
			t.Fatal("strongest comparator, ablation or frozen threshold omitted")
		}
		if passedArm {
			passed++
		}
		t.Logf("F17_DEV seed=%d policy=%s B=%v C=%v return=%v return_trace=%v candidate=%d/10 strongest=%s/%d gain=%+d recovery=%d fastest=%d retained=%v archive=%d passing=%v",
			arm.Seed, arm.Policy, b.Correct, c.Correct, ret.Correct, ret.CorrectTrace,
			ret.Correct[0], name, strong, arm.AdvantageStrongest, offset, fastest, retained,
			arm.ArchiveCountAtG1, passedArm)
	}
	class := F17NO_GO
	if passed == 4 {
		class = F17Signal
	}
	if totalWork != report.TotalRuleWork || passed != report.PassingArms || report.Classification != class {
		t.Fatal("development loser or cost suppressed; classification post-tuned")
	}
	second, err := F17Development()
	if err != nil || !reflect.DeepEqual(report, second) {
		t.Fatal("source-derived result non-deterministic", err)
	}
	t.Logf("F17_FROZEN_DEV=%s passing=%d/4 whole_process_cost_unverified=true scientific_accepted=false owner_eligible=false", class, passed)
}

func TestF17UnknownSeedsNoLeakageDelayedCreditAndColdReplay(t *testing.T) {
	for _, bad := range []uint32{0, 17, 31, 59, 83, 71 + 1} {
		if _, err := f17Generate(bad, "fixed"); err == nil {
			t.Fatal("unknown or first-use seed admitted")
		}
	}
	for _, policy := range []string{"", "oracle", "first-use", "disagreement"} {
		if _, err := f17Generate(71, policy); err == nil {
			t.Fatal("unknown policy admitted")
		}
	}
	for _, seed := range f17Seeds() {
		laws, err := f17WorldRules(seed)
		if err != nil || laws[0] == laws[1] || laws[1] == laws[2] || laws[0] == laws[2] {
			t.Fatal("missing distinct laws")
		}
		for _, policy := range f17Policies() {
			stream, err := f17Generate(seed, policy)
			if err != nil || len(stream) != 60 {
				t.Fatal("bad stream")
			}
			state := int(f12Mix(seed^0x125ecafe) & 3)
			initial := state
			var after [60]int
			m := f13New()
			var g1 []byte
			for step, e := range stream {
				expected := -1
				if step == 1 {
					expected = initial
				}
				if step >= 2 {
					expected = after[step-2]
				}
				action, err := f17Action(seed, policy, step)
				if err != nil || e.Step != step || e.Phase != 0 || e.Sensor != state&1 ||
					e.DelayedState != expected || e.Action != action || e.Cue != f12Cue(seed, step, 0) {
					tFailF17(t, "unannounced rule/sensor/delay schedule exposed")
				}
				law := laws[0]
				if step >= 16 && step < 32 {
					law = laws[1]
				}
				if step >= 32 && step < 48 {
					law = laws[2]
				}
				state = f12Next(law, state, 0, e.Cue, e.Action)
				after[step] = state
				if m.Observe(e) != nil || len(m.Credits) != max(0, step+1-2) {
					t.Fatal("unrevealed effect credited")
				}
				if step == 53 {
					g1, err = m.Snapshot()
					if err != nil {
						t.Fatal(err)
					}
					cold, err := f13Load(g1, f3Hash(g1))
					if err != nil {
						t.Fatal(err)
					}
					m = cold
				}
			}
			if m.Pending[0].Step != 58 || m.Pending[1].Step != 59 || len(m.Credits) != 58 {
				t.Fatal("pending causal ID or delayed credit lost")
			}
			got, err := m.Snapshot()
			if err != nil {
				t.Fatal(err)
			}
			replay := f13New()
			for _, e := range stream {
				if replay.Observe(e) != nil {
					t.Fatal("replay")
				}
			}
			want, err := replay.Snapshot()
			if err != nil || !bytes.Equal(got, want) {
				t.Fatal("G1 cold to G2 mismatch")
			}
			if m.Observe(stream[0]) == nil {
				t.Fatal("replayed first event admitted")
			}
			tampered := append([]byte{}, g1...)
			tampered[len(tampered)-8] ^= 1
			if _, err := f13Load(tampered, f3Hash(g1)); err == nil {
				t.Fatal("corrupt checkpoint admitted")
			}
		}
	}
}
func tFailF17(t *testing.T, msg string) { t.Helper(); t.Fatal(msg) }

func TestF17ForgedScienceAndNegativeResultsRejected(t *testing.T) {
	baseline, err := F17Development()
	if err != nil {
		t.Fatal(err)
	}
	duplicate := func() F17Report {
		raw, e := json.Marshal(baseline)
		if e != nil {
			t.Fatal(e)
		}
		var v F17Report
		if json.Unmarshal(raw, &v) != nil {
			t.Fatal("roundtrip")
		}
		return v
	}
	controls := []struct {
		name   string
		mutate func(*F17Report)
	}{
		{"source", func(r *F17Report) { r.ParentF16DigestSHA256 = "forged" }},
		{"earlier negatives", func(r *F17Report) { r.EarlierNegativesPreserved = false }},
		{"schema", func(r *F17Report) { r.Schema = "forged" }},
		{"seed", func(r *F17Report) { r.Seeds[0] = 59 }},
		{"budget", func(r *F17Report) { r.ActionsPerArm = 999 }},
		{"gain", func(r *F17Report) { r.MinimumStrongGain = 0 }},
		{"cost", func(r *F17Report) { r.TotalRuleWork = 0 }},
		{"loser", func(r *F17Report) { r.Arms = r.Arms[:3] }},
		{"trace", func(r *F17Report) { r.Arms[0].Windows[2].CorrectTrace[0] = "1111111111" }},
		{"pending", func(r *F17Report) { r.Arms[0].G2Pending = 0 }},
		{"cold", func(r *F17Report) { r.Arms[0].ColdMatches = false }},
		{"false science", func(r *F17Report) { r.ScientificAccepted = true }},
		{"first-use", func(r *F17Report) { r.IndependentFirstUseConsumed = true }},
		{"owner", func(r *F17Report) { r.OwnerEligible = true }},
		{"dispatch", func(r *F17Report) { r.DispatchAuthorized = true }},
		{"live", func(r *F17Report) { r.ActiveResearchChanged = true }},
		{"paid", func(r *F17Report) { r.PaidAPICalls = 1 }},
	}
	for _, c := range controls {
		t.Run(c.name, func(t *testing.T) {
			forged := duplicate()
			c.mutate(&forged)
			forged.DigestSHA256 = f17Digest(forged) // a valid self-hash is insufficient
			if F17Validate(forged) == nil {
				t.Fatal("rehashed forgery accepted")
			}
		})
	}
}
