"""Read-only Q21 R29 tests; all input rows are fabricated score receipts.

There is no invocation of sourcefree.generate, model fitting, DEV evaluation,
original MiniGrid/Pycolab, CKB-plane, or protected first use.
"""
from __future__ import annotations

import copy
import math
import unittest
from pathlib import Path

import evaluator as ev
import reconcile as r
import sourcefree as src


def stage(name, platform, rss, cpu):
    return {
        "schema": "forge.q21.native-process-resource.v1",
        "stage": name,
        "platform": platform,
        "rss_scope": "CUMULATIVE_PROCESS_HIGH_WATER_NOT_ISOLATED_STAGE",
        "start_process_peak_rss_bytes": rss-1,
        "process_peak_rss_bytes": rss,
        "process_cpu_seconds": cpu,
        "io_measurement_source":
            "windows_getprocessiocounters" if platform == "Windows"
            else "linux_proc_self_io",
        "io": {
            "read_transfer_bytes": 8, "write_transfer_bytes": 9,
            "disk_read_bytes": None if platform == "Windows" else 0,
            "disk_write_bytes": None if platform == "Windows" else 0,
        },
    }


def family_result(family, platform):
    null = family == src.FAMILIES[2]
    curr_loss = .6
    hist_loss = .598 if null else .58
    arms = {}
    for name in ev.ARM_NAMES:
        current = name == ev.MEMORYLESS[0]
        lagged = name == ev.HISTORY[0]
        score = curr_loss if current else (
            hist_loss if lagged else (.63 if name in ev.MEMORYLESS else .62))
        fit_nll = .20 if current else (
            .19 if lagged else (.3 if name in ev.MEMORYLESS else .4))
        arms[name] = {
            "fit_cost": {
                "checkpoint_bytes": 10, "fit_validation_nll": fit_nll,
                "checkpoint_sha256": "b"*64,
            },
            "result": {
                "mean_nll": score,
                "episode_nll": [score]*src.ROLE_COUNTS["DEV"],
            },
        }
    losses = [curr_loss, hist_loss]
    gain = losses[0] - losses[1]
    receipts = [
        stage("source_generation", platform, 100, .15),
        stage("generation_to_evaluation_handoff", platform, 110, .04),
        stage("model_fit_validation_dev_oracle_bootstrap", platform, 130, .7),
    ]
    resource = {
        "schema": r.RESOURCE_SCHEMA,
        "source_generation": receipts[0],
        "generation_to_evaluation_handoff": receipts[1],
        "fit_dev_oracle_bootstrap": receipts[2],
        "total_process_cpu_seconds": .89,
        "process_peak_rss_bytes": 130,
        "rss_scope": "CUMULATIVE_PROCESS_HIGH_WATER_NOT_ISOLATED_MODEL",
        "public_input_serialization": {
            "serialized_bytes": 800, "serialized_sha256": "a"*64,
            "encoding": "canonical_json_utf8",
        },
        "all_seven_model_serialized_checkpoint_bytes": 70,
        "checkpoint_persisted_bytes": "NOT_MEASURED_NO_PERSISTENCE_CLAIM",
        "adapter_transport": {
            "adapter_mode": "none", "wire_bytes": 0, "adapter_bytes": 0,
        },
        "scientific_qualification": "NOT_AUTHORIZED_BY_RESOURCE_CENSUS",
    }
    return {
        "family": family,
        "protected_scientific_first_use": False,
        "native_peak_rss_measured": True,
        "native_peak_rss_qualified": False,
        "role_sha256": {
            "FIT_TRAIN": "1"*64,
            "FIT_VALID": "2"*64,
            "DEV": "3"*64,
        },
        "arm_results": arms,
        "best_current": ev.MEMORYLESS[0],
        "best_history": ev.HISTORY[0],
        "gain": {
            "gain_nats_per_bit": gain,
            "lower_95": gain-.001,
            "upper_95": gain+.001,
            "resampling_unit": "EPISODE",
            "replicates": 2048,
        },
        "privileged_oracle_nll": .58,
        "oracle_is_not_matched_comparator": True,
        "public_oracle_headroom": .02,
        "native_resource_census": resource,
    }


def receipt(platform):
    return {
        "schema": r.SCHEMA,
        "os_name": platform,
        "candidate_source_sha": "e"*40,
        "protocol_git_blob": src.PROTOCOL_BLOB,
        "protected_scientific_first_use": False,
        "by_family": {
            family: family_result(family, platform)
            for family in src.FAMILIES
        },
    }


DOC = {
    "schema": src.SCHEMA,
    "frozen_dev_decision": {
        "history_gain_min_nats_per_bit_each_real_family": .012,
        "history_gain_95pct_bootstrap_lower_bound_each_real_family_min": .002,
        "public_oracle_headroom_vs_best_memoryless_min_nats_each_real_family":
            .015,
        "null_family_max_apparent_history_gain_nats": .005,
    },
}


