"""V42 read-only original-owner authenticated route/negative test coverage."""
from contextlib import contextmanager
import inspect
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from f139 import nci04_v42_original_owner_readonly as route
from f139 import nci04_v42_owner_source_readiness as source


class V42OriginalOwnerReadOnlyTests(unittest.TestCase):
    def inputs(self):
        target = "a"*40
        event = {
            "action": "created",
            "issue": {"number": 807, "user": {"login": source.OWNER}},
            "sender": {"login": source.OWNER},
            "comment": {
                "id": route.PREDECESSOR_COMMENT_ID + 1,
                "author_association": "OWNER",
                "user": {"login": source.OWNER},
                "body": route.PREFIX + target + " " +
                    str(route.PREDECESSOR_COMMENT_ID),
            },
        }
        env = {
            "GITHUB_REPOSITORY": source.REPO,
            "GITHUB_ACTOR": source.OWNER,
            "GITHUB_EVENT_NAME": "issue_comment",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_SHA": target, "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_RUN_ID": "12345",
            "RUNNER_NAME": "FORGE-CODEX-REMOTE",
        }
        return target, env, event

    def test_new_exact_owner_comment_is_required(self):
        target, env, event = self.inputs()
        self.assertTrue(route.authenticate(env, event, target))
        for field, invalid in (
            ("GITHUB_ACTOR", "outsider"),
            ("GITHUB_RUN_ATTEMPT", "2"),
            ("GITHUB_RUN_ID", "0"),
            ("RUNNER_NAME", "other"),
            ("GITHUB_REF", "refs/heads/feature"),
            ("GITHUB_SHA", "b"*40),
            ("OPENAI_API_KEY", "not-permitted"),
        ):
            with self.subTest(field=field):
                bad = dict(env, **{field: invalid})
                with self.assertRaises(route.V42OriginalReadOnlyDenied):
                    route.authenticate(bad, event, target)
        for path, value in (
            (("issue", "number"), 1715),
            (("issue", "pull_request"), {}),
            (("sender", "login"), "outsider"),
            (("comment", "id"), route.PREDECESSOR_COMMENT_ID),
            (("comment", "body"), route.PREFIX + "b"*40),
            (("comment", "author_association"), "CONTRIBUTOR"),
            (("comment", "user"), {"login": "outsider"}),
        ):
            with self.subTest(path=path):
                bad = json.loads(json.dumps(event))
                bad[path[0]][path[1]] = value
                with self.assertRaises(route.V42OriginalReadOnlyDenied):
                    route.authenticate(env, bad, target)

    def test_unapproved_event_does_not_read_provider_or_database(self):
        target, env, event = self.inputs()
        event["comment"]["body"] = "not approved"
        with patch.object(source, "release_source",
                          side_effect=AssertionError("provider must not read")):
            with self.assertRaises(route.V42OriginalReadOnlyDenied):
                route.inspect("/untrusted/state.sqlite", env, event,
                              target=target, get=lambda _: None)

    def test_real_path_read_only_after_source_proof_and_remote_recheck(self):
        target, env, event = self.inputs()
        with tempfile.TemporaryDirectory() as temp:
            env["LOCALAPPDATA"] = temp
            db = Path(temp) / "FORGE-F139" / "state.sqlite"
            db.parent.mkdir()
            db.write_bytes(b"untouched private placeholder")
            before = db.read_bytes()
            receipt = {"target_source_sha": target,
                       "main_qualification_run_id": 123,
                       "main_qualification_job_count": 8}
            cold = {"original_source_sha": source.BEFORE,
                    "original_head_seq": source.FROZEN_SEQ,
                    "original_head_sha256": source.FROZEN_HEAD,
                    "original_owner_mutations": 0,
                    "verified_tasks": 153, "quarantined_tasks": 56,
                    "pending_issue_admitted": False}
            @contextmanager
            def owned(_):
                yield
            fake = MagicMock()
            with patch.object(source, "release_source",
                              return_value=receipt) as read_remote, \
                 patch.object(route, "_read_only_owner_lease", new=owned), \
                 patch.object(route.Database, "open_readonly",
                              return_value=fake) as opened, \
                 patch.object(source, "original_owner_cold_read",
                              return_value=cold) as read_cold:
                status = route.inspect(db, env, event, target=target,
                                       get=lambda _: None)
                self.assertEqual(read_remote.call_count, 2)
                opened.assert_called_once_with(db)
                read_cold.assert_called_once_with(fake)
                self.assertEqual(status["main_qualification_job_count"], 8)
                self.assertEqual(status["historical_verified"], 153)
                self.assertFalse(status["source_transition_authorized"])
                self.assertFalse(status["task_restart_authorized"])
                self.assertFalse(status["scientific_first_use"])
                self.assertEqual(status["new_dispatches"], 0)
            self.assertEqual(db.read_bytes(), before)

    def test_ambiguous_provider_second_read_cannot_qualify(self):
        target, env, event = self.inputs()
        with tempfile.TemporaryDirectory() as temp:
            env["LOCALAPPDATA"] = temp
            path = Path(temp) / "FORGE-F139" / "state.sqlite"
            path.parent.mkdir()
            path.write_bytes(b"fixed")
            first = {"target_source_sha": target,
                     "main_qualification_run_id": 1}
            second = dict(first, main_qualification_run_id=2)
            @contextmanager
            def owned(_):
                yield
            fake = MagicMock()
            cold = {"original_source_sha": source.BEFORE,
                    "original_head_seq": source.FROZEN_SEQ,
                    "original_head_sha256": source.FROZEN_HEAD,
                    "original_owner_mutations": 0}
            with patch.object(source, "release_source",
                              side_effect=(first, second)), \
                 patch.object(route, "_read_only_owner_lease", new=owned), \
                 patch.object(route.Database, "open_readonly",
                              return_value=fake), \
                 patch.object(source, "original_owner_cold_read",
                              return_value=cold):
                with self.assertRaisesRegex(
                        route.V42OriginalReadOnlyDenied,
                        "ORIGINAL_OR_REMOTE_CHANGED"):
                    route.inspect(path, env, event, target=target,
                                  get=lambda _: None)

    def test_existing_workflow_adds_one_event_only_readonly_job(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/f139-g54-v9-owner-cutover.yml"
                    ).read_text(encoding="utf-8")
        marker = "\n  v42-original-owner-readonly:\n"
        self.assertEqual(workflow.count(marker), 1)
        addition = workflow.split(marker, 1)[1]
        self.assertIn("F139-V42-ORIGINAL-READONLY ", addition)
        self.assertIn("github.event_name == 'issue_comment'", addition)
        self.assertIn("f139.nci04_v42_original_owner_readonly", addition)
        self.assertIn("GITHUB_RUN_ATTEMPT -ceq '1'", addition)
        self.assertIn("RUNNER_NAME -ceq 'FORGE-CODEX-REMOTE'", addition)
        self.assertIn("6912162079", addition)
        self.assertIn("source_transition_authorized", inspect.getsource(route))
        self.assertNotIn("  schedule:", addition)
        self.assertNotIn("  workflow_dispatch:", addition)
        for forbidden in ("Start-ScheduledTask", "Disable-ScheduledTask",
                          "Stop-ScheduledTask", "Enable-ScheduledTask",
                          "Register-ScheduledTask", "Stop-Process",
                          "gh api --method", "Invoke-Expression",
                          "Import-Clixml", "OPENAI_API_KEY:"):
            self.assertNotIn(forbidden, addition)
        self.assertFalse(hasattr(route, "original_source_commit"))
        self.assertFalse(hasattr(route, "deploy"))
        self.assertFalse(hasattr(route, "activate"))


