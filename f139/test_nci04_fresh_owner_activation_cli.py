"""Bounded original-owner fresh activation entry: source-only and negatives."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from f139 import nci04_fresh_owner_activation_cli as entry
from f139.nci04_fresh_activation_writer import (
    APPROVAL_PREFIX, WORKFLOW,
)
from f139.nci04_fresh_yggdrasil_boundary import (
    ACCEPTED, AMALGAM_HEAD, LINEAGE_HEAD,
)


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github/workflows/f139-fresh-original-owner-activation.yml"
ADMISSION_PATH = ROOT / ".github/workflows/f139-fresh-original-owner-admission.yml"
HEAD = "b" * 40


def event():
    return {
        "action": "created", "repository": {"full_name": entry.REPO},
        "sender": {"login": entry.OWNER},
        "issue": {"number": 1830, "state": "open",
                  "user": {"login": entry.OWNER}},
        "comment": {
            "id": 12345,
            "url": "https://api.github.com/repos/" + entry.REPO +
                   "/issues/comments/12345",
            "author_association": "OWNER",
            "user": {"login": entry.OWNER},
            "body": APPROVAL_PREFIX + " " + HEAD,
            "created_at": "2026-11-20T12:30:00Z",
        },
    }


def environment():
    return {
        "RUNNER_NAME": "FORGE-CODEX-REMOTE",
        "GITHUB_REPOSITORY": entry.REPO,
        "GITHUB_ACTOR": entry.OWNER,
        "GITHUB_EVENT_NAME": "issue_comment",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_WORKFLOW_REF": WORKFLOW,
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_RUN_ID": "44700000000",
        "GITHUB_SHA": HEAD,
        "GH_TOKEN": "test-credential-never-logged",
    }


class FreshOwnerActivationEntryTests(unittest.TestCase):
    def test_workflow_only_gated_owner_job(self):
        src = WORKFLOW_PATH.read_text(encoding="utf-8")
        admission = ADMISSION_PATH.read_text(encoding="utf-8")
        self.assertEqual(src.count("on:\n  issue_comment:\n    types: [created]"), 1)
        self.assertNotIn("\nconcurrency:\n", src)
        self.assertIn("    concurrency:\n      group: forge-f139-fresh-owner-admission\n"
                      "      cancel-in-progress: false\n", src)
        self.assertIn("group: forge-f139-fresh-owner-admission", admission)
        self.assertIn("github.event.issue.number == 1830", src)
        self.assertIn("github.event.comment.author_association == 'OWNER'", src)
        self.assertIn("startsWith(github.event.comment.body, "
                      "'F139-FRESH-DEV-STAGE-ACTIVATE ')", src)
        self.assertIn("python -B -m f139.nci04_fresh_owner_activation_cli", src)
        self.assertIn("persist-credentials: false", src)
        self.assertIn("F139_WORKER_DISPATCH_AUTHORIZED=FALSE", src)
        for unsafe in ("Stop-ScheduledTask", "Start-ScheduledTask",
                       "Register-ScheduledTask", "Set-ScheduledTask",
                       "gh api --method POST", "workflow_dispatch:", "schedule:"):
            self.assertNotIn(unsafe, src)

    def test_explicit_get_routes_only(self):
        self.assertTrue(entry.allow_get(entry.FORGE + "/branches/main", 12345))
        self.assertTrue(entry.allow_get(entry.FORGE + "/issues/comments/12345", 12345))
        self.assertTrue(entry.allow_get(entry.ISSUE_PAGE, 12345))
        self.assertTrue(entry.allow_get(entry.FORGE + "/issues/807", 12345))
        self.assertTrue(entry.allow_get(entry.YGG + "/branches/main", 12345))
        for head in (AMALGAM_HEAD, LINEAGE_HEAD):
            self.assertTrue(entry.allow_get(
                entry.YGG + "/compare/" + ACCEPTED + "..." + head, 12345))
        for route in (
            "https://api.github.com/" + entry.FORGE + "/branches/main",
            "repos/other/FORGE/issues/807",
            entry.FORGE + "/issues/comments/12346",
            entry.FORGE + "/issues/-1",
            entry.FORGE + "/issues/807?state=closed",
            entry.YGG + "/actions/runs/1",
            entry.YGG + "/contents/../../danger",
            "POST", "--method POST", "",
        ):
            with self.subTest(route=route):
                self.assertFalse(entry.allow_get(route, 12345))

    def test_provider_read_denies_unexpected_route_before_subprocess(self):
        with patch.object(entry.subprocess, "run") as invoke:
            with self.assertRaisesRegex(
                entry.FreshOwnerActivationDenied, "PROVIDER_ROUTE_DENIED"
            ):
                entry.read_provider("repos/other/SECRET", 1)
            invoke.assert_not_called()

    def test_owner_event_is_exact(self):
        # This helper is platform-bound: mock only platform identity.
        with patch.object(entry.os, "name", "nt"), patch.object(
            entry.sys, "platform", "win32"
        ):
            self.assertEqual(entry.event_and_source(event(), environment()),
                             (HEAD, 12345))
            for field, value in (
                ("RUNNER_NAME", "foreign-runner"),
                ("GITHUB_REF", "refs/heads/feature"),
                ("GITHUB_WORKFLOW_REF", "untrusted/path"),
                ("GITHUB_RUN_ATTEMPT", "2"),
                ("GITHUB_SHA", "a" * 40),
                ("GITHUB_ACTOR", "other"),
                ("GITHUB_RUN_ID", "0"),
                ("OPENAI_API_KEY", "not-allowed"),
            ):
                with self.subTest(field=field):
                    bad = environment()
                    bad[field] = value
                    with self.assertRaises(ValueError):
                        entry.event_and_source(event(), bad)
            for mutate in (
                lambda e: e["comment"].update(body="unexpected"),
                lambda e: e["comment"].update(author_association="CONTRIBUTOR"),
                lambda e: e["issue"].update(number=807),
                lambda e: e["sender"].update(login="other"),
                lambda e: e["comment"]["user"].update(login="other"),
            ):
                forged = event()
                mutate(forged)
                with self.assertRaises(ValueError):
                    entry.event_and_source(forged, environment())

    def test_partial_archive_never_replayed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            entry.no_previous_attempt(root)
            (root / "f139-v59-before-44700000000").mkdir()
            with self.assertRaisesRegex(ValueError, "PRIOR_ATTEMPT"):
                entry.no_previous_attempt(root)

    def test_source_bound_remote_comment_and_protected_branch(self):
        remote = dict(event()["comment"], issue_url="https://api.github.com/repos/" +
                      entry.REPO + "/issues/1830")
        branch = {"name": "main", "protected": True,
                  "commit": {"sha": HEAD}}
        def get(route):
            if route.endswith("/branches/main"):
                return branch
            return remote
        class Done:
            def __init__(self, stdout):
                self.stdout = stdout
                self.returncode = 0
        with patch.object(entry.subprocess, "run",
                          side_effect=[Done(HEAD.encode() + b"\n"), Done(b"")]):
            entry.check_provider_source(HEAD, event(), 12345, get)
        with patch.object(entry.subprocess, "run") as run:
            def corrupt(route):
                if route.endswith("/branches/main"):
                    return branch
                return dict(remote, author_association="CONTRIBUTOR")
            with self.assertRaisesRegex(ValueError, "PROVIDER_OWNER_COMMENT_DRIFT"):
                entry.check_provider_source(HEAD, event(), 12345, corrupt)
            run.assert_not_called()


    def test_owner_pr_source_scope_and_mutation_negatives(self):
        from scripts.check_rar_g145_pr_scope import (
            FRESH_ACTIVATION_BASE, FRESH_ACTIVATION_BLOB,
            FRESH_ACTIVATION_BRANCH, FRESH_ACTIVATION_FILES,
            FRESH_ACTIVATION_TREE, FRESH_ACTIVATION_WORKFLOW,
            FRESH_ACTIVATION_NATIVE_WORKFLOW, FRESH_ACTIVATION_NATIVE_BLOB,
            FRESH_ACTIVATION_G137, FRESH_ACTIVATION_G137_BLOB,
            FRESH_ACTIVATION_CRYPTO_TEST, FRESH_ACTIVATION_CRYPTO_BLOB,
            admit_fresh_owner_activation_bridge, generic_paths_safe,
        )
        head = "b" * 40
        base = FRESH_ACTIVATION_BASE
        request = {
            "number": 1847,
            "author_association": "OWNER",
            "user": {"login": "spoonman136668-ai"},
            "head": {"sha": head, "ref": FRESH_ACTIVATION_BRANCH,
                     "repo": {"full_name": "spoonman136668-ai/FORGE"}},
            "base": {"sha": base, "ref": "main",
                     "repo": {"full_name": "spoonman136668-ai/FORGE"}},
        }
        files = sorted(FRESH_ACTIVATION_FILES)
        answers = {
            ("merge-base", base, head): base,
            ("rev-parse", base + "^{tree}"): FRESH_ACTIVATION_TREE,
            ("rev-parse", head + ":" + FRESH_ACTIVATION_WORKFLOW):
                FRESH_ACTIVATION_BLOB,
            ("rev-parse", head + ":" + FRESH_ACTIVATION_NATIVE_WORKFLOW):
                FRESH_ACTIVATION_NATIVE_BLOB,
            ("rev-parse", head + ":" + FRESH_ACTIVATION_G137):
                FRESH_ACTIVATION_G137_BLOB,
            ("rev-parse", head + ":" + FRESH_ACTIVATION_CRYPTO_TEST):
                FRESH_ACTIVATION_CRYPTO_BLOB,
            ("diff", "--no-renames", "--name-only", base, head):
                "\n".join(files),
        }
        git = lambda *args: answers[args]
        self.assertFalse(generic_paths_safe(files))
        self.assertEqual(
            admit_fresh_owner_activation_bridge(head, base, request, git),
            "EXACT_PR1847_FRESH_NATIVE_OWNER_ACTIVATION_CI_ONLY")
        for wrong in (
            dict(request, number=1846),
            dict(request, author_association="COLLABORATOR"),
            dict(request, user={"login": "not-owner"}),
            dict(request, head=dict(request["head"], ref="wrong-branch")),
            dict(request, base=dict(request["base"], sha="c" * 40)),
        ):
            with self.subTest(input=wrong):
                with self.assertRaises(ValueError):
                    admit_fresh_owner_activation_bridge(head, base, wrong, git)
        for item, bad in (
            (("merge-base", base, head), "0" * 40),
            (("rev-parse", base + "^{tree}"), "0" * 40),
            (("rev-parse", head + ":" + FRESH_ACTIVATION_WORKFLOW), "0" * 40),
            (("rev-parse", head + ":" + FRESH_ACTIVATION_NATIVE_WORKFLOW), "0" * 40),
            (("rev-parse", head + ":" + FRESH_ACTIVATION_G137), "0" * 40),
            (("rev-parse", head + ":" + FRESH_ACTIVATION_CRYPTO_TEST), "0" * 40),
            (("diff", "--no-renames", "--name-only", base, head),
             "\n".join(files) + "\n.github/workflows/other.yml"),
        ):
            with self.subTest(item=item):
                bad_answers = dict(answers)
                bad_answers[item] = bad
                with self.assertRaisesRegex(ValueError, "EXACT_SCOPE_DENIED"):
                    admit_fresh_owner_activation_bridge(
                        head, base, request, lambda *args: bad_answers[args])


if __name__ == "__main__":
    unittest.main()
