"""G13 V2 frozen signed-admission report semantics; no native tickets dispatched."""
import copy
import unittest
from dataclasses import replace

from f139.nci04_native_contract import Candidate, digest, NativeContractError
from f139.nci04_signed_native import NativeAdmission
from f139.nci04_worker_v2 import (
    SOURCE_SHA, SOURCE_TREE, EXPECTED_MODULES, FROZEN_COUNTS, REPORT_SCHEMA,
    RECEIPT_SCHEMA, COMPILE, unit_argv, supported_modules, validate_v2, receipt_v2,
)


class V2ContractTests(unittest.TestCase):
    def setUp(self):
        self.c = Candidate("a" * 64, "b" * 64, SOURCE_SHA, SOURCE_TREE,
                           "yggdrasil/public_causal_cells.py",
                           "c" * 64, "d" * 64, b"def x(): return 1\n",
                           "Yggdrasil")

    def result(self, argv, count=None, outcome="PASS"):
        return {
            "argv": list(argv), "outcome": outcome,
            "returncode": 0 if outcome == "PASS" else 1,
            "test_count": count, "output_sha256": digest(b"synthetic fixed report"),
            "output_bytes": 22, "elapsed_ms": 1,
        }

    def report(self, oslabel="ubuntu-latest"):
        modules, excluded = supported_modules(oslabel)
        return {
            "schema": REPORT_SCHEMA, "intent_sha256": self.c.intent_sha256,
            "qualification_key": self.c.qualification_key,
            "target_commit": SOURCE_SHA, "target_tree_sha": SOURCE_TREE,
            "candidate_path": self.c.path, "candidate_sha256": self.c.after_sha256,
            "os": oslabel, "complete_git_ancestry": True,
            "original_tracked_test_modules": sorted(EXPECTED_MODULES),
            "pristine_source_atlas": self.result(unit_argv("test_code_atlas.py"), 4),
            "supported_behavior_modules": list(modules),
            "explicit_unsupported_modules": list(excluded),
            "candidate_behavior": [
                self.result(unit_argv(module), FROZEN_COUNTS[module]) for module in modules],
            "candidate_compile": self.result(COMPILE),
            "qualification_complete": True, "development_only": True,
            "scientific_first_use": False, "protected_holdouts_accessed": 0,
            "accepted_ref_mutations": 0, "paid_model_calls": 0,
        }

    def test_linux_entire_suite_is_mandatory(self):
        r = self.report()
        self.assertTrue(validate_v2(self.c, r))
        self.assertEqual(len(r["candidate_behavior"]), 3)
        self.assertEqual(sum(x["test_count"] for x in r["candidate_behavior"]), 41)

    def test_windows_posix_only_accounted_as_unsupported(self):
        r = self.report("windows-latest")
        self.assertTrue(validate_v2(self.c, r))
        self.assertEqual(r["explicit_unsupported_modules"], ["test_free_fanout_sidecar.py"])
        self.assertEqual(sum(x["test_count"] for x in r["candidate_behavior"]), 21)

    def test_source_atlas_cannot_be_skipped_or_forged(self):
        for key, val in [
                ("pristine_source_atlas", None),
                ("complete_git_ancestry", False),
                ("original_tracked_test_modules", ["test_native_cells.py"])]:
            with self.subTest(key=key):
                r = self.report()
                r[key] = val
                with self.assertRaises(NativeContractError):
                    validate_v2(self.c, r)

    def test_candidate_cannot_choose_unsupported_modules(self):
        r = self.report("windows-latest")
        r["explicit_unsupported_modules"] = []
        with self.assertRaises(NativeContractError):
            validate_v2(self.c, r)
        r = self.report()
        r["explicit_unsupported_modules"] = ["test_free_fanout_sidecar.py"]
        with self.assertRaises(NativeContractError):
            validate_v2(self.c, r)

    def test_zero_tests_missing_suite_and_false_positive_rejected(self):
        for change in ("zero", "omit", "invent_success", "wrong_command"):
            with self.subTest(change=change):
                r = self.report()
                if change == "zero":
                    r["candidate_behavior"][0]["test_count"] = 0
                elif change == "omit":
                    r["candidate_behavior"].pop(1)
                elif change == "invent_success":
                    r["candidate_behavior"][1]["outcome"] = "TEST_FAILURE"
                    r["candidate_behavior"][1]["returncode"] = 1
                else:
                    r["candidate_behavior"][1]["argv"] = ["python", "-c", "print(1)"]
                with self.assertRaises(NativeContractError):
                    validate_v2(self.c, r)

    def test_preserved_negative_receipt_no_false_pass(self):
        r = self.report()
        r["candidate_behavior"][0]["outcome"] = "TEST_FAILURE"
        r["candidate_behavior"][0]["returncode"] = 1
        r["candidate_behavior"] = r["candidate_behavior"][:1]
        r["candidate_compile"] = None
        r["qualification_complete"] = False
        self.assertFalse(validate_v2(self.c, r))
        entry = NativeAdmission("ticket", "Yggdrasil", "e"*40, 123, "ubuntu-latest",
                                907, 6019876053, self.c, "f"*64)
        receipt = receipt_v2(entry, r)
        self.assertEqual(receipt["schema"], RECEIPT_SCHEMA)
        self.assertFalse(receipt["native_qualified"])
        self.assertFalse(receipt["scientific_first_use_authorized"])
        self.assertEqual(receipt["original_signed_admission_sha256"], "f"*64)

    def test_explicit_zero_test_negative_is_retained_but_never_passes(self):
        r = self.report()
        r["candidate_behavior"][0]["outcome"] = "TEST_FAILURE"
        r["candidate_behavior"][0]["returncode"] = 1
        r["candidate_behavior"][0]["test_count"] = 0
        r["candidate_behavior"] = r["candidate_behavior"][:1]
        r["candidate_compile"] = None
        r["qualification_complete"] = False
        self.assertFalse(validate_v2(self.c, r))
        r["qualification_complete"] = True
        with self.assertRaisesRegex(NativeContractError, "FALSE_QUALIFICATION"):
            validate_v2(self.c, r)

    def test_unbound_os_or_admission_cannot_make_signed_receipt(self):
        entry = NativeAdmission("ticket", "Yggdrasil", "e"*40, 123, "ubuntu-latest",
                                907, 6019876053, self.c, "f"*64)
        self.assertTrue(receipt_v2(entry, self.report())["native_qualified"])
        with self.assertRaises(NativeContractError):
            receipt_v2(entry, self.report("windows-latest"))
        with self.assertRaises(NativeContractError):
            receipt_v2(replace(entry, authorization_sha256=""), self.report())

    def test_legacy_receipt_schema_never_reused(self):
        self.assertNotEqual(RECEIPT_SCHEMA,
                            "forge.f139.nci04.native-execution-receipt.v1")
        self.assertNotEqual(REPORT_SCHEMA,
                            "forge.f139.nci04.native-development-diagnostic.v1")
        self.assertEqual(supported_modules("windows-latest")[1],
                         ("test_free_fanout_sidecar.py",))
        with self.assertRaises(NativeContractError):
            supported_modules("macos-latest")

    def test_binding_rejects_changed_candidate(self):
        r = self.report()
        with self.assertRaises(NativeContractError):
            validate_v2(replace(self.c, after_sha256="0"*64), r)
        r["paid_model_calls"] = 1
        with self.assertRaises(NativeContractError):
            validate_v2(self.c, r)


if __name__ == "__main__":
    unittest.main()
