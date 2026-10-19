"""F124-CM source-free engineering tests: NOT prospective scientific source."""
import importlib.util
from pathlib import Path
import random
import unittest

PATH = Path(__file__).with_name("f124cm_learned_online_state.py")
spec = importlib.util.spec_from_file_location("f124cm_candidate", PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def toy_rows():
    # Toy synthetic engineering fixture, never a development/held-out cohort.
    weights = (0x1047, 0x4143, 0x8200b, 0x100201)
    ref = m.LearnedModel(weights)
    rng = random.Random(20261019)
    unique, result = set(), []
    while len(result) < 48:
        e, s, lag = (rng.randrange(16) for _ in range(3))
        if (e, s, lag) in unique:
            continue
        unique.add((e, s, lag))
        result.append((e, s, lag,
                       m.predict(ref, e, m.OnlineState(s, lag)).current))
    return result[:40], result[40:]


class EngineeringOnly(unittest.TestCase):
    def test_fit_recovers_new_sequential_feature_transition(self):
        fit, check = toy_rows()
        model, evidence = m.fit(fit, check)
        self.assertIsNotNone(model, evidence)
        self.assertEqual(evidence["rank"], 25)
        self.assertEqual(evidence["FIT_mismatches"], 0)
        self.assertEqual(evidence["CHECK_mismatches"], 0)
        self.assertFalse(evidence["scientific_accepted"])
        self.assertEqual(evidence["coefficient_bits"], 100)
        self.assertEqual(evidence["online_history_bits"], 8)
        for row in check:
            self.assertEqual(m.predict(model, row[0], m.OnlineState(row[1], row[2])),
                             m.OnlineState(row[3], row[1]))

    def test_veto_cannot_train_on_check(self):
        fit, check = toy_rows()
        tampered = list(check)
        e, s, lag, y = tampered[0]
        tampered[0] = (e, s, lag, y ^ 1)
        model, evidence = m.fit(fit, tampered)
        self.assertIsNone(model)
        self.assertEqual(evidence["CHECK_mismatches"], 1)
        self.assertFalse(evidence["model_admitted_on_public_check"])

    def test_nonidentifiable_fits_fail_closed(self):
        fit = [(e, s, lag, 0) for e in range(4)
               for s in range(10) for lag in (0,)][:40]
        check = [(e, s, 1, 0) for e in range(2) for s in range(4)]
        candidate, receipt = m.fit(fit, check)
        self.assertIsNone(candidate)
        self.assertFalse(receipt["identifiable"])
        self.assertLess(receipt["rank"], 25)

    def test_bad_shapes_and_bool_fields_fail_closed(self):
        fit, check = toy_rows()
        with self.assertRaises(ValueError):
            m.fit(fit[:39], check)
        with self.assertRaises(ValueError):
            m.fit([(True, *row[1:]) for row in fit], check)
        with self.assertRaises(ValueError):
            m.predict(m.LearnedModel((0, 0, 0, 1 << 25)), 0,
                      m.OnlineState(0, 0))

    def test_state_is_online_and_lagged_effect_is_not_stateless(self):
        model = m.LearnedModel((1 << 10, 0, 0, 0))  # bit1 of lagged state
        first = m.predict(model, 0, m.OnlineState(0, 2))
        second = m.predict(model, 0, first)
        self.assertEqual(first, m.OnlineState(1, 0))
        self.assertEqual(second, m.OnlineState(0, 1))


if __name__ == "__main__":
    unittest.main()
