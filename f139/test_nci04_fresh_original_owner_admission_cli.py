"""Negative controls for the source-only, owner-comment fresh admission route."""
from __future__ import annotations

import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from f139.nci04_fresh_original_owner_admission_cli import (
    OwnerAdmissionDenied, allowed_read, find_one_activated, inspect_event,
)
from f139.nci04_fresh_native_intake import OWNER_WORKFLOW

SOURCE = "a" * 40


class OwnerAdmissionCLIControls(unittest.TestCase):
    def setUp(self):
        self.env = {
            "RUNNER_NAME": "FORGE-CODEX-REMOTE",
            "GITHUB_REPOSITORY": "spoonman136668-ai/FORGE",
            "GITHUB_ACTOR": "spoonman136668-ai",
            "GITHUB_EVENT_NAME": "issue_comment",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_WORKFLOW_REF": OWNER_WORKFLOW,
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_RUN_ID": "5001",
            "GITHUB_SHA": SOURCE,
        }
        self.event = {
            "action": "created",
            "repository": {"full_name": "spoonman136668-ai/FORGE"},
            "sender": {"login": "spoonman136668-ai"},
            "issue": {"number": 1830, "state": "open",
                      "user": {"login": "spoonman136668-ai"}},
            "comment": {
                "id": 5002, "author_association": "OWNER",
                "user": {"login": "spoonman136668-ai"},
                "body": "F139-FRESH-DEV-ADMIT " + SOURCE + " 4001",
                "url": ("https://api.github.com/repos/"
                        "spoonman136668-ai/FORGE/issues/comments/5002"),
            },
        }

    def test_only_exact_owner_event_is_accepted_for_parsing(self):
        self.assertEqual(inspect_event(self.event, self.env), (4001, 5002))

    def test_reject_unqualified_actors_attempts_and_workflows(self):
        for key, value in (
            ("GITHUB_ACTOR", "other"),
            ("RUNNER_NAME", "random-runner"),
            ("GITHUB_WORKFLOW_REF", "evil/workflow.yml@refs/heads/main"),
            ("GITHUB_RUN_ATTEMPT", "2"),
            ("GITHUB_REF", "refs/heads/branch"),
            ("OPENAI_API_KEY", "unexpected"),
        ):
            with self.subTest(key=key):
                env = dict(self.env, **{key: value})
                with self.assertRaises(OwnerAdmissionDenied):
                    inspect_event(self.event, env)

    def test_reject_changed_comment_body_issue_and_author(self):
        for field, value in (
            ("body", "F139-FRESH-DEV-ADMIT " + SOURCE + " 4001\nextra"),
            ("body", "F139-FRESH-DEV-ADMIT " + ("b" * 40) + " 4001"),
            ("body", "F139-FRESH-DEV-ADMIT " + SOURCE + " 0"),
            ("author_association", "CONTRIBUTOR"),
            ("id", 0),
        ):
            with self.subTest(field=field):
                comment = dict(self.event["comment"], **{field: value})
                with self.assertRaises(OwnerAdmissionDenied):
                    inspect_event(dict(self.event, comment=comment), self.env)
        issue = dict(self.event["issue"], number=807)
        with self.assertRaises(OwnerAdmissionDenied):
            inspect_event(dict(self.event, issue=issue), self.env)

    def test_provider_allowlist_has_no_mutation_surface(self):
        self.assertTrue(allowed_read(
            "repos/spoonman136668-ai/FORGE/branches/main", 4001, 5002))
        self.assertTrue(allowed_read(
            "repos/spoonman136668-ai/Yggdrasil/git/commits/" + SOURCE,
            4001, 5002))
        self.assertFalse(allowed_read(
            "repos/spoonman136668-ai/FORGE/issues/4002", 4001, 5002))
        self.assertFalse(allowed_read(
            "repos/spoonman136668-ai/FORGE/actions/workflows/dispatches",
            4001, 5002))
        self.assertFalse(allowed_read(
            "repos/spoonman136668-ai/Yggdrasil/git/refs/heads/main",
            4001, 5002))

    def test_exactly_one_cold_activated_db_or_fail_closed(self):
        class Readonly:
            def close(self):
                pass
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "FORGE-F139"
            root.mkdir()
            a = root / "f139-fresh-dev-10" / "state.sqlite"
            b = root / "f139-fresh-dev-11" / "state.sqlite"
            a.parent.mkdir()
            b.parent.mkdir()
            a.touch()
            b.touch()
            status = {
                str(a): {"source_sha": SOURCE,
                         "disposition": "FRESH_ACTIVATION_RECORDED_DISPATCH_BLOCKED"},
                str(b): {"source_sha": SOURCE,
                         "disposition": "FRESH_DEVELOPMENT_STAGED_DISABLED_NO_DISPATCH"},
            }
            with patch("f139.nci04_fresh_original_owner_admission_cli."
                       "Database.open_readonly", return_value=Readonly()), patch(
                "f139.nci04_fresh_original_owner_admission_cli."
                "inspect_staged_fresh_native_mode",
                side_effect=lambda db, path: status[str(path)]):
                self.assertEqual(find_one_activated(root, SOURCE), a)
                status[str(b)]["disposition"] = (
                    "FRESH_ACTIVATION_RECORDED_DISPATCH_BLOCKED")
                with self.assertRaisesRegex(
                        OwnerAdmissionDenied, "EXACTLY_ONE_ACTIVATED"):
                    find_one_activated(root, SOURCE)
                status[str(a)]["source_sha"] = "b" * 40
                with self.assertRaisesRegex(
                        OwnerAdmissionDenied, "FRESH_SOURCE_MISMATCH"):
                    find_one_activated(root, SOURCE)


if __name__ == "__main__":
    unittest.main()
