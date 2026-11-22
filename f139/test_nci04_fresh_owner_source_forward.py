"""Synthetic authenticated forward-owner source proof; no task or GH mutations."""
from __future__ import annotations
import json
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from f139.nci04_native_contract import canonical
from f139.nci04_fresh_owner_source_forward import (
    DOMAIN, FIELDS, FORGE, JOB, NAME, PREFIX, SCHEMA, WORKFLOW,
    ForwardSourceDenied, inspect_forward, installed_forward_source, sign,
)
from f139.nci04_fresh_worker_protocol import SOURCE


class FakeDB:
    class Connection:
        def __init__(self, term_hash):
            self.term_hash = term_hash
        def execute(self, query):
            if query != "SELECT kind,sha FROM events WHERE seq=9":
                raise AssertionError("unexpected ledger query")
            return self
        def fetchone(self):
            return {"kind": "FRESH_WORKER_PROVIDER_CUSTODY",
                    "sha": self.term_hash}
    def __init__(self, filename, sha):
        self.filename = filename
        self.conn = self.Connection(sha)
    def meta(self):
        return {"head_seq": 9}


class FakeAPI:
    def __init__(self, routes):
        self.routes = routes
        self.reads = []
    def get(self, path):
        self.reads.append(path)
        return json.loads(json.dumps(self.routes[path]))


class SourceForwardTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.key = "strictly-synthetic-owner-signature-key-" * 2
        self.release = {
            "admission_source_sha": SOURCE,
            "worker_release_sha": "a" * 40,
            "worker_release_tree": "b" * 40,
        }
        self.doc = {
            "schema": SCHEMA, "admission_source_sha": SOURCE,
            "worker_release_sha": self.release["worker_release_sha"],
            "worker_release_tree": self.release["worker_release_tree"],
            "owner_source_sha": "c" * 40, "owner_source_tree": "d" * 40,
            "pr_number": 1863, "pr_head_sha": "e" * 40,
            "owner_run_id": 600, "owner_comment_id": 601,
            "regression_run_id": 602, "source_run_id": 603,
            "rehearsal_run_id": 604, "terminal_seq": 9,
            "terminal_hash": "f" * 64,
            "task_name": "FORGE-F139-UnifiedController",
            "development_only": True, "worker_release_unchanged": True,
            "scientific_first_use": False, "paid_model_calls": 0,
        }
        self.doc["owner_signature"] = sign(self.doc, self.key)
        self.db = FakeDB(self.folder / "state.sqlite", self.doc["terminal_hash"])
        mk_run = lambda n: {
            "id": n, "head_sha": self.doc["pr_head_sha"],
            "event": "pull_request", "run_attempt": 1,
            "status": "completed", "conclusion": "success",
        }
        jobs = lambda names: {
            "total_count": len(names),
            "jobs": [{"name": n, "status": "completed", "conclusion": "success"}
                     for n in sorted(names)]
        }
        self.routes = {
            FORGE + "/branches/main": {
                "name": "main", "protected": True,
                "commit": {"sha": self.doc["owner_source_sha"]},
            },
            FORGE + "/git/commits/" + self.doc["owner_source_sha"]: {
                "sha": self.doc["owner_source_sha"],
                "tree": {"sha": self.doc["owner_source_tree"]},
            },
            FORGE + "/pulls/" + str(self.doc["pr_number"]): {
                "merged": True, "state": "closed",
                "merge_commit_sha": self.doc["owner_source_sha"],
                "head": {"sha": self.doc["pr_head_sha"],
                         "repo": {"full_name": "spoonman136668-ai/FORGE"}},
                "base": {"repo": {"full_name": "spoonman136668-ai/FORGE"}},
                "user": {"login": "spoonman136668-ai"},
            },
            FORGE + "/issues/comments/" + str(self.doc["owner_comment_id"]): {
                "id": self.doc["owner_comment_id"],
                "issue_url": "https://api.github.com/" + FORGE + "/issues/1830",
                "body": PREFIX + self.doc["owner_source_sha"] + " " +
                    self.doc["pr_head_sha"] + " " + str(self.doc["pr_number"]) +
                    " " + str(self.doc["regression_run_id"]) +
                    " " + str(self.doc["source_run_id"]) +
                    " " + str(self.doc["rehearsal_run_id"]),
                "user": {"login": "spoonman136668-ai"},
                "author_association": "OWNER",
            },
            FORGE + "/actions/runs/" + str(self.doc["owner_run_id"]): {
                "id": self.doc["owner_run_id"],
                "event": "issue_comment", "path": WORKFLOW,
                "head_sha": self.doc["owner_source_sha"],
                "run_attempt": 1, "status": "completed",
                "conclusion": "success",
                "actor": {"login": "spoonman136668-ai"},
            },
            FORGE + "/actions/runs/" + str(self.doc["owner_run_id"])
                + "/jobs?per_page=100": {
                    "total_count": 1,
                    "jobs": [{"name": JOB, "runner_name": "FORGE-CODEX-REMOTE",
                              "status": "completed", "conclusion": "success"}],
                },
        }
        cases = [
            (602, {"windows_f139", "linux_f139", "windows_genenv",
                   "linux_genenv", "windows_native", "linux_native",
                   "windows", "linux"}),
            (603, {"source (ubuntu-latest)", "source (windows-latest)"}),
            (604, {"development-rehearsal (ubuntu-latest)",
                   "development-rehearsal (windows-latest)"}),
        ]
        for run, names in cases:
            route = FORGE + "/actions/runs/" + str(run)
            self.routes[route] = mk_run(run)
            self.routes[route + "/jobs?per_page=100"] = jobs(names)
        self.api = FakeAPI(self.routes)

    def test_without_certificate_old_source_pin_remains_mandatory(self):
        self.assertEqual(installed_forward_source(
            self.db, self.api, self.release, self.key),
            (self.release["worker_release_sha"],
             self.release["worker_release_tree"]))
        self.assertEqual(self.api.reads, [])

    def test_signed_cold_certificate_requires_all_three_qualified_os_runs(self):
        (self.folder / NAME).write_bytes(canonical(self.doc))
        self.assertEqual(installed_forward_source(
            self.db, self.api, self.release, self.key),
            (self.doc["owner_source_sha"], self.doc["owner_source_tree"]))
        self.assertGreaterEqual(len(self.api.reads), 10)
        self.assertEqual(self.db.meta()["head_seq"], 9)

    def test_forgery_or_changed_file_rejected_before_any_provider(self):
        for changed in (
            {"owner_source_sha": "4" * 40},
            {"worker_release_unchanged": False},
            {"paid_model_calls": 1},
            {"owner_signature": "f" * 64},
            {"owner_run_id": True},
        ):
            with self.subTest(changed=changed):
                forged = dict(self.doc, **changed)
                with self.assertRaises(ForwardSourceDenied):
                    inspect_forward(forged, db=self.db, api=self.api,
                                    release=self.release, key=self.key)
        self.assertEqual(self.api.reads, [])

    def test_provider_alterations_fail_closed(self):
        def run(case, route, field, value):
            original = self.routes[route]
            self.routes[route] = dict(original, **{field: value})
            try:
                with self.subTest(case=case), self.assertRaises(ForwardSourceDenied):
                    inspect_forward(self.doc, db=self.db, api=self.api,
                                    release=self.release, key=self.key)
            finally:
                self.routes[route] = original
        run("moved main", FORGE + "/branches/main", "protected", False)
        run("not merged", FORGE + "/pulls/1863", "merged", False)
        run("source CI failed", FORGE + "/actions/runs/603", "conclusion", "failure")
        run("owner run not complete", FORGE + "/actions/runs/600",
            "status", "in_progress")

    def test_original_owner_two_phase_cutover_remains_one_task(self):
        # Static confinement only; does not claim live Task Scheduler PASS.
        repo = Path(__file__).resolve().parent.parent
        script = (repo / "f139" / "nci04_fresh_owner_source_forward.ps1").read_text(
            encoding="utf-8")
        workflow = (repo / ".github" / "workflows" /
                    "f139-fresh-owner-source-forward.yml").read_text(encoding="utf-8")
        for token in ("Disable-ScheduledTask", "Stop-ScheduledTask",
                      "Set-ScheduledTask", "Enable-ScheduledTask",
                      "Start-ScheduledTask", "CheckLedger",
                      "F139_FRESH_FORWARD_COLD_TERMINAL9=PASS",
                      "F139_FRESH_ORIGINAL_SAME_TASK_SOURCE_FORWARDED=PASS"):
            self.assertIn(token, script)
        for forbidden in ("Register-ScheduledTask", "Unregister-ScheduledTask",
                          "New-ScheduledTaskTrigger", "Invoke-Expression",
                          "powershell -EncodedCommand"):
            self.assertNotIn(forbidden, script)
        self.assertIn("'-Phase Prepare", workflow.replace(" -Phase Prepare", "'-Phase Prepare"))
        self.assertIn(" -Phase Start", workflow)
        self.assertIn("fresh-original-owner-source-forward-start:", workflow)
        self.assertIn("concurrency:", workflow)
        self.assertEqual(workflow.count("  fresh-original-owner-source-forward:"), 1)
        self.assertEqual(workflow.count("  fresh-original-owner-source-forward-start:"), 1)

    def test_exact_owner_workflow_exception_preserves_generic_denial(self):
        # Explicit one-owner PR + one changed workflow blob, never a general
        # privilege to bypass workflow guards or native security harnesses.
        import os
        from scripts.check_rar_g145_pr_scope import admit_original_pr

        main = "e0467115ea085e2f0ddbee258e4d8937f6a90f10"
        head = "a" * 40
        branch = "engineering/f139-fresh-original-source-forward-20261122"
        workflow = ".github/workflows/f139-fresh-owner-source-forward.yml"
        original_workflow = ".github/workflows/f139-fresh-original-owner-rebind.yml"
        paths = sorted((
            workflow, ".github/workflows/forge-f139-source-qualification.yml",
            "f139/nci04_fresh_lifecycle.py",
            "f139/nci04_fresh_owner_source_forward.ps1",
            "f139/nci04_fresh_owner_source_forward.py",
            "f139/nci04_fresh_successor_publication.py",
            "f139/test_nci04_fresh_owner_source_forward.py",
            "scripts/check_rar_g145_pr_scope.py",
        ))
        req = {
            "number": 1863, "author_association": "OWNER",
            "user": {"login": "spoonman136668-ai"},
            "head": {"ref": branch, "sha": head,
                     "repo": {"full_name": "spoonman136668-ai/FORGE"}},
            "base": {"ref": "main", "sha": main,
                     "repo": {"full_name": "spoonman136668-ai/FORGE"}},
        }
        expected = {
            ("merge-base", main, head): main,
            ("rev-parse", main + "^{tree}"):
                "ebe959a996b7d0e90eced139912141fe0fb17482",
            ("rev-parse", main + ":" + original_workflow):
                "28cc3bf32afaa257c5c60d0c26a368dcd3da821f",
            ("rev-parse", head + ":" + workflow):
                "e86c8c45f04dc14b3c3a7457ca837d113a422903",
            ("diff", "--no-renames", "--name-only", main, head):
                "\n".join(paths),
        }
        def fake_git(*args):
            return expected[args]
        event = self.folder / "source-forward-owner-event.json"
        env = {"GITHUB_EVENT_NAME": "pull_request",
               "GITHUB_EVENT_PATH": str(event),
               "GITHUB_HEAD_REF": branch,
               "GITHUB_BASE_REF": "main"}
        with patch.dict(os.environ, env):
            def admit(payload=req, overrides=None):
                event.write_text(json.dumps({"pull_request": payload}),
                                 encoding="utf-8")
                return admit_original_pr(head, fake_git if overrides is None
                                         else lambda *args: overrides[args])
            self.assertEqual(
                admit(), "F139_FORWARD_ORIGINAL_OWNER_SCOPED_SOURCE_CI_ONLY")
            for bad in (
                {**req, "number": 1864},
                {**req, "author_association": "CONTRIBUTOR"},
                {**req, "user": {"login": "untrusted"}},
                {**req, "head": {**req["head"], "ref": "main"}},
            ):
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    admit(bad)
            for field, value in (
                (("rev-parse", main + ":" + original_workflow), "f" * 40),
                (("rev-parse", head + ":" + workflow), "f" * 40),
                (("diff", "--no-renames", "--name-only", main, head),
                 "\n".join(paths[:-1])),
                (("merge-base", main, head), "f" * 40),
            ):
                with self.subTest(field=field), self.assertRaises(ValueError):
                    admit(req, {**expected, field: value})

    def test_certificate_corrupt_or_symlink_never_falls_back(self):
        path = self.folder / NAME
        path.write_bytes(b'{"not":"canonical"}\n')
        with self.assertRaises(ForwardSourceDenied):
            installed_forward_source(self.db, self.api, self.release, self.key)
        path.unlink()
        path.symlink_to(self.folder / "missing.json")
        with self.assertRaises(ForwardSourceDenied):
            installed_forward_source(self.db, self.api, self.release, self.key)
