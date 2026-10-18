"""F124-BI engineering/source-custody negative controls; no registered cohort."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest

DIR = Path(__file__).resolve().parent


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, DIR / filename)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


verify = module("f124bi_provider_verification", "f124bi_provider_verify.py")
measure = module("f124bi_resource_measurement", "f124bi_measure.py")


class ProviderCustodyTests(unittest.TestCase):
    def test_local_immutable_birth_first_parent_chain(self):
        result = verify.verify(local_only=True)
        self.assertTrue(result["strict_first_parent_source_birth_chronology"])
        self.assertTrue(result["algorithm_bodies_distinct"])
        self.assertFalse(result["provider_commit_blob_tree_authenticated"])
        self.assertFalse(result["external_independent_source_origin_confirmed"])
        self.assertFalse(result["scientific_admission_authorized"])
        self.assertEqual(result["registered_case_generated"], 0)

    def test_tampered_birth_identity_fails_closed(self):
        prev = verify.BIRTHS["U"]
        try:
            verify.BIRTHS["U"] = (prev[0], "0" * 40, prev[2])
            with self.assertRaises(RuntimeError):
                verify.verify(local_only=True)
        finally:
            verify.BIRTHS["U"] = prev

    def test_no_unqualified_resource_promotion_in_method(self):
        import json
        d = json.loads(verify.METHOD.read_text(encoding="utf-8"))
        self.assertFalse(d["independence_boundaries"]["scientific_admission"])
        self.assertFalse(d["independence_boundaries"]["protected_source_use"])
        self.assertEqual(d["resource_method"]["actual_repeats_per_arm_per_fixture"], 3)


class PartialResourceTests(unittest.TestCase):
    def row(self, fixture, arm, source="paired"):
        return {
            "schema": "mass.f124bi.fit-partial-child-measurement.v1",
            "arm": arm, "fixture": fixture,
            "public_48_sha256": source,
            "observations": 48, "FIT": 40, "CHECK": 8,
            "source_family_visible_to_model": False,
            "CPU_ns_including_import_and_source_prep": 123,
            "peak_process_RSS_bytes": 50000000,
            "fit_outcome_descriptive_only": {},
            "TRAIN_192_cpu_ns": None,
            "representation_scoring_cpu_ns": None,
            "full_native_graph_scoring_cpu_ns": None,
            "complete_cognition_state_bytes": None,
            "resource_parity_proven": False,
            "scientific_acceptance": False,
            "registered_source_generated": 0,
        }

    def test_same_public_no_prospective_and_no_parity(self):
        rows = [self.row(fixture, arm)
                for fixture in (-940, -939)
                for arm in measure.ARM_IDS for _ in range(measure.REPEATS)]
        result = measure.aggregate(rows)
        self.assertEqual(result["recorded_arm_count"], 12)
        self.assertFalse(result["resource_parity_qualified"])
        self.assertFalse(result["scientific_admission"])
        self.assertEqual(result["registered_source_constructed"], 0)

    def test_missing_resource_and_public_data_mismatch_rejected(self):
        rows = [self.row(fixture, arm)
                for fixture in (-940, -939)
                for arm in measure.ARM_IDS for _ in range(measure.REPEATS)]
        rows[0]["TRAIN_192_cpu_ns"] = 0  # invalid claim of measured TRAIN
        with self.assertRaises(RuntimeError):
            measure.aggregate(rows)
        rows[0]["TRAIN_192_cpu_ns"] = None
        rows[0]["public_48_sha256"] = "different"
        with self.assertRaises(RuntimeError):
            measure.aggregate(rows)
        rows[0]["public_48_sha256"] = "paired"
        rows[0]["source_family_visible_to_model"] = True
        with self.assertRaises(RuntimeError):
            measure.aggregate(rows)

    def test_unsafe_cohort_selection_rejected(self):
        with self.assertRaises(RuntimeError):
            measure._matched_public("U-SEAL")
        with self.assertRaises(RuntimeError):
            measure._matched_public("R-PROTECTED")


if __name__ == "__main__":
    unittest.main()
