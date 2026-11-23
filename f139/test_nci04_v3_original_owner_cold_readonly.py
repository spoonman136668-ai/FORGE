"""Synthetic V3 composition controls; NEVER run a real owner or scientific trial."""
from __future__ import annotations

from copy import deepcopy
import unittest
from unittest.mock import patch

from f139.local_controller import F139Error, SingleOwner
from f139.nci04_native_contract import canonical
from f139.nci04_v3_original_owner_cold_readonly import (
    SCHEMA, V3_CERT_NAME, V3ColdReadDenied,
    inspect_original_owner_cold_readonly,
)
from f139.test_nci04_v2_failed_prepare_restore_original import (
    RecoveryContractTests,
)
from f139.test_nci04_v3_remote_readonly_preflight import (
    HEAD, MERGE, PR, REPO, RUNS, TREE, fixture,
)


class V3OriginalColdReadOnlyTests(unittest.TestCase):
    def setUp(self):
        # Reuse the existing signed V1, three-task SQLite, and original
        # recovered-owner fixture rather than building a second custody oracle.
        old = RecoveryContractTests("test_cold_original_history_and_signature")
        old.setUp()
        self.addCleanup(old.doCleanups)
        self.old = old
        self.api = fixture()

    def run_gate(self, **overrides):
        args = {
            "db": self.old.db,
            "api": self.api,
            "key": self.old.key,
            "folder": self.old.folder,
            "owner_source_sha": MERGE,
            "owner_source_tree": TREE,
            "pr_number": PR,
            "pr_head_sha": HEAD,
            **RUNS,
        }
        args.update(overrides)
        with patch.object(SingleOwner, "held", return_value=True), patch(
            "f139.nci04_v2_failed_prepare_restore_original.read_lifecycle",
            return_value=(self.old.release, self.old.entries),
        ):
            return inspect_original_owner_cold_readonly(**args)

    def test_remote_and_signed_cold_v1_both_verified_without_authority(self):
        first = self.run_gate()
        second = self.run_gate()
        self.assertEqual(first, second)
        self.assertEqual(first["schema"], SCHEMA)
        self.assertEqual(first["source_commit"], MERGE)
        self.assertEqual(first["qualified_head"], HEAD)
        self.assertEqual(first["verified_terminal_tasks"], 3)
        self.assertRegex(first["previous_certificate_sha256"], r"^[a-f0-9]{64}$")
        self.assertEqual(first["original_windows_sid_and_task"], "NOT_CHECKED")
        self.assertEqual(first["installed_checkout"], "NOT_CHECKED")
        for key in ("safe_to_disable_task", "source_forward_authorized",
                    "signed_v3_certificate", "scientific_first_use"):
            self.assertFalse(first[key])
        self.assertEqual(first["sqlite_mutations"], 0)
        self.assertEqual(first["worker_dispatches"], 0)

    def test_missing_original_v1_certificate_denied(self):
        (self.old.folder / "fresh-original-owner-source-forward.json").unlink()
        with self.assertRaisesRegex(V3ColdReadDenied, "HISTORY_UNVERIFIED"):
            self.run_gate()

    def test_wrong_original_hmac_denied(self):
        path = self.old.folder / "fresh-original-owner-source-forward.json"
        bad = dict(self.old.doc, owner_signature="0" * 64)
        path.write_bytes(canonical(bad))
        with self.assertRaises(V3ColdReadDenied):
            self.run_gate()

    def test_v2_certificate_collision_denied(self):
        (self.old.folder / "fresh-original-owner-source-forward-v2.json").write_bytes(b"{}")
        with self.assertRaises(V3ColdReadDenied):
            self.run_gate()

    def test_v3_certificate_already_exists_rejected_before_remote(self):
        (self.old.folder / V3_CERT_NAME).write_bytes(b"{}")
        with self.assertRaisesRegex(V3ColdReadDenied, "ALREADY_PRESENT"):
            self.run_gate()
        self.assertEqual(self.api.calls, [])

    def test_original_lock_missing_rejected_before_remote(self):
        with patch.object(SingleOwner, "held", return_value=False):
            with self.assertRaisesRegex(V3ColdReadDenied, "LOCK_REQUIRED"):
                inspect_original_owner_cold_readonly(
                    self.old.db, self.api, self.old.key, self.old.folder,
                    owner_source_sha=MERGE, owner_source_tree=TREE,
                    pr_number=PR, pr_head_sha=HEAD, **RUNS,
                )
        self.assertEqual(self.api.calls, [])

    def test_unfinished_original_task_denied(self):
        self.old.db.conn.execute(
            "UPDATE tasks SET stage='WAIT_PROVIDER' WHERE ticket='c'")
        with self.assertRaises(V3ColdReadDenied):
            self.run_gate()

    def test_negative_original_custody_denied(self):
        self.old.entries[-1]["negative"] = {"disposition": "unresolved"}
        with self.assertRaises(V3ColdReadDenied):
            self.run_gate()

    def test_remote_provider_failure_denied_without_cold_audit(self):
        with patch.object(self.api, "get",
                          side_effect=F139Error("F139_GITHUB_API_FAILED")), patch(
            "f139.nci04_v3_original_owner_cold_readonly.validate",
            side_effect=AssertionError("cold audit must not run"),
        ) as cold:
            with self.assertRaises(V3ColdReadDenied):
                self.run_gate()
            cold.assert_not_called()

    def test_merged_git_tree_changed_rejected(self):
        path = REPO + "/git/commits/" + HEAD
        self.api.documents[path]["tree"]["sha"] = "f" * 40
        with self.assertRaises(V3ColdReadDenied):
            self.run_gate()

    def test_main_moves_after_cold_audit_rejected(self):
        original = self.api.get
        n = [0]
        def get(path):
            if path == REPO + "/branches/main":
                n[0] += 1
                if n[0] == 3:
                    return {"name": "main", "protected": True,
                            "commit": {"sha": "f" * 40}}
            return original(path)
        with patch.object(self.api, "get", side_effect=get):
            with self.assertRaises(V3ColdReadDenied):
                self.run_gate()
        self.assertEqual(n[0], 3)

    def test_any_sqlite_mutation_during_cold_check_rejected(self):
        from f139.nci04_v3_original_owner_cold_readonly import (
            inspect_original_owner_cold_readonly as inspect,
        )
        def mutate(*args, **kwargs):
            self.old.db.conn.execute("INSERT INTO tasks VALUES ('x','VERIFIED')")
            return {
                "original_source_sha": self.old.doc["owner_source_sha"],
                "original_source_tree": self.old.doc["owner_source_tree"],
                "verified_tasks": 3,
                "v2_certificate_present": False,
            }
        with patch.object(SingleOwner, "held", return_value=True), patch(
            "f139.nci04_v3_original_owner_cold_readonly.validate",
            side_effect=mutate,
        ):
            with self.assertRaises(V3ColdReadDenied):
                inspect(
                    self.old.db, self.api, self.old.key, self.old.folder,
                    owner_source_sha=MERGE, owner_source_tree=TREE,
                    pr_number=PR, pr_head_sha=HEAD, **RUNS,
                )

    def test_wrong_source_or_unsafe_inputs_do_not_mutate(self):
        for bad in (
            {"pr_number": 1870},
            {"owner_source_sha": HEAD},
            {"key": "too-short"},
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(V3ColdReadDenied):
                    self.run_gate(**bad)

    def test_source_has_no_windows_task_or_provider_write_path(self):
        from pathlib import Path
        source = Path(__file__).with_name(
            "nci04_v3_original_owner_cold_readonly.py").read_text()
        for forbidden in ("Register-ScheduledTask", "Set-ScheduledTask",
                          "Stop-ScheduledTask", "Enable-ScheduledTask",
                          "api.post(", "api.patch(", "write(", "sign("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
