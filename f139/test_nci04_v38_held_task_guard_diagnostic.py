"""Negative controls for isolated original-owner exit-predicate diagnosis."""
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from f139 import nci04_v38_held_task_guard_diagnostic as diagnostic
from f139 import nci04_v41_hybrid_forward_owner_profile as profile
from scripts import check_rar_g145_pr_scope as scope

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/f139-v38-held-task-guard-diagnostic-once.yml"
DOC = ROOT / "docs/F139-V38-HELD-GUARD-DIAGNOSTIC-ONCE.md"


class GuardDiagnosticTests(unittest.TestCase):
    def test_bounded_returncode_classification_and_no_replay(self):
        db = Path("state.sqlite")
        calls = []
        def original_reader(path, *, runner):
            self.assertEqual(path, db)
            result = runner(["inert-original-guard-command"],
                            timeout=25, check=False)
            self.assertEqual(result.stdout, b"")
            if result.returncode:
                raise profile.HeldTaskIdentityDenied(
                    "F139_HYBRID_V38_HELD_TASK_"
                    "SID_SOURCE_OR_QUIESCENCE_NOT_VERIFIED")
            return True
        for code in (41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 0):
            def execute(argv, **kwargs):
                calls.append((code, argv))
                return subprocess.CompletedProcess(argv, code, stdout=b"")
            observed = diagnostic.classify(
                db, readback=original_reader, execute=execute)
            self.assertEqual(observed, "PASS_PREDICATES_ONLY" if code == 0
                             else "EXIT_" + str(code))
        self.assertEqual(len(calls), 12)

    def test_unexpected_powershell_exit_is_never_accepted(self):
        def reader(path, *, runner):
            result = runner(["inert"])
            raise profile.HeldTaskIdentityDenied(
                "F139_HYBRID_V38_HELD_TASK_"
                "SID_SOURCE_OR_QUIESCENCE_NOT_VERIFIED")
        for value in (1, 40, 52, 255):
            def execute(argv, **kwargs):
                return subprocess.CompletedProcess(argv, value)
            with self.assertRaisesRegex(
                    diagnostic.GuardDiagnosticDenied,
                    "UNCLASSIFIED_GUARD_RESULT"):
                diagnostic.classify(Path("state.sqlite"),
                                    readback=reader, execute=execute)

    def test_no_second_guard_execution_or_unrelated_exception(self):
        calls = []
        def twice(path, *, runner):
            runner(["inert"])
            runner(["inert"])
        def execute(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0)
        with self.assertRaisesRegex(
                diagnostic.GuardDiagnosticDenied, "SECOND_TASK_PROBE_DENIED"):
            diagnostic.classify(Path("state.sqlite"), readback=twice,
                                execute=execute)
        self.assertEqual(len(calls), 1)

    def test_exact_owner_comment_prior_failure_and_main(self):
        target = "a" * 40
        event = {"action": "created",
                 "issue": {"number": 807,
                           "user": {"login": diagnostic.OWNER}},
                 "sender": {"login": diagnostic.OWNER},
                 "comment": {"id": diagnostic.PREVIOUS_COMMENT + 1,
                             "body": diagnostic.PREFIX + target +
                                     " " + str(diagnostic.PREVIOUS_COMMENT),
                             "author_association": "OWNER",
                             "user": {"login": diagnostic.OWNER}}}
        env = {"GITHUB_SHA": target, "GITHUB_REPOSITORY": diagnostic.REPO,
               "GITHUB_REF": "refs/heads/main",
               "GITHUB_ACTOR": diagnostic.OWNER,
               "GITHUB_EVENT_NAME": "issue_comment",
               "GITHUB_RUN_ATTEMPT": "1",
               "RUNNER_NAME": "FORGE-CODEX-REMOTE",
               "GITHUB_RUN_ID": "43659000001"}
        def fake_get(route):
            if route.endswith("/issues/comments/" +
                              str(diagnostic.PREVIOUS_COMMENT + 1)):
                return {"id": diagnostic.PREVIOUS_COMMENT + 1,
                        "body": event["comment"]["body"],
                        "author_association": "OWNER",
                        "user": {"login": diagnostic.OWNER},
                        "issue_url": "https://api.github.com/repos/" +
                                     diagnostic.REPO + "/issues/807",
                        "created_at": "2026-11-15T01:20:00Z"}
            if route.endswith("/issues/comments/" +
                              str(diagnostic.PREVIOUS_COMMENT)):
                return {"id": diagnostic.PREVIOUS_COMMENT,
                        "body": diagnostic.PREVIOUS_BODY,
                        "author_association": "OWNER",
                        "user": {"login": diagnostic.OWNER},
                        "created_at": "2026-11-15T00:31:46Z"}
            if route.endswith("/actions/runs/" + str(diagnostic.PREVIOUS_RUN)):
                return {"id": diagnostic.PREVIOUS_RUN,
                        "head_sha": diagnostic.PREVIOUS_SHA,
                        "run_attempt": 1, "event": "issue_comment",
                        "status": "completed", "conclusion": "failure",
                        "actor": {"login": diagnostic.OWNER}}
            if route.endswith("/branches/main"):
                return {"name": "main", "protected": True,
                        "commit": {"sha": target}}
            if route.endswith("/issues/807"):
                return {"state": "open", "body": (
                    '{"lanes":["Wingless","Yggdrasil"],'
                    '"scientific_first_use":false,"new_controller":false,'
                    '"new_scheduler":false,"new_queue":false}')}
            raise AssertionError("unexpected read route")
        self.assertEqual(diagnostic.authenticate(fake_get, env, event),
                         target)
        for variant in (
            {"GITHUB_RUN_ATTEMPT": "2"},
            {"RUNNER_NAME": "OTHER"},
            {"GITHUB_SHA": diagnostic.PREVIOUS_SHA},
            {"GITHUB_ACTOR": "OTHER"},
            {"OPENAI_API_KEY": "not-allowed"},
        ):
            with self.assertRaises(diagnostic.GuardDiagnosticDenied):
                diagnostic.authenticate(fake_get, {**env, **variant}, event)
        with self.assertRaises(diagnostic.GuardDiagnosticDenied):
            diagnostic.authenticate(fake_get, env, {
                **event, "comment": {**event["comment"], "id":
                                     diagnostic.PREVIOUS_COMMENT}})

    def test_single_workflow_no_mutating_actions_and_g145_fence(self):
        source = WORKFLOW.read_text("utf-8")
        self.assertIn("issue_comment:\n    types: [created]", source)
        self.assertIn("group: forge-f139-v41-original-owner-live-install",
                      source)
        self.assertIn("runs-on: [self-hosted, Windows, forge-codex-isolated]",
                      source)
        self.assertIn("GITHUB_RUN_ATTEMPT -cne '1'", source)
        self.assertIn("F139-V38-HELD-TASK-GUARD-DIAG ", source)
        self.assertIn("9bda78341bc3651e8b7b0a24ea6c7858dbff05c6", source)
        self.assertIn("f139.nci04_v38_held_task_guard_diagnostic", source)
        for forbidden in (
            "\n  schedule:", "\n  workflow_dispatch:", "\n  push:",
            "actions: write", "issues: write", "contents: write",
            "Set-ScheduledTask", "Start-ScheduledTask", "Stop-ScheduledTask",
            "Enable-ScheduledTask", "Disable-ScheduledTask",
            "Register-ScheduledTask", "upgrade-hybrid-lane",
            "gh api --method", "Start-Process",
        ):
            self.assertNotIn(forbidden, source)
        self.assertFalse(scope.generic_paths_safe(
            [".github/workflows/f139-v38-held-task-guard-diagnostic-once.yml"]))
        self.assertEqual(scope.V38_DIAG_BRANCH,
                         "engineering/f139-v38-held-task-guard-diagnostic-once-20261114")
        self.assertEqual(len(scope.V38_DIAG_FILES), 7)
        scope.v38_diagnostic_negative_controls()
        self.assertIn("no task", DOC.read_text("utf-8").lower())


if __name__ == "__main__":
    unittest.main()
