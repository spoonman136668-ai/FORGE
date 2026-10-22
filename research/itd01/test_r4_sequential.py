"""ITD-01 R4 adversarial public-only active learning interface checks."""
import hashlib
import unittest

from public_dev import PUBLIC_FAMILIES, canonical
from r4_public_experience import (N_INPUT, public_training,
                                  sample_trajectory, PublicTranscript,
                                  rollout, eval_agent)
from r4_sequential_controls import (RecurrentPolicy,
                                    PredictiveTransitionPlanner,
                                    ExplicitTrajectoryMemory,
                                    model_sha, model_bytes)
from run_r4_sequential import experiment


class SequentialDEV(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.episodes,cls.birth=public_training(17,8)

    def test_training_only_public_features_and_actions(self):
        self.assertEqual(len(self.episodes),16)
        self.assertEqual(len(self.birth),64)
        self.assertTrue(self.episodes)
        for tr in self.episodes:
            self.assertTrue(tr)
            self.assertEqual(tr[-1]["y"],9)
            for row in tr:
                self.assertEqual(set(row),{"x","key","y"})
                self.assertEqual(len(row["x"]),N_INPUT)
                self.assertTrue(0<=row["y"]<10)
                self.assertEqual(len(row["key"]),6)
                self.assertNotIn("hidden",canonical(row).decode())

    def test_teacher_uses_public_reset_once_and_repeatable(self):
        for family in PUBLIC_FAMILIES:
            a=sample_trajectory(family,"DEV-R4-REPLAY",8121)
            b=sample_trajectory(family,"DEV-R4-REPLAY",8121)
            self.assertEqual(a,b)
            self.assertGreater(len(a["rows"]),4)
            self.assertLessEqual(len(a["rows"]),40)

    def test_recurrent_bptt_learns_and_keeps_8_scalar_state(self):
        model=RecurrentPolicy(17)
        before=model_sha(model)
        model.train(self.episodes,epochs=2)
        self.assertGreater(model.updates,0)
        self.assertNotEqual(before,model_sha(model))
        self.assertEqual(len(model.init_state()),8)
        self.assertLess(model_bytes(model),33554432)

    def test_predictive_transition_model_actually_fits_delay(self):
        actor=PredictiveTransitionPlanner()
        self.assertEqual(actor.updates,0)
        actor.train(self.episodes)
        self.assertGreater(actor.updates,0)
        self.assertEqual(actor.delay_fit[0],2)
        self.assertEqual(actor.delay_fit[1],3)
        self.assertGreater(actor.partial_counts[1],0)

    def test_memory_trains_from_public_sequential_decisions(self):
        actor=ExplicitTrajectoryMemory()
        actor.train(self.episodes)
        self.assertEqual(actor.updates,sum(map(len,self.episodes)))
        self.assertTrue(actor.counts)
        self.assertGreater(model_bytes(actor),100)
        self.assertLess(model_bytes(actor),33554432)

    def test_planner_solves_new_public_causal_development_worlds(self):
        model=PredictiveTransitionPlanner()
        model.train(self.episodes)
        first_sha=model_sha(model)
        for family in PUBLIC_FAMILIES:
            for seed in (31,71,73,79):
                result=rollout(model,family,79900+seed,
                               "DEV-R4-PLANNER-"+str(seed))
                self.assertTrue(result["legal"])
                self.assertTrue(result["reward"],(family,seed,result))
                self.assertLessEqual(result["steps"],40)
        self.assertEqual(model_sha(model),first_sha)

    def test_three_separate_model_classes_train_and_score(self):
        for constructor in (lambda:RecurrentPolicy(17),
                            PredictiveTransitionPlanner,ExplicitTrajectoryMemory):
            actor=constructor()
            actor.train(self.episodes)
            saved=model_sha(actor)
            scored=eval_agent(actor,17,3,"normal","validation")
            self.assertEqual(set(scored),set(PUBLIC_FAMILIES))
            for fam in PUBLIC_FAMILIES:
                self.assertEqual(scored[fam]["n"],3)
                self.assertTrue(0<=scored[fam]["success"]<=1)
            self.assertEqual(saved,model_sha(actor))

    def test_history_erase_and_event_blind_keep_public_boundary(self):
        actor=PredictiveTransitionPlanner()
        actor.train(self.episodes)
        for mode in ("normal","erase","blind_delayed"):
            scored=eval_agent(actor,17,2,mode,"challenge")
            self.assertEqual(sum(x["n"] for x in scored.values()),4)

    def test_public_dev_smoke_resource_receipt_and_no_first_use(self):
        report=experiment(17,4,2,2,False)
        self.assertFalse(report["scientific_first_use"])
        self.assertFalse(report["protected_H1_H2_born_or_used"])
        self.assertEqual(report["authority"],"NONE_DEV_ONLY")
        self.assertEqual(len(report["models"]),3)
        self.assertEqual(report["native_wingless_or_yggdrasil_transfer"],"NOT_TESTED")
        self.assertGreater(report["process_cpu_seconds_environment_included"],0)
        for model in report["models"]:
            self.assertGreater(model["training_updates"],0)
            self.assertGreater(model["model_bytes"],0)
            self.assertEqual(len(model["frozen_model_sha256"]),64)


if __name__=="__main__":
    unittest.main()
