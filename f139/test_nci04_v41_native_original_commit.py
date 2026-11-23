"""Native original V41 commit request negatives; never touch the real owner."""
import copy
from pathlib import Path
import inspect
import os
import sys
import unittest
from unittest.mock import patch

from f139.nci04_native_contract import canonical
from f139 import nci04_v41_native_original_commit as native


TARGET = "8" * 40


def request():
    return {
        "schema": native.SCHEMA,
        "target_source_sha": TARGET,
        "release_pr_number": 1748,
        "backup_run_id": 123456,
        "sealed_manifest_sha256": "a" * 64,
        "owner_approval_comment_id": 123457,
        "original_head_seq": 1826,
        "original_head_sha256": "b" * 64,
        "expected_copy_head_sha256": "c" * 64,
        "expected_escrow_event_sha256": "d" * 64,
        "binary_sha256": "e" * 64,
        "scientific_first_use": False,
        "hybrid_admission": False,
        "new_controller": False,
        "new_scheduler": False,
        "new_queue": False,
        "paid_model_calls": 0,
    }


def event(doc=None):
    doc = request() if doc is None else doc
    return {
        "action": "created",
        "issue": {"number": 807, "user": {"login": native.OWNER}},
        "sender": {"login": native.OWNER},
        "comment": {
            "id": 123458, "user": {"login": native.OWNER},
            "author_association": "OWNER",
            "body": native.PREFIX + canonical(doc).decode("ascii"),
            "created_at": "2026-11-13T18:00:00Z",
            "updated_at": "2026-11-13T18:00:00Z",
        },
    }


ENV = {
    "GITHUB_REPOSITORY": native.REPO, "GITHUB_ACTOR": native.OWNER,
    "GITHUB_EVENT_NAME": "issue_comment",
    "GITHUB_REF": "refs/heads/main",
    "RUNNER_NAME": "FORGE-CODEX-REMOTE",
    "GITHUB_RUN_ATTEMPT": "1", "GITHUB_SHA": TARGET,
    "GITHUB_RUN_ID": "234567",
}


def get(route):
    assert route == ("repos/" + native.REPO + "/issues/comments/123458")
    return {**event()["comment"], "issue_url":
            "https://api.github.com/repos/" + native.REPO + "/issues/807"}


