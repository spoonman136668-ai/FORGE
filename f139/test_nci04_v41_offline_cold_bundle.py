"""Offline V41 backup/restore development fixtures: never original owner."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner
from f139 import nci04_v41_offline_cold_bundle as bundle
from f139 import nci04_v41_cold_copy_verifier as cold

TARGET = "7fb1bb9e0fe9439a6a7da8b66c6b0ef7acdc7595"


class OfflineColdBundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.original = self.root / "state.sqlite"
        with closing(Database.initialize(self.original, cold.FROM)):
            pass
        self.run_id = 77121
        self.folder = self.root / ("f139-v41-before-" + str(self.run_id))

    def history(self, db):
        meta = db.meta()
        return {
            "source_sha": cold.FROM, "original_head_seq": meta["head_seq"],
            "original_head_sha256": meta["head_hash"],
            "verified_historical_tasks": 153,
            "quarantined_historical_tasks": 56,
            "source_transition_authorized": False, "scientific_first_use": False,
        }

    def remote(self, get, target):
        return {
            "original_source_sha": cold.FROM,
            "target_source_sha": target, "unique_eligible_issues": 200,
            "source_transition_authorized": False, "scientific_first_use": False,
        }

    @staticmethod
    def custody(kind):
        if kind == "archive":
            ticket = "f139-nci04-test"
            run = 11
            prefix = "provider-custody/" + ticket + "/" + str(run)
            blob = {"ubuntu-latest.zip": b"ubuntu-payload",
                    "windows-latest.zip": b"windows-payload"}
            blob["manifest.json"] = (
                json.dumps({"ticket": ticket, "run_id": run,
                            "sha256": {name[:-4]: hashlib.sha256(value).hexdigest()
                                       for name, value in blob.items()}},
                           sort_keys=True, separators=(",", ":")).encode("ascii"))
            files = {prefix + "/" + name: value for name, value in blob.items()}
        else:
            files = {"prior-generation-custody/" + cold.FROM +
                     "/f139-genenv-source.exe": b"binary"}
        def handler(db, folder, *, copy_files):
            result = {}
            for relative, payload in files.items():
                path = folder.joinpath(*relative.split("/"))
                if copy_files:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(payload)
                if path.read_bytes() != payload:
                    raise ValueError("custody mismatch")
                result[relative] = hashlib.sha256(payload).hexdigest()
            return result
        return handler

    def attempt(self, *, run_id=None, locked=True, wrong_remote=False,
                broken_archive=False, mutate_backup=False):
        with SingleOwner(self.original.with_suffix(".lock")):
            with closing(Database.open_readonly(self.original)) as db:
                def remote(get, target):
                    doc = self.remote(get, target)
                    if wrong_remote:
                        doc["unique_eligible_issues"] = 199
                    return doc

                def archive(db, folder, *, copy_files):
                    if broken_archive:
                        return {}
                    return self.custody("archive")(db, folder, copy_files=copy_files)

                with patch.object(bundle.SingleOwner, "held", return_value=locked), \
                     patch.object(cold, "original_ledger_preflight", side_effect=self.history), \
                     patch.object(cold, "source_preflight", side_effect=remote), \
                     patch.object(cold, "copy_provider_archives", side_effect=archive), \
                     patch.object(cold, "copy_generation_executable",
                                  side_effect=self.custody("binary")):
                    if mutate_backup:
                        real = cold.verify_cold_copy
                        def tamper(original, backup, get, **kwargs):
                            backup.write_bytes(b"tampered backup")
                            return real(original, backup, get, **kwargs)
                        with patch.object(cold, "verify_cold_copy", side_effect=tamper):
                            return bundle.stage_offline_cold_bundle(
                                db, lambda _: None, target=TARGET,
                                run_id=self.run_id if run_id is None else run_id)
                    return bundle.stage_offline_cold_bundle(
                        db, lambda _: None, target=TARGET,
                        run_id=self.run_id if run_id is None else run_id)

    def test_real_sqlite_backup_and_disposable_restoration(self):
        result = self.attempt()
        self.assertEqual(result["schema"], bundle.SCHEMA)
        self.assertEqual(result["files_sha256"]["state.sqlite"],
                         hashlib.sha256((self.folder/"state.sqlite").read_bytes()).hexdigest())
        self.assertEqual(result["new_dispatches"], 0)
        self.assertFalse(result["release_qualified"])
        self.assertFalse(result["owner_quiescence_verified"])
        self.assertFalse(result["scientific_first_use"])
        self.assertTrue((self.folder/"manifest.sha256.json").is_file())
        self.assertFalse(list(self.folder.glob("v41-restore-*")))
        with closing(sqlite3.connect(str(self.folder/"state.sqlite"))) as db:
            self.assertEqual(db.execute("PRAGMA quick_check").fetchone()[0], "ok")
        for suffix in ("-wal", "-shm", "-journal"):
            self.assertFalse(Path(str(self.folder/"state.sqlite") + suffix).exists())


    def test_historical_negative_zip_adjunct_survives_cold_detached_restore(self):
        # Synthetic payloads exercise authentic filesystem semantics; this is
        # engineering qualification, not a real owner or scientific receipt.
        payloads = {
            "native-negative/f139-nci04-first/11/ubuntu-latest.zip":
                b"negative-failed-provider-1",
            "native-negative/f139-nci04-second/22/ubuntu-latest.zip":
                b"negative-failed-provider-2",
        }
        expected = {path: hashlib.sha256(data).hexdigest()
                    for path, data in payloads.items()}
        definitions = tuple(("NATIVE_NEGATIVE_CUSTODIED" if i == 0
                             else "NATIVE_SPLIT_NEGATIVE_CUSTODIED",
                             path, expected[path])
                            for i, path in enumerate(payloads))
        for relative, data in payloads.items():
            source = self.root.joinpath(*relative.split("/"))
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(data)
        before = hashlib.sha256(self.original.read_bytes()).hexdigest()
        with patch.object(cold, "_negative_definitions",
                          return_value=definitions), \
             patch.object(cold, "required_negative_custody",
                          return_value=expected):
            receipt = self.attempt()
            self.assertEqual(receipt["negative_custody_manifest_sha256"],
                             bundle.digest(bundle.canonical(expected)))
            self.assertEqual({k: v for k, v in receipt["files_sha256"].items()
                              if k.startswith("native-negative/")}, expected)
            self.original.rename(self.original.with_suffix(".offline"))
            restored = self.offline(receipt)
            self.assertTrue(restored["independent_restore_verified"])
            self.assertFalse(restored["source_transition_authorized"])
        self.assertEqual(
            hashlib.sha256(self.original.with_suffix(".offline").read_bytes()).hexdigest(),
            before)
        self.assertFalse(list(self.folder.glob("f139-v41-independent-restore-*")))

    def test_historical_negative_missing_or_tampered_fails_closed(self):
        payload = b"custodied-negative"
        relative = "native-negative/f139-nci04-first/11/ubuntu-latest.zip"
        wanted = hashlib.sha256(payload).hexdigest()
        definitions = (("NATIVE_NEGATIVE_CUSTODIED", relative, wanted),)
        original = self.root.joinpath(*relative.split("/"))
        original.parent.mkdir(parents=True)
        original.write_bytes(payload)
        target = self.root / "detached"
        target.mkdir()
        with patch.object(cold, "_negative_definitions",
                          return_value=definitions):
            expected = {relative: wanted}
            self.assertEqual(cold.copy_negative_custody(
                self.root, target, expected, copy_files=True), expected)
            self.assertEqual(cold.copy_negative_custody(
                self.root, target, expected, copy_files=False), expected)
            copied = target.joinpath(*relative.split("/"))
            copied.write_bytes(b"tampered")
            with self.assertRaisesRegex(Exception, "NEGATIVE_CUSTODY_COPIED_BYTES_CHANGED"):
                cold.copy_negative_custody(self.root, target, expected,
                                           copy_files=False)
            copied.write_bytes(payload)
            original.unlink()
            with self.assertRaisesRegex(Exception, "NEGATIVE_CUSTODY_ORIGINAL_FILE_INVALID"):
                cold.copy_negative_custody(self.root, target, expected,
                                           copy_files=False)
            with self.assertRaisesRegex(Exception, "NEGATIVE_CUSTODY_SCOPE"):
                cold.copy_negative_custody(
                    self.root, target, {"native-negative/unlisted.zip": wanted},
                    copy_files=False)

    def test_run_id_is_create_only_with_no_replay(self):
        self.attempt()
        with self.assertRaisesRegex(bundle.V41BundleDenied, "RUN_ALREADY_STAGED"):
            self.attempt()
        self.assertEqual(len(list(self.root.glob("f139-v41-before-*"))), 1)

    def test_remote_or_mutex_mismatch_prevents_bundle_creation(self):
        with self.assertRaisesRegex(bundle.V41BundleDenied, "FROZEN_LEDGER_OR_REMOTE"):
            self.attempt(wrong_remote=True)
        self.assertFalse(self.folder.exists())
        with self.assertRaisesRegex(bundle.V41BundleDenied, "LOCKED_QUERY_ONLY"):
            self.attempt(locked=False)
        self.assertFalse(self.folder.exists())

    def test_missing_archive_custody_never_seals_partial_bundle(self):
        with self.assertRaisesRegex(bundle.V41BundleDenied,
                                    "PROVIDER_OR_EXECUTABLE_CUSTODY_MISSING"):
            self.attempt(broken_archive=True)
        self.assertTrue(self.folder.exists())
        self.assertFalse((self.folder/"manifest.sha256.json").exists())
        with self.assertRaisesRegex(bundle.V41BundleDenied, "RUN_ALREADY_STAGED"):
            self.attempt()

    def test_backup_tamper_never_seals_receipt(self):
        with self.assertRaises(Exception):
            self.attempt(mutate_backup=True)
        self.assertFalse((self.folder/"manifest.sha256.json").exists())

    def test_unwritable_original_connection_is_rejected(self):
        with SingleOwner(self.original.with_suffix(".lock")):
            with closing(Database(self.original)) as writable:
                with self.assertRaisesRegex(bundle.V41BundleDenied,
                                            "LOCKED_QUERY_ONLY"):
                    bundle.stage_offline_cold_bundle(
                        writable, lambda _: None, target=TARGET, run_id=77)
        self.assertFalse((self.root/"f139-v41-before-77").exists())

    def test_no_dispatch_task_or_owner_transition_api(self):
        import inspect
        source = inspect.getsource(bundle)
        for prohibited in ("Disable-ScheduledTask", "Start-ScheduledTask",
                           "workflow_dispatch(", "create_ref(", "db.event(",
                           "UPDATE meta SET", "owner_policy_patch("):
            self.assertNotIn(prohibited, source)


    def offline(self, receipt, *, target=TARGET, run_id=None, head_seq=None,
                head_sha=None, manifest_sha=None):
        return bundle.verify_sealed_bundle_offline(
            self.folder, expected_manifest_sha256=(
                receipt["manifest_sha256"] if manifest_sha is None else manifest_sha),
            target=target,
            run_id=self.run_id if run_id is None else run_id,
            expected_head_seq=(
                receipt["original_head_seq"] if head_seq is None else head_seq),
            expected_head_sha256=(
                receipt["original_head_sha256"] if head_sha is None else head_sha))

    def test_detached_offline_restore_does_not_need_original_or_network(self):
        receipt = self.attempt()
        self.original.rename(self.original.with_suffix(".offline"))
        outcome = self.offline(receipt)
        self.assertTrue(outcome["independent_restore_verified"])
        self.assertFalse(outcome["original_owner_host_verified"])
        self.assertFalse(outcome["source_transition_authorized"])
        self.assertEqual(outcome["manifest_sha256"], receipt["manifest_sha256"])
        self.assertFalse(list(self.folder.glob("f139-v41-independent-restore-*")))

    def test_manifest_digest_and_external_original_identity_must_match(self):
        receipt = self.attempt()
        with self.assertRaises(bundle.V41BundleDenied):
            self.offline(receipt, manifest_sha="0" * 64)
        with self.assertRaises(bundle.V41BundleDenied):
            self.offline(receipt, target="f" * 40)
        with self.assertRaises(bundle.V41BundleDenied):
            self.offline(receipt, head_seq=receipt["original_head_seq"] + 1)
        with self.assertRaises(bundle.V41BundleDenied):
            self.offline(receipt, head_sha=("f" * 64 if receipt["original_head_sha256"] == "0" * 64 else "0" * 64))
        with self.assertRaises(bundle.V41BundleDenied):
            self.offline(receipt, run_id=self.run_id + 1)

    def test_offline_tamper_to_sqlite_provider_and_generator_denied(self):
        for prefix in ("state.sqlite", "provider-custody/",
                       "prior-generation-custody/"):
            with self.subTest(prefix=prefix):
                with tempfile.TemporaryDirectory() as tmp:
                    receipt = self.attempt(run_id=self.run_id)
                    relative = next(k for k in receipt["files_sha256"]
                                    if k.startswith(prefix))
                    target = self.folder.joinpath(*relative.split("/"))
                    original = target.read_bytes()
                    target.write_bytes(original + b"tamper")
                    with self.assertRaises(bundle.V41BundleDenied):
                        self.offline(receipt)
                    target.write_bytes(original)
                    # Clean up the staged bundle without touching the source.
                    import shutil
                    shutil.rmtree(self.folder)
        self.assertFalse(self.folder.exists())

    def test_unlisted_file_or_sidecar_fails_and_no_issuance(self):
        receipt = self.attempt()
        extra = self.folder / "not-in-manifest"
        extra.write_bytes(b"unlisted")
        with self.assertRaisesRegex(bundle.V41BundleDenied,
                                    "UNLISTED_OR_MISSING_BUNDLE_FILE"):
            self.offline(receipt)
        extra.unlink()
        sidecar = self.folder / "state.sqlite-wal"
        sidecar.write_bytes(b"")
        with self.assertRaises(bundle.V41BundleDenied):
            self.offline(receipt)

    def test_unsealed_and_changed_authority_flags_are_denied(self):
        receipt = self.attempt()
        sealed = self.folder / "manifest.sha256.json"
        doc = json.loads(sealed.read_bytes())
        doc["source_transition_authorized"] = True
        raw = bundle.canonical(doc)
        sealed.write_bytes(raw)
        with self.assertRaisesRegex(bundle.V41BundleDenied,
                                    "FROZEN_MANIFEST_OR_AUTHORITY_FIELDS_DRIFT"):
            self.offline(receipt, manifest_sha=hashlib.sha256(raw).hexdigest())
        sealed.unlink()
        with self.assertRaisesRegex(bundle.V41BundleDenied,
                                    "SEALED_MANIFEST_REQUIRED"):
            self.offline(receipt)

    def test_offline_recovery_rejects_linked_files(self):
        receipt = self.attempt()
        archive = next(k for k in receipt["files_sha256"]
                       if k.startswith("provider-custody/") and k.endswith(".zip"))
        path = self.folder.joinpath(*archive.split("/"))
        scratch = self.root / "linked-copy.zip"
        scratch.write_bytes(path.read_bytes())
        path.unlink()
        try:
            path.symlink_to(scratch)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable on runner")
        with self.assertRaises(bundle.V41BundleDenied):
            self.offline(receipt)

    def test_late_added_file_during_restore_is_denied(self):
        receipt = self.attempt()
        open_original = cold._open_immutable_hashed_backup

        def inject_after_inventory(path):
            if Path(path).name == "restored.sqlite":
                (self.folder / "late-inserted.txt").write_bytes(b"unlisted")
            return open_original(path)

        with patch.object(cold, "_open_immutable_hashed_backup",
                          side_effect=inject_after_inventory):
            with self.assertRaisesRegex(bundle.V41BundleDenied,
                                        "BUNDLE_CHANGED_DURING_OFFLINE_AUDIT"):
                self.offline(receipt)


if __name__ == "__main__":
    unittest.main()
