"""V41 cold backup authorization negatives: no original host mutation."""
from pathlib import Path
import unittest

from f139 import nci04_v41_owner_cold_backup as gate

SHA = "2ee1d2e3894558a92231e5922980f8c96e731b36"
ENV = dict(GITHUB_REPOSITORY=gate.REPO, GITHUB_ACTOR=gate.OWNER,
           GITHUB_EVENT_NAME="issue_comment", GITHUB_REF="refs/heads/main",
           RUNNER_NAME="FORGE-CODEX-REMOTE", GITHUB_RUN_ATTEMPT="1",
           GITHUB_SHA=SHA, GITHUB_RUN_ID="12345")


def event():
    return {
        "action": "created", "sender": {"login": gate.OWNER},
        "issue": {"number": 807, "user": {"login": gate.OWNER}},
        "comment": {"id": 77, "body": gate.PREFIX + SHA,
                    "user": {"login": gate.OWNER},
                    "author_association": "OWNER",
                    "created_at": "2026-11-12T21:00:00Z"},
    }


def get(route):
    assert route == "repos/" + gate.REPO + "/issues/comments/77"
    return {**event()["comment"],
            "issue_url": "https://api.github.com/repos/" +
                         gate.REPO + "/issues/807"}


class OwnerBackupGateTests(unittest.TestCase):
    def attempt(self, env=None, ev=None, reader=get):
        return gate.verify_owner_event(ENV if env is None else env,
                                       event() if ev is None else ev,
                                       reader, target=SHA)

    def test_owner_comment_double_read_exact(self):
        calls = []
        def read(route):
            calls.append(route)
            return get(route)
        self.assertEqual(self.attempt(reader=read), 12345)
        self.assertEqual(len(calls), 2)

    def test_wrong_actor_runner_source_and_replay_denied(self):
        for key, value in (
            ("GITHUB_ACTOR", "other"), ("GITHUB_REPOSITORY", "other/repo"),
            ("GITHUB_REF", "refs/heads/test"), ("GITHUB_SHA", "a" * 40),
            ("RUNNER_NAME", "unknown"), ("GITHUB_EVENT_NAME", "push"),
            ("GITHUB_RUN_ATTEMPT", "2"), ("GITHUB_RUN_ID", "0")):
            with self.subTest(key=key), self.assertRaises(gate.OwnerBackupDenied):
                self.attempt(env={**ENV, key: value})

    def test_bad_owner_comment_and_807_custody_denied(self):
        for name in ("wrong_prefix", "wrong_owner", "wrong_issue",
                     "is_pr", "wrong_sender", "wrong_assoc", "replayed"):
            request = event()
            if name == "wrong_prefix":
                request["comment"]["body"] = "F139-V41-CUTOVER " + SHA
            elif name == "wrong_owner":
                request["comment"]["user"]["login"] = "other"
            elif name == "wrong_issue":
                request["issue"]["number"] = 1715
            elif name == "is_pr":
                request["issue"]["pull_request"] = {}
            elif name == "wrong_sender":
                request["sender"]["login"] = "other"
            elif name == "wrong_assoc":
                request["comment"]["author_association"] = "CONTRIBUTOR"
            else:
                request["action"] = "edited"
            with self.subTest(name=name), self.assertRaises(gate.OwnerBackupDenied):
                self.attempt(ev=request)

    def test_second_github_readback_drift_denied(self):
        calls = []
        def drift(route):
            calls.append(route)
            result = get(route)
            if len(calls) == 2:
                result["body"] = "tampered"
            return result
        with self.assertRaisesRegex(gate.OwnerBackupDenied,
                                    "OWNER_COMMENT_READBACK_DRIFT"):
            self.attempt(reader=drift)

    def test_existing_workflow_quiescence_and_no_task_mutation(self):
        file = (Path(__file__).resolve().parents[1] /
                ".github/workflows/f139-g54-v9-owner-cutover.yml")
        data = file.read_text(encoding="utf-8")
        marker = "\n  v41-owner-cold-backup-only:\n"
        self.assertEqual(data.count(marker), 1)
        body = data.split(marker, 1)[1]
        self.assertIn("forge-codex-isolated", body)
        self.assertIn("F139-V41-COLD-BACKUP-ONLY ", body)
        self.assertIn("F139_V41_ORIGINAL_TASK_NOT_QUIESCED", body)
        self.assertIn("nci04_v41_owner_cold_backup", body)
        self.assertIn("persist-credentials: false", body)
        self.assertIn("permissions:\n      contents: read\n      issues: read", body)
        self.assertIn("forge-f139-g54-v9-owner-cutover", data)
        for forbidden in ("Disable-ScheduledTask", "Stop-ScheduledTask",
                          "Start-ScheduledTask", "Set-ScheduledTask",
                          "Register-ScheduledTask", "Invoke-Expression",
                          "workflow_dispatch"):
            self.assertNotIn(forbidden, body)

    def test_no_owner_writer_in_backup_module(self):
        text = (Path(__file__).with_name("nci04_v41_owner_cold_backup.py")
                .read_text(encoding="utf-8"))
        for forbidden in ("db.event(", "UPDATE meta SET",
                          "Disable-ScheduledTask", "create_ref(",
                          "create_native_feed_issue"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
