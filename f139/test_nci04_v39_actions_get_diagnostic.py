"""Negative and classification tests for original-host read-only V39 GH provider."""
from pathlib import Path
import json
import subprocess
from types import SimpleNamespace
import unittest

from f139 import nci04_v39_actions_get_diagnostic as probe
from scripts import check_rar_g145_pr_scope as g145

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/f139-v39-actions-get-diagnostic-once.yml"


def example():
    head = "a" * 40
    comment_id = probe.PREV_COMMENT + 1
    body = probe.PREFIX + head + " " + str(probe.PREV_COMMENT)
    env = {
        "GITHUB_SHA": head, "GITHUB_REPOSITORY": probe.REPO,
        "GITHUB_REF": "refs/heads/main", "GITHUB_ACTOR": probe.OWNER,
        "GITHUB_EVENT_NAME": "issue_comment", "GITHUB_RUN_ATTEMPT": "1",
        "RUNNER_NAME": "FORGE-CODEX-REMOTE", "GH_TOKEN": "synthetic-token",
    }
    event = {
        "action": "created", "sender": {"login": probe.OWNER},
        "issue": {
            "number": 807, "user": {"login": probe.OWNER},
            "body": json.dumps({
                "lanes": ["Wingless", "Yggdrasil"],
                "scientific_first_use": False,
                "new_controller": False, "new_scheduler": False,
                "new_queue": False, "paid_model_calls": 0,
            }),
        },
        "comment": {
            "id": comment_id, "body": body,
            "user": {"login": probe.OWNER},
            "author_association": "OWNER",
        },
    }
    return env, event


