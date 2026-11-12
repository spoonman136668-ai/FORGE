"""Adversarial source-only O4 tests: no protected roles, no hidden-state labels."""
from __future__ import annotations
import math
import unittest

from public_source import (
    FAMILIES, ROLES, COUNTS, STEPS, PublicRoleRefused,
    public_seed, episode, dataset, digest,
)
from models import (
    ARMS, PublicActionHMM, PublicRecurrent, PublicHistoryCounts,
    fit_select, loss, score,
)
from runner import verify_protocol


class TestO4PublicDevelopment(unittest.TestCase):
    def test_frozen_protocol_and_preregistered_exact_model_inventory(self):
        protocol = verify_protocol()
        self.assertEqual(tuple(protocol["arms"]), ARMS)
        self.assertEqual(protocol["role_episodes_per_family"], COUNTS)
        self.assertEqual(protocol["predecessors"]["Q20"], "DEV_NO_GO_RETAIN")

    def test_role_disjointness_and_public_episodes(self):
        for family in FAMILIES:
            role_digests = []
            for role in ROLES:
                examples = dataset(role, family)
                self.assertEqual(len(examples), COUNTS[role])
                self.assertEqual(len(examples[0]), STEPS)
                for ep in examples:
                    self.assertTrue(all(type(bit) is int and bit in (0, 1)
                                        for row in ep for bit in row))
                    self.assertTrue(all(ep[t][2] == ep[t+1][0]
                                        for t in range(STEPS-1)))
                role_digests.append(digest(examples))
            self.assertEqual(len(set(role_digests)), 3)

    def test_protected_roles_unknown_families_and_invalid_indices_denied(self):
        for invalid in ("FIT_TRAIN", "FIT_VALID", "DEV", "HELD",
                        "ORIGINAL", "Q20_DEV", "Q21N01_FIT_VALID"):
            with self.assertRaises(PublicRoleRefused):
                episode(invalid, FAMILIES[0], 0)
        for invalid in (-1, COUNTS["O4_TRAIN"], True, 1.0):
            with self.assertRaises(PublicRoleRefused):
                public_seed("O4_TRAIN", FAMILIES[0], invalid)
        with self.assertRaises(PublicRoleRefused):
            episode("O4_TRAIN", "HIDDEN_FAMILY", 0)

    def test_recurrent_same_capacity_public_optimization_updates(self):
        ep = dataset("O4_TRAIN", FAMILIES[0])[:2]
        for name in ARMS[:3]:
            m = PublicRecurrent(name, 17)
            initial = m.checkpoint()
            m.fit(ep)
            self.assertNotEqual(initial, m.checkpoint())
            self.assertEqual(m.updates, m.epochs * len(ep))
            self.assertTrue(all(0 < p < 1 and math.isfinite(p)
                                for p in m.predict(ep[0])))
        a = PublicRecurrent("RNN_TANH_SGD_16E", 17)
        b = PublicRecurrent("RNN_TANH_ADAM_16E", 17)
        self.assertEqual(sum(len(row) for row in a.w)+len(a.v),
                         sum(len(row) for row in b.w)+len(b.v))
        a.fit(ep)
        b.fit(ep)
        self.assertEqual(a.updates, b.updates)
        self.assertNotEqual(a.checkpoint(), b.checkpoint())

    def test_unsupervised_action_hmm_fits_only_public_sequences(self):
        eps = dataset("O4_TRAIN", FAMILIES[1])[:4]
        m = PublicActionHMM(17)
        baseline = m.checkpoint()
        m.fit(eps, iterations=3)
        self.assertNotEqual(baseline, m.checkpoint())
        self.assertEqual(m.updates, 3)
        self.assertEqual(len(m.predict(eps[0])), STEPS)
        self.assertTrue(all(0 < p < 1 for p in m.predict(eps[0])))
        self.assertTrue(math.isfinite(score(m, eps)))

    def test_public_counts_fit_identical_observation_history(self):
        eps = dataset("O4_TRAIN", FAMILIES[0])[:3]
        for lag in (False, True):
            model = PublicHistoryCounts(lag)
            model.fit(eps)
            self.assertEqual(model.updates, 3*STEPS)
            self.assertTrue(math.isfinite(score(model, eps)))
            self.assertGreater(len(model.table), 0)

    def test_public_selection_is_fitted_and_dev_has_no_updates(self):
        train = dataset("O4_TRAIN", FAMILIES[1])[:3]
        select = dataset("O4_SELECT", FAMILIES[1])[:2]
        dev = dataset("O4_DEV", FAMILIES[1])[:2]
        for arm in ARMS:
            model, receipt = fit_select(arm, train, select)
            self.assertTrue(math.isfinite(receipt["selection_nll"]))
            self.assertGreater(model.updates, 0)
            frozen = model.checkpoint()
            self.assertTrue(math.isfinite(score(model, dev)))
            self.assertEqual(frozen, model.checkpoint())

    def test_public_belief_depends_on_observed_history_not_hidden_state(self):
        m = PublicActionHMM(17)
        first = ((0, 0, 0), (0, 1, 1), (1, 0, 1))
        second = ((0, 0, 1), (1, 1, 1), (1, 0, 1))
        self.assertAlmostEqual(m.predict(first)[0], m.predict(second)[0], places=12)
        self.assertNotEqual(m.predict(first)[1], m.predict(second)[1])
        self.assertTrue(math.isfinite(loss(0, 0.5)))
        with self.assertRaises(ValueError):
            loss(2, 0.5)


if __name__ == "__main__":
    unittest.main()