class ReadOnlyReplayQualification(unittest.TestCase):
    def setUp(self):
        self.windows = receipt("Windows")
        self.linux = receipt("Linux")

    def check(self):
        return r.compare(self.windows, self.linux, DOC)

    def test_exact_dual_os_replay_remains_advisory(self):
        out = self.check()
        self.assertTrue(out["numerical_agreement_within_frozen_tolerance"])
        self.assertTrue(out["q21_dev_threshold_signal"])
        self.assertTrue(out["matching_reported_checkpoint_hashes"])
        self.assertEqual(out["original_scientific_first_use"], "NOT_PERFORMED")
        self.assertEqual(out["execution_authority"], "NONE")
        self.assertIn("REQUIRED", out["advisory_disposition"])

    def test_different_checkpoint_hashes_not_claimed_bit_identical(self):
        self.linux["by_family"][src.FAMILIES[0]]["arm_results"][
            ev.HISTORY[0]]["fit_cost"]["checkpoint_sha256"] = "c"*64
        out = self.check()
        self.assertFalse(out["matching_reported_checkpoint_hashes"])
        self.assertEqual(len(out["checkpoint_hash_divergences"]), 1)

    def test_cross_os_data_and_source_identity_drift_are_fatal(self):
        self.linux["by_family"][src.FAMILIES[0]][
            "role_sha256"]["DEV"] = "5"*64
        with self.assertRaisesRegex(ValueError, "COHORT_DIGEST"):
            self.check()
        self.linux = receipt("Linux")
        self.linux["candidate_source_sha"] = "f"*40
        with self.assertRaisesRegex(ValueError, "CANDIDATE_SOURCE_DRIFT"):
            self.check()

    def test_tiny_numerical_difference_allowed_but_large_loss_rejected(self):
        # Keep all internal mean/episode/gain accounting consistent.
        arm = self.linux["by_family"][src.FAMILIES[0]][
            "arm_results"][ev.HISTORY[0]]["result"]
        arm["mean_nll"] += 5e-7
        arm["episode_nll"] = [arm["mean_nll"]]*src.ROLE_COUNTS["DEV"]
        self.linux["by_family"][src.FAMILIES[0]][
            "gain"]["gain_nats_per_bit"] -= 5e-7
        self.assertTrue(self.check()["numerical_agreement_within_frozen_tolerance"])
        arm["mean_nll"] += 2e-6
        arm["episode_nll"] = [arm["mean_nll"]]*src.ROLE_COUNTS["DEV"]
        self.linux["by_family"][src.FAMILIES[0]][
            "gain"]["gain_nats_per_bit"] -= 2e-6
        with self.assertRaisesRegex(ValueError, "NUMERICAL_DRIFT"):
            self.check()

    def test_dev_selected_model_cannot_override_fit_valid(self):
        row = self.linux["by_family"][src.FAMILIES[0]]
        row["best_current"] = ev.MEMORYLESS[1]
        with self.assertRaisesRegex(ValueError, "POSTHOC_DEV"):
            self.check()

    def test_false_resource_or_first_use_claim_rejected(self):
        row = self.windows["by_family"][src.FAMILIES[0]]
        row["native_peak_rss_qualified"] = True
        with self.assertRaisesRegex(ValueError, "FORGED_RESOURCE"):
            self.check()
        row["native_peak_rss_qualified"] = False
        self.windows["protected_scientific_first_use"] = True
        with self.assertRaisesRegex(ValueError, "PROTECTED"):
            self.check()

    def test_missing_native_io_and_unsupported_per_model_rss_rejected(self):
        cost = self.windows["by_family"][src.FAMILIES[1]][
            "native_resource_census"]
        cost["rss_scope"] = "PER_MODEL_RSS"
        with self.assertRaisesRegex(ValueError, "UNJUSTIFIED_ISOLATED_RSS"):
            self.check()
        cost["rss_scope"] = "CUMULATIVE_PROCESS_HIGH_WATER_NOT_ISOLATED_MODEL"
        cost["source_generation"]["io"]["read_transfer_bytes"] = None
        with self.assertRaisesRegex(ValueError, "IO_TRANSFER_MISSING"):
            self.check()

    def test_missing_episode_and_illegal_bootstrap_failure(self):
        row = self.windows["by_family"][src.FAMILIES[0]]
        row["arm_results"][ev.ARM_NAMES[0]]["result"]["episode_nll"].pop()
        with self.assertRaisesRegex(ValueError, "DEV_EPISODE_CLUSTER"):
            self.check()
        self.windows = receipt("Windows")
        self.windows["by_family"][src.FAMILIES[0]][
            "gain"]["replicates"] = 2000
        with self.assertRaisesRegex(ValueError, "BOOTSTRAP_CONTRACT_DRIFT"):
            self.check()

    def test_cross_os_threshold_decision_must_match_even_within_float_tolerance(self):
        # Two CI runs can agree within 1e-6 in all reported NLLs yet
        # disagree on a binary threshold. That is not a reproducible GO.
        a = self.windows["by_family"][src.FAMILIES[0]]["gain"]
        b = self.linux["by_family"][src.FAMILIES[0]]["gain"]
        a["lower_95"] = .00200005
        b["lower_95"] = .00199995
        with self.assertRaisesRegex(ValueError,
                                    "CROSS_OS_SCIENTIFIC_DECISION_DRIFT"):
            self.check()

    def test_reconciliation_source_has_no_generator_training_or_dispatch_calls(self):
        import ast
        tree = ast.parse(
            Path(r.__file__).read_text(encoding="utf-8")
        )
        forbidden = {"generate", "fit_gradient", "fit_hmm",
                     "evaluate_one_family", "evaluate_with_native_resource_census",
                     "subprocess", "dispatch", "exec", "eval"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = node.func
                if isinstance(fn, ast.Name):
                    self.assertNotIn(fn.id, forbidden)
                elif isinstance(fn, ast.Attribute):
                    self.assertNotIn(fn.attr, forbidden)
        self.assertNotIn("sourcefree.generate", Path(r.__file__).read_text())


if __name__ == "__main__":
    unittest.main()
