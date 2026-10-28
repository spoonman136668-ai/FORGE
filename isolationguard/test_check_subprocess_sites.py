"""Adversarial tests for the exact-existing Go subprocess-call inventory."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from isolationguard.check_subprocess_sites import EXPECTED, check


class ExistingGoSubprocessSitesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for rel, lines in EXPECTED.items():
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            text = "\n".join(
                line for line, count in lines.items() for _ in range(count)
            ) + "\n"
            target.write_text(text, encoding="utf-8")

    def test_exact_historical_inventory_is_accepted(self):
        check(self.root)

    def test_original_repository_has_no_additions(self):
        check(Path(__file__).resolve().parents[1])

    def test_new_subprocess_at_new_path_is_rejected(self):
        extra = self.root / "cmd" / "unsafe" / "main.go"
        extra.parent.mkdir(parents=True, exist_ok=True)
        extra.write_text('cmd:=exec.Command("sh","-c","unknown")\n', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "added="):
            check(self.root)

    def test_new_subprocess_inside_allowed_file_is_rejected(self):
        target = self.root / "cmd" / "f96eval" / "main.go"
        with target.open("a", encoding="utf-8") as writer:
            writer.write('c:=exec.Command("arbitrary","binary")\n')
        with self.assertRaisesRegex(ValueError, "changed="):
            check(self.root)

    def test_existing_invocation_change_is_rejected(self):
        target = self.root / "cyclecontroller" / "controller.go"
        source = target.read_text(encoding="utf-8")
        target.write_text(source.replace("--synthetic-only", "--unbounded"), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed="):
            check(self.root)

    def test_missing_or_repeated_existing_invocation_is_rejected(self):
        target = self.root / "originalclaim" / "process_integration_test.go"
        source = target.read_text(encoding="utf-8")
        target.write_text(source.splitlines()[0] + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed="):
            check(self.root)
        target.write_text(source + source, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed="):
            check(self.root)

    def test_supervisor_custody_remains_separately_allowed(self):
        for rel in (
            "subprocesssupervisor/supervise.go",
            "cmd/forge-synthetic-supervisor/main_test.go",
        ):
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('cmd:=exec.Command("bounded","synthetic")\n', encoding="utf-8")
        check(self.root)


if __name__ == "__main__":
    unittest.main()
