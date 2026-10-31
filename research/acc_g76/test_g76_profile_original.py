"""Offline tests for G76 frozen source and profiler diagnostic contract."""
import tempfile
import unittest
from pathlib import Path

from g76_profile_original import (
    CASES, MODEL_REV, MODEL_REPO, TEXT_BLOB_SHA1, TEXT_BYTES,
    TEXT_REPO_REV, TEXT_PATH, WEIGHT_BYTES, WEIGHT_SHA256,
    git_blob_sha1, load_frozen_text,
)
from g76i_timeline import SCHEMA, necessary_removable_fraction, validate_trace


class G76ProfileContract(unittest.TestCase):
    def test_frozen_model_and_text_identity(self):
        self.assertEqual(MODEL_REPO, "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
        self.assertEqual(MODEL_REV, "c13e4efb205d7a8e5d13c088aa10a9dabac9b96a")
        self.assertEqual(WEIGHT_BYTES, 2200119864)
        self.assertEqual(WEIGHT_SHA256, "6e6001da2106d4757498752a021df6c2bdc332c650aae4bae6b0c004dcf14933")
        self.assertEqual(TEXT_REPO_REV, "81db45c9c48c592f0b77f01fc59e677ad0a5634e")
        self.assertEqual(TEXT_PATH, "1342.txt")
        self.assertEqual(TEXT_BYTES, 717602)
        self.assertEqual(TEXT_BLOB_SHA1, "0a7d439c2f34b0dfacb88b7116429a9575b5735c")
        self.assertEqual(CASES, ((24576,512),(98304,1536)))

    def test_git_blob_digest_is_canonical(self):
        self.assertEqual(git_blob_sha1(b"abc"), "f2ba8f84ab5c1bce84a7b441cb1959cfc7093b7f")

    def test_existing_file_with_wrong_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "wrong.txt"
            path.write_bytes(b"not the pinned Jane Austen source")
            with self.assertRaisesRegex(RuntimeError, "G76_TEXT_SOURCE_DRIFT"):
                load_frozen_text(path)

    def test_profiler_schema_and_threshold_are_diagnostic_only(self):
        self.assertEqual(SCHEMA, "forge.acc.g76i.cuda-timeline.v1")
        self.assertAlmostEqual(necessary_removable_fraction(), 1 - 1/1.15)
        summary = validate_trace({"traceEvents":[
            {"ph":"X","cat":"cpu_op"},
            {"ph":"X","cat":"kernel"},
            {"ph":"X","cat":"cuda_runtime"}
        ]})
        self.assertEqual(summary["cpu_events"],1)
        self.assertEqual(summary["kernel_events"],1)
        self.assertEqual(summary["cuda_runtime_events"],1)
        self.assertEqual(summary["launch_overhead_fraction"],"UNMEASURED")
        self.assertEqual(summary["speedup"],"UNMEASURED")

    def test_invalid_target_and_trace_fail_closed(self):
        for value in (1.0,0.0,float("nan"),float("inf")):
            with self.assertRaises(ValueError):
                necessary_removable_fraction(value)
        for value in (None,{},{"traceEvents":{}},[]):
            with self.assertRaises(ValueError):
                validate_trace(value)


if __name__ == "__main__":
    unittest.main()
