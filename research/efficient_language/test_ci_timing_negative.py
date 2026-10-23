"""Fail-closed replay audit of independently read original GitHub timing metadata.

This historical comparison is cross-source and runner-unmatched; it is never
a qualified experiment, cache authorization or scientific outcome.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import unittest

FILE = Path(__file__).with_name("ci_timing_negative_20261023.json")
SHA = re.compile(r"[0-9a-f]{40}\\Z")


class OriginalCINegative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(FILE.read_text(encoding="utf-8"))

    def test_original_provider_run_ids_and_source_commits(self):
        x = self.doc
        self.assertEqual(x["schema"],
                         "forge.language-screen.original-ci-timing-observation.v1")
        self.assertEqual([x["baseline"]["run_id"], x["candidate"]["run_id"]],
                         [40030498018, 40031428380])
        self.assertEqual(x["baseline"]["source_commit_sha"],
                         "493df02f3be292255c163831cca90aa267fbda9d")
        self.assertEqual(x["candidate"]["source_commit_sha"],
                         "447a08b9d28aa5a8f5d7e1c6fccf66afc5a7f1f5")
        self.assertFalse(x["same_source_identity"])
        self.assertFalse(x["same_hardware_and_cache_verified"])
        for run in (x["baseline"], x["candidate"]):
            self.assertRegex(run["source_commit_sha"], SHA)
            self.assertEqual(run["url"],
                             "https://github.com/spoonman136668-ai/FORGE/actions/runs/"
                             + str(run["run_id"]))
            self.assertEqual(run["workflow_name"],
                             "FORGE public Linux and Windows qualification")
            self.assertEqual((run["status"], run["conclusion"]),
                             ("completed", "success"))

    def test_jobs_and_phases_have_consistent_original_utc_timestamps(self):
        for run in (self.doc["baseline"], self.doc["candidate"]):
            jobs = run["jobs"]
            self.assertEqual([j["name"] for j in jobs], ["linux", "windows"])
            self.assertEqual(len({j["job_id"] for j in jobs}), 2)
            for j in jobs:
                self.assertEqual((j["status"], j["conclusion"]),
                                 ("completed", "success"))
                start = datetime.fromisoformat(j["started_at"].replace("Z", "+00:00"))
                stop = datetime.fromisoformat(j["completed_at"].replace("Z", "+00:00"))
                self.assertEqual(start.utcoffset().total_seconds(), 0)
                self.assertEqual(stop.utcoffset().total_seconds(), 0)
                self.assertEqual((stop - start).total_seconds(), j["elapsed_seconds"])
                self.assertGreater(j["elapsed_seconds"], 0)
                phases = {s["step"]: s for s in j["qualification_phases"]}
                self.assertIn("F139 Python controller and native-custody regression",phases)
                full = ("Tests, race, vet and build" if j["name"]=="linux"
                        else "Native Windows source qualification")
                self.assertIn(full, phases)
                self.assertLessEqual(sum(s["elapsed_seconds"] for s in phases.values()),
                                     j["elapsed_seconds"])
                for s in phases.values():
                    a = datetime.fromisoformat(s["started_at"].replace("Z","+00:00"))
                    b = datetime.fromisoformat(s["completed_at"].replace("Z","+00:00"))
                    self.assertTrue(start <= a <= b <= stop)
                    self.assertEqual((b-a).total_seconds(), s["elapsed_seconds"])
            self.assertEqual(run["parallel_job_critical_path_seconds"],
                             max(j["elapsed_seconds"] for j in jobs))

    def test_negative_result_not_disguised_as_qualified_gain(self):
        b=self.doc["baseline"]
        c=self.doc["candidate"]
        self.assertEqual((b["jobs"][0]["elapsed_seconds"],
                          c["jobs"][0]["elapsed_seconds"]), (161,160))
        self.assertEqual((b["jobs"][1]["elapsed_seconds"],
                          c["jobs"][1]["elapsed_seconds"]), (225,292))
        self.assertEqual(
            c["parallel_job_critical_path_seconds"]
            - b["parallel_job_critical_path_seconds"],
            self.doc["observed_parallel_critical_path_delta_seconds"])
        self.assertEqual(self.doc["observed_parallel_critical_path_delta_seconds"],67)
        self.assertAlmostEqual(
            self.doc["observed_parallel_critical_path_delta_fraction"], 67/225)
        self.assertEqual(self.doc["results_conclusion"],
                         "FASTER_LANGUAGE_SCREEN_NOT_DEMONSTRATED")

    def test_archived_observation_cannot_self_authorize_firstuse_or_cache(self):
        for field in ("qualified_turnaround_gain_verified",
                      "provider_artifacts_independently_authenticated",
                      "language_quality_measured","candidate_model_executed",
                      "performance_causality_established","scientific_first_use",
                      "experimental_dispatch"):
            with self.subTest(field=field):
                self.assertIs(self.doc[field],False)
        self.assertIs(self.doc["full_regression_success_on_each_observed_source"],
                      True)
        self.assertIs(self.doc["provider_records_original_readback"],True)
        self.assertIs(self.doc["same_source_identity"],False)
        self.assertIs(self.doc["same_hardware_and_cache_verified"],False)


if __name__ == "__main__":
    unittest.main()
