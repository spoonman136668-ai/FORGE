"""V41 candidate stage contract: owner intent and read-only negative controls."""
import copy
import inspect
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from f139.nci04_native_contract import canonical
from f139 import nci04_v41_candidate_stage as stage


TARGET = "9" * 40
ENV = {
    "GITHUB_REPOSITORY": stage.REPO,
    "GITHUB_ACTOR": stage.OWNER,
    "GITHUB_EVENT_NAME": "issue_comment",
    "GITHUB_REF": "refs/heads/main",
    "GITHUB_RUN_ATTEMPT": "1",
    "RUNNER_NAME": "FORGE-CODEX-REMOTE",
    "GITHUB_SHA": TARGET,
    "GITHUB_RUN_ID": "987654",
}


def request():
    return {
        "schema": stage.SCHEMA, "target_source_sha": TARGET,
        "release_pr_number": 1749,
        "scientific_first_use": False,
        "hybrid_admission": False,
        "new_controller": False,
        "new_scheduler": False,
        "new_queue": False,
        "paid_model_calls": 0,
    }


def event(document=None):
    if document is None:
        document = request()
    return {
        "action": "created",
        "issue": {"number": 807, "user": {"login": stage.OWNER}},
        "sender": {"login": stage.OWNER},
        "comment": {
            "id": 556677, "user": {"login": stage.OWNER},
            "author_association": "OWNER",
            "created_at": "2026-11-13T18:00:00Z",
            "updated_at": "2026-11-13T18:00:00Z",
            "body": stage.PREFIX + canonical(document).decode("ascii"),
        },
    }


def get(route):
    assert route == "repos/" + stage.REPO + "/issues/comments/556677"
    return {**event()["comment"],
            "issue_url": "https://api.github.com/repos/" +
            stage.REPO + "/issues/807"}


