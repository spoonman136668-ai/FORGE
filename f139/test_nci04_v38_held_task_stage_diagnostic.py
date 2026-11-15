"""Freeze bounded stage-localized original owner guard diagnosis on both OS."""
import json
from pathlib import Path
import subprocess
import unittest

from f139 import nci04_v38_held_task_stage_diagnostic as diag
from f139 import nci04_v41_hybrid_forward_owner_profile as original
from scripts import check_rar_g145_pr_scope as scope

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github" / "workflows" /
            "f139-v38-held-task-stage-diagnostic-once.yml")


class HeldTaskStageTests(unittest.TestCase):
    def test_frozen_bounded_exit_codes_preserve_original_guard(self):
        self.assertEqual(diag.CODES, frozenset(range(41, 52)))
        for code in (*range(41, 52), 0, 1, 52):
            calls = []
            def run(argv, **kwargs):
                calls.append(argv)
                return subprocess.CompletedProcess(argv, code, stdout=b"")
            def reader(db, *, runner):
                self.assertEqual(db, Path("state.sqlite"))
                receipt = runner(["fake-only"], timeout=25)
                if receipt.returncode or code in (1, 52):
                    raise original.HeldTaskIdentityDenied(
                        "F139_HYBRID_V38_HELD_TASK_"
                        "SID_SOURCE_OR_QUIESCENCE_NOT_VERIFIED")
                return True
            result = diag.classify(
                Path("state.sqlite"), reader=reader, execute=run)
            expected = ("PASS_PREDICATES_ONLY" if code == 0 else
                        "EXIT_" + str(code) if 41 <= code <= 51 else
                        "SHELL_UNEXPECTED")
            self.assertEqual(result, expected)
            self.assertEqual(len(calls), 1)

    def test_task_precondition_does_not_invoke_original_subprocess(self):
        def fail(db, *, runner):
            raise original.HeldTaskIdentityDenied(
                "F139_HYBRID_V38_HELD_TASK_EXACT_ORIGINAL_SQLITE_PATH_REQUIRED")
        def never(*args, **kwargs):
            self.fail("task shell must not run before guard path precondition")
        self.assertEqual(diag.classify(Path("state.sqlite"), reader=fail,
                                       execute=never), "TASK_PREREQUISITE")

    def test_unexpected_stdout_or_shell_timeout_is_denied(self):
        def rejected(db, *, runner):
            output = runner(["fake"], timeout=25)
            if output.returncode == 0:
                raise original.HeldTaskIdentityDenied(
                    "F139_HYBRID_V38_HELD_TASK_"
                    "SID_SOURCE_OR_QUIESCENCE_NOT_VERIFIED")
            return True
        def bad(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0, stdout=b"bad")
        self.assertEqual(diag.classify(Path("state.sqlite"),
                                       reader=rejected, execute=bad),
                         "SHELL_UNEXPECTED")
        def timed(db, *, runner):
            runner(["fake"], timeout=25)
        def timeout(argv, **kwargs):
            raise subprocess.TimeoutExpired(argv, 25)
        self.assertEqual(diag.classify(Path("state.sqlite"),
                                       reader=timed, execute=timeout),
                         "SHELL_TIMEOUT")

    def test_second_execution_is_blocked_even_if_attempted(self):
        calls = []
        def twice(db, *, runner):
            runner(["fake"])
            runner(["fake"])
        def run(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0)
        self.assertEqual(diag.classify(Path("state.sqlite"),
                                       reader=twice, execute=run),
                         "TASK_UNEXPECTED")
        self.assertEqual(len(calls), 1)

    def test_current_original_owner_comment_and_prior_failed_run(self):
        target = "a" * 40
        comment_id = diag.PREV_COMMENT + 1
        body = diag.PREFIX + target + " " + str(diag.PREV_COMMENT)
        event = {
            "action": "created",
            "issue": {"number": 807, "user": {"login": diag.OWNER}},
            "sender": {"login": diag.OWNER},
            "comment": {"id": comment_id, "body": body,
                        "author_association": "OWNER",
                        "user": {"login": diag.OWNER}},
        }
        env = {
            "GITHUB_SHA": target, "GITHUB_REPOSITORY": diag.REPO,
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_ACTOR": diag.OWNER,
            "GITHUB_EVENT_NAME": "issue_comment",
            "GITHUB_RUN_ATTEMPT": "1",
            "RUNNER_NAME": "FORGE-CODEX-REMOTE",
            "GITHUB_RUN_ID": "43662000001",
        }
        def get(route):
            if route == "repos/" + diag.REPO + "/issues/comments/" + str(comment_id):
                return {"id": comment_id, "body": body,
                        "author_association": "OWNER",
                        "user": {"login": diag.OWNER},
                        "issue_url": "https://api.github.com/repos/" +
                                     diag.REPO + "/issues/807",
                        "created_at": "2026-11-15T01:30:00Z"}
            if route == "repos/" + diag.REPO + "/issues/comments/" + str(diag.PREV_COMMENT):
                return {"id": diag.PREV_COMMENT, "body": diag.PREV_BODY,
                        "author_association": "OWNER",
                        "user": {"login": diag.OWNER},
                        "created_at": "2026-11-15T00:55:07Z"}
            if route == "repos/" + diag.REPO + "/actions/runs/" + str(diag.PREV_RUN):
                return {"id": diag.PREV_RUN, "head_sha": diag.PREV_SHA,
                        "run_attempt": 1, "event": "issue_comment",
                        "status": "completed", "conclusion": "failure",
                        "actor": {"login": diag.OWNER}}
            if route == "repos/" + diag.REPO + "/branches/main":
                return {"name": "main", "protected": True,
                        "commit": {"sha": target}}
            if route == "repos/" + diag.REPO + "/issues/807":
                return {"state": "open", "body": json.dumps({
                    "lanes": ["Wingless", "Yggdrasil"],
                    "scientific_first_use": False, "new_controller": False,
                    "new_scheduler": False, "new_queue": False,
                    "paid_model_calls": 0})}
            self.fail("unexpected non-allowlisted mock API route")
        self.assertEqual(diag.authenticate(get, env, event), target)
        for change in ({"GITHUB_ACTOR": "other"},
                       {"GITHUB_RUN_ATTEMPT": "2"},
                       {"RUNNER_NAME": "other"},
                       {"OPENAI_API_KEY": "x"},
                       {"GITHUB_SHA": diag.PREV_SHA}):
            with self.assertRaises(diag.StageDenied):
                diag.authenticate(get, {**env, **change}, event)
        with self.assertRaises(diag.StageDenied):
            diag.authenticate(get, env, {**event, "comment": {
                **event["comment"], "id": diag.PREV_COMMENT}})

    def test_g145_frozen_workflow_and_no_mutations(self):
        workflow = WORKFLOW.read_text("utf-8")
        self.assertIn("on:\n  issue_comment:\n    types: [created]", workflow)
        self.assertIn("group: forge-f139-v41-original-owner-live-install", workflow)
        self.assertIn("runs-on: [self-hosted, Windows, forge-codex-isolated]", workflow)
        self.assertIn("f139.nci04_v38_held_task_stage_diagnostic", workflow)
        self.assertIn("9bda78341bc3651e8b7b0a24ea6c7858dbff05c6", workflow)
        self.assertIn("GITHUB_RUN_ATTEMPT -cne '1'", workflow)
        for forbidden in (
                "\n  schedule:", "\n  workflow_dispatch:", "\n  push:",
                "Start-ScheduledTask", "Stop-ScheduledTask",
                "Set-ScheduledTask", "Enable-ScheduledTask",
                "Disable-ScheduledTask", "Register-ScheduledTask",
                "New-ScheduledTask", "gh workflow run",
                "upgrade-hybrid-lane", "actions: write",
                "issues: write", "contents: write"):
            self.assertNotIn(forbidden, workflow)
        self.assertFalse(scope.generic_paths_safe([
            ".github/workflows/f139-v38-held-task-stage-diagnostic-once.yml"]))
        self.assertEqual(scope.V38_STAGE_BRANCH,
                         "engineering/f139-v38-held-task-stage-diagnostic-20261114")
        self.assertEqual(len(scope.V38_STAGE_FILES), 7)
        scope.v38_stage_negative_controls()


if __name__ == "__main__":
    unittest.main()
