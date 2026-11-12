package nativediscovery

import (
	"bytes"
	"encoding/json"
	"reflect"
	"testing"
)

func TestF23FrozenProspectiveControlsAndColdReplay(t *testing.T) {
	report, e := F23Development()
	if e != nil {
		t.Fatal(e)
	}
	if F23Validate(report) != nil {
		t.Fatal("source-bound F23 report failed to validate")
	}
	if report.Schema != F23Schema || report.ParentF22Commit != F23F22Parent ||
		report.Seeds != [2]uint32{151, 157} || report.Policies != [2]string{"balanced", "skewed"} ||
		report.Actions != 128 || report.FeedbackDelay != 2 || report.Novel != [2]int{64, 79} ||
		report.Late != [2]int{80, 95} || report.Return != [2]int{96, 111} ||
		report.MinimumGain != 2 || len(report.Arms) != 4 || report.TotalRuleWork <= 0 ||
		!report.EarlierNegativesPreserved || !report.DevelopmentOnly ||
		report.FirstUseConsumed || report.ScientificAccepted || report.WholeProcessCostProven ||
		report.OwnerEligible || report.DispatchAuthorized || report.ActiveResearchChanged ||
		report.AgentCalls != 0 || report.PaidAPICalls != 0 {
		t.Fatal("frozen gate/authority drift")
	}
	passing, work := 0, 0
	for i, a := range report.Arms {
		seed, policy := report.Seeds[i/2], report.Policies[i%2]
		cold, raw, e := f23Run(seed, policy, true)
		warm, original, e2 := f23Run(seed, policy, false)
		if e != nil || e2 != nil || !reflect.DeepEqual(cold, warm) || !bytes.Equal(raw, original) ||
			!reflect.DeepEqual(cold, a) || !a.ColdMatches || a.CheckpointCredits != 94 ||
			a.FinalCredits != 126 || a.Pending != 2 || len(a.CheckpointSHA256) != 64 ||
			len(a.FinalSHA256) != 64 || len(a.TraceSHA256) != 64 {
			t.Fatal("checkpoint/lineage/replay mismatch", e, e2)
		}
		m, e := f23Load(raw, a.FinalSHA256)
		if e != nil || len(m.Credits) != 126 || len(m.Pending) != 2 || m.Pending[0].Step != 126 ||
			m.Pending[1].Step != 127 || len(m.ControlPreds) != 128 {
			t.Fatal("cold bytes dropped pending delayed consequence")
		}
		for j, w := range a.Windows {
			expected := [3]F23Window{{Name: "novel-C", Start: 64, End: 79}, {Name: "late-C", Start: 80, End: 95}, {Name: "return-A", Start: 96, End: 111}}[j]
			if w.Name != expected.Name || w.Start != expected.Start || w.End != expected.End || len(w.SelectorIDs) != 16 {
				t.Fatal("scoring windows drift")
			}
			for _, ch := range w.SelectorIDs {
				if ch < '0' || ch > '6' {
					t.Fatal("online selector encoded a non-control or oracle")
				}
			}
			for k, v := range w.Correct {
				bits := 0
				for _, ch := range w.Trace[k] {
					if ch == '1' {
						bits++
					} else if ch != '0' {
						t.Fatal("incorrect correctness trace")
					}
				}
				if len(w.Trace[k]) != 16 || bits != v || w.Work[k] < 1 {
					t.Fatalf("missing/misaligned baseline %s", f23Kinds()[k])
				}
				work += w.Work[k]
			}
		}
		ret, late := a.Windows[2], a.Windows[1]
		best, bestName := -1, ""
		for k := 1; k <= 7; k++ {
			if ret.Correct[k] > best {
				best, bestName = ret.Correct[k], f23Kinds()[k]
			}
		}
		good := a.ColdMatches && a.MaxArchiveCount > 0 && late.Correct[0] >= late.Correct[8]-2 &&
			ret.Correct[0]-ret.Correct[8] >= 2 &&
			f23Recovery(ret.Trace[8])-f23Recovery(ret.Trace[0]) >= 1 &&
			ret.Correct[0]-ret.Correct[9] >= 2 &&
			ret.Correct[0]-ret.Correct[11] >= 2 &&
			ret.Correct[0]-ret.Correct[10] >= 1 &&
			ret.Correct[0]-ret.Correct[12] >= 1 && ret.DistinctRolling8 >= 2
		if a.Passes != good || a.HindsightBestScore != best || a.HindsightBestName != bestName ||
			a.GainSelector != ret.Correct[0]-ret.Correct[8] ||
			a.RecoveryGainSelector != f23Recovery(ret.Trace[8])-f23Recovery(ret.Trace[0]) ||
			a.GainNoArchive != ret.Correct[0]-ret.Correct[9] ||
			a.GainUniform != ret.Correct[0]-ret.Correct[10] ||
			a.GainWrongCredit != ret.Correct[0]-ret.Correct[11] ||
			a.GainRandom != ret.Correct[0]-ret.Correct[12] ||
			a.LateCRetention != (late.Correct[0] >= late.Correct[8]-2) {
			t.Fatal("non-deployable hindsight control substituted, or gates drifted")
		}
		if a.Passes {
			passing++
		}
		t.Logf("F23_DEV seed=%d policy=%s C-new=%v C-late=%v A-return=%v selector=%s gain=%+d recovery_delta=%d ablations(no/unif/wrong/random)=%+d/%+d/%+d/%+d distinct_vs_rolling8=%d hindsight=%s/%d PASS=%v",
			seed, policy, a.Windows[0].Correct, a.Windows[1].Correct, ret.Correct,
			ret.SelectorIDs, a.GainSelector, a.RecoveryGainSelector, a.GainNoArchive, a.GainUniform,
			a.GainWrongCredit, a.GainRandom, ret.DistinctRolling8, a.HindsightBestName, a.HindsightBestScore, a.Passes)
	}
	classification := F23NoGo
	if passing == 4 {
		classification = F23Signal
	}
	if report.PassingArms != passing || report.TotalRuleWork != work || report.Classification != classification {
		t.Fatal("negative or cost concealed")
	}
	t.Logf("F23_FROZEN_DEV=%s passing=%d/4 rule_work=%d first_use=false science_accepted=false", classification, passing, work)
}
func TestF23WorldOnlyGeneratorAndNoOracle(t *testing.T) {
	for _, bad := range []uint32{0, 17, 31, 59, 83, 101, 113, 127, 131, 137, 150, 152, 156, 158} {
		if _, e := f23Laws(bad); e == nil {
			t.Fatal("first-use/unknown seed admitted")
		}
	}
	for _, bad := range []string{"", "oracle", "fixed", "random", "phase"} {
		if _, _, e := f23ActionCue(151, bad, 0); e == nil {
			t.Fatal("unregistered policy admitted")
		}
	}
	for _, seed := range f23Seeds() {
		for _, policy := range f23Policies() {
			laws, _ := f23Laws(seed)
			for step := 0; step < F23Actions; step++ {
				cue, action, e := f23ActionCue(seed, policy, step)
				if e != nil || cue < 0 || cue > 3 || action < 0 || action > 1 {
					t.Fatal("invalid exogenous action")
				}
				law := laws[0]
				if step >= 32 && step < 64 {
					law = laws[1]
				}
				if step >= 64 && step < 96 {
					law = laws[2]
				}
				actual, e := f23Truth(seed, step, cue, action)
				if e != nil || actual != f20Truth(law, cue, action) {
					t.Fatal("generator phase changed")
				}
				noisy, e := f23Observation(seed, step, cue, action)
				if e != nil || noisy < -1 || noisy > 1 {
					t.Fatal("invalid delayed observation")
				}
			}
		}
	}
	if _, _, _, e := f23Belief(nil, 0, 0, 0, "oracle"); e == nil {
		t.Fatal("oracle candidate admitted")
	}
	if _, _, _, e := f23Belief(nil, 4, 0, 0, "regime-belief"); e == nil {
		t.Fatal("out of range cue admitted")
	}
	if _, _, _, e := f23Belief(nil, 0, 2, 0, "regime-belief"); e == nil {
		t.Fatal("out of range action admitted")
	}
	if _, _, _, e := f23Belief(nil, 0, 0, 128, "regime-belief"); e == nil {
		t.Fatal("future oracle time admitted")
	}
	if _, _, _, e := f23Belief([]f20Credit{{Step: 0, Cue: 0, Action: 2}}, 0, 0, 3, "regime-belief"); e == nil {
		t.Fatal("forged action admitted")
	}
	if _, _, e := f23Conventional(7, nil, 0, 0); e == nil {
		t.Fatal("missing conventional baseline accepted")
	}
}
func TestF23BeliefComponentsActuallyUpdateAndDoNotReadTruth(t *testing.T) {
	// Same credited stream must produce exactly the same forecast regardless of
	// which seed's hidden rule produced it; f23Belief takes no seed or true law.
	recs := make([]f20Credit, 0, 110)
	for i := 0; i < 110; i++ {
		recs = append(recs, f20Credit{Step: i, Cue: i % 4, Action: i % 2, WrongAction: (i + 1) % 2, Value: (i / 3) % 2})
	}
	x, w, bank, e := f23Belief(recs, 2, 1, 112, "regime-belief")
	y, w2, bank2, e2 := f23Belief(recs, 2, 1, 112, "regime-belief")
	if e != nil || e2 != nil || x != y || w != w2 || bank != bank2 || bank == 0 {
		t.Fatal("non-deterministic or inert bank")
	}
	no, _, n, e := f23Belief(recs, 2, 1, 112, "no-archive")
	if e != nil || n != 0 || no < 0 || no > 1 {
		t.Fatal("archive ablation leaked state")
	}
	for _, kind := range []string{"uniform-retrieval", "wrong-credit", "random-retrieval"} {
		bit, work, b, e := f23Belief(recs, 2, 1, 112, kind)
		if e != nil || work <= 0 || bit < 0 || bit > 1 || b < 1 {
			t.Fatal("ablation unavailable", kind)
		}
	}
}
func TestF23RehashedReportsDenied(t *testing.T) {
	report, e := F23Development()
	if e != nil {
		t.Fatal(e)
	}
	mutate := []struct {
		name string
		f    func(*F23Report)
	}{
		{"parent", func(x *F23Report) { x.ParentF22Commit = "fabricated" }},
		{"history", func(x *F23Report) { x.EarlierNegativesPreserved = false }},
		{"first use seed", func(x *F23Report) { x.Seeds[0] = 59 }},
		{"world", func(x *F23Report) { x.Actions = 129 }},
		{"feedback", func(x *F23Report) { x.FeedbackDelay = 0 }},
		{"window", func(x *F23Report) { x.Return[0] = 95 }},
		{"gain", func(x *F23Report) { x.MinimumGain = 0 }},
		{"remove loser", func(x *F23Report) { x.Arms = x.Arms[:3] }},
		{"reorder", func(x *F23Report) { x.Arms[0], x.Arms[1] = x.Arms[1], x.Arms[0] }},
		{"erase baseline", func(x *F23Report) { x.Arms[0].Windows[2].Correct[8] = 0 }},
		{"selectors", func(x *F23Report) { x.Arms[0].Windows[2].SelectorIDs = "0000000000000000" }},
		{"cold", func(x *F23Report) { x.Arms[0].FinalSHA256 = "fake" }},
		{"premature science", func(x *F23Report) { x.ScientificAccepted = true }},
		{"first-use", func(x *F23Report) { x.FirstUseConsumed = true }},
		{"cost", func(x *F23Report) { x.WholeProcessCostProven = true }},
		{"owner", func(x *F23Report) { x.OwnerEligible = true }},
		{"dispatch", func(x *F23Report) { x.DispatchAuthorized = true }},
		{"active", func(x *F23Report) { x.ActiveResearchChanged = true }},
		{"paid", func(x *F23Report) { x.PaidAPICalls = 1 }},
	}
	for _, tc := range mutate {
		t.Run(tc.name, func(t *testing.T) {
			raw, _ := json.Marshal(report)
			var x F23Report
			if json.Unmarshal(raw, &x) != nil {
				t.Fatal("copy")
			}
			tc.f(&x)
			x.DigestSHA256 = f23Digest(x)
			if F23Validate(x) == nil {
				t.Fatal("rehashed forged report accepted")
			}
		})
	}
}
func TestF23CheckpointRejectsStaleAndNonCanonical(t *testing.T) {
	m := f23Ledger{Seen: 2, Pending: []f20Probe{{Step: 0, Cue: 0, Action: 0, WrongAction: 0}, {Step: 1, Cue: 1, Action: 1, WrongAction: 0}}, ControlPreds: [][7]int{{}, {}}}
	raw, e := f23Snapshot(m)
	if e != nil {
		t.Fatal(e)
	}
	if _, e := f23Load(raw, f3Hash(raw)); e != nil {
		t.Fatal(e)
	}
	tampered := bytes.Replace(raw, []byte("\"seen\":2"), []byte("\"seen\":3"), 1)
	if _, e := f23Load(tampered, f3Hash(raw)); e == nil {
		t.Fatal("stale checkpoint hash accepted")
	}
	if _, e := f23Load(tampered, f3Hash(tampered)); e == nil {
		t.Fatal("inconsistent rehashed delayed ledger accepted")
	}
	if _, e := f23Load(append(append([]byte{}, raw...), []byte(" ")...), f3Hash(append(append([]byte{}, raw...), []byte(" ")...))); e == nil {
		t.Fatal("noncanonical bytes accepted")
	}
	m.ControlPreds[0][0] = 2
	if _, e := f23Snapshot(m); e == nil {
		t.Fatal("forged forecast accepted")
	}
}