class V42ExactOriginalCIScopeTests(unittest.TestCase):
    """Pin exact owner PR/source pair so ordinary PRs cannot edit workflows."""
    def admit(self, *, pr=1782, owner="spoonman136668-ai",
              role="OWNER", base="6006942116330ffc579784c88b1610d19b3f73cc",
              tree="1783004aec8c720ad28c47a68175264bad394d8c",
              before_blob="b0dfd96bb86cdb834dd908a7518027d12cc9ad95",
              after_blob="d8bfcad81206d82df7d4c2431bd56a570dbc755a",
              changes=None):
        from scripts import check_rar_g145_pr_scope as guard
        branch = "engineering/f139-v42-original-host-readonly-bridge-20261116"
        head = "c"*40
        workflow = ".github/workflows/f139-g54-v9-owner-cutover.yml"
        frozen = guard.FROZEN_SCOPES[branch][1]
        paths = sorted(frozen) if changes is None else changes
        payload = {"pull_request": {
            "number": pr, "author_association": role,
            "user": {"login": owner},
            "head": {"sha": head, "ref": branch,
                     "repo": {"full_name": guard.REPO}},
            "base": {"sha": base, "ref": "main",
                     "repo": {"full_name": guard.REPO}}}}
        outputs = {
            ("rev-parse", "6006942116330ffc579784c88b1610d19b3f73cc^{tree}"):
                tree,
            ("rev-parse", "6006942116330ffc579784c88b1610d19b3f73cc:"+workflow):
                before_blob,
            ("rev-parse", head+":"+workflow): after_blob,
            ("diff", "--no-renames", "--name-only",
             "6006942116330ffc579784c88b1610d19b3f73cc", head):
                "\n".join(paths),
        }
        with tempfile.TemporaryDirectory() as tmp:
            event_path = Path(tmp) / "event.json"
            event_path.write_text(json.dumps(payload), encoding="utf-8")
            with patch.dict(os.environ, {
                "GITHUB_EVENT_NAME": "pull_request",
                "GITHUB_EVENT_PATH": str(event_path),
                "GITHUB_HEAD_REF": branch,
                "GITHUB_BASE_REF": "main",
            }):
                return guard.admit_original_pr(head, lambda *a: outputs[a])

    def test_exact_pr1782_scoped_source_admitted_only_for_ci(self):
        self.assertEqual(self.admit(),
                         "FROZEN_G141_G144_OR_G145_HARNESS_DEVELOPMENT")

    def test_wrong_owner_scope_or_blobs_fail_closed(self):
        from scripts import check_rar_g145_pr_scope as guard
        branch = "engineering/f139-v42-original-host-readonly-bridge-20261116"
        paths = sorted(guard.FROZEN_SCOPES[branch][1])
        cases = (
            {"pr": 1783}, {"role": "CONTRIBUTOR"},
            {"owner": "other"},
            {"base": "f"*40}, {"tree": "f"*40},
            {"before_blob": "f"*40}, {"after_blob": "f"*40},
            {"changes": paths[:-1]},
            {"changes": paths + ["f139/local_controller.py"]},
            {"changes": paths + [paths[0]]},
        )
        for kwargs in cases:
            with self.subTest(**kwargs):
                with self.assertRaises(ValueError):
                    self.admit(**kwargs)
        self.assertFalse(guard.generic_paths_safe(
            [".github/workflows/f139-g54-v9-owner-cutover.yml"]))


if __name__ == "__main__":
    unittest.main()