class ActionsReadOnlyTests(unittest.TestCase):
    def test_signed_event_and_policy_must_be_original(self):
        env, event = example()
        self.assertEqual(probe.authorize(env, event),
                         (probe.PREV_COMMENT + 1, "a" * 40))
        for mutation in (
            {"GITHUB_SHA": probe.V4_SHA}, {"GITHUB_ACTOR": "OTHER"},
            {"GITHUB_RUN_ATTEMPT": "2"}, {"RUNNER_NAME": "OTHER"},
            {"OPENAI_API_KEY": "secret"}, {"GH_TOKEN": ""},
            {"GITHUB_REF": "refs/pull/1768/merge"},
        ):
            with self.subTest(mutation=mutation), self.assertRaises(probe.Denied):
                probe.authorize({**env, **mutation}, event)
        for mutation in (
            {"comment": {**event["comment"], "id": probe.PREV_COMMENT}},
            {"comment": {**event["comment"], "body": "F139-V39-OTHER"}},
            {"comment": {**event["comment"], "author_association": "CONTRIBUTOR"}},
            {"sender": {"login": "OTHER"}},
            {"issue": {**event["issue"], "number": 808}},
            {"issue": {**event["issue"], "body": json.dumps({
                "lanes": ["Wingless", "Yggdrasil", "TTT-Hybrid"],
                "scientific_first_use": True,
            })}},
        ):
            with self.subTest(mutation=mutation), self.assertRaises(probe.Denied):
                probe.authorize(env, {**event, **mutation})

    def test_static_non_http_and_http_cli_classifications(self):
        samples = (
            (b"gh: HTTP 401: private", "HTTP_AUTH"),
            (b"HTTP 403: private", "HTTP_AUTH"),
            (b"HTTP 404: private", "HTTP_NOT_FOUND"),
            (b"HTTP 429: private", "HTTP_LIMIT"),
            (b"HTTP 502: private", "HTTP_SERVER"),
            (b"HTTP 422: private", "HTTP_OTHER"),
            (b"api rate limit exceeded", "RATE_LIMIT"),
            (b"connection reset by peer: PRIVATE", "TRANSPORT"),
            (b"gh auth login", "CLI_AUTH"),
            (b"unknown flag: PRIVATE", "CLI_ARGUMENT"),
            (b"private route user data 998877", "CLI_OTHER"),
            (b"", "CLI_OTHER"),
        )
        for raw, expected in samples:
            with self.subTest(expected=expected):
                observed = probe.classify_stderr(raw)
                self.assertEqual(observed, expected)
                self.assertIn(observed, probe.ALLOWED_RESULTS)
                self.assertNotIn("PRIVATE", observed)

    def test_exact_get_args_bounded_binary_response_and_no_raw_leak(self):
        route = "repos/" + probe.REPO + "/actions/runs/" + str(probe.V4_RUN)
        expected = {"kind": "run", "id": probe.V4_RUN,
                    "sha": probe.V4_SHA, "conclusion": "failure"}
        valid = json.dumps({
            "id": probe.V4_RUN, "head_sha": probe.V4_SHA,
            "run_attempt": 1, "event": "issue_comment",
            "status": "completed", "conclusion": "failure",
            "actor": {"login": probe.OWNER},
        }).encode("utf-8")
        def fake(raw=valid, code=0, err=b"SECRET"):
            def runner(args, **kw):
                self.assertEqual(args, ["gh", "api", route])
                self.assertEqual(kw["stdin"], subprocess.DEVNULL)
                self.assertEqual(kw["stdout"], subprocess.PIPE)
                self.assertEqual(kw["stderr"], subprocess.PIPE)
                self.assertEqual(kw["timeout"], 35)
                self.assertIs(kw["check"], False)
                return SimpleNamespace(returncode=code, stdout=raw, stderr=err)
            return runner
        self.assertEqual(probe.gh_read(route, expected, runner=fake()), "OK")
        self.assertEqual(probe.gh_read(route, expected, runner=fake(b"private", 0)),
                         "INVALID_JSON")
        self.assertEqual(probe.gh_read(route, expected,
                         runner=fake(b"PRIVATE SECRET", 1, b"PRIVATE SECRET")),
                         "CLI_OTHER")
        self.assertEqual(probe.gh_read(route, expected,
                         runner=fake(b"x" * (probe.MAX_STDOUT + 1), 0)), "OVERSIZE")
        other = "repos/" + probe.REPO + "/actions/runs/17"
        with self.assertRaises(probe.Denied):
            probe.gh_read(other, expected, runner=fake())
        with self.assertRaises(probe.Denied):
            probe.gh_read("repos/" + probe.REPO + "/actions/dispatches", expected,
                          runner=fake())
        def timeout(*args, **kw):
            raise subprocess.TimeoutExpired("SECRET", 35, output=b"SECRET")
        def missing(*args, **kw):
            raise FileNotFoundError("PRIVATE")
        self.assertEqual(probe.gh_read(route, expected, runner=timeout), "TIMEOUT")
        self.assertEqual(probe.gh_read(route, expected, runner=missing), "CLI_MISSING")

    def test_exact_three_readonly_gets_and_no_task_use(self):
        env, event = example()
        visited = []
        def reader(route, expected):
            visited.append((route, expected["id"]))
            return "OK" if expected["kind"] == "comment" else "CLI_OTHER"
        self.assertEqual(probe.diagnose(env, event, reader=reader),
                         "C_OK-V4_CLI_OTHER-V3_CLI_OTHER")
        self.assertEqual([ref for _, ref in visited],
                         [probe.PREV_COMMENT + 1, probe.V4_RUN, probe.V3_RUN])
        source = (ROOT / "f139/nci04_v39_actions_get_diagnostic.py").read_text("utf-8")
        for disallowed in ("Get-ScheduledTask", "Start-ScheduledTask",
                           "Stop-ScheduledTask", "Set-ScheduledTask",
                           "Register-ScheduledTask", "Enable-ScheduledTask",
                           "Disable-ScheduledTask", "sqlite3.connect",
                           "gh api --method POST", "actions/workflows/",
                           "CREATE TABLE", "UPDATE tasks", "os.system("):
            self.assertNotIn(disallowed, source)
        self.assertIn('["gh", "api", route]', source)

    def test_new_one_shot_workflow_and_exact_source_guard(self):
        text = WORKFLOW.read_text("utf-8")
        self.assertIn("on:\n  issue_comment:\n    types: [created]", text)
        self.assertIn("group: forge-f139-v39-original-actions-get-once", text)
        self.assertIn("runs-on: [self-hosted, Windows, forge-codex-isolated]", text)
        self.assertIn("F139-V39-ACTIONS-GET-DIAG ", text)
        self.assertIn("6892377331", text)
        self.assertIn("f139.nci04_v39_actions_get_diagnostic", text)
        self.assertIn("9bda78341bc3651e8b7b0a24ea6c7858dbff05c6", text)
        self.assertIn("6857bf5c81d9662f7cf26f4a07eb59e463ac8253", text)
        for forbidden in ("\n  schedule:", "\n  workflow_dispatch:",
                          "\n  workflow_call:", "\n  push:",
                          "actions: write", "contents: write", "issues: write",
                          "Set-ScheduledTask", "Start-ScheduledTask",
                          "Stop-ScheduledTask", "Register-ScheduledTask"):
            self.assertNotIn(forbidden, text)
        self.assertFalse(g145.generic_paths_safe([
            ".github/workflows/f139-v39-actions-get-diagnostic-once.yml"]))
        self.assertEqual(g145.V39_ACTIONS_GET_BRANCH,
                         "engineering/f139-v39-original-actions-get-cause-20261115")
        self.assertEqual(len(g145.V39_ACTIONS_GET_FILES), 7)
        g145.v39_actions_get_negative_controls()


if __name__ == "__main__":
    unittest.main()
