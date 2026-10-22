"""Q15 source-free development contract, analytical gradient and leakage tests."""
import math
import pathlib
import unittest

import experiment as e


class SourceFreeQ15Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = e.load_frozen()

    def test_original_sources_never_imported_by_experiment(self):
        src = pathlib.Path(e.__file__).read_text(encoding="utf-8")
        for banned in ("import minigrid", "import pycolab",
                       "from minigrid", "from pycolab",
                       "import requests", "import github",
                       "import subprocess", "import socket"):
            self.assertNotIn(banned, src)

    def test_frozen_protocol_has_no_original_source_cohort(self):
        p = self.protocol
        self.assertEqual(p["generator"]["only_allowed_cohorts_in_Q15"],
                         ["train", "validation"])
        self.assertEqual(p["optimizer"]["recurrent_epochs"], 80)
        self.assertEqual(p["optimizer"]["restarts"], [0, 1, 2])
        self.assertEqual({x["name"] for x in
                          p["generator"]["protected_future_source_free_holdout_not_executed_in_Q15"]},
                         {"F_C", "F_D"})

    def test_train_and_validation_seeds_are_distinct_and_deterministic(self):
        for family in e.FAMILY_NAMES:
            train = [e.seed_for("train", family, i) for i in range(256)]
            validation = [e.seed_for("validation", family, i) for i in range(64)]
            self.assertEqual(len(set(train + validation)), 320)
            self.assertEqual(e.seed_for("train", family, 0), train[0])

    def test_unseen_held_family_never_generated(self):
        future = self.protocol["generator"][
            "protected_future_source_free_holdout_not_executed_in_Q15"]
        for family in future:
            for role in ("held", "train", "validation"):
                with self.subTest(family=family["name"], role=role):
                    with self.assertRaisesRegex(RuntimeError,
                                                "HELD_OR_ORIGINAL_GENERATION_FORBIDDEN"):
                        e.generate(role, family)

    def test_invalid_role_cannot_reinterpret_training(self):
        family = self.protocol["generator"]["training_families"][0]
        for role in ("test", "protected", "scientific", "held", ""):
            with self.subTest(role=role):
                with self.assertRaisesRegex(RuntimeError,
                                            "HELD_OR_ORIGINAL_GENERATION_FORBIDDEN"):
                    e.generate(role, family)

    def test_train_family_episode_counts_and_binary_outputs(self):
        for family in self.protocol["generator"]["training_families"]:
            eps = e.generate("train", family)
            self.assertEqual(len(eps), 256)
            for name, obs, labels in eps[:3]:
                self.assertEqual(name, family["name"])
                self.assertEqual(len(obs), family["steps"])
                self.assertEqual(len(labels), family["steps"])
                self.assertTrue(set(obs).issubset({-1, 1}))
                self.assertTrue(set(labels).issubset({0, 1}))
            self.assertEqual(e.cohort_digest(eps),
                             e.cohort_digest(e.generate("train", family)))

    def test_gradient_matches_centered_finite_differences(self):
        xs = (+1, -1, +1, +1, -1)
        ys = (1, 0, 1, 1, 0)
        for name,par in [
            ("LINEAR_PREDICTIVE_STATE", [0.31, 0.48, 0.73, -0.12]),
            ("TANH_RNN", [0.31, 0.48, 0.05, 0.73, -0.12])
        ]:
            with self.subTest(name=name):
                gradient = e.recurrent_gradient(name, par, xs, ys)
                def total(q):
                    logits = e.recurrent_forward(name, q, xs)[1]
                    return sum(e.logloss(logit, label)
                               for logit, label in zip(logits, ys))
                for idx in range(len(par)):
                    delta=1e-5
                    up=par.copy()
                    down=par.copy()
                    up[idx]+=delta
                    down[idx]-=delta
                    numeric=(total(up)-total(down))/(2*delta)
                    self.assertAlmostEqual(gradient[idx], numeric, delta=5e-6)

    def test_train_only_bayes_fit_fully_supervised(self):
        observations = [
            ("F_A", (+1,-1,+1), (1,0,1)),
            ("F_B", (-1,+1,-1), (0,1,0)),
        ]
        estimated,cost = e.train_bayes(observations)
        self.assertEqual(cost["optimizer_steps"], 1)
        self.assertEqual(estimated["noise"], 1e-4)
        self.assertTrue(0 < estimated["hazard"] < 0.5)

    def test_models_have_finite_loss_with_one_scalar_state(self):
        ep=("F_A", (+1,-1,+1,-1), (1,0,1,0))
        cases=[
            ("LINEAR_PREDICTIVE_STATE",[0.2,0.3,0.5,0.0],None),
            ("TANH_RNN",[0.2,0.3,0.0,0.5,0.0],None),
            ("TRAINED_BAYES_FILTER",[],{"noise":0.2,"hazard":0.1}),
            ("TRAINED_SYMBOLIC_MAJORITY",[0.3,0.0],None),
            ("TRAINED_CURRENT_ONLY_LOGISTIC",[0.3,0.0],None),
        ]
        for name,params,meta in cases:
            self.assertTrue(math.isfinite(e.nll_episode(name,params,ep,meta)))

    def test_candidate_cannot_report_unearned_acceptance(self):
        doc=self.protocol
        self.assertEqual(doc["gate"]["independent_held_acceptance"],
                         "NOT AUTHORIZED_IN_Q15")
        self.assertEqual(doc["context"]["known_negatives"][-1],
                         "Q14 global original reset custody NO-GO remains")
        self.assertNotIn("F_C", e.FAMILY_NAMES)
        self.assertNotIn("F_D", e.FAMILY_NAMES)


if __name__ == "__main__":
    unittest.main()
