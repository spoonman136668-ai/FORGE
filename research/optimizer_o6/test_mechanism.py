"""O6 exact-source developmental tests; NOT actual scientific held-out transfer."""
import hashlib
import math
import unittest

from public_source import (
    FAMILIES, ROLES, ROLE_COUNTS, STEPS, ReservedSourceRole,
    seed, public_episode, role_episodes, source_digest,
)
from innovation_gated import InnovationGatedBelief
from o5_frozen_online import OnlineLocalBelief
from o4_frozen_controls import PublicActionHMM, PublicHistoryCounts, score
from runner import ARMS, validate_protocol, fitted


class O6PublicMechanismTests(unittest.TestCase):
    def test_frozen_protocol_and_exact_six_arm_inventory(self):
        p = validate_protocol()
        self.assertEqual(tuple(p["arms"]), ARMS)
        self.assertEqual(p["steps_per_episode"], 24)
        self.assertEqual(p["old_negative_custody"]["Q20"], "DEV_NO_GO")

    def test_new_family_roles_public_schema_and_disjoint_hashes(self):
        for family in FAMILIES:
            digests = []
            for role in ROLES:
                eps = role_episodes(role, family)
                self.assertEqual(len(eps), ROLE_COUNTS[role])
                self.assertTrue(all(len(ep) == STEPS for ep in eps))
                for ep in eps:
                    self.assertTrue(all(len(row) == 3 and
                                        all(type(v) is int and v in (0, 1)
                                            for v in row) for row in ep))
                    self.assertTrue(all(ep[i][2] == ep[i+1][0]
                                        for i in range(STEPS-1)))
                digests.append(source_digest(eps))
            self.assertEqual(len(set(digests)), 3)

    def test_unauthorized_scientific_and_previous_dev_roles_refused(self):
        for role in ("HELD", "FIT_TRAIN", "FIT_VALID", "Q21N01_DEV",
                     "O5_PUBLIC_TRAIN", "O4_DEV", "ORIGINAL", "DEV"):
            with self.assertRaises(ReservedSourceRole):
                public_episode(role, FAMILIES[0], 0)
        for invalid in (-1, 64, True, "1", 1.5):
            with self.assertRaises(ReservedSourceRole):
                seed(ROLES[0], FAMILIES[0], invalid)
        with self.assertRaises(ReservedSourceRole):
            public_episode(ROLES[0], "O6_PROTECTED", 0)

    def test_online_gated_predicted_state_learns_from_public_only(self):
        model = InnovationGatedBelief(17)
        examples = role_episodes(ROLES[0], FAMILIES[0])[:4]
        before = model.checkpoint()
        model.fit(examples)
        self.assertNotEqual(before, model.checkpoint())
        self.assertEqual(model.updates, 4*STEPS)
        self.assertEqual(len(model.predict(examples[0])), STEPS)
        self.assertTrue(all(0 < p < 1 and math.isfinite(p)
                            for p in model.predict(examples[0])))

    def test_gate_changes_updates_without_updating_evaluation_state(self):
        examples = role_episodes(ROLES[0], FAMILIES[1])[:4]
        gated, plain = InnovationGatedBelief(17), OnlineLocalBelief(17)
        gated.fit(examples)
        plain.fit(examples)
        self.assertEqual(gated.updates, plain.updates)
        self.assertNotEqual(gated.checkpoint(), plain.checkpoint())
        self.assertNotEqual(gated.flip, plain.flip)
        frozen = gated.checkpoint()
        _ = gated.predict(examples[0])
        self.assertEqual(gated.checkpoint(), frozen)

    def test_explicit_frozen_transition_ablation(self):
        examples = role_episodes(ROLES[0], FAMILIES[0])[:4]
        model = InnovationGatedBelief(31, train_transition=False)
        initial_flip = list(model.flip)
        model.fit(examples)
        self.assertEqual(initial_flip, model.flip)
        self.assertNotEqual(model.emission, InnovationGatedBelief(31, False).emission)
        self.assertEqual(model.updates, 4*STEPS)

    def test_all_six_models_actually_fit_same_public_examples(self):
        train = role_episodes(ROLES[0], FAMILIES[1])[:3]
        select = role_episodes(ROLES[1], FAMILIES[1])[:2]
        dev = role_episodes(ROLES[2], FAMILIES[1])[:2]
        for arm in ARMS:
            model, selection = fitted(arm, train, select)
            self.assertGreater(model.updates, 0)
            self.assertTrue(math.isfinite(selection["public_select_nll"]))
            before = model.checkpoint()
            self.assertTrue(math.isfinite(score(model, dev)))
            self.assertEqual(model.checkpoint(), before)

    def test_invalid_public_input_refused_before_state_mutation(self):
        model = InnovationGatedBelief(17)
        starting = model.checkpoint()
        invalid = (
            ((0, 1, 1, "hidden"),) * 24,
            ((0, 1, True),) * 24,
            ((0, 1, 1),) * 23,
        )
        for example in invalid:
            with self.subTest(example=example[0]), self.assertRaises(ValueError):
                model.fit((example,))
            self.assertEqual(model.checkpoint(), starting)

    def test_source_determinism_and_distinct_families(self):
        a = public_episode(ROLES[0], FAMILIES[0], 0)
        b = public_episode(ROLES[0], FAMILIES[1], 0)
        self.assertEqual(a, public_episode(ROLES[0], FAMILIES[0], 0))
        self.assertNotEqual(source_digest(a), source_digest(b))


if __name__ == "__main__":
    unittest.main()
