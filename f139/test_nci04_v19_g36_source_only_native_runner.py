"""G36 fixed source-only split native runner: strict false-success negatives."""
import pathlib
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from f139 import nci04_v19_g36_source_only_native_runner as g


class G36ContractTests(unittest.TestCase):
    def setUp(self):
        self.command = [sys.executable, "-B", "-m", "unittest",
                        "discover", "-s", "tests", "-p", "test_code_atlas.py", "-v"]
        self.good_out = (b"Ran 4 tests in 0.02s\n"
                         b"YGG_ATLAS_FAIL_CLOSED: working source mismatch: " +
                         g.TARGET.encode() + b"\n")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def execute(self, output, code, expect=False):
        fake = SimpleNamespace(stdout=output, returncode=code)
        with patch.object(g.subprocess, "run", return_value=fake):
            return g.fixed_run(pathlib.Path(self.tmp.name), self.command,
                               expect_atlas_negative=expect)

    def test_pins_repaired_atlas_and_historic_single_delta(self):
        self.assertEqual(g.BASE, "fc5d28a836f33caad3a576e0a6d4a1bf211cd857")
        self.assertEqual(g.BASE_TREE, "4cab523b03f7316b2470eddb93c479ec9e8cbab4")
        self.assertEqual(g.OLD_BASE, "021423311027517c9096c76bed7d35ac53c4a229")
        self.assertEqual(g.HEAD, "339276862e42a067344990dc20d907f203009b90")
        self.assertEqual(g.SOURCE, "0743ca22b76ebd943a66f05a36ea919301676be0")

    def test_expected_atlas_negative_cannot_become_a_test_pass(self):
        r=self.execute(self.good_out,1,expect=True)
        self.assertTrue(r["pass"])
        self.assertEqual(r["status"],"EXPECTED_FROZEN_ATLAS_REJECTION")
        self.assertEqual(r["test_count"],4)
        self.assertIsNone(r["peak_rss_bytes"])
        failed=self.execute(self.good_out,1,expect=False)
        self.assertFalse(failed["pass"])
        self.assertEqual(failed["status"],"FAIL")

    def test_alternative_failure_or_zero_discovery_cannot_satisfy_atlas(self):
        inputs=[
            (b"Ran 4 tests in 0.02s\nModuleNotFoundError: No module named resource",1),
            (b"Ran 4 tests in 0.02s\nYGG_ATLAS_FAIL_CLOSED: indexed file set changed",1),
            (b"Ran 4 tests in 0.02s\nworking source mismatch: other.py",1),
            (b"Ran 4 tests in 0.02s\nOK",0),
        ]
        for raw,code in inputs:
            with self.subTest(raw=raw[:60]):
                r=self.execute(raw,code,expect=True)
                self.assertFalse(r["pass"])
        with self.assertRaises(RuntimeError):
            self.execute(b"Ran 0 tests in 0.01s",1,expect=True)

    def test_zero_test_and_false_resource_claim_fail_closed(self):
        with self.assertRaises(RuntimeError):
            self.execute(b"Ran 0 tests\nOK\n",0)
        with self.assertRaises(RuntimeError):
            self.execute(b"NOT A REAL DISCOVERED TEST COUNT",0)
        r=self.execute(b"Ran 21 tests in 0.1s\nOK",0)
        self.assertEqual(r["status"],"PASS")
        self.assertIsNone(r["peak_rss_bytes"])

    def test_fixed_argv_rejects_injected_shells_and_non_runner_tests(self):
        with self.assertRaises(RuntimeError):
            with patch.object(g.subprocess,"run") as execute:
                g.fixed_run(pathlib.Path(self.tmp.name),
                            ["bash","-c","echo false-success"])
                execute.assert_not_called()
        with self.assertRaises(RuntimeError):
            with patch.object(g.subprocess,"run") as execute:
                g.fixed_run(pathlib.Path(self.tmp.name),
                            [sys.executable,"-B","-m","pip","install","unknown"])
                execute.assert_not_called()

    def test_invalid_candidate_commit_cannot_be_promoted(self):
        self.assertEqual(g.ATLAS,"test_code_atlas.py")
        self.assertEqual(g.TARGET,"yggdrasil/public_causal_cells.py")
        self.assertEqual(g.HEAD_TREE,"de431210951f1f0e79e447a532914cdfa431d25f")


if __name__ == "__main__":
    unittest.main()
