"""Current V41 Hybrid full backup and detached-restore adversarial fixtures."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner
from f139 import nci04_v41_hybrid_cold_bundle as bundle
from f139 import nci04_v41_hybrid_cold_pair as pair
from f139 import nci04_v41_cold_copy_verifier as cold

TARGET = "788673aae2d1b42a0c9152395a866e910191cbdd"


class HybridFullColdBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = self.root / "state.sqlite"
        with closing(Database.initialize(self.original, pair.V41_SOURCE)) as owner:
            owner.enable(legacy_suspended=True)
            owner.enable_native_two_slots()
        self.run_id = 78214
        self.folder = self.root / ("f139-hybrid-before-" + str(self.run_id))

    @staticmethod
    def custody(mode):
        if mode == "archive":
            ticket, run = "f139-nci04-fixture", 17
            prefix = "provider-custody/" + ticket + "/" + str(run)
            values = {"ubuntu-latest.zip": b"ubuntu-native",
                      "windows-latest.zip": b"windows-native"}
            values["manifest.json"] = json.dumps(
                {"ticket": ticket, "run_id": run,
                 "sha256": {key[:-4]: hashlib.sha256(value).hexdigest()
                            for key, value in values.items()}},
                sort_keys=True, separators=(",", ":")).encode("ascii")
            files = {prefix + "/" + key: val
                     for key, val in values.items()}
        else:
            files = {"prior-generation-custody/" + pair.V41_SOURCE
                     + "/f139-genenv-source.exe": b"frozen-generator"}
        def copy(db, folder, *, copy_files):
            result = {}
            for relative, payload in files.items():
                path = folder.joinpath(*relative.split("/"))
                if copy_files:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(payload)
                if path.read_bytes() != payload:
                    raise AssertionError("fixture custody mismatch")
                result[relative] = hashlib.sha256(payload).hexdigest()
            return result
        return copy

    def get(self, route):
        if route == "repos/spoonman136668-ai/FORGE/branches/main":
            return {"name": "main", "protected": True,
                    "commit": {"sha": pair.V41_SOURCE}}
        if route == "repos/spoonman136668-ai/FORGE/pulls/1660":
            return {"number": 1660, "state": "open", "merged": False,
                    "head": {"sha": TARGET},
                    "base": {"sha": pair.V41_SOURCE, "ref": "main"}}
        raise AssertionError("unexpected provider query")

    def attempt(self, *, run_id=None, lock=True, no_archives=False,
                active=False, provider=None):
        with patch.object(pair, "MIN_V41_HEAD", 0), \
             patch.object(pair, "verify_native_activation",
                          return_value=True), \
             patch.object(cold, "copy_provider_archives",
                          side_effect=(lambda *a, **k: {}
                                       if no_archives else
                                       self.custody("archive")(*a, **k))), \
             patch.object(cold, "copy_generation_executable",
                          side_effect=self.custody("binary")):
            with closing(Database.open_readonly(self.original)) as original:
                if not lock:
                    return bundle.stage_complete_cold_bundle(
                        original, provider or self.get, target_sha=TARGET,
                        run_id=self.run_id if run_id is None else run_id)
                with SingleOwner(self.original.with_suffix(".lock")):
                    return bundle.stage_complete_cold_bundle(
                        original, provider or self.get, target_sha=TARGET,
                        run_id=self.run_id if run_id is None else run_id)

    def detached(self, receipt, *, head_seq=None, sha=None, target=None,
                 run_id=None):
        # Synthetic fixtures have no genuine 1829 event history.
        with patch.object(pair, "MIN_V41_HEAD", 0):
            return bundle.verify_detached_restore(
                self.folder,
                expected_manifest_sha256=(
                    receipt["manifest_sha256"] if sha is None else sha),
                target_sha=TARGET if target is None else target,
                run_id=self.run_id if run_id is None else run_id,
                expected_head_seq=(receipt["original_head_seq"]
                                   if head_seq is None else head_seq),
                expected_head_sha256=receipt["original_head_sha256"])

    def test_full_custody_and_original_independent_detached_restore(self):
        receipt = self.attempt()
        self.assertTrue(receipt["independent_detached_restore_verified"])
        self.assertTrue(receipt["provider_archives_bytes_verified"])
        self.assertTrue(receipt["generation_binary_bytes_verified"])
        self.assertFalse(receipt["source_transition_authorized"])
        self.assertFalse(receipt["hybrid_admission"])
        self.assertEqual(receipt["original_owner_mutations"], 0)
        self.assertTrue((self.folder/"manifest.sha256.json").exists())
        self.original.rename(self.root/"source-moved.sqlite")
        proof = self.detached(receipt)
        self.assertTrue(proof["independent_detached_restore_verified"])
        self.assertFalse(proof["original_owner_host_verified"])
        self.assertFalse(proof["worker_dispatched"])
        self.assertFalse(list(self.folder.glob("f139-v41-hybrid-restore-*")))

    def test_manifest_source_identity_and_independent_anchor_denials(self):
        receipt = self.attempt()
        for named in (dict(sha="0"*64), dict(target="f"*40),
                      dict(head_seq=receipt["original_head_seq"]+1),
                      dict(run_id=self.run_id+1)):
            with self.subTest(named=named), self.assertRaises(
                    bundle.HybridBundleDenied):
                self.detached(receipt, **named)
        with self.assertRaises(bundle.HybridBundleDenied):
            self.detached(receipt, sha="bad")

    def test_bad_provider_identity_denies_creation(self):
        def wrong(route):
            if route.endswith("/pulls/1660"):
                return {"number": 1660, "state": "open",
                        "merged": False, "head": {"sha": "f"*40},
                        "base": {"sha": pair.V41_SOURCE, "ref": "main"}}
            return self.get(route)
        with self.assertRaisesRegex(pair.HybridColdPairDenied, "SOURCE_DRIFT"):
            self.attempt(provider=wrong)
        self.assertFalse(self.folder.exists())

    def test_missing_lock_denies_before_stage(self):
        with self.assertRaisesRegex(bundle.HybridBundleDenied, "LOCKED_QUERY_ONLY"):
            self.attempt(lock=False)
        self.assertFalse(self.folder.exists())

    def test_no_provider_backup_never_seals_and_never_replays(self):
        with self.assertRaisesRegex(bundle.HybridBundleDenied,
                                    "ORIGINAL_CUSTODY_MISSING"):
            self.attempt(no_archives=True)
        self.assertTrue(self.folder.exists())
        self.assertFalse((self.folder/"manifest.sha256.json").exists())
        with self.assertRaisesRegex(bundle.HybridBundleDenied,
                                    "BACKUP_RUN_REPLAY"):
            self.attempt()

    def test_run_id_immutable_create_only(self):
        self.attempt()
        with self.assertRaisesRegex(bundle.HybridBundleDenied,
                                    "BACKUP_RUN_REPLAY"):
            self.attempt()

    def test_copy_tampering_fails_detached_recovery(self):
        receipt = self.attempt()
        manifest = json.loads((self.folder/"manifest.sha256.json").read_bytes())
        for prefix in ("state.sqlite", "provider-custody/",
                       "prior-generation-custody/"):
            with self.subTest(prefix=prefix):
                key = next(k for k in manifest["files_sha256"]
                           if k.startswith(prefix))
                path = self.folder.joinpath(*key.split("/"))
                original = path.read_bytes()
                path.write_bytes(original + b"corruption")
                with self.assertRaises(Exception):
                    self.detached(receipt)
                path.write_bytes(original)

    def test_unlisted_file_symlink_and_sqlite_sidecar_denied(self):
        receipt = self.attempt()
        extra = self.folder/"unlisted.txt"
        extra.write_bytes(b"unknown")
        with self.assertRaisesRegex(bundle.HybridBundleDenied,
                                    "UNLISTED_OR_MISSING"):
            self.detached(receipt)
        extra.unlink()
        sidecar = Path(str(self.folder/"state.sqlite") + "-wal")
        sidecar.write_bytes(b"wal-only")
        with self.assertRaisesRegex(Exception, "UNLISTED_OR_MISSING|SIDECAR"):
            self.detached(receipt)
        sidecar.unlink()
        target = self.folder/"symlink.bin"
        try:
            target.symlink_to(self.folder/"state.sqlite")
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable on platform")
        with self.assertRaisesRegex(bundle.HybridBundleDenied,
                                    "UNTRUSTED_LINK"):
            self.detached(receipt)

    def test_manifest_replacement_is_not_accepted(self):
        receipt = self.attempt()
        path = self.folder/"manifest.sha256.json"
        orig = path.read_bytes()
        path.write_bytes(orig + b" ")
        with self.assertRaisesRegex(bundle.HybridBundleDenied,
                                    "INDEPENDENT_MANIFEST_HASH"):
            self.detached(receipt)
        path.write_bytes(orig)

    def test_original_unchanged_even_when_bundle_verified(self):
        before = self.original.read_bytes()
        self.attempt()
        self.assertEqual(self.original.read_bytes(), before)
        with closing(Database.open_readonly(self.original)) as db:
            self.assertEqual(db.meta()["source_sha"], pair.V41_SOURCE)
            self.assertFalse(pair.is_migrated(db))

    def test_no_live_task_policy_or_source_change_surface(self):
        import inspect
        raw = inspect.getsource(bundle)
        for forbidden in ("Disable-ScheduledTask", "Start-ScheduledTask",
                          "workflow_dispatch(", "create_ref(", "db.event(",
                          "UPDATE meta SET", "owner_policy_patch("):
            self.assertNotIn(forbidden, raw)


if __name__ == "__main__":
    unittest.main()