class NativeOriginalCommitRequestTests(unittest.TestCase):
    def test_exact_signed_owner_comment_twice_and_request_has_no_permit(self):
        calls = []
        def reader(route):
            calls.append(route)
            return get(route)
        result = native.verify_install_dispatch(ENV, event(), reader)
        self.assertEqual(calls, [
            "repos/" + native.REPO + "/issues/comments/123458"] * 2)
        self.assertEqual(result["owner_install_comment_id"], 123458)
        self.assertEqual(result["event_run_id"], 234567)
        for key in ("scientific_first_use", "hybrid_admission",
                    "new_controller", "new_scheduler", "new_queue"):
            self.assertFalse(result[key])
        self.assertNotIn("release_qualified", result)
        self.assertNotIn("owner_task_enabled", result)
        self.assertEqual(result["target_source_sha"], TARGET)

    def test_replay_wrong_runner_actor_and_source_never_read_github(self):
        cases = (
            ("GITHUB_RUN_ATTEMPT", "2"),
            ("GITHUB_SHA", "f" * 40),
            ("GITHUB_ACTOR", "other"),
            ("RUNNER_NAME", "github-hosted"),
            ("GITHUB_REPOSITORY", "other/repo"),
            ("GITHUB_REF", "refs/heads/other"),
            ("GITHUB_RUN_ID", "0"),
        )
        for field, value in cases:
            with self.subTest(field=field):
                calls = []
                def reader(route):
                    calls.append(route)
                    return get(route)
                with self.assertRaises(native.NativeOriginalCommitDenied):
                    native.verify_install_dispatch({**ENV, field: value},
                                                  event(), reader)
                self.assertEqual(calls, [])

    def test_wrong_owner_issue_event_comment_identity_denied(self):
        for variant in ("edited", "wrong_issue", "pr", "wrong_sender",
                        "wrong_comment_owner", "wrong_assoc", "wrong_body"):
            with self.subTest(variant=variant):
                e = copy.deepcopy(event())
                if variant == "edited":
                    e["action"] = "edited"
                elif variant == "wrong_issue":
                    e["issue"]["number"] = 1715
                elif variant == "pr":
                    e["issue"]["pull_request"] = {}
                elif variant == "wrong_sender":
                    e["sender"]["login"] = "stranger"
                elif variant == "wrong_comment_owner":
                    e["comment"]["user"]["login"] = "stranger"
                elif variant == "wrong_assoc":
                    e["comment"]["author_association"] = "COLLABORATOR"
                elif variant == "wrong_body":
                    e["comment"]["body"] = "F139-V41-PAUSE-BACKUP-RESUME " + TARGET
                with self.assertRaises(native.NativeOriginalCommitDenied):
                    native.verify_install_dispatch(ENV, e, get)

    def test_forged_science_scheduler_binary_and_target_denied(self):
        for key, value in (
            ("scientific_first_use", True),
            ("hybrid_admission", True),
            ("new_controller", True), ("new_scheduler", True),
            ("new_queue", True), ("paid_model_calls", 1),
            ("release_pr_number", 0),
            ("backup_run_id", 0),
            ("owner_approval_comment_id", 0),
            ("original_head_seq", 0),
            ("sealed_manifest_sha256", "bad"),
            ("original_head_sha256", "bad"),
            ("expected_copy_head_sha256", "bad"),
            ("expected_escrow_event_sha256", "bad"),
            ("binary_sha256", "bad"),
            ("target_source_sha", "1" * 40),
        ):
            with self.subTest(field=key):
                body = {**request(), key: value}
                with self.assertRaises(native.NativeOriginalCommitDenied):
                    native.verify_install_dispatch(ENV, event(body), get)

    def test_duplicate_json_field_and_noncanonical_request_denied(self):
        doc = request()
        bad = event(doc)
        bad["comment"]["body"] = (
            native.PREFIX + '{"schema":"a","schema":"b"}')
        with self.assertRaises(native.NativeOriginalCommitDenied):
            native.verify_install_dispatch(ENV, bad, get)
        bad = event(doc)
        bad["comment"]["body"] += " "
        with self.assertRaises(native.NativeOriginalCommitDenied):
            native.verify_install_dispatch(ENV, bad, get)

    def test_second_authenticated_readback_and_comment_edit_fail_closed(self):
        calls = []
        def altered(route):
            calls.append(route)
            e = get(route)
            if len(calls) == 2:
                e["body"] = "edited"
            return e
        with self.assertRaisesRegex(native.NativeOriginalCommitDenied,
                                    "OWNER_COMMENT_REMOTE_DRIFT"):
            native.verify_install_dispatch(ENV, event(), altered)
        self.assertEqual(len(calls), 2)
        def newer(route):
            r = get(route)
            r["updated_at"] = "2026-11-13T19:00:00Z"
            return r
        with self.assertRaises(native.NativeOriginalCommitDenied):
            native.verify_install_dispatch(ENV, event(), newer)

    def test_original_commit_has_no_cli_and_cannot_enter_unqualified_host(self):
        module = inspect.getsource(native)
        self.assertNotIn('if __name__ == "__main__"', module)
        self.assertNotIn("Set-ScheduledTask", module)
        self.assertNotIn("Disable-ScheduledTask", module)
        self.assertNotIn("Start-ScheduledTask", module)
        self.assertNotIn("Register-ScheduledTask", module)
        self.assertNotIn("gh api --method", module)
        # No native commit from a Linux/hosted runner or arbitrary API object.
        with patch.object(native.sys, "platform", "linux"):
            with self.assertRaisesRegex(native.NativeOriginalCommitDenied,
                                        "NATIVE_ORIGINAL_ONLY"):
                native.original_commit_after_independent_rehearsal(
                    Path("/tmp/never-existing-original.sqlite"),
                    Path("/tmp/untrusted"), Path("/tmp/fake.exe"),
                    Path("/tmp/isolated.sqlite"),
                    env=ENV, event=event(), api=object())
        # Preserve original owner task and separate Wingless/Yggdrasil research.
        self.assertIn("SingleOwner(db_path.with_suffix", module)
        self.assertIn("fence.inert_handoff", module)
        self.assertIn("atomic._commit_pair_under_existing_owner_lock", module)
        self.assertIn("POSTCOMMIT_TASK_MUST_REMAIN_DISABLED", module)


if __name__ == "__main__":
    unittest.main()