class CandidateStageSourceOnlyTests(unittest.TestCase):
    def test_exact_owner_event_source_bound_and_double_provider_read(self):
        calls = []
        def reader(route):
            calls.append(route)
            return get(route)
        receipt = stage.verify_stage_event(ENV, event(), reader)
        self.assertEqual(receipt["target_source_sha"], TARGET)
        self.assertEqual(receipt["release_pr_number"], 1749)
        self.assertEqual(receipt["stage_comment_id"], 556677)
        self.assertEqual(receipt["stage_run_id"], 987654)
        self.assertEqual(calls, [
            "repos/" + stage.REPO + "/issues/comments/556677"] * 2)
        for forbidden in ("scientific_first_use", "hybrid_admission",
                          "new_controller", "new_scheduler", "new_queue"):
            self.assertFalse(receipt[forbidden])

    def test_untrusted_runner_actor_ref_attempt_and_source_fail_no_reads(self):
        for key, value in (
            ("RUNNER_NAME", "not-original"),
            ("GITHUB_ACTOR", "stranger"),
            ("GITHUB_SHA", "f" * 40),
            ("GITHUB_REF", "refs/heads/other"),
            ("GITHUB_EVENT_NAME", "push"),
            ("GITHUB_RUN_ATTEMPT", "2"),
            ("GITHUB_RUN_ID", "0"),
        ):
            with self.subTest(key=key):
                routes = []
                def reader(route):
                    routes.append(route)
                    return get(route)
                with self.assertRaises(stage.V41StageDenied):
                    stage.verify_stage_event({**ENV, key: value},
                                             event(), reader)
                self.assertEqual(routes, [])

    def test_forged_request_source_and_science_expansion_denied(self):
        for key, value in (
            ("target_source_sha", "f" * 40),
            ("release_pr_number", 0),
            ("release_pr_number", True),
            ("scientific_first_use", True),
            ("hybrid_admission", True),
            ("new_controller", True),
            ("new_scheduler", True),
            ("new_queue", True),
            ("paid_model_calls", 1),
        ):
            with self.subTest(key=key):
                with self.assertRaises(stage.V41StageDenied):
                    stage.verify_stage_event(
                        ENV, event({**request(), key: value}), get)

    def test_edited_unrelated_or_duplicate_request_denied(self):
        for variant in ("edited", "foreign", "wrong_issue",
                        "pull_request", "wrong_comment", "noncanonical"):
            with self.subTest(variant=variant):
                e = copy.deepcopy(event())
                if variant == "edited":
                    e["action"] = "edited"
                elif variant == "foreign":
                    e["sender"]["login"] = "stranger"
                elif variant == "wrong_issue":
                    e["issue"]["number"] = 1715
                elif variant == "pull_request":
                    e["issue"]["pull_request"] = {}
                elif variant == "wrong_comment":
                    e["comment"]["author_association"] = "COLLABORATOR"
                else:
                    e["comment"]["body"] += " "
                with self.assertRaises(stage.V41StageDenied):
                    stage.verify_stage_event(ENV, e, get)
        e = copy.deepcopy(event())
        e["comment"]["body"] = (
            stage.PREFIX + '{"schema":"x","schema":"y"}')
        with self.assertRaises(stage.V41StageDenied):
            stage.verify_stage_event(ENV, e, get)

    def test_forged_second_get_and_changed_timestamp_denied(self):
        calls = []
        def reader(route):
            calls.append(route)
            data = get(route)
            if len(calls) == 2:
                data["body"] = "modified"
            return data
        with self.assertRaisesRegex(
                stage.V41StageDenied, "OWNER_COMMENT_READBACK_DRIFT"):
            stage.verify_stage_event(ENV, event(), reader)
        self.assertEqual(len(calls), 2)
        def later(route):
            data = get(route)
            data["updated_at"] = "2026-11-13T19:00:00Z"
            return data
        with self.assertRaises(stage.V41StageDenied):
            stage.verify_stage_event(ENV, event(), later)

    def test_linux_never_stages_even_with_owner_fixture(self):
        with patch.object(stage.sys, "platform", "linux"), \
             patch.object(stage.subprocess, "run") as executed:
            with self.assertRaisesRegex(
                    stage.V41StageDenied, "WINDOWS_ORIGINAL_OWNER_ONLY"):
                stage.stage_owner_native_candidate(ENV, event(), object())
            executed.assert_not_called()

    def test_bounded_commands_require_success_and_do_not_retry(self):
        with self.assertRaisesRegex(stage.V41StageDenied,
                                    "BOUNDED_NATIVE_COMMAND"):
            stage._call([])
        with self.assertRaisesRegex(stage.V41StageDenied,
                                    "BOUNDED_NATIVE_COMMAND"):
            stage._call(["go"] * 11)
        calls = []
        def run(argv, **kwargs):
            calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 1, b"", b"failed")
        with patch.object(stage.subprocess, "run", side_effect=run):
            with self.assertRaisesRegex(
                    stage.V41StageDenied, "SOURCE_TOOLCHAIN_COMMAND_FAILED"):
                stage._call(["git", "version"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1]["stdin"], subprocess.DEVNULL)

    def test_exact_create_only_staging_no_original_task_or_policy_writes(self):
        text = inspect.getsource(stage)
        for required in (
            '"git", "clone", "--local", "--no-hardlinks", "--quiet"',
            '"go", "build", "-trimpath", "-buildvcs=false"',
            "binary_dir.mkdir(parents=True, exist_ok=False)",
            "not install.exists()",
            "not binary_dir.exists()",
            "GITHUB_RUN_ATTEMPT",
            "release._remote_source",
            "api.protected_main() == target",
        ):
            self.assertIn(required, text)
        for forbidden in (
            "Disable-ScheduledTask", "Enable-ScheduledTask",
            "Stop-ScheduledTask", "Start-ScheduledTask",
            "Set-ScheduledTask", "Register-ScheduledTask",
            "gh api --method", "PATCH repos/", "DELETE repos/",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
