"""Negative-first checks for F139 real development training, not science."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from f139 import dev_learning as d

SHA = "a" * 40

class DevLearningTests(unittest.TestCase):
    def test_actual_two_lane_fit_and_held_development_comparison(self):
        one = d.run("Qualification", 1, SHA)
        two = d.run("Qualification", 1, SHA)
        self.assertEqual([v["lane"] for v in one["lanes"]], ["Wingless", "Yggdrasil"])
        self.assertEqual(one["lanes"], two["lanes"])
        for row in one["lanes"]:
            a, b = row["trained_candidate"], row["trained_control"]
            self.assertEqual(a["search_evaluations"], b["search_evaluations"])
            self.assertEqual(a["training_cohort_sha256"], b["training_cohort_sha256"])
            self.assertEqual(a["transfer_cohort_sha256"], b["transfer_cohort_sha256"])
            self.assertEqual(a["transfer_total"], 96)
            self.assertEqual(row["classification"], "POSITIVE_DEVELOPMENT"
                             if row["transfer_correct_delta"] > 0
                             else "NEGATIVE_OR_TIE_DEVELOPMENT")
            self.assertFalse(row["new_architecture_proven"])
        self.assertTrue(one["real_cpu_training_executed"])
        self.assertFalse(one["autonomous_code_generation"])
        self.assertFalse(one["persistent_accepted_model_updated"])
        self.assertFalse(one["protected_first_use"])
        self.assertEqual(one["optimizer_policy_mutations"], 0)
        self.assertEqual(one["paid_api_calls"], 0)
        self.assertGreater(one["peak_python_bytes"], 0)

    def test_programs_and_generations_do_not_repeat_development_data(self):
        for lane in ("Wingless", "Yggdrasil"):
            x = d.run(lane, 1, SHA)
            y = d.run(lane, 2, SHA)
            self.assertEqual(len(x["lanes"]), 1)
            self.assertNotEqual(x["lanes"][0]["trained_candidate"]["training_cohort_sha256"],
                                y["lanes"][0]["trained_candidate"]["training_cohort_sha256"])

    def test_forbidden_inputs_or_wrong_git_sha_block(self):
        for lane, gen, sha in [("Science",1,SHA), ("Wingless",0,SHA),
                                ("Wingless",100001,SHA), ("Wingless",1,"z"*40)]:
            with self.assertRaises(ValueError):
                d.run(lane, gen, sha)
        with patch.dict(os.environ, {"GITHUB_SHA": "b" * 40}):
            with self.assertRaisesRegex(ValueError, "EXACT_SOURCE_DRIFT"):
                d.run("Wingless", 1, SHA)

    def test_negative_result_retained_and_never_accepted(self):
        def fake(lane, generation, candidate):
            return {"training_cohort_sha256": "a"*64, "transfer_cohort_sha256": "b"*64,
                    "search_evaluations": 64, "transfer_correct": 48}
        with patch.object(d, "fit", side_effect=fake):
            out = d.run("Qualification", 1, SHA)
        self.assertTrue(all(r["classification"] == "NEGATIVE_OR_TIE_DEVELOPMENT"
                            and not r["independent_scientific_validation"]
                            for r in out["lanes"]))

    def test_exclusive_output_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dev.json"
            args = ["dev_learning", "--lane", "Wingless", "--generation", "1",
                    "--source-sha", SHA, "--output", str(path)]
            with patch("sys.argv", args):
                d.main()
            original = path.read_bytes()
            self.assertEqual(json.loads(original)["source_sha"], SHA)
            with patch("sys.argv", args), self.assertRaisesRegex(ValueError, "EXCLUSIVE_OUTPUT"):
                d.main()
            self.assertEqual(path.read_bytes(), original)

if __name__ == "__main__":
    unittest.main()
