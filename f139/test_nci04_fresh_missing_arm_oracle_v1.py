"""Source-only negative and cold-replay checks for the inert V1 oracle.

The fixture is historical real Yggdrasil native source; the test constructs a
candidate-like overlay in a disposable checkout. It does not replay an issue,
run a signed worker or claim scientific first-use on original data.
"""
from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

from f139.nci04_fresh_missing_arm_oracle_v1 import COMMAND, ORACLE, SCHEMA, SUCCESS

SOURCE = Path(__file__).with_name("fixtures") / "model_free_yggdrasil_992ef.py"
ANCHOR = "        return 0 if lhs > rhs else 1\n"
METHOD = '''
    def propose_missing_action(self, address: int, *, retained: bool = False) -> int | None:
        """Suggest the unobserved arm, or abstain if neither/both are observed."""
        cell = self._address(address, retained)
        attempts0 = sum(self._counts[cell][0])
        attempts1 = sum(self._counts[cell][1])
        if (attempts0 == 0) == (attempts1 == 0):
            return None
        return 0 if attempts0 == 0 else 1
'''


class MissingArmOracleV1Tests(unittest.TestCase):
    @staticmethod
    def candidate_source():
        raw = SOURCE.read_text(encoding="utf-8")
        if raw.count(ANCHOR) != 1 or "def propose_missing_action" in raw:
            raise AssertionError("HISTORICAL_FIXTURE_DRIFT")
        return raw.replace(ANCHOR, ANCHOR + METHOD, 1)

    def run_overlay(self, source):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "yggdrasil"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "public_causal_cells.py").write_text(source, encoding="utf-8")
            env = {k: v for k, v in os.environ.items()
                   if k.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP",
                                    "TMP", "HOME", "USERPROFILE", "PATHEXT",
                                    "SYSTEMDRIVE", "COMSPEC"}}
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            return subprocess.run(
                [sys.executable, "-B", "-c", ORACLE], cwd=root, env=env,
                stdin=subprocess.DEVNULL, capture_output=True,
                timeout=20, check=False)

    def test_version_and_fixed_command_are_not_live_worker_changes(self):
        self.assertEqual(SCHEMA, "forge.f139.nci04.fresh-missing-arm-oracle.v1")
        self.assertEqual(COMMAND, ("python", "-B", "-c", ORACLE))
        self.assertIn("propose_missing_action", ORACLE)
        self.assertIn("PublicCausalCells.restore", ORACLE)
        self.assertNotIn("choose_wilson", ORACLE)

    def test_source_equivalent_positive_cross_bank_and_cold_restore(self):
        result = self.run_overlay(self.candidate_source())
        self.assertEqual(result.returncode, 0, result.stderr[-700:])
        self.assertEqual(result.stdout.strip(), SUCCESS.encode("ascii"))

    def test_original_unmodified_source_fails_no_method(self):
        result = self.run_overlay(SOURCE.read_text(encoding="utf-8"))
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(SUCCESS.encode(), result.stdout)

    def test_mutations_are_rejected(self):
        original = self.candidate_source()
        mutations = {
            "wrong_arm": original.replace(
                "return 0 if attempts0 == 0 else 1",
                "return 1 if attempts0 == 0 else 0"),
            "no_abstention": original.replace(
                "return None\n        return 0 if attempts0 == 0 else 1",
                "return 0\n        return 0 if attempts0 == 0 else 1"),
            "mutating_read": original.replace(
                "attempts0 = sum(self._counts[cell][0])",
                "self._counts[cell][0][0] += 1\n"
                "        attempts0 = sum(self._counts[cell][0])"),
            "opposite_bank": original.replace(
                "cell = self._address(address, retained)\n"
                "        attempts0 = sum(self._counts[cell][0])",
                "cell = self._address(address, not retained)\n"
                "        attempts0 = sum(self._counts[cell][0])"),
            "not_checkpointed": original.replace(
                "return cells\n", "return cls()\n"),
        }
        for label, changed in mutations.items():
            with self.subTest(mutation=label):
                self.assertNotEqual(changed, original)
                result = self.run_overlay(changed)
                self.assertNotEqual(result.returncode, 0, label)
                self.assertNotIn(SUCCESS.encode(), result.stdout)


if __name__ == "__main__":
    unittest.main()
