"""Q21 adversarial source-only tests. No Q21 cohorts or real science executed."""
import hashlib
import math
import pathlib
import unittest
from unittest import mock

import sourcefree as q


class Q21Prequalification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = q.protocol()
        cls.family = q.FAMILIES[0]
        cls.toy = q.public_episode(cls.family,
            [(0, 0), (0, 1), (1, 1), (1, 0)], [0, 1, 0])

    def test_exact_frozen_protocol(self):
        raw = (q.HERE / "FROZEN_PROTOCOL.json").read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        self.assertEqual(blob, q.PROTOCOL_BLOB)
        self.assertEqual(self.doc["schema"], q.SCHEMA)
        self.assertEqual(self.doc["state"], "FROZEN_DESIGN_ONLY_NOT_EXECUTED")

    def test_preflight_does_not_generate_q21_development_episodes(self):
        with mock.patch.object(q, "generate", side_effect=AssertionError("Q21_EARLY_DATA")):
            result = q.preflight()
        self.assertEqual(result["sourcefree_q21_development_cohorts_generated"], 0)
        self.assertEqual(result["full_Q21_dev_and_scientific_qualification"], "NOT_RUN")

    def test_protected_roles_are_denied_even_if_named(self):
        for role in ("HELD_NEW_SENSOR_FAMILY", "HELD_LONG_HORIZON_TRANSFER",
                     "held", "original", "scientific", "", "fit", "dev"):
            with self.subTest(role=role):
                with self.assertRaisesRegex(ValueError, "UNKNOWN_OR_PROTECTED_ROLE"):
                    q.initial_seed(role, self.family, 0)

    def test_frozen_seed_rule_is_role_and_episode_disjoint(self):
        seeds = set()
        for role in sorted(q.ROLES):
            for family in q.FAMILIES:
                for idx in (0, 1, q.ROLE_COUNTS[role]-1):
                    seed = q.initial_seed(role, family, idx)
                    self.assertNotIn(seed, seeds)
                    seeds.add(seed)
                    self.assertEqual(seed, q.initial_seed(role, family, idx))
        with self.assertRaisesRegex(ValueError, "EPISODE_INDEX_OUTSIDE_FROZEN_ROLE"):
            q.initial_seed("DEV", self.family, q.ROLE_COUNTS["DEV"])

    def test_public_contract_rejects_private_oracle_metadata(self):
        with self.assertRaisesRegex(ValueError, "PRIVATE_FIELDS_IN_EMPIRICAL_ROWS"):
            q.public_rows([(self.toy[0], self.toy[1], self.toy[2],
                            {"responsive_slot": 0})])
        with self.assertRaisesRegex(ValueError, "INVALID_PUBLIC_ACTION"):
            q.public_episode(self.family, [(0,0), (1,1)], [2])
        with self.assertRaisesRegex(ValueError, "ACTION_OBSERVATION_MISMATCH"):
            q.public_episode(self.family, [(0,0)], [0])

    def test_all_models_observe_only_present_and_past(self):
        self.assertEqual(q.context(self.toy, 0, False), (0, 0, 0))
        self.assertEqual(q.context(self.toy, 0, True), (0, 0, 0, 4))
        self.assertEqual(q.context(self.toy, 1, True), (1, 1, 0, 0))
        with self.assertRaisesRegex(ValueError, "FUTURE_OR_INVALID_TIME_INDEX"):
            q.context(self.toy, len(self.toy[2]), True)

    def test_fitted_current_history_controls_are_distinct(self):
        current = q.fit_counts([self.toy], False)
        history = q.fit_counts([self.toy], True)
        self.assertTrue(all(len(values) == 4 for values in current.values()))
        self.assertTrue(all(len(values) == 4 for values in history.values()))
        for table in (current, history):
            for values in table.values():
                self.assertAlmostEqual(sum(values), 1.0, places=13)
        for table, use_history in ((current, False), (history, True)):
            preds = q.forecast_counts(table, self.toy, use_history)
            self.assertEqual(len(preds), 3)
            self.assertTrue(all(0 < p < 1 for pair in preds for p in pair))

    def test_public_marginalized_oracle_is_swap_equivariant(self):
        changed = q.public_episode(self.family,
            [(b,a) for a,b in self.toy[1]], list(self.toy[2]))
        x = q.marginalized_public_oracle(self.toy, self.doc)
        y = q.marginalized_public_oracle(changed, self.doc)
        for left, right in zip(x, y):
            self.assertAlmostEqual(left[0], right[1], places=12)
            self.assertAlmostEqual(left[1], right[0], places=12)

    def test_oracle_is_not_provided_episode_responsive_identity(self):
        row = self.toy
        oracle = q.marginalized_public_oracle(row, self.doc)
        self.assertEqual(len(oracle), 3)
        self.assertTrue(all(math.isfinite(p) and 0 < p < 1
                            for pair in oracle for p in pair))
        self.assertTrue(math.isfinite(q.nll(row, oracle)))
        self.assertTrue(self.doc["frozen_dev_decision"]["do_not_treat_oracle_as_equal_information_control"])

    def test_invalid_forecast_rejected(self):
        with self.assertRaisesRegex(ValueError, "FORECAST_NONFINITE"):
            q.nll(self.toy, [(math.nan, .5)]*3)
        with self.assertRaisesRegex(ValueError, "FORECAST_COUNT_DRIFT"):
            q.nll(self.toy, [(.5,.5)])

    def test_no_original_source_or_runner_control_imports(self):
        source = pathlib.Path(q.__file__).read_text().lower()
        for term in ("import minigrid", "import pycolab", "import subprocess",
                     "import requests", "import socket", "import github",
                     "import ckb", "dispatch", "tradeguard"):
            with self.subTest(term=term):
                self.assertNotIn(term, source)

    def test_source_only_no_model_promotion_or_cohort_training(self):
        result = q.preflight()
        self.assertEqual(result["status"], "Q21_SOURCE_ONLY_PREFLIGHT_PASS")
        self.assertEqual(result["protected_sources_used"], False)
        self.assertEqual(result["empirical_controls_present"],
                         ["current_public_counts", "history_public_counts"])


if __name__ == "__main__":
    unittest.main()
