"""Original V19 owner witness contract: no production task or network writes."""
from __future__ import annotations

import inspect
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from f139.local_controller import Database
import f139.nci04_v19_original_owner_nowrite_probe as probe


class ReadOnlyOwnerProbeTests(unittest.TestCase):
    def test_non_original_runner_rejected_before_any_owner_or_remote_calls(self):
        with tempfile.TemporaryDirectory(prefix="f139-nowrite-negative-") as tmp:
            with patch.dict(probe.os.environ, {"RUNNER_NAME":"NOT-ORIGINAL"}, clear=True):
                with self.assertRaisesRegex(probe.OwnerReadOnlyDenied,
                                            "ORIGINAL_WINDOWS_RUNNER_REQUIRED"):
                    probe.owner_witness(Path(tmp) / "absent.sqlite")

    def test_probe_never_mutates_task_controller_or_remote_git(self):
        source = inspect.getsource(probe)
        for forbidden in (
            "Disable-ScheduledTask", "Enable-ScheduledTask", "Stop-ScheduledTask",
            "Start-ScheduledTask", "Set-ScheduledTask", "Register-ScheduledTask",
            "transition_source(", "db.event(", "db.conn.execute(\"UPDATE ",
            "issues/807", "git push", "git checkout", "gh api -X",
            "requests.post", "activate_native(", "run_once(",
        ):
            self.assertNotIn(forbidden, source, forbidden)
        self.assertIn("Get-ScheduledTask", source)
        self.assertIn("RUNNER_NAME", source)
        self.assertIn("F139_V19_PROBE_DB", source)
        self.assertIn("GetFullPath", source)
        self.assertIn("GetCurrent()", source)
        self.assertIn("Database.open_readonly(db_path)", source)
        self.assertIn("with SingleOwner(db_path.with_suffix(\".lock\")):", source)
        self.assertIn("v19_original_release_readonly_preflight(", source)

    def test_probe_output_cannot_authorize_source_cutover(self):
        with tempfile.TemporaryDirectory(prefix="f139-nowrite-proof-") as td:
            db_path = Path(td) / "fixture.sqlite"
            db = Database.initialize(db_path, probe.SOURCE)
            db.close()
            readonly = {
                "schema":"forge.f139.v19.original-owner-release-readiness-nowrite.v1",
                "read_only":True,
                "runtime_cutover_authorized":False,
                "original_sqlite_writes":0,
                "github_writes":0,
            }
            with patch.object(probe, "owner_witness", return_value=True), patch.object(
                    probe, "v19_original_release_readonly_preflight",
                    return_value=readonly) as preflight:
                proof = probe.inspect_original_owner(db_path)
            self.assertEqual(proof, readonly)
            self.assertEqual(preflight.call_count, 1)
            _, kwargs = preflight.call_args
            self.assertTrue(callable(kwargs["owner_witness"]))
            self.assertTrue(callable(kwargs["original_get"]))
            self.assertEqual(kwargs["owner_witness"](), True)

    def test_foreign_authority_proof_rejected(self):
        with tempfile.TemporaryDirectory(prefix="f139-nowrite-reject-") as td:
            db_path = Path(td) / "fixture.sqlite"
            db = Database.initialize(db_path, probe.SOURCE)
            db.close()
            for broken in (
                {"read_only":True, "runtime_cutover_authorized":True,
                 "original_sqlite_writes":0, "github_writes":0},
                {"read_only":True, "runtime_cutover_authorized":False,
                 "original_sqlite_writes":1, "github_writes":0},
                {"read_only":False, "runtime_cutover_authorized":False,
                 "original_sqlite_writes":0, "github_writes":0},
            ):
                with self.subTest(broken=broken), patch.object(
                        probe, "owner_witness", return_value=True), patch.object(
                        probe, "v19_original_release_readonly_preflight",
                        return_value=broken):
                    with self.assertRaisesRegex(
                            probe.OwnerReadOnlyDenied, "UNEXPECTED_RELEASE_AUTHORITY"):
                        probe.inspect_original_owner(db_path)


if __name__ == "__main__":
    unittest.main()
