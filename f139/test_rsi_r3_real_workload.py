"""R3 authentic FORGE source-workload falsification; outcome may be NO_GO."""
from pathlib import Path
import json
import unittest

from f139.rsi_r3_real_workload import (
    BLOB, RealRSIDenied, TARGET, blob, cohorts, run, variant,
)

ROOT = Path(__file__).resolve().parents[1]


class RealSourceWorkloadTests(unittest.TestCase):
    def test_real_maintained_module_preimage_and_bounded_patch_grammar(self):
        source = (ROOT / TARGET).read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(blob(source), BLOB)
        self.assertEqual(source, variant(source, 0))
        for operation in (1, 2, 3):
            with self.subTest(operation=operation):
                after = variant(source, operation)
                self.assertNotEqual(after, source)
                self.assertEqual(after.count(b"@lru_cache(maxsize="), 1)
                compile(after, TARGET, "exec")

    def test_forbidden_operator_or_changed_source_fails_closed(self):
        source = (ROOT / TARGET).read_bytes().replace(b"\r\n", b"\n")
        with self.assertRaisesRegex(RealRSIDenied, "TARGET_DRIFT"):
            variant(source + b"\n# malicious drift\n", 1)
        for invalid in (-1, 4, True, None, 1.0, "1"):
            with self.subTest(invalid=invalid), self.assertRaises(RealRSIDenied):
                variant(source, invalid)

    def test_real_paths_have_no_train_validation_holdout_overlap(self):
        source, groups = cohorts(ROOT)
        self.assertEqual(blob(source), BLOB)
        paths = {name: {path for path, _ in data} for name, data in groups.items()}
        excluded = {"f139/rsi_r3_real_workload.py",
                    "f139/test_rsi_r3_real_workload.py"}
        self.assertFalse(excluded & set().union(*paths.values()))
        self.assertFalse(paths["train"] & paths["holdout"])
        self.assertFalse(paths["train"] & paths["validation"])
        self.assertFalse(paths["validation"] & paths["holdout"])
        self.assertGreaterEqual(min(map(len, paths.values())), 8)

    def test_existing_native_generator_against_authentic_forge_workload(self):
        result = run(ROOT)
        self.assertEqual(result["baseline_blob"], BLOB)
        self.assertNotEqual(result["generation_1"], result["generation_2"])
        self.assertEqual(len(result["trials"]), 2)
        self.assertFalse(result["rsi_proven"])
        self.assertFalse(result["scientific_accepted"])
        self.assertFalse(result["original_owner_autonomous"])
        self.assertFalse(result["whole_process_cost_qualified"])
        for trial in result["trials"]:
            self.assertEqual(len(trial["results"]), 4)
            self.assertTrue(all(row["correct"] > 0 for row in trial["results"]))
        # Print all raw metrics even when the frozen threshold fails.
        print("FORGE_RSI_R3_REAL_WORKLOAD=" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
