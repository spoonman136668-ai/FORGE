"""Negative controls for original event1835 full create-only cold backup."""
from __future__ import annotations
import copy
import inspect
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from f139.nci04_native_contract import canonical, digest
from f139 import nci04_v42_owner_source_readiness as v42
from f139 import nci04_v43_event1835_cold as cold
from f139 import nci04_v43_owner_backup_cli as entry


class V43FullBackupTests(unittest.TestCase):
    def request(self):
        target = "a" * 40
        cid = entry.PREVIOUS_READ_COMMENT_ID + 10
        env = {
            "GITHUB_REPOSITORY": v42.REPO,
            "GITHUB_ACTOR": v42.OWNER,
            "GITHUB_EVENT_NAME": "issue_comment",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_SHA": target,
            "RUNNER_NAME": "FORGE-CODEX-REMOTE",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_RUN_ID": "43851489999",
        }
        event = {
            "action": "created",
            "issue": {"number": 807,
                      "user": {"login": v42.OWNER}},
            "sender": {"login": v42.OWNER},
            "comment": {
                "id": cid, "author_association": "OWNER",
                "user": {"login": v42.OWNER},
                "created_at": "2026-11-16T13:30:00Z",
                "updated_at": "2026-11-16T13:30:00Z",
                "body": entry.PREFIX + target + " " +
                    str(entry.PREVIOUS_READ_COMMENT_ID)},
        }
        current = {
            **event["comment"],
            "issue_url": "https://api.github.com/repos/" +
                v42.REPO + "/issues/807"}
        old = {
            "user": {"login": v42.OWNER},
            "body": "F139-V42-ORIGINAL-READONLY "
                    "42ddb373b4dbbf31ea36b08f585e5c5cdc706b9f "
                    "6912162079",
            "created_at": "2026-11-16T10:26:05Z"}
        def get(route):
            if route.endswith("/issues/comments/" + str(cid)):
                return copy.deepcopy(current)
            if route.endswith("/issues/comments/" +
                              str(entry.PREVIOUS_READ_COMMENT_ID)):
                return copy.deepcopy(old)
            raise AssertionError("unrelated GitHub route: " + route)
        return env, event, get, current

    def test_fresh_original_comment_authenticated(self):
        env, event, get, _ = self.request()
        self.assertEqual(entry.intent(get, env, event),
                         (env["GITHUB_SHA"], 43851489999,
                          event["comment"]["id"]))

    def test_owner_run_and_comment_negative_controls(self):
        env, event, get, current = self.request()
        changes = [
            ("env", "GITHUB_REPOSITORY", "other/FORGE"),
            ("env", "GITHUB_ACTOR", "other"),
            ("env", "GITHUB_RUN_ATTEMPT", "2"),
            ("env", "RUNNER_NAME", "other"),
            ("env", "OPENAI_API_KEY", "not-permitted"),
            ("env", "GITHUB_REF", "refs/heads/other"),
            ("event", "action", "edited"),
            ("comment", "id", entry.PREVIOUS_READ_COMMENT_ID),
            ("comment", "body", "F139-V43-COLD-BACKUP other"),
            ("comment", "author_association", "CONTRIBUTOR"),
            ("comment", "user", {"login": "other"}),
            ("issue", "number", 1715),
            ("issue", "pull_request", {}),
        ]
        for kind, key, val in changes:
            with self.subTest(kind=kind, key=key):
                e, x, getter, _ = self.request()
                if kind == "env":
                    e[key] = val
                elif kind == "event":
                    x[key] = val
                else:
                    x[kind][key] = val
                with self.assertRaises(entry.OriginalBackupDenied):
                    entry.intent(getter, e, x)
        bad = copy.deepcopy(current)
        bad["body"] = "tampered"
        def spoof(route):
            if route.endswith(str(event["comment"]["id"])):
                return bad
            return get(route)
        with self.assertRaisesRegex(
                entry.OriginalBackupDenied, "REMOTE_OWNER_INTENT"):
            entry.intent(spoof, env, event)

    def test_absent_or_tampered_backup_fails_without_owner_write(self):
        with tempfile.TemporaryDirectory() as root:
            original = Path(root) / "state.sqlite"
            original.write_bytes(b"original untouched")
            new = cold.backup_folder(original, 43851489999)
            self.assertFalse(new.exists())
            with self.assertRaises(cold.OriginalColdDenied):
                cold.verify_detached_restore(
                    new, target="a" * 40, run_id=43851489999,
                    manifest_sha="b" * 64)
            self.assertEqual(original.read_bytes(), b"original untouched")
            new.mkdir()
            manifest = {
                "schema": cold.SCHEMA,
                "original_source_sha": v42.BEFORE,
                "target_source_sha": "a"*40,
                "run_id": 43851489999,
                "original_head_seq": v42.FROZEN_SEQ,
                "original_head_sha256": v42.FROZEN_HEAD,
                "predecessor_backup_run_id": 43800000000,
                "predecessor_backup_manifest_sha256": "a"*64,
                "files_sha256": {"state.sqlite": "b"*64},
                "logical_all_tables_sha256": "c"*64,
                "provider_archives_manifest_sha256": "d"*64,
                "generation_binary_manifest_sha256": "e"*64,
                "negative_custody_manifest_sha256": "f"*64,
                "restored_sqlite_sha256": "0"*64,
                "original_owner_mutations": 0, "new_dispatches": 0,
                "source_transition_authorized": False,
                "owner_policy_modified": False,
                "task_resume_authorized": False,
                "hybrid_admission": False,
                "scientific_first_use": False,
            }
            raw = canonical(manifest)
            (new / "manifest.sha256.json").write_bytes(raw)
            receipt = cold._manifest(new, target="a"*40,
                                     run_id=43851489999,
                                     manifest_sha=digest(raw))
            self.assertEqual(receipt["original_head_seq"], 1835)
            manifest["source_transition_authorized"] = True
            raw = canonical(manifest)
            (new / "manifest.sha256.json").write_bytes(raw)
            with self.assertRaisesRegex(
                    cold.OriginalColdDenied, "AUTHORITY_INVALID"):
                cold._manifest(new, target="a"*40,
                               run_id=43851489999,
                               manifest_sha=digest(raw))
            with self.assertRaises(cold.OriginalColdDenied):
                cold._manifest(new, target="a"*40,
                               run_id=43851489999,
                               manifest_sha="0"*64)
            self.assertEqual(original.read_bytes(), b"original untouched")

    def test_untrusted_database_cannot_trigger_cold_backup(self):
        with self.assertRaises(cold.OriginalColdDenied):
            cold.stage_full_backup(object(), target="a"*40,
                                   run_id=43851489999,
                                   release_witness=lambda: True,
                                   original_witness=lambda: True)
        for value in (None, "a" * 39, "A" * 40, v42.BEFORE):
            with self.subTest(target=value), self.assertRaises(
                    cold.OriginalColdDenied):
                cold.stage_full_backup(object(), target=value,
                                       run_id=43851489999,
                                       release_witness=lambda: True,
                                       original_witness=lambda: True)

    def test_reused_readback_comment_cannot_authorize_new_backup(self):
        env, event, get, _ = self.request()
        event["comment"]["id"] = entry.PREVIOUS_READ_COMMENT_ID
        with self.assertRaises(entry.OriginalBackupDenied):
            entry.intent(get, env, event)

    def test_existing_original_workflow_only_no_new_scheduler(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / ".github/workflows/f139-g54-v9-owner-cutover.yml"
                  ).read_text(encoding="utf-8")
        marker = "\n  v43-original-owner-cold-backup:\n"
        self.assertEqual(source.count(marker), 1)
        added = source.split(marker, 1)[1]
        self.assertIn("F139-V43-COLD-BACKUP ", added)
        self.assertIn("f139.nci04_v43_owner_backup_cli", added)
        self.assertIn("github.event_name == 'issue_comment'", added)
        self.assertIn("RUNNER_NAME -ceq 'FORGE-CODEX-REMOTE'", added)
        self.assertIn("GITHUB_RUN_ATTEMPT -ceq '1'", added)
        self.assertIn("6913813568", added)
        self.assertIn("GH_TOKEN: " + "$"+"{{ github.token }}", added)
        self.assertNotIn("schedule:", added)
        for denied in (
            "Stop-ScheduledTask", "Disable-ScheduledTask",
            "Start-ScheduledTask", "Register-ScheduledTask",
            "Set-ScheduledTask", "Stop-Process",
            "gh api --method", "Invoke-Expression"):
            self.assertNotIn(denied, added)
        for module in (cold, entry):
            src = inspect.getsource(module)
            self.assertNotIn("db.event(", src)
            self.assertNotIn("db.transition_source(", src)
            self.assertNotIn("Disable-ScheduledTask", src)
            self.assertFalse(hasattr(module, "activate"))
            self.assertFalse(hasattr(module, "install"))


    def test_actual_windows_path_factory_not_rejected_by_type_guard(self):
        """argparse(type=Path) yields WindowsPath, never type(value) is Path."""
        source = inspect.getsource(entry.original_backup)
        self.assertIn("isinstance(db_path, Path)", source)
        self.assertNotIn("type(db_path) is Path", source)
        self.assertTrue(isinstance(Path("."), Path))
        self.assertIsNot(type(Path(".")), Path)



if __name__ == "__main__":
    unittest.main()
