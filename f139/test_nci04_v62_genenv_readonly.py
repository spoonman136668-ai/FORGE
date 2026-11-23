"""Read-only V62 owner GenEnv binary custody witness, no model/owner execution.

Exercise the real YAML-embedded Python script against disposable SQLite paths,
not actual original Windows tasks, credentials, source checkouts or controllers.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/f139-g54-v9-owner-cutover.yml"
OLD = "c06403c8b6035c6c7013866a7ea08cef1244b507"
HEAD = "e10be7151e19f2104ef2659ae04bef89b2711eea1659decb1477fd7354ff24ec"
PREFIX = "F139_V62_GENENV_READONLY="


def source() -> str:
    content = WORKFLOW.read_text(encoding="utf-8")
    begin = "          $genenvProbe=@'\n"
    finish = "\n          '@"
    if content.count(begin) != 1:
        raise AssertionError("exactly one authenticated read-only witness required")
    text = content.split(begin, 1)[1].split(finish, 1)[0]
    return "\n".join(line[10:] if line.startswith("          ") else ""
                     for line in text.splitlines()) + "\n"


class OriginalOwnerV62GenEnvReadonlyTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="f139-v62-readonly-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.path = self.root / "state.sqlite"
        self.bin = self.root / "genenv-source" / OLD / "f139-genenv-source.exe"
        self.bin.parent.mkdir(parents=True)
        self.bin.write_bytes(b"GENENV_FIXTURE_ONLY_NEVER_EXECUTED")
        self.pin = hashlib.sha256(self.bin.read_bytes()).hexdigest()
        self.release = {
            "schema": "forge.f139.source-transition.v47",
            "to_source_sha": OLD,
            "genenv_executable_sha256": self.pin,
            "generation_mechanism_sha256": "b" * 64,
        }
        self.write_db()

    def write_db(self, *, head=HEAD):
        if self.path.exists():
            self.path.unlink()
        with sqlite3.connect(self.path) as db:
            db.execute(
                "CREATE TABLE meta(id INTEGER, source_sha TEXT, "
                "head_seq INTEGER, head_hash TEXT)"
            )
            db.execute("INSERT INTO meta VALUES(1, ?, 1864, ?)", (OLD, head))
            db.execute("CREATE TABLE events(seq INTEGER, kind TEXT, payload TEXT)")
            db.execute(
                "INSERT INTO events VALUES (1858, 'SOURCE_TRANSITION_ADMITTED', ?)",
                (json.dumps(self.release, sort_keys=True),)
            )

    def run_probe(self, *, source_arg=OLD):
        return subprocess.run(
            [sys.executable, "-B", "-", str(self.path), source_arg],
            input=source(), capture_output=True, text=True,
            timeout=30, check=False,
        )

    def receipt(self):
        result = self.run_probe()
        self.assertEqual(result.returncode, 0, result.stderr[-750:])
        self.assertTrue(result.stdout.startswith(PREFIX), result.stdout[-400:])
        return json.loads(result.stdout[len(PREFIX):])

    def test_exact_read_only_probe_and_no_raw_paths(self):
        before = self.path.read_bytes()
        output = self.receipt()
        self.assertEqual(output["binary_custody"], "BINARY_PIN_MATCH_READONLY")
        self.assertTrue(output["source_release_bound"])
        self.assertTrue(output["binary_pin_present"])
        self.assertTrue(output["typed_mechanism_pin_present"])
        self.assertFalse(output["backend_failure_cause_proven"])
        for key in ("provider_gets", "generator_invocations",
                    "original_mutations"):
            self.assertEqual(output[key], 0)
        self.assertFalse(output["scientific_first_use"])
        self.assertFalse(output["worker_dispatched"])
        self.assertEqual(self.path.read_bytes(), before)
        for unsafe in ("GENENV_FIXTURE", str(self.root), self.pin,
                       "token", "secret", "error_message"):
            self.assertNotIn(unsafe, json.dumps(output))

    def test_missing_binary_preserves_ledger(self):
        self.bin.unlink()
        before = self.path.read_bytes()
        output = self.receipt()
        self.assertEqual(output["binary_custody"], "BINARY_MISSING")
        self.assertEqual(self.path.read_bytes(), before)

    def test_digest_mismatch_does_not_execute_generator(self):
        self.bin.write_bytes(b"TAMPERED_SOURCE")
        output = self.receipt()
        self.assertEqual(output["binary_custody"], "BINARY_DIGEST_MISMATCH")
        self.assertEqual(output["generator_invocations"], 0)

    def test_bad_release_or_pin_is_only_a_negative_witness(self):
        self.release["schema"] = "forge.f139.source-transition.v36"
        self.write_db()
        self.assertEqual(self.receipt()["binary_custody"], "SOURCE_RELEASE_UNBOUND")
        self.release["schema"] = "forge.f139.source-transition.v47"
        self.release["genenv_executable_sha256"] = "not-a-digest"
        self.write_db()
        self.assertEqual(self.receipt()["binary_custody"], "BINARY_PIN_UNBOUND")
        self.release["genenv_executable_sha256"] = self.pin
        self.release["generation_mechanism_sha256"] = ""
        self.write_db()
        self.assertEqual(
            self.receipt()["binary_custody"], "TYPED_MECHANISM_PIN_UNBOUND")

    def test_wrong_original_source_or_event_head_denied(self):
        before = self.path.read_bytes()
        wrong = self.run_probe(source_arg="0" * 40)
        self.assertNotEqual(wrong.returncode, 0)
        self.assertNotIn(PREFIX, wrong.stdout)
        self.assertEqual(self.path.read_bytes(), before)
        self.write_db(head="1" * 64)
        wrong = self.run_probe()
        self.assertNotEqual(wrong.returncode, 0)
        self.assertNotIn(PREFIX, wrong.stdout)

    def test_workflow_scoped_to_existing_owner_no_mutations(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        start = workflow.index("  read-only-status:\n")
        end = workflow.index("      - name: V41 original-owner locked issue/", start)
        status = workflow[start:end]
        self.assertIn("runs-on: [self-hosted, Windows, forge-codex-isolated]",
                      status)
        self.assertIn("F139-V9-STATUS ", status)
        self.assertIn("F139_G54_STATUS_READ_ONLY=PASS", status)
        self.assertIn("F139_V62_GENENV_READONLY=", status)
        self.assertIn("F139_V62_GENENV_READONLY_SOURCE_DENIED", status)
        for forbidden in (
            "Disable-ScheduledTask", "Stop-ScheduledTask",
            "Enable-ScheduledTask", "Start-ScheduledTask",
            "Set-ScheduledTask", "Register-ScheduledTask",
            "Unregister-ScheduledTask", "Stop-Process", "Start-Process",
            "gh api -X POST", "gh api -X PATCH",
            "gh api --method POST", "gh api --method PATCH",
        ):
            self.assertNotIn(forbidden, status)
        # V41 never turns a valid current V9 owner audit into an outdated
        # historical-source failure.
        self.assertIn(
            "github.sha == '2c7caad5a4502d4b874a11d57207a35cf033eb08'",
            workflow[end:end+430],
        )


if __name__ == "__main__":
    unittest.main()
