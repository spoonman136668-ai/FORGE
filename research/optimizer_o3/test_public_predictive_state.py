"""Strict public-only O3 source, training, separation and negative controls."""
import hashlib
import math
import unittest

from public_source import (
    FAMILIES, ROLES, ROLE_COUNTS, STEPS, RoleRefused, canonical,
    public_episode, role_digest, role_episodes, seed_for,
)
from learners import FittedRecurrent, PublicCountControl, fit_models, score


class TestO3PublicPredictiveState(unittest.TestCase):
    def test_public_source_only_and_exact_role_splits(self):
        for family in FAMILIES:
            seen = []
            for role in ROLES:
                rows = role_episodes(role, family)
                self.assertEqual(len(rows), ROLE_COUNTS[role])
                self.assertEqual(len(rows[0]), STEPS)
                self.assertTrue(all(len(p) == 3 and
                                    all(type(bit) is int and bit in (0, 1)
                                        for bit in p)
                                    for ep in rows for p in ep))
                self.assertTrue(all(ep[t][2] == ep[t+1][0]
                                    for ep in rows for t in range(STEPS-1)))
                seen.append(role_digest(role, family, rows))
            self.assertEqual(len(set(seen)), 3)

    def test_no_protected_roles_or_future_privileged_source(self):
        for role in ("FIT_TRAIN", "FIT_VALID", "DEV", "HELD", "ORIGINAL",
                     "Q21N01_FIT_TRAIN", "Q20_HELD"):
            with self.assertRaises(RoleRefused):
                public_episode(role, FAMILIES[0], 0)
        for bad_index in (-1, 48, True, "1"):
            with self.assertRaises(RoleRefused):
                seed_for("PUBLIC_TRAIN", FAMILIES[0], bad_index)
        with self.assertRaises(RoleRefused):
            public_episode("PUBLIC_TRAIN", "UNKNOWN_FAMILY", 0)

    def test_causal_action_contrast_and_null_properties_are_public(self):
        for family in FAMILIES:
            rows = role_episodes("PUBLIC_TRAIN", family)
            action_values = {a for e in rows for _, a, _ in e}
            targets = {next_obs for e in rows for _, _, next_obs in e}
            self.assertEqual(action_values, {0, 1})
            self.assertEqual(targets, {0, 1})
        a = public_episode("PUBLIC_TRAIN", FAMILIES[0], 0)
        self.assertEqual(a, public_episode("PUBLIC_TRAIN", FAMILIES[0], 0))

    def test_recurrent_state_actually_updates_after_public_training(self):
        episodes = role_episodes("PUBLIC_TRAIN", FAMILIES[0])[:4]
        for kind in ("ONE_BELIEF_SIGMOID_RTRL", "TWO_STATE_TANH_RTRL"):
            m = FittedRecurrent(kind, 17)
            before = m.checkpoint()
            m.train(episodes)
            self.assertNotEqual(before, m.checkpoint())
            self.assertEqual(m.updates, 5 * len(episodes))
            predictions = m.predict_episode(episodes[0])
            self.assertEqual(len(predictions), STEPS)
            self.assertTrue(all(math.isfinite(p) and 0 < p < 1
                                for p in predictions))

    def test_controls_all_actually_fit_same_public_examples(self):
        train = role_episodes("PUBLIC_TRAIN", FAMILIES[1])[:4]
        selection = role_episodes("PUBLIC_SELECT", FAMILIES[1])[:3]
        fitted = fit_models(train, selection)
        self.assertEqual(set(fitted), {
            "ONE_BELIEF_SIGMOID_RTRL", "TWO_STATE_TANH_RTRL",
            "FOUR_LAG_BAYES_COUNTS", "EXACT_CONTEXT_EPISODIC",
            "CURRENT_ONLY_COUNTS",
        })
        for model, meta in fitted.values():
            self.assertTrue(math.isfinite(meta["public_select_nll"]))
            self.assertGreater(model.updates, 0)
            self.assertGreater(len(model.checkpoint()), 0)
        self.assertEqual(fitted["ONE_BELIEF_SIGMOID_RTRL"][0].updates,
                         5 * len(train))

    def test_no_public_dev_update_or_hidden_label_adaptation(self):
        train = role_episodes("PUBLIC_TRAIN", FAMILIES[0])[:3]
        select = role_episodes("PUBLIC_SELECT", FAMILIES[0])[:2]
        dev = role_episodes("PUBLIC_DEV", FAMILIES[0])[:2]
        fitted = fit_models(train, select)
        for model, _ in fitted.values():
            before = model.checkpoint()
            loss = score(model, dev)
            self.assertTrue(math.isfinite(loss))
            self.assertEqual(before, model.checkpoint())

    def test_tiny_direct_controls_do_not_require_hidden_state(self):
        current = PublicCountControl("CURRENT_ONLY_COUNTS")
        lagged = PublicCountControl("FOUR_LAG_BAYES_COUNTS")
        episodes = (((0, 1, 1), (1, 1, 1), (1, 0, 0)),)
        current.train(episodes)
        lagged.train(episodes)
        self.assertTrue(math.isfinite(score(current, episodes)))
        self.assertTrue(math.isfinite(score(lagged, episodes)))
        self.assertNotEqual(hashlib.sha256(current.checkpoint()).digest(),
                            hashlib.sha256(lagged.checkpoint()).digest())


if __name__ == "__main__":
    unittest.main()
