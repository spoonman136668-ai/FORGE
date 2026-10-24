"""Development-only L10-B7 stateful world adversarial evidence.

No L9/WebNLG, no prospective sources. All training and checking records are
deterministic invented episodes, and model predictions precede current labels.
"""
from dataclasses import replace
from hashlib import sha256
from collections import Counter
import unittest

import l10_b7_changing_world_dev as world

class ChangingWorldTests(unittest.TestCase):
    def test_exact_original_dev_grid_and_deterministic_source_identity(self):
        a=[world.create_dev_episode(f,s) for f in world.FAMILIES for s in world.SPLITS]
        b=[world.create_dev_episode(f,s) for f in world.FAMILIES for s in world.SPLITS]
        self.assertEqual(a,b)
        self.assertEqual(len({x.identity for x in a}),6)
        self.assertEqual([x.hidden_switch for x in a if x.split=="CHECK"],[0,1,1])
        self.assertTrue(all(set(x.actions)==set(world.ACTIONS) for x in a))
    def test_forged_role_phase_family_or_switch_rejected(self):
        e=world.create_dev_episode(world.FAMILIES[0],"CHECK")
        for change in ({"role":"L10_PROSPECTIVE_NEW_SOURCE_FAMILY"},
                       {"start_phase":1-e.start_phase},
                       {"hidden_switch":1-e.hidden_switch},
                       {"identity":"0"*64},
                       {"family":"unseen-prospective"}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                world.validate_episode(replace(e,**change))
        with self.assertRaises(ValueError):
            world.create_dev_episode("unseen-prospective","CHECK")
    def test_nonbijective_stateful_emission_and_p2_intervention(self):
        e=world.create_dev_episode("world-phase","CHECK")
        self.assertEqual(world.EFFECT_BASE["P0"],world.EFFECT_BASE["P2"])
        self.assertEqual(world.FLIP_ACTION,"P2")
        for t in range(1,world.N):
            if e.actions[t-1]=="P2":
                self.assertEqual(world.parity_before(e.actions,t)^world.parity_before(e.actions,t-1),1)
        self.assertTrue(all(world.truth_bit(e,t) in (0,1) for t in range(world.N)))
    def test_two_intervening_actions_before_feedback(self):
        e=world.create_dev_episode("world-switch","CHECK")
        w=world.World(e,"CLEAN")
        self.assertEqual(w.deliver(),())
        w.act(0,e.actions[0])
        self.assertEqual(w.deliver(),())
        w.act(1,e.actions[1])
        self.assertEqual(w.deliver(),())
        w.act(2,e.actions[2])
        delivered=w.deliver()
        self.assertEqual(len(delivered),1)
        self.assertEqual(delivered[0].available_at,3)
        self.assertEqual(delivered[0].step,0)
        self.assertEqual(delivered[0].bit,world.truth_bit(e,0))
        self.assertNotEqual(delivered[0].action,e.actions[3]) if delivered[0].action!=e.actions[3] else None
    def test_withheld_training_no_unearned_state_inference(self):
        e=world.create_dev_episode("world-phase","FIT")
        m=world.fit(e,"WITHHELD")
        self.assertEqual(m["relative"],{})
        self.assertEqual(m["received_fit_effects"],0)
        check=world.create_dev_episode("world-phase","CHECK")
        for meth in world.METHODS:
            self.assertIsNone(world.predict(meth,m,[],check.actions,0))
        self.assertEqual(world.benchmark_family("world-phase","WITHHELD","exact-bayesian-change-point")["abstentions"],12)
    def test_fitted_relative_offsets_avoid_global_start_leakage(self):
        for f in world.FAMILIES:
            fitted=world.fit(world.create_dev_episode(f,"FIT"),"CLEAN")
            self.assertEqual(fitted["received_fit_effects"],12)
            self.assertEqual(fitted["relative"],{"P0":0,"P1":1,"P2":0})
            self.assertEqual(set(fitted["last_by_code"]),set(world.ACTIONS))
    def test_strong_bayesian_rejects_unknown_switch_without_feedback(self):
        m=world.fit(world.create_dev_episode("world-switch","FIT"),"CLEAN")
        e=world.create_dev_episode("world-switch","CHECK")
        # Before the delayed step-6 observation arrives, switch=0 and switch=1
        # remain equally possible. With post-step-3 feedback phase is resolved.
        past=world.Feedback(e.identity,0,e.actions[0],world.truth_bit(e,0),3,"0"*64)
        self.assertEqual(len(world._phase_candidates(m,[past],e.actions)),2)
        self.assertIsNone(world.predict("exact-bayesian-change-point",m,[past],e.actions,6))
        self.assertIn(world.predict("local-phase-adapter",m,[past],e.actions,6),(0,1))
    def test_bayesian_changes_posterior_only_after_legal_delayed_effect(self):
        e=world.create_dev_episode("world-interference","CHECK")
        m=world.fit(world.create_dev_episode("world-interference","FIT"),"CLEAN")
        before=world.Feedback(e.identity,0,e.actions[0],world.truth_bit(e,0),3,"0"*64)
        switch=world.Feedback(e.identity,6,e.actions[6],world.truth_bit(e,6),9,"1"*64)
        with self.assertRaises(ValueError):
            world.predict("exact-bayesian-change-point",m,[before,switch],e.actions,8)
        self.assertEqual(len(world._phase_candidates(m,[before,switch],e.actions)),1)
        self.assertEqual(world.predict("exact-bayesian-change-point",m,[before,switch],e.actions,9),
                         world.truth_bit(e,9))
    def test_model_restart_persists_public_state_only(self):
        e=world.create_dev_episode("world-phase","FIT")
        m=world.fit(e,"CLEAN")
        check=world.create_dev_episode("world-phase","CHECK")
        observation=world.Feedback(check.identity,0,check.actions[0],world.truth_bit(check,0),3,"2"*64)
        raw=world.snapshot(m,[observation])
        loaded,events=world.restore(raw)
        self.assertEqual(m,loaded)
        self.assertEqual(events,(observation,))
        for unwanted in ("hidden_switch","start_phase","world-interference"):
            self.assertNotIn(unwanted,raw.decode())
        with self.assertRaises(ValueError):
            world.restore(raw+b" ")
        with self.assertRaises(ValueError):
            world.restore(raw.replace(b'"schema":"forge.optimizer.language.l10.b7-restart-v1"',
                                     b'"schema":"wrong"'))
    def test_fit_role_boundary_and_forged_inputs(self):
        e=world.create_dev_episode("world-phase","CHECK")
        with self.assertRaises(ValueError):
            world.fit(e,"CLEAN")
        m=world.fit(world.create_dev_episode("world-phase","FIT"),"CLEAN")
        for bad in ("L10_PROSPECTIVE_NEW_SOURCE_FAMILY","AUDIT","L9_AUDIT_DEV"):
            with self.assertRaises(ValueError):
                world.fit(world.create_dev_episode("world-phase","FIT"),bad)
        with self.assertRaises(ValueError):
            world.predict("not-qualified",m,[],e.actions,3)
        with self.assertRaises(ValueError):
            world.predict("local-phase-adapter",m,[world.Feedback(e.identity,1,e.actions[1],0,4,"3"*64)],e.actions,2)
    def test_full_grid_controls_and_no_protected_scientific_go(self):
        report=world.benchmark()
        self.assertEqual(report["families"],3)
        self.assertEqual(len(report["outcomes"]),12)
        self.assertTrue(all(r["decisions"]==36 for r in report["outcomes"]))
        self.assertTrue(all(0<=r["correct"]+r["abstentions"]<=36 for r in report["outcomes"]))
        self.assertTrue(all(r["correct"]==0 and r["abstentions"]==36
                            for r in report["outcomes"] if r["regime"]=="WITHHELD"))
        self.assertFalse(report["scientific_go"])
        self.assertFalse(report["prospective_first_use_consumed"])
        self.assertFalse(report["native_causal_discovery_proven"])
        self.assertFalse(report["original_l9_webnlg_consumed"])
    def test_check_step_scores_change_point_sensitivity(self):
        for family in world.FAMILIES:
            local=world.benchmark_family(family,"CLEAN","local-phase-adapter")
            bayes=world.benchmark_family(family,"CLEAN","exact-bayesian-change-point")
            self.assertTrue(local["recovered_model_state"])
            self.assertTrue(bayes["recovered_model_state"])
            self.assertEqual(local["simulated_restarts"],1)
            self.assertEqual(bayes["simulated_restarts"],1)
            self.assertLessEqual(bayes["abstentions"],12)
            self.assertEqual(local["first_interference_feedback_tick"],
                             bayes["first_interference_feedback_tick"])
            self.assertEqual(local["first_interference_feedback_tick"],9)
    def test_corrupted_sensor_causes_factual_risk_not_gain(self):
        m=world.benchmark_family("world-interference","INVERTED_FEEDBACK","local-phase-adapter")
        good=world.benchmark_family("world-interference","CLEAN","local-phase-adapter")
        self.assertNotEqual(m["fitted_state_sha256"],good["fitted_state_sha256"])
        self.assertTrue(m["correct"]<=12 and good["correct"]<=12)
        self.assertTrue(m["fit_state_bytes"]>0)
if __name__=="__main__":
    unittest.main()
