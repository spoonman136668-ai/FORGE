"""Frozen event-1832 cold-copy contract; no live owner/backup touched."""
import json
import tempfile
import unittest
from pathlib import Path

from f139.nci04_native_contract import canonical, digest
from f139 import nci04_v41_hybrid_event1833_successor as successor
from f139 import nci04_v41_hybrid_event1833_cold as cold


class Event1832ColdContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.target = "b" * 40
        self.run_id = 43799999111
        self.folder = Path(self.tmp.name) / (
            "f139-v40-before-" + str(self.run_id))
        self.folder.mkdir()
        self.manifest = {
            "schema": cold.SCHEMA,
            "original_source_sha": successor.SOURCE,
            "target_source_sha": self.target,
            "run_id": self.run_id,
            "original_head_seq": successor.PREDECESSOR_SEQ,
            "original_head_sha256": "a" * 64,
            "predecessor_backup_run_id": 43769577997,
            "predecessor_backup_manifest_sha256": "a" * 64,
            "files_sha256": {"state.sqlite": "c" * 64},
            "logical_all_tables_sha256": "d" * 64,
            "provider_archives_manifest_sha256": "e" * 64,
            "generation_binary_manifest_sha256": "f" * 64,
            "negative_custody_manifest_sha256": "1" * 64,
            "restored_sqlite_sha256": "2" * 64,
            "original_owner_mutations": 0,
            "new_dispatches": 0,
            "source_transition_authorized": False,
            "owner_policy_modified": False,
            "task_resume_authorized": False,
            "hybrid_admission": False,
            "scientific_first_use": False,
        }

    def sealed(self, manifest):
        p = self.folder / "manifest.sha256.json"
        raw = canonical(manifest)
        p.write_bytes(raw)
        return digest(raw)

    def test_manifest_contract_accepts_exact_held_event1832_shape(self):
        self.assertEqual(set(self.manifest), cold.FIELDS)
        sha = self.sealed(self.manifest)
        self.assertEqual(
            cold._manifest(self.folder, self.target, self.run_id, sha),
            self.manifest)

    def test_manifest_guard_denies_wrong_source_history_and_science(self):
        modifications = (
            ("original_source_sha", "c" * 40),
            ("original_head_seq", 1831),
            ("original_head_sha256", "broken"),
            ("target_source_sha", "c" * 40),
            ("run_id", self.run_id + 1),
            ("source_transition_authorized", True),
            ("owner_policy_modified", True),
            ("task_resume_authorized", True),
            ("hybrid_admission", True),
            ("scientific_first_use", True),
            ("original_owner_mutations", 1),
            ("new_dispatches", 1),
            ("restored_sqlite_sha256", "broken"),
            ("predecessor_backup_manifest_sha256", "broken"),
        )
        for key, value in modifications:
            with self.subTest(key=key):
                changed = {**self.manifest, key: value}
                sha = self.sealed(changed)
                with self.assertRaisesRegex(
                        cold.Event1832ColdDenied,
                        "EVENT1832_COLD_MANIFEST_FIELDS_OR_AUTHORITY_DRIFT"):
                    cold._manifest(
                        self.folder, self.target, self.run_id, sha)

    def test_missing_and_tampered_manifest_fail_before_bytes_read(self):
        with self.assertRaisesRegex(
                cold.Event1832ColdDenied, "SEALED_MANIFEST_MISSING"):
            cold.verify_detached_restore(
                self.folder, target=self.target,
                run_id=self.run_id, manifest_sha="f"*64)
        good = self.sealed(self.manifest)
        (self.folder / "manifest.sha256.json").write_bytes(b"{}")
        with self.assertRaisesRegex(
                cold.Event1832ColdDenied, "MANIFEST_SHA_MISMATCH"):
            cold.verify_detached_restore(
                self.folder, target=self.target,
                run_id=self.run_id, manifest_sha=good)

    def test_no_original_owner_without_mutex_or_unqualified_implicit_release(self):
        original = Path(self.tmp.name) / "state.sqlite"
        self.assertEqual(cold.folder_for(original, self.run_id),
                         self.folder)
        with self.assertRaisesRegex(
                cold.Event1832ColdDenied, "ORIGINAL_OWNER_COLD_AUTHORIZATION_REQUIRED"):
            cold.stage_complete_cold_bundle(
                None, target=self.target, run_id=self.run_id,
                disabled_owner_witness=lambda: True,
                release_witness=lambda: True)
        src = Path(cold.__file__).read_text("utf-8")
        for forbidden in (
            "Start-ScheduledTask", "Enable-ScheduledTask",
            "Disable-ScheduledTask", "Stop-ScheduledTask",
            "workflow_dispatch", "gh workflow run",
            "gh api --method PATCH", "OPENAI_API_KEY"):
            self.assertNotIn(forbidden, src)
        self.assertIn("original.conn.backup(output)", src)
        self.assertIn("verify_detached_restore(", src)
        self.assertIn("bundle._validate_files(", src)
        self.assertIn("SingleOwner.held(", src)


if __name__ == "__main__":
    unittest.main()
