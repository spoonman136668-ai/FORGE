"""F124-CZ sourcefree out-of-affine engineering and fairness acceptance.

No new science, hidden original, or protected source. These assertions
qualify mechanistic correctness, not positive scientific transfer. Real
holdout successes/failures are retained by whole-OS runner without filter.
"""
from __future__ import annotations
import ast
import copy
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import f124cz_outofclass_fixture as fixture
import f124cy_shared_causal_composition as old
import f124cz_shared_quadratic_model as shared
import f124cz_independent_pooled_control as peer
import f124cz_edge_quadratic_control as edge
import f124cz_outofclass_trial as trial

class OutsideOldOperatorClass(unittest.TestCase):
    def test_independent_source_only_new_families_and_no_reused_cases(self):
        self.assertEqual(fixture.REGIMES,("nonlinear_cross_role_quadratic",
                         "modular_carry_composition"))
        self.assertEqual(fixture.SEEDS,(41,42,43,44))
        self.assertEqual(shared.WIDTH,peer.SIZE==211 and 211)
        self.assertEqual(shared.PAIRS,peer.ORDER)
        self.assertEqual(len(shared.PAIRS),190)
        for regime in fixture.REGIMES:
            for seed in fixture.SEEDS:
                source=fixture.born(regime,seed)
                self.assertEqual(set(source),{"FIT","CHECK","HELDOUT"})
                self.assertEqual((len(source["FIT"]),len(source["CHECK"]),
                                  len(source["HELDOUT"])),(24,8,8))
                for ep in source["FIT"]+source["CHECK"]+source["HELDOUT"]:
                    shared.validate(ep);peer.check_episode(ep)
                self.assertEqual(fixture.born(regime,seed),source)
    def test_shared_and_fully_trained_independent_pooled_control_use_exact_same_basis(self):
        for seed in fixture.SEEDS:
            episodes=fixture.born(fixture.REGIMES[0],seed)
            model,receipt=shared.fit(episodes["FIT"])
            independent,other=peer.train(episodes["FIT"])
            self.assertIsNotNone(model,receipt)
            self.assertIsNotNone(independent,other)
            self.assertEqual(receipt["FIT_bit_errors"],0)
            self.assertEqual(other["FIT_bit_errors"],0)
            self.assertEqual(model["weights"],independent["masks"])
    def test_independent_directed_edge_gets_every_public_training_row(self):
        fit=fixture.born(fixture.REGIMES[0],41)["FIT"]
        model,receipt=edge.fit(fit)
        self.assertIsNotNone(model,receipt)
        self.assertEqual(receipt["FIT_rows"],192)
        self.assertEqual(receipt["directed_source_target_programs"],6)
    def test_non_affine_source_must_have_nonzero_second_derivative(self):
        # Cross-source conjunction x_i & x_j proves the authored quadratic
        # synthetic class is not representable by an affine 21-bit map.
        for seed in fixture.SEEDS:
            rng=__import__("random").Random(
                  17102201+seed*997+0*91273)
            hidden=fixture.quadratic_parameters(rng)
            diff=0
            for bit in range(4):
                for i,j in hidden[bit][1]:
                    baseline=[2,4,7,3,1]
                    value=0
                    for m in range(4):
                        x=baseline.copy()
                        if m&1:x[i//4]^=1<<(i%4)
                        if m&2:x[j//4]^=1<<(j%4)
                        value^=fixture.value(fixture.REGIMES[0],*x,hidden)
                    diff|=value
            self.assertNotEqual(diff,0,(seed,"source unexpectedly affine"))
    def test_check_and_heldout_no_teacher_forcing(self):
        public=fixture.born(fixture.REGIMES[0],41)
        for model_fitter,fn in ((shared.fit,shared.predict),(peer.train,peer.trajectory)):
            model,_=model_fitter(public["FIT"])
            ep=public["HELDOUT"][0]
            flipped=copy.deepcopy(ep)
            for event in flipped["events"]:event["observed"]^=15
            self.assertEqual(fn(model,ep),fn(model,flipped))
    def test_source_generator_absent_in_both_nonlinear_fitters(self):
        for path in ("f124cz_shared_quadratic_model.py",
                     "f124cz_independent_pooled_control.py",
                     "f124cz_edge_quadratic_control.py"):
            tree=ast.parse((HERE/path).read_text())
            imports=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):imports.extend(x.name for x in node.names)
                elif isinstance(node,ast.ImportFrom):imports.append(node.module or "")
            self.assertNotIn("f124cz_outofclass_fixture",imports)
            self.assertFalse(any(x.startswith(("f124cu_","f124cr_","f124co_"))
                              for x in imports))
    def test_frozen_prior_and_strong_peer_use_same_public_inputs(self):
        regime=fixture.REGIMES[0]
        outcomes=[trial.original(regime,41,arm) for arm in trial.ARMS]
        for field in ("FIT_public_SHA256","CHECK_veto_public_SHA256",
                      "HELDOUT_public_SHA256"):
            self.assertEqual(len({q[field] for q in outcomes}),1)
        for q in outcomes:
            self.assertFalse(q["science_accepted"])
            self.assertFalse(q["no_old_924_through_937_original_sci_sources_used"] is False)
            self.assertEqual(q["FIT_complete_episodes"],24)
            self.assertEqual(q["HELDOUT_public_SHA256"],outcomes[0]["HELDOUT_public_SHA256"])
    def test_original_affine_receives_no_hidden_new_quadratic_basis(self):
        fit=fixture.born(fixture.REGIMES[0],41)["FIT"]
        _,receipt=old.fit(fit,"ungated_shared_linear_GF2")
        self.assertEqual(receipt["FIT_rows"],192)
        self.assertIn("FIT_inconsistent",receipt)

if __name__=="__main__":unittest.main()
