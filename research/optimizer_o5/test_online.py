"""O5: bounded, independent source-only engineering assertions."""
import hashlib
import math
from pathlib import Path
import unittest

from public_source import (
    FAMILIES, ROLES, ROLE_COUNTS, STEPS, ForbiddenRole,
    seed, episode, role_episodes, digest,
)
from online_local import OnlineLocalBelief
from o4_frozen_controls import PublicActionHMM, PublicHistoryCounts, score
from public_dev import ARMS, fit_arm, frozen


class O5Qualification(unittest.TestCase):
    def test_frozen_protocol_and_control_inventory(self):
        p = frozen()
        self.assertEqual(tuple(p["arms"]), ARMS)
        self.assertEqual(p["episode_steps"], STEPS)
        self.assertEqual(p["predecessor_O4"]["disposition"],
                         "PUBLIC_DEV_HMM_BETTER_BY_SMALL_NLL_MARGIN_COST_UNMATCHED_NO_SCIENTIFIC_GO")

    def test_roles_disjoint_and_public_action_observation_only(self):
        for family in FAMILIES:
            seen = []
            for role in ROLES:
                rows = role_episodes(role, family)
                self.assertEqual(len(rows), ROLE_COUNTS[role])
                self.assertTrue(all(len(ep) == STEPS for ep in rows))
                self.assertTrue(all(all(type(bit) is int and bit in (0, 1)
                                        for bit in row)
                                    for ep in rows for row in ep))
                self.assertTrue(all(ep[k][2] == ep[k+1][0]
                                    for ep in rows for k in range(STEPS-1)))
                seen.append(digest(rows))
            self.assertEqual(len(set(seen)), 3)
            self.assertEqual(seed(ROLES[0], family, 0),
                             seed(ROLES[0], family, 0))

    def test_reserved_old_and_protected_roles_blocked(self):
        for role in ("DEV", "HELD", "ORIGINAL", "Q21_DEV",
                     "Q21N01_FIT_TRAIN", "Q20_FIT", "O4_TRAIN"):
            with self.assertRaises(ForbiddenRole):
                episode(role, FAMILIES[0], 0)
        for index in (-1, 64, True, 1.5, "1"):
            with self.assertRaises(ForbiddenRole):
                seed(ROLES[0], FAMILIES[0], index)
        with self.assertRaises(ForbiddenRole):
            episode(ROLES[0], "A_LEAKED_PRIVATE_FAMILY", 0)

    def test_online_state_learns_only_public_experience(self):
        train = role_episodes(ROLES[0], FAMILIES[0])[:4]
        model = OnlineLocalBelief(17)
        initial = model.checkpoint()
        model.fit(train)
        self.assertNotEqual(initial, model.checkpoint())
        self.assertEqual(model.updates, STEPS*len(train))
        self.assertEqual(len(model.predict(train[0])), STEPS)
        self.assertTrue(all(0 < p < 1 for p in model.predict(train[0])))

    def test_frozen_transition_ablation_learning_is_controlled(self):
        train = role_episodes(ROLES[0], FAMILIES[1])[:4]
        active = OnlineLocalBelief(17, True)
        ablated = OnlineLocalBelief(17, False)
        unchanged = ablated.flip[:]
        active.fit(train)
        ablated.fit(train)
        self.assertEqual(ablated.flip, unchanged)
        self.assertNotEqual(active.flip, unchanged)
        self.assertEqual(active.updates, ablated.updates)
        self.assertNotEqual(active.checkpoint(), ablated.checkpoint())

    def test_same_public_data_fits_original_o4_comparators(self):
        train = role_episodes(ROLES[0], FAMILIES[0])[:3]
        select = role_episodes(ROLES[1], FAMILIES[0])[:2]
        for name in ARMS:
            model, receipt = fit_arm(name, train, select)
            self.assertGreater(model.updates, 0)
            self.assertTrue(math.isfinite(receipt["selection_nll"]))
            self.assertGreater(len(model.checkpoint()), 0)
            self.assertEqual(model.checkpoint(), model.checkpoint())

    def test_no_dev_learning_or_privileged_model_inputs(self):
        train = role_episodes(ROLES[0], FAMILIES[1])[:3]
        valid = role_episodes(ROLES[1], FAMILIES[1])[:2]
        dev = role_episodes(ROLES[2], FAMILIES[1])[:2]
        for name in ARMS:
            model, _ = fit_arm(name, train, valid)
            before = model.checkpoint()
            self.assertTrue(math.isfinite(score(model, dev)))
            self.assertEqual(before, model.checkpoint())
        malformed = list(dev[0])
        malformed[0] = (0, 0, 1, "hidden_state")
        own = OnlineLocalBelief(17)
        before = own.checkpoint()
        with self.assertRaises(ValueError):
            own.fit((tuple(malformed),))
        self.assertEqual(before, own.checkpoint())

    def test_filter_retains_observation_dependence_without_future_leak(self):
        m = OnlineLocalBelief(17)
        first = ((0, 1, 0),)*24
        second = ((0, 1, 1),)*24
        # Repeated patterns do not satisfy the episode chaining invariant,
        # so assemble two valid public sequences instead.
        ea = tuple([(0, 1, 0)]*24)
        eb = tuple([(0, 1, 1)] + [(1, 1, 1)]*23)
        pa, pb = m.predict(ea), m.predict(eb)
        self.assertAlmostEqual(pa[0], pb[0], places=12)
        self.assertNotEqual(pa[1], pb[1])
        self.assertEqual(m.updates, 0)

    def test_online_training_deterministic_and_no_role_rebirth(self):
        ep = role_episodes(ROLES[0], FAMILIES[0])[:4]
        a, b = OnlineLocalBelief(31), OnlineLocalBelief(31)
        a.fit(ep)
        b.fit(ep)
        self.assertEqual(a.checkpoint(), b.checkpoint())
        self.assertNotEqual(hashlib.sha256(a.checkpoint()).hexdigest(),
                            hashlib.sha256(OnlineLocalBelief(31).checkpoint()).hexdigest())


if __name__ == "__main__":
    unittest.main()
