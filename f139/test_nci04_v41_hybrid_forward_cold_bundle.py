"""Frozen V38 complete-cold-manifest contract and negative controls.

No owner action, real evidence bytes, live source or science first-use are
produced by these tests. Full owner acceptance requires the real Windows
task/SID, exact new source and independently detached original backup.
"""
import tempfile
import unittest
from pathlib import Path

from f139 import nci04_v41_hybrid_forward_cold_bundle as bundle
from f139 import nci04_v41_hybrid_forward_repair as forward


class ForwardColdContractTests(unittest.TestCase):
    def setUp(self):
        self.target = "b" * 40
        self.manifest = {
            "schema": bundle.SCHEMA,
            "original_source_sha": forward.FROM,
            "candidate_sha": self.target,
            "run_id": 34567,
            "original_head_seq": forward.V37_SEQ,
            "original_head_sha256": forward.V37_HEAD,
            "predecessor_backup_run_id": 43631799596,
            "predecessor_backup_manifest_sha256": "c" * 64,
            "files_sha256": {"state.sqlite": "a" * 64},
            "logical_all_tables_sha256": "d" * 64,
            "provider_archives_manifest_sha256": "e" * 64,
            "generation_binary_manifest_sha256": "f" * 64,
            "negative_custody_manifest_sha256": "1" * 64,
            "restored_sqlite_sha256": "2" * 64,
            "original_owner_mutations": 0,
            "new_dispatches": 0,
            "owner_quiescence_verified": False,
            "source_transition_authorized": False,
            "owner_policy_modified": False,
            "worker_dispatched": False,
            "hybrid_admission": False,
            "scientific_first_use": False,
        }

    def test_frozen_v38_manifest_shape_is_exact(self):
        self.assertEqual(set(self.manifest), bundle.FILES)
        bundle._validate_manifest(self.manifest, self.target, 34567)

    def test_old_precommit_source_cannot_be_presented_as_v38_backup(self):
        old = dict(self.manifest)
        old["original_source_sha"] = (
            "1a40fe4e3ec6e93a1631d59863b95e90981d734e")
        with self.assertRaisesRegex(
                bundle.ForwardColdDenied, "MANIFEST_OR_AUTHORITY_DRIFT"):
            bundle._validate_manifest(old, self.target, 34567)
        old = dict(self.manifest)
        old["original_head_seq"] = 1829
        with self.assertRaisesRegex(
                bundle.ForwardColdDenied, "MANIFEST_OR_AUTHORITY_DRIFT"):
            bundle._validate_manifest(old, self.target, 34567)

    def test_replay_science_wrong_target_or_unexpected_fields_are_denied(self):
        for field, value in (
            ("candidate_sha", forward.FROM),
            ("run_id", 34568),
            ("source_transition_authorized", True),
            ("hybrid_admission", True),
            ("scientific_first_use", True),
            ("new_dispatches", 1),
            ("original_owner_mutations", 1),
            ("restored_sqlite_sha256", "not-a-hash"),
        ):
            with self.subTest(field=field):
                corrupted = {**self.manifest, field: value}
                with self.assertRaisesRegex(
                        bundle.ForwardColdDenied,
                        "MANIFEST_OR_AUTHORITY_DRIFT"):
                    bundle._validate_manifest(corrupted, self.target, 34567)
        with self.assertRaisesRegex(
                bundle.ForwardColdDenied, "MANIFEST_OR_AUTHORITY_DRIFT"):
            bundle._validate_manifest(
                {**self.manifest, "unapproved": True}, self.target, 34567)

    def test_missing_fresh_folder_cannot_be_interpreted_as_old_bundle(self):
        with tempfile.TemporaryDirectory() as temp:
            old = Path(temp) / "f139-hybrid-before-43631799596"
            old.mkdir()
            with self.assertRaisesRegex(
                    bundle.ForwardColdDenied,
                    "CANONICAL_NONLINK_FOLDER_REQUIRED"):
                bundle.verify_detached_restore(
                    old, target=self.target, run_id=34567,
                    manifest_sha="c" * 64)

    def test_no_implicit_source_stage_or_second_controller(self):
        with self.assertRaisesRegex(
                bundle.ForwardColdDenied,
                "INDEPENDENT_OWNER_RELEASE_AND_LOCK_REQUIRED"):
            bundle.stage_complete_cold_bundle(
                None, {}, target=self.target, run_id=34567,
                owner_disabled_witness=lambda: True,
                release_witness=lambda: True)
        source = Path(bundle.__file__).read_text("utf-8")
        for forbidden in ("Start-ScheduledTask", "Stop-ScheduledTask",
                          "Enable-ScheduledTask", "Disable-ScheduledTask",
                          "workflow_dispatch", "gh workflow run",
                          "gh api --method PATCH"):
            self.assertNotIn(forbidden, source)
        self.assertIn("f139-v38-before-", source)


if __name__ == "__main__":
    unittest.main()
