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

    def test_other_signed_owner_pr_is_not_source_forward_authorized(self):
        # A genuine owner signature does not widen the exact PR #1863 route.
        for number in (1862, 1864, 1900, True):
            with self.subTest(number=number):
                bad = dict(self.doc, pr_number=number)
                bad["owner_signature"] = sign(
                    {k: v for k, v in bad.items() if k != "owner_signature"},
                    self.key)
                with self.assertRaisesRegex(
                        ForwardSourceDenied, "RECORD_SCOPE_OR_AUTHORITY_INVALID"):
                    inspect_forward(bad, db=self.db, api=self.api,
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

    def test_source_certificate_uses_bounded_argument_not_native_stdin(self):
        """Exercise module signing, verification and negative inputs."""
        import base64
        import os
        import subprocess
        import sys
        repo = Path(__file__).resolve().parent.parent
        script = (repo / "f139" / "nci04_fresh_owner_source_forward.ps1").read_text(encoding="utf-8")
        for marker in ("SIGNED_CERT_DOCUMENT_SIZE_INVALID",
                       "START_DOCUMENT_SIZE_INVALID",
                       " -m f139.nci04_fresh_owner_source_forward sign-cert $cert $encodedDoc",
                       " -m f139.nci04_fresh_owner_source_forward verify-cert $signature $encodedDoc"):
            self.assertIn(marker, script)
        self.assertNotIn(" -c $code $cert", script)
        self.assertNotIn(" -c $code $signature", script)
        unsigned = {k: v for k, v in self.doc.items() if k != "owner_signature"}
        encoded = base64.b64encode(canonical(unsigned)).decode("ascii")
        env = dict(os.environ, F139_WORKER_HMAC_KEY=self.key)
        def invoke(mode, target, payload, environ=env):
            return subprocess.run([sys.executable, "-B", "-m",
                                   "f139.nci04_fresh_owner_source_forward",
                                   mode, str(target), payload],
                                  cwd=repo, env=environ, capture_output=True,
                                  text=True, timeout=30, check=False)
        cert = self.folder / "native-transport-certificate.json"
        created = invoke("sign-cert", cert, encoded)
        self.assertEqual(created.returncode, 0, created.stderr)
        self.assertEqual(created.stdout.strip(), "F139_FRESH_FORWARD_CERTIFICATE=CREATE_ONLY_SIGNED")
        signed = json.loads(cert.read_bytes())
        self.assertEqual(cert.read_bytes(), canonical(signed))
        self.assertEqual(signed["owner_signature"], self.doc["owner_signature"])
        verified = invoke("verify-cert", signed["owner_signature"], encoded)
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertEqual(verified.stdout.strip(), "F139_FORWARD_HMAC_VERIFIED")
        before = cert.read_bytes()
        self.assertNotEqual(invoke("sign-cert", cert, encoded).returncode, 0)
        self.assertEqual(cert.read_bytes(), before)
        self.assertNotEqual(invoke("verify-cert", "0" * 64, encoded).returncode, 0)
        for i, payload in enumerate(("", "%%%",
                base64.b64encode(b"not json").decode("ascii"),
                base64.b64encode(b"x" * 8193).decode("ascii"),
                base64.b64encode(canonical({"schema": "wrong"})).decode("ascii"))):
            target = self.folder / ("negative-" + str(i) + ".json")
            self.assertNotEqual(invoke("sign-cert", target, payload).returncode, 0)
            self.assertFalse(target.exists())
        for name, bad_env in (("short-key", dict(env, F139_WORKER_HMAC_KEY="short")),
            ("missing-key", {k: v for k, v in env.items() if k != "F139_WORKER_HMAC_KEY"})):
            target = self.folder / (name + ".json")
            self.assertNotEqual(invoke("sign-cert", target, encoded, bad_env).returncode, 0)
            self.assertFalse(target.exists())

    def test_windows_powershell_51_native_json_transport(self):
        """Native Windows PowerShell passes metadata, never Python source."""
        import os
        import shutil
        import subprocess
        import sys
        if os.name != "nt":
            self.skipTest("PowerShell 5.1 transport is Windows-only")
        shell = shutil.which("powershell.exe")
        self.assertIsNotNone(shell)
        repo = Path(__file__).resolve().parent.parent
        wrapper = self.folder / "native-transport.ps1"
        wrapper.write_text(
            "$ErrorActionPreference='Stop'\\n"
            "$encodedDoc=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($env:FORGE_TEST_JSON))\\n"
            "$result=@(& $env:FORGE_TEST_PYTHON -B -m f139.nci04_fresh_owner_source_forward sign-cert $env:FORGE_TEST_CERT $encodedDoc)\\n"
            "if($LASTEXITCODE -ne 0 -or $result.Count -ne 1 -or $result[0] -cne 'F139_FRESH_FORWARD_CERTIFICATE=CREATE_ONLY_SIGNED'){throw 'NATIVE_SIGN_NOT_VERIFIED'}\\n"
            "$signature=(Get-Content -Raw -LiteralPath $env:FORGE_TEST_CERT | ConvertFrom-Json).owner_signature\\n"
            "$ok=@(& $env:FORGE_TEST_PYTHON -B -m f139.nci04_fresh_owner_source_forward verify-cert $signature $encodedDoc)\\n"
            "if($LASTEXITCODE -ne 0 -or $ok.Count -ne 1 -or $ok[0] -cne 'F139_FORWARD_HMAC_VERIFIED'){throw 'NATIVE_VERIFY_NOT_VERIFIED'}\\n",
            encoding="utf-8")
        unsigned = {k: v for k, v in self.doc.items() if k != "owner_signature"}
        destination = self.folder / "powershell-51-certificate.json"
        env = dict(os.environ, F139_WORKER_HMAC_KEY=self.key,
                   FORGE_TEST_JSON=json.dumps(unsigned, separators=(",", ":")),
                   FORGE_TEST_PYTHON=sys.executable,
                   FORGE_TEST_CERT=str(destination))
        result = subprocess.run([shell, "-NoProfile", "-NonInteractive",
                                 "-ExecutionPolicy", "Bypass", "-File", str(wrapper)],
                                cwd=repo, env=env, capture_output=True,
                                text=True, timeout=40, check=False)
        self.assertEqual(result.returncode, 0, "PowerShell 5.1 module transport failed: "+result.stdout+result.stderr)
        doc = json.loads(destination.read_bytes())
        self.assertEqual(doc["owner_signature"], self.doc["owner_signature"])
        self.assertEqual(destination.read_bytes(), canonical(doc))

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
        self.assertIn("$PrNumber -eq 1863", script)
        self.assertNotIn("$PrNumber -ge 1863", script)
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
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
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

    def test_g156_forward_requires_independent_exact_source_admission(self):
        import os
        from scripts import check_rar_g156_dynamic_base_cache as g156
        branch = "engineering/f139-fresh-original-source-forward-20261122"
        base = "e0467115ea085e2f0ddbee258e4d8937f6a90f10"
        tree = "ebe959a996b7d0e90eced139912141fe0fb17482"
        head = "a" * 40
        scoped = "F139_FORWARD_ORIGINAL_OWNER_SCOPED_SOURCE_CI_ONLY"
        with patch.dict(os.environ, {"GITHUB_HEAD_REF": branch}):
            with patch.object(g156, "admit_original_pr", return_value=scoped):
                self.assertIsNone(g156._release_scope(base, tree, head))
                for bad_base, bad_tree in (("f" * 40, tree),
                                           (base, "f" * 40)):
                    with self.subTest(base=bad_base, tree=bad_tree):
                        with self.assertRaisesRegex(
                                ValueError, "G156_F139_FORWARD_EXACT_OWNER"):
                            g156._release_scope(bad_base, bad_tree, head)
            for unauthorised in ("EXACT_MAIN_ANCESTOR_GENERIC_SOURCE_PR",
                                 "FROZEN_G141_G144_OR_G145_HARNESS_DEVELOPMENT"):
                with self.subTest(admission=unauthorised):
                    with patch.object(g156, "admit_original_pr",
                                      return_value=unauthorised):
                        with self.assertRaisesRegex(
                                ValueError, "G156_F139_FORWARD_EXACT_OWNER"):
                            g156._release_scope(base, tree, head)
        with patch.dict(os.environ, {"GITHUB_HEAD_REF": "unrelated-source"}):
            with patch.object(g156, "admit_original_pr", return_value=scoped):
                with self.assertRaisesRegex(
                        ValueError, "G156_UNAUTHORIZED_GENERIC_PR_SOURCE"):
                    g156._release_scope(base, tree, head)

    def test_g156_forward_cache_miss_never_restores_base_cache(self):
        import os
        from scripts import check_rar_g156_dynamic_base_cache as g156
        branch = "engineering/f139-fresh-original-source-forward-20261122"
        # Distinct fingerprints occur even when changed source is non-Go:
        # the cache inventory includes broader inputs in Go package dirs.
        with patch.dict(os.environ, {"GITHUB_HEAD_REF": branch}):
            self.assertFalse(g156._base_cache_eligible("a", "b", "base", "head"))
            self.assertFalse(g156._base_cache_eligible("a", "a", "base", "head"))
        with patch.dict(os.environ, {"GITHUB_HEAD_REF": "other-branch"}):
            self.assertTrue(g156._base_cache_eligible("a", "b", "base", "head"))
            self.assertFalse(g156._base_cache_eligible("a", "a", "base", "head"))
            self.assertFalse(g156._base_cache_eligible("a", "b", "same", "same"))

    def test_certificate_corrupt_or_symlink_never_falls_back(self):
        path = self.folder / NAME
        path.write_bytes(b'{"not":"canonical"}\n')
        with self.assertRaises(ForwardSourceDenied):
            installed_forward_source(self.db, self.api, self.release, self.key)
        path.unlink()
        path.symlink_to(self.folder / "missing.json")
        with self.assertRaises(ForwardSourceDenied):
            installed_forward_source(self.db, self.api, self.release, self.key)
