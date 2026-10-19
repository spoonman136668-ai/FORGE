"""Engineering-only F124-BH test suite; never imports unseen registered data."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("bh_readiness", HERE / "f124bh_readiness.py")
bh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bh)


class BirthChronologyTests(unittest.TestCase):
    def test_frozen_before_two_distinct_source_births(self):
        p = bh.verify_chronology()
        self.assertEqual(p["families"]["U"]["cohort"], [902000, 902127])
        self.assertEqual(p["families"]["R"]["cohort"], [903000, 903127])
        self.assertNotEqual(p["families"]["U"]["shape"],
                            p["families"]["R"]["shape"])

    def test_only_negative_fixture_operators_are_realized(self):
        receipt = bh.synthetic_operator_audit()
        self.assertEqual(set(receipt), {"U", "R"})
        self.assertNotEqual(receipt["U"]["source_blob"],
                            receipt["R"]["source_blob"])
        for lane in receipt.values():
            self.assertEqual(lane["registered_cases_generated"], 0)
            self.assertIs(lane["witnessed_externally"], False)
            self.assertEqual(lane["synthetic_fixed_point_count"], 258)

    def test_roundtrips_do_not_depend_on_learned_kernel(self):
        u = bh.module("f124bh_u_test", "f124bh_u_family.py")
        r = bh.module("f124bh_r_test", "f124bh_r_family.py")
        cases = (0, 1, 2, 31, 255, 256, 65534, 65535, 0x1234, 0xcafe)
        for m, fixture in ((u, -940), (r, -939)):
            recipe = m._recipe(fixture)
            self.assertTrue(all(m.inverse(m.forward(x, recipe), recipe) == x
                                for x in cases))
            for case in (-1, 0, 900000, 901000, 902000, 902127,
                         903000, 903127):
                with self.assertRaises(ValueError):
                    m.fixture(case)


class CompleteResourceGateTests(unittest.TestCase):
    @staticmethod
    def ledger(n=10):
        return dict.fromkeys(bh.COMPONENTS, n)

    def test_no_partial_or_missing_resources_ever_qualify(self):
        a = self.ledger()
        b = self.ledger(20)
        del a["metatrain_cpu_ns"]
        with self.assertRaises(ValueError):
            bh.full_budget(a, b)
        a["metatrain_cpu_ns"] = None
        with self.assertRaises(ValueError):
            bh.full_budget(a, b)
        a["metatrain_cpu_ns"] = -1
        with self.assertRaises(ValueError):
            bh.full_budget(a, b)

    def test_complete_budget_enforces_all_fields_and_training(self):
        a = self.ledger()
        b = self.ledger(20)
        # Resident peak must include measured logical memory minimum (5*n).
        a["task_peak_rss_bytes"] = 100
        b["task_peak_rss_bytes"] = 200
        a["train_peak_rss_bytes"] = 110
        b["train_peak_rss_bytes"] = 210
        x = bh.full_budget(a, b, eligible_symbolic=b)
        self.assertIs(x["mechanically_resource_eligible"], True)
        self.assertIs(x["transfer_scientifically_accepted"], False)
        self.assertEqual(x["totals"]["candidate"]["task_cpu_ns"], 50)
        self.assertEqual(x["totals"]["candidate"]["amortized_cpu_ns_ceiling"], 51)
        self.assertEqual(x["totals"]["candidate"]["whole_process_peak_rss_bytes"], 110)
        with self.assertRaises(ValueError):
            bh.full_budget({**a, "model_weight_bytes": 1000}, b)
        with self.assertRaises(ValueError):
            bh.full_budget({**a, "graph_scoring_cpu_ns": 10000}, b)
        with self.assertRaises(ValueError):
            bh.full_budget(a, b, denominator=256)

    def test_no_unearned_OOD_claim_in_readiness(self):
        receipt = bh.readiness()
        self.assertEqual(receipt["registered_cohort_generated"], 0)
        self.assertEqual(receipt["registered_cohort_consumed"], 0)
        self.assertIs(receipt["protected_first_use"], False)
        self.assertIs(receipt["scientific_acceptance"], False)
        self.assertIs(receipt["resource_parity_qualified"], False)
        self.assertIs(receipt["independent_external_birth_witness"], False)
        self.assertIs(receipt["optimizer_promotion"], False)
        self.assertEqual(receipt["preregistered_gain_per_cohort"], 8)
        self.assertEqual(set(receipt["negative_fixture_measurements_only"]),
                         {"U", "R"})
        for lane in receipt["negative_fixture_measurements_only"].values():
            self.assertTrue(lane["fit_CPU_ns"] >= 0)
            self.assertTrue(lane["whole_task_RSS_not_qualified"])
            self.assertTrue(lane["TRAIN_amortization_not_qualified"])
            self.assertTrue(lane["score_and_representation_cost_not_qualified"])


if __name__ == "__main__":
    unittest.main()
