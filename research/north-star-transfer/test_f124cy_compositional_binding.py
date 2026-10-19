"""F124-CY executable source-free causal composition acceptance contracts."""
import ast
import copy
from pathlib import Path
import sys
import unittest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import f124cy_sourcefree_fixture as fixture
import f124cy_shared_causal_composition as shared
import f124cy_independent_edge_control as control
import f124cy_sourcefree_trial as trial

class CompositionalBinding(unittest.TestCase):
    def test_shared_learned_model_recovers_sourcefree_sequences(self):
        # This probes a disclosed, deliberately narrow bit-affine causal
        # grammar. A positive result is not independent scientific transfer.
        for regime in fixture.REGIMES:
            for seed in range(4):
                d=fixture.born(regime,seed)
                m,receipt=shared.fit(d["fit"],regime)
                self.assertIsNotNone(m,(regime,seed,receipt))
                self.assertEqual(receipt["FIT_error_bits"],0)
                check=[shared.score(m,x) for x in d["check"]]
                self.assertTrue(all(x["correct"] for x in check),(regime,seed,check))
                self.assertTrue(all(shared.score(m,x)["correct"] for x in d["heldout"]))
                self.assertTrue(all(not shared.score(m,fixture.matched_hard_negative(x))["correct"]
                                   for x in d["heldout"]))
    def test_fit_is_on_entire_public_sequence_and_holdout_is_not_training(self):
        data=fixture.born(fixture.REGIMES[0],0)
        m,_=shared.fit(data["fit"],fixture.REGIMES[0])
        x=copy.deepcopy(data["heldout"][0])
        before=shared.trajectory(m,x)
        for row in x["events"]:
            row["observed"]^=15
        self.assertEqual(shared.trajectory(m,x),before)
        # CHECK and heldout labels cannot be teacher-forced into recurrence.
        self.assertNotEqual(before,[e["observed"] for e in x["events"]])
    def test_genuinely_learned_entity_renaming_equivariance(self):
        data=fixture.born(fixture.REGIMES[1],0)
        m,_=shared.fit(data["fit"],fixture.REGIMES[1])
        x=data["heldout"][0]
        renamed={"alpha":"gamma","beta":"alpha","gamma":"beta"}
        x2={"initial":{renamed[k]:list(v) for k,v in x["initial"].items()},
            "events":[{**row,"target":renamed[row["target"]],
                       "source":renamed[row["source"]]} for row in x["events"]]}
        self.assertEqual(shared.trajectory(m,x),shared.trajectory(m,x2))
    def test_equally_informed_independent_control_trains_all_six_edges(self):
        for regime in fixture.REGIMES:
            data=fixture.born(regime,1)
            trained,rec=control.train(data["fit"],regime)
            self.assertIsNotNone(trained,rec)
            self.assertEqual(rec["trained_directed_edge_groups"],
                             6 if regime==fixture.REGIMES[0] else 12)
            self.assertTrue(rec["fully_fitted_without_CHECK_tuning"])
            self.assertGreater(len(trained["edges"]),0)
            self.assertEqual(trial.test(regime,1,"shared")["same_public_FIT_sha256"],
                             trial.test(regime,1,"edge_control")["same_public_FIT_sha256"])
    def test_prevent_source_oracle_and_previous_originals(self):
        forbidden=("f124cu_","f124cr_","f124co_","f124cn_",
                   "f124cy_sourcefree_fixture")
        for file in ("f124cy_shared_causal_composition.py",
                     "f124cy_independent_edge_control.py"):
            t=ast.parse((HERE/file).read_text())
            imports=[]
            for node in ast.walk(t):
                if isinstance(node,ast.Import):imports.extend(i.name for i in node.names)
                elif isinstance(node,ast.ImportFrom):imports.append(node.module or "")
            self.assertFalse(any(name.startswith(forbidden) for name in imports))
        source=fixture.born(fixture.REGIMES[0],0)
        self.assertEqual(set(source),{"fit","check","heldout"})
        self.assertEqual(len(source["fit"]),24)
    def test_no_private_secret_oracle_or_extra_observation_in_input(self):
        d=fixture.born(fixture.REGIMES[0],0)
        bad=copy.deepcopy(d["fit"])
        bad[0]["events"][0]["secret_law"]="no"
        with self.assertRaises(ValueError):shared.fit(bad,fixture.REGIMES[0])
        altered=copy.deepcopy(d["fit"])
        altered[0]["events"].pop()
        with self.assertRaises(ValueError):control.train(altered,fixture.REGIMES[0])
    def test_native_comparator_evidence_naturally_marked_not_science(self):
        for arm in trial.ARMS:
            row=trial.test(fixture.REGIMES[0],0,arm)
            self.assertEqual(row["FIT_episodes"],24)
            self.assertFalse(row["science_accepted"])
            self.assertFalse(row["original_source_ids_924_to_937_read"])
            self.assertTrue(row["synthetic_known_parity_basis_given_to_both_parity_arms"])
            self.assertEqual(row["heldout_episodes"],8)
            self.assertEqual(row["CHECK_veto_only_episodes"],8)

if __name__=="__main__":unittest.main()
