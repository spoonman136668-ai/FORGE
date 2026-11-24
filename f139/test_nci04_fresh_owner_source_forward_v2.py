"""Synthetic V2 forward proof: never install a Windows task or write a feed issue."""
from __future__ import annotations

from copy import deepcopy
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from f139.nci04_native_contract import canonical, digest
from f139.nci04_fresh_owner_source_forward import (
    NAME as OLD_NAME, installed_forward_source, sign as old_sign,
)
from f139.nci04_fresh_owner_source_forward_v2 import (
    CI_JOBS, DOMAIN, FIELDS, NAME, OWNER_JOB, PREFIX, PR, SCHEMA,
    WORKFLOW, PREVIOUS_OWNER_MAIN, ForwardV2Denied,
    inspect_installed_v2, inspect_v2, sign,
)
from f139 import test_nci04_fresh_owner_source_forward as old_fixture


class LedgerConnection:
    def __init__(self, original, second_hash):
        self.original = original
        self.second_hash = second_hash
        self.terminal_count = 2
        self.second_kind = "FRESH_WORKER_PROVIDER_CUSTODY"
        self.unfinished_tasks = 0

    def execute(self, statement, values=()):
        if statement == "SELECT kind,sha FROM events WHERE seq=9":
            return Result({"kind": "FRESH_WORKER_PROVIDER_CUSTODY",
                           "sha": self.original})
        if statement == "SELECT kind,sha FROM events WHERE seq=?":
            if values != (16,):
                raise AssertionError("unexpected terminal sequence")
            return Result({"kind": self.second_kind, "sha": self.second_hash})
        if statement == "SELECT COUNT(*) FROM events WHERE kind=? AND seq<=?":
            if values != ("FRESH_WORKER_PROVIDER_CUSTODY", 16):
                raise AssertionError("unexpected count")
            return Result((self.terminal_count,))
        if statement == "SELECT COUNT(*) FROM events WHERE kind=?":
            if values != ("FRESH_WORKER_PROVIDER_CUSTODY",):
                raise AssertionError("unexpected count query")
            return Result((self.terminal_count,))
        if statement == ("SELECT COUNT(*) FROM tasks "
                         "WHERE stage IN ('READY','START_RISK','WAIT_PROVIDER','QUARANTINED')"):
            return Result((self.unfinished_tasks,))
        raise AssertionError("unexpected read-only SQL: " + statement)


class Result:
    def __init__(self, item):
        self.item = item
    def fetchone(self):
        return self.item


class FakeLedger:
    def __init__(self, filename, original_hash, last_hash):
        self.filename = filename
        self.conn = LedgerConnection(original_hash, last_hash)
        self.seq = 16
    def meta(self):
        return {"head_seq": self.seq, "head_hash": self.conn.second_hash}


class ForwardV2Tests(unittest.TestCase):
    def setUp(self):
        old = old_fixture.SourceForwardTests(
            "test_signed_cold_certificate_requires_all_three_qualified_os_runs")
        old.setUp()
        self.addCleanup(old.doCleanups)
        self.old = old
        self.folder = old.folder
        self.key = old.key
        self.release = deepcopy(old.release)
        self.previous = deepcopy(old.doc)
        self.previous["pr_number"] = 1865
        self.previous["owner_source_sha"] = PREVIOUS_OWNER_MAIN
        self.previous["owner_signature"] = old_sign(
            {k: v for k, v in self.previous.items()
             if k != "owner_signature"}, self.key)
        self.previous_bytes = canonical(self.previous)
        self.second_hash = "9" * 64
        self.db = FakeLedger(old.db.filename, self.previous["terminal_hash"],
                             self.second_hash)
        self.routes = deepcopy(old.routes)
        base = "repos/spoonman136668-ai/FORGE"
        self.routes[base + "/git/commits/" + PREVIOUS_OWNER_MAIN] = {
            "sha": PREVIOUS_OWNER_MAIN,
            "tree": {"sha": self.previous["owner_source_tree"]},
        }
        archived_pr = deepcopy(self.routes[base + "/pulls/1863"])
        archived_pr["merge_commit_sha"] = PREVIOUS_OWNER_MAIN
        self.routes[base + "/pulls/1865"] = archived_pr
        # Historical owner PREPARE workflow ran on the #1865 merge commit,
        # not on the earlier PR #1863 source from the shared V1 fixture.
        self.routes[base + "/actions/runs/600"]["head_sha"] = PREVIOUS_OWNER_MAIN
        self.routes[base + "/issues/comments/601"]["body"] = (
            old_fixture.PREFIX + PREVIOUS_OWNER_MAIN + " " +
            self.previous["pr_head_sha"] + " 1865 " +
            str(self.previous["regression_run_id"]) + " " +
            str(self.previous["source_run_id"]) + " " +
            str(self.previous["rehearsal_run_id"]))
        self.head = "7" * 40
        self.tree = "8" * 40
        self.pr_head = "6" * 40
        self.routes["repos/spoonman136668-ai/FORGE/branches/main"]["commit"]["sha"] = self.head
        base = "repos/spoonman136668-ai/FORGE"
        self.routes[base + "/git/commits/" + self.head] = {
            "sha": self.head, "tree": {"sha": self.tree},
        }
        self.routes[base + "/pulls/" + str(PR)] = {
            "merged": True, "state": "closed", "merge_commit_sha": self.head,
            "head": {"sha": self.pr_head,
                     "repo": {"full_name": "spoonman136668-ai/FORGE"}},
            "base": {"repo": {"full_name": "spoonman136668-ai/FORGE"}},
            "user": {"login": "spoonman136668-ai"},
        }
        self.doc = {
            "schema": SCHEMA,
            "admission_source_sha": self.previous["admission_source_sha"],
            "worker_release_sha": self.previous["worker_release_sha"],
            "previous_certificate_sha256": digest(self.previous_bytes),
            "previous_owner_source_sha": self.previous["owner_source_sha"],
            "previous_owner_source_tree": self.previous["owner_source_tree"],
            "owner_source_sha": self.head, "owner_source_tree": self.tree,
            "pr_number": PR, "pr_head_sha": self.pr_head,
            "regression_run_id": 802, "source_run_id": 803,
            "rehearsal_run_id": 804, "owner_run_id": 800,
            "owner_comment_id": 801,
            "terminal_seq": 16, "terminal_hash": self.second_hash,
            "terminal_count": 2,
            "last_ticket": "f139-nci04-i1851-" + "a" * 12 + "-" + "b" * 8,
            "task_name": "FORGE-F139-UnifiedController",
            "development_only": True, "worker_release_unchanged": True,
            "scientific_first_use": False, "paid_model_calls": 0,
        }
        self.sign()
        self.routes[base + "/issues/comments/801"] = {
            "id": 801,
            "issue_url": "https://api.github.com/" + base + "/issues/1830",
            "body": self.body(), "user": {"login": "spoonman136668-ai"},
            "author_association": "OWNER",
        }
        self.routes[base + "/actions/runs/800"] = {
            "id": 800, "event": "issue_comment",
            "path": WORKFLOW, "head_sha": self.head,
            "run_attempt": 1, "status": "completed",
            "conclusion": "success", "actor": {"login": "spoonman136668-ai"},
        }
        self.routes[base + "/actions/runs/800/jobs?per_page=100"] = {
            "jobs": [{"name": OWNER_JOB, "runner_name": "FORGE-CODEX-REMOTE",
                      "status": "completed", "conclusion": "success"}],
            "total_count": 1,
        }
        for field, names in CI_JOBS:
            run_id = self.doc[field]
            self.routes[base + "/actions/runs/" + str(run_id)] = {
                "id": run_id, "head_sha": self.pr_head,
                "event": "pull_request", "run_attempt": 1,
                "status": "completed", "conclusion": "success",
            }
            self.routes[base + "/actions/runs/" + str(run_id)
                        + "/jobs?per_page=100"] = {
                "total_count": len(names),
                "jobs": [{"name": name, "status": "completed",
                          "conclusion": "success"} for name in sorted(names)],
            }
        self.api = old_fixture.FakeAPI(self.routes)
        (self.folder / OLD_NAME).write_bytes(self.previous_bytes)
        (self.folder / NAME).write_bytes(canonical(self.doc))
        self.entries = [
            {"record": {"ticket": "f139-nci04-i1849-previous"},
             "stage": "VERIFIED", "negative": None,
             "custody": {"run_id": 11}},
            {"record": {"ticket": self.doc["last_ticket"]},
             "stage": "VERIFIED", "negative": None,
             "custody": {"run_id": 12}},
        ]

    def body(self):
        d = self.doc
        return (PREFIX + d["owner_source_sha"] + " " + d["pr_head_sha"] +
                " " + str(PR) + " " + str(d["regression_run_id"]) +
                " " + str(d["source_run_id"]) + " " +
                str(d["rehearsal_run_id"]) + " " + str(d["terminal_seq"]) +
                " " + d["terminal_hash"])

    def sign(self):
        self.doc["owner_signature"] = sign(
            {k: v for k, v in self.doc.items()
             if k != "owner_signature"}, self.key)

    def validate(self):
        with patch("f139.nci04_fresh_lifecycle.read_lifecycle",
                   return_value=(self.release, self.entries)) as cold:
            result = inspect_installed_v2(self.db, self.api,
                                          self.release, self.key)
            cold.assert_called_once_with(self.db, self.key)
            return result

    def test_v2_canonical_chain_all_providers_and_multi_ticket_head(self):
        self.assertEqual(self.validate(), (self.head, self.tree))
        self.assertGreaterEqual(len(self.api.reads), 18)
        self.assertEqual(self.db.meta()["head_seq"], 16)
        self.assertEqual(self.db.conn.terminal_count, 2)

    def test_v2_signature_and_immutable_archived_v1_are_both_required(self):
        self.doc["owner_source_sha"] = "3" * 40
        (self.folder / NAME).write_bytes(canonical(self.doc))
        with self.assertRaisesRegex(ForwardV2Denied, "OWNER_SIGNATURE_INVALID"):
            self.validate()
        self.doc["owner_source_sha"] = self.head
        self.sign()
        (self.folder / NAME).write_bytes(canonical(self.doc))
        prior = dict(self.previous, owner_source_sha="f" * 40)
        (self.folder / OLD_NAME).write_bytes(canonical(prior))
        with self.assertRaisesRegex(
                ForwardV2Denied, "PREVIOUS_CERTIFICATE_CHAIN_DRIFT"):
            self.validate()

    def test_signed_but_unqualified_previous_owner_certificate_is_rejected(self):
        bad = dict(self.previous, worker_release_tree="e" * 40)
        bad["owner_signature"] = old_sign(
            {k: v for k, v in bad.items()
             if k != "owner_signature"}, self.key)
        raw = canonical(bad)
        self.doc["previous_certificate_sha256"] = digest(raw)
        self.sign()
        (self.folder / OLD_NAME).write_bytes(raw)
        (self.folder / NAME).write_bytes(canonical(self.doc))
        with self.assertRaisesRegex(
                ForwardV2Denied, "PREVIOUS_CUSTODY_INVALID"):
            self.validate()

    def test_signed_multi_ticket_terminal_prefix_must_match_full_cold_audit(self):
        self.db.conn.second_hash = "1" * 64
        with self.assertRaisesRegex(
                ForwardV2Denied, "MULTITICKET_COLD_TERMINAL_DRIFT"):
            self.validate()
        self.db.conn.second_hash = self.second_hash
        self.db.conn.terminal_count = 1
        with self.assertRaisesRegex(
                ForwardV2Denied, "MULTITICKET_COLD_TERMINAL_DRIFT"):
            self.validate()
        self.db.conn.terminal_count = 2
        self.entries[1]["negative"] = {"run_id": 44}
        with self.assertRaisesRegex(
                ForwardV2Denied, "MULTITICKET_COLD_TERMINAL_DRIFT"):
            self.validate()
        self.entries[1]["negative"] = None
        with patch("f139.nci04_fresh_lifecycle.read_lifecycle",
                   side_effect=ValueError("BAD_ORIGINAL_LEDGER_CUSTODY")):
            with self.assertRaisesRegex(ValueError, "BAD_ORIGINAL_LEDGER_CUSTODY"):
                inspect_installed_v2(self.db, self.api, self.release, self.key)

    def test_future_ledger_extensions_do_not_replay_original_cutover(self):
        self.db.seq = 23
        self.entries.append({"record": {"ticket": "future-distinct-ticket"},
                             "stage": "READY", "negative": None})
        self.assertEqual(self.validate(), (self.head, self.tree))

    def test_wrong_merged_main_or_ci_or_owner_receipt_denied(self):
        base = "repos/spoonman136668-ai/FORGE"
        paths = [
            (base + "/branches/main", "protected", False),
            (base + "/pulls/" + str(PR), "merged", False),
            (base + "/actions/runs/802", "conclusion", "failure"),
            (base + "/actions/runs/800", "status", "in_progress"),
            (base + "/issues/comments/801", "author_association", "NONE"),
        ]
        for path, field, value in paths:
            original = deepcopy(self.routes[path])
            try:
                with self.subTest(path=path):
                    self.routes[path][field] = value
                    with self.assertRaises(ForwardV2Denied):
                        self.validate()
            finally:
                self.routes[path] = original

    def test_unauthorized_pr_and_unsafe_parameter_flags_denied_before_provider(self):
        for field, value in (
            ("pr_number", PR - 1),
            ("terminal_seq", 9),
            ("terminal_count", 1),
            ("development_only", False),
            ("worker_release_unchanged", False),
            ("scientific_first_use", True),
            ("paid_model_calls", 1),
            ("owner_run_id", 0),
        ):
            with self.subTest(field=field):
                bad = dict(self.doc, **{field: value})
                bad["owner_signature"] = sign(
                    {k: v for k, v in bad.items()
                     if k != "owner_signature"}, self.key)
                (self.folder / NAME).write_bytes(canonical(bad))
                self.api.reads.clear()
                with self.assertRaisesRegex(
                        ForwardV2Denied, "EXACT_SIGNED_SCOPE_INVALID"):
                    self.validate()
                self.assertEqual(self.api.reads, [])
        (self.folder / NAME).write_bytes(canonical(self.doc))

    def test_installed_owner_no_v2_keeps_legacy_source_pin(self):
        (self.folder / NAME).unlink()
        # Historical V1 has moved main and must now fail closed rather than
        # silently accepting a previously valid signed source.
        with self.assertRaises(old_fixture.ForwardSourceDenied):
            installed_forward_source(self.db, self.api, self.release, self.key)
        (self.folder / NAME).write_bytes(canonical(self.doc))
        with patch("f139.nci04_fresh_lifecycle.read_lifecycle",
                   return_value=(self.release, self.entries)):
            self.assertEqual(installed_forward_source(
                self.db, self.api, self.release, self.key),
                (self.head, self.tree))


    def test_preflight_requires_cold_verified_multi_ticket_and_no_second_cert(self):
        from f139.nci04_fresh_owner_source_forward_v2 import preflight_v2_unsigned
        (self.folder / NAME).unlink()
        with patch("f139.local_controller.SingleOwner.held", return_value=True), patch(
            "f139.nci04_fresh_lifecycle.read_lifecycle",
            return_value=(self.release, self.entries)
        ) as cold:
            raw = preflight_v2_unsigned(
                self.db, self.api, self.release, self.key,
                candidate=self.head, head=self.pr_head,
                regression_run_id=802, source_run_id=803,
                rehearsal_run_id=804)
            self.assertEqual(raw["previous_owner_source_sha"], PREVIOUS_OWNER_MAIN)
            self.assertEqual(raw["terminal_seq"], 16)
            self.assertEqual(raw["terminal_count"], 2)
            self.assertEqual(raw["terminal_hash"], self.second_hash)
            self.assertEqual(raw["last_ticket"], self.doc["last_ticket"])
            self.assertEqual(raw["worker_release_sha"],
                             self.release["worker_release_sha"])
            cold.assert_called_once_with(self.db, self.key)
            self.assertNotIn("owner_run_id", raw)
            self.assertNotIn("owner_signature", raw)
            self.entries[1]["stage"] = "WAIT_PROVIDER"
            with self.assertRaisesRegex(
                    ForwardV2Denied, "PREFLIGHT_TERMINAL_OR_REMOTE_EFFECT_UNCERTAIN"):
                preflight_v2_unsigned(
                    self.db, self.api, self.release, self.key,
                    candidate=self.head, head=self.pr_head,
                    regression_run_id=802, source_run_id=803,
                    rehearsal_run_id=804)
            self.entries[1]["stage"] = "VERIFIED"
            self.db.conn.unfinished_tasks = 1
            with self.assertRaisesRegex(
                    ForwardV2Denied, "PREFLIGHT_UNFINISHED_TASK_HOLD"):
                preflight_v2_unsigned(
                    self.db, self.api, self.release, self.key,
                    candidate=self.head, head=self.pr_head,
                    regression_run_id=802, source_run_id=803,
                    rehearsal_run_id=804)
            self.db.conn.unfinished_tasks = 0
        with self.assertRaisesRegex(
                ForwardV2Denied, "PREFLIGHT_ORIGINAL_KERNEL_LOCK_REQUIRED"):
            preflight_v2_unsigned(
                self.db, self.api, self.release, self.key,
                candidate=self.head, head=self.pr_head,
                regression_run_id=802, source_run_id=803,
                rehearsal_run_id=804)

    def test_transport_create_only_synthetic_signature_and_bad_metadata(self):
        import base64
        import os
        import subprocess
        import sys

        repo = Path(__file__).resolve().parent.parent
        unsigned = {k: v for k, v in self.doc.items()
                    if k != "owner_signature"}
        encoded = base64.b64encode(canonical(unsigned)).decode("ascii")
        env = dict(os.environ, F139_WORKER_HMAC_KEY=self.key)
        path = self.folder / "transport" / NAME
        path.parent.mkdir()
        def sign_cert(value, target=path, env_override=env):
            return subprocess.run(
                [sys.executable, "-B", "-m",
                 "f139.nci04_fresh_owner_source_forward_v2",
                 "sign-cert", str(target), value],
                cwd=repo, env=env_override, capture_output=True,
                text=True, timeout=25, check=False)
        run = sign_cert(encoded)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout.strip(),
                         "F139_FRESH_FORWARD_V2_SIGNED_CREATE_ONLY")
        actual = path.read_bytes()
        self.assertEqual(actual, canonical(self.doc))
        self.assertNotEqual(sign_cert(encoded).returncode, 0)
        self.assertEqual(path.read_bytes(), actual)
        for value in ("%%%", "",
                      base64.b64encode(b"not json").decode("ascii"),
                      base64.b64encode(canonical({"schema": "wrong"})).decode("ascii")):
            dest = self.folder / "transport" / ("bad-" + str(len(value)) + "-" + NAME)
            self.assertNotEqual(sign_cert(value, dest).returncode, 0)
            self.assertFalse(dest.exists())
        missing = {k: v for k, v in env.items()
                   if k != "F139_WORKER_HMAC_KEY"}
        self.assertNotEqual(sign_cert(encoded,
                            self.folder / "transport" / ("missing-" + NAME),
                            missing).returncode, 0)

    def test_two_phase_owner_script_is_nonreplaying_and_owner_only(self):
        import os
        import shutil
        import subprocess

        root = Path(__file__).resolve().parent.parent
        script_path = root / "f139" / "nci04_fresh_owner_source_forward_v2.ps1"
        workflow_path = root / ".github" / "workflows" / "f139-fresh-owner-source-forward-v2.yml"
        script = script_path.read_text(encoding="utf-8")
        workflow = workflow_path.read_text(encoding="utf-8")
        self.assertEqual(workflow.count("  fresh-original-owner-source-forward-v2-prepare:"), 1)
        self.assertEqual(workflow.count("  fresh-original-owner-source-forward-v2-start:"), 1)
        self.assertIn("github.actor == 'spoonman136668-ai'", workflow)
        self.assertIn("github.event.issue.number == 1830", workflow)
        self.assertIn("github.ref == 'refs/heads/main'", workflow)
        self.assertIn("runs-on: [self-hosted, Windows, forge-codex-isolated]", workflow)
        self.assertEqual(workflow.count(
            "group: forge-f139-fresh-existing-disabled-task-rebind"), 2)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("F139-FRESH-OWNER-SOURCE-FORWARD-V2-START", workflow)
        self.assertIn("F139-FRESH-OWNER-SOURCE-FORWARD-V2 ", workflow)
        self.assertIn("$previousMain='f24251e0d95938e593a54c1577a34efadc8080d8'", script)
        self.assertIn("$prScope=1869", script)
        self.assertIn("Disable-ScheduledTask", script)
        self.assertIn("Stop-ScheduledTask", script)
        self.assertIn("Set-ScheduledTask", script)
        self.assertIn("Enable-ScheduledTask", script)
        self.assertIn("Start-ScheduledTask", script)
        self.assertIn("F139_V2_ORIGINAL_SAME_OWNER_PREPARED_DISABLED_ONLY=PASS", workflow)
        self.assertIn("F139_V2_ORIGINAL_SAME_OWNER_STARTED=PASS", workflow)
        self.assertIn("F139_FRESH_OWNER_SOURCE_FORWARD_V2_PREPARED_DISABLED=PASS", script)
        self.assertIn("F139_FRESH_ORIGINAL_OWNER_SOURCE_FORWARD_V2_RUNNING=PASS", script)
        self.assertIn("F139_SCIENTIFIC_FIRST_USE=FALSE", script)
        for token in ("Register-ScheduledTask", "Unregister-ScheduledTask",
                      "New-ScheduledTaskTrigger", "Invoke-Expression",
                      "powershell -EncodedCommand", "F139_FEED_PUBLISH"):
            self.assertNotIn(token, script)
        prepare, start = script.split("  } else {\n    Need ($PrepRun", 1)
        self.assertNotIn("Enable-ScheduledTask -TaskName $taskName", prepare)
        self.assertNotIn("Start-ScheduledTask -TaskName $taskName", prepare)
        self.assertIn("Enable-ScheduledTask -TaskName $taskName", start)
        self.assertIn("Start-ScheduledTask -TaskName $taskName", start)
        # The original V1 owner may be stopped by its old protected-main
        # authentication after PR merge. Only the original task in either
        # healthy running state OR already-cold disabled state is admissible.
        # The disabled path must never replay STOP or START, and both must
        # require the exact archived checkout and query-only cold evidence.
        self.assertIn("$originalControllers=@(Owners)", prepare)
        self.assertIn("$runningOriginal=($task.Settings.Enabled -eq $true", prepare)
        self.assertIn("$idleOriginal=($task.Settings.Enabled -eq $true", prepare)
        self.assertIn("$heldOriginal=($task.Settings.Enabled -eq $false", prepare)
        # Windows Task Scheduler reports distinct Running, Ready, Disabled,
        # Queued and Unknown states. Only the first three exact states are
        # admissible; a queued/unknown task must never be source-forwarded.
        self.assertIn("[string]$task.State -ceq 'Running'", prepare)
        self.assertIn("[string]$task.State -ceq 'Ready'", prepare)
        self.assertIn("[string]$task.State -ceq 'Disabled'", prepare)
        self.assertIn("[string]$stopped.State -ceq 'Disabled'", prepare)
        self.assertNotIn("[string]$task.State -cne 'Running'", prepare)
        self.assertNotIn("[string]$stopped.State -cne 'Running'", prepare)
        self.assertIn(
            "[string]$task.State -ceq 'Disabled' -and", start)
        self.assertIn("$originalControllers.Count -eq 0)", prepare)
        self.assertIn("$originalControllers.Count -eq 1)", prepare)
        self.assertIn(
            "Need ($runningOriginal -or $idleOriginal -or $heldOriginal) "
            "'ONLY_RUNNING_IDLE_OR_COLD_DISABLED_ORIGINAL_OWNER_REQUIRED'", prepare)
        self.assertIn("if ($runningOriginal -or $idleOriginal) {\n"
                      "      Disable-ScheduledTask -TaskName $taskName", prepare)
        self.assertIn("if ($runningOriginal) {\n"
                      "        Stop-ScheduledTask -TaskName $taskName", prepare)
        self.assertEqual(
            prepare.count("Stop-ScheduledTask -TaskName $taskName"), 1)
        self.assertLess(prepare.index("ExactGit $source $previousMain"),
                        prepare.index("if ($runningOriginal)"))
        self.assertLess(prepare.index("if ($runningOriginal)"),
                        prepare.index(" preflight $db $encoded)"))
        self.assertLess(prepare.index(" preflight $db $encoded)"),
                        prepare.index(" sign-cert $cert $encodedDoc)"))
        self.assertIn(
            "[string]$stopped.Actions[0].Arguments -ceq "
            "[string]$task.Actions[0].Arguments", prepare)
        if os.name == "nt":
            power = shutil.which("powershell.exe")
            self.assertIsNotNone(power)
            verifier = self.folder / "parse-v2.ps1"
            verifier.write_text(
                "param([string]$Source)\n"
                "$tokens=$null;$errors=$null\n"
                "[System.Management.Automation.Language.Parser]::ParseFile("
                "$Source,[ref]$tokens,[ref]$errors)|Out-Null\n"
                "if($errors.Count -ne 0){$errors|Out-String|Write-Error;exit 1}\n",
                encoding="utf-8")
            check = subprocess.run(
                [power, "-NoProfile", "-NonInteractive",
                 "-ExecutionPolicy", "Bypass", "-File", str(verifier),
                 "-Source", str(script_path)], capture_output=True,
                text=True, timeout=30, check=False)
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)


    def test_exact_scoped_v2_workflow_ci_admission_and_negative_controls(self):
        from scripts.check_rar_g145_pr_scope import (
            F139_V2_BASE, F139_V2_BASE_G145, F139_V2_BRANCH,
            F139_V2_PATHS, F139_V2_PR, F139_V2_RESULT,
            F139_V2_WORKFLOW, F139_V2_WORKFLOW_BLOB,
            admit_f139_v2_source, generic_paths_safe,
        )

        head = "3" * 40
        self.assertFalse(generic_paths_safe([F139_V2_WORKFLOW]))
        self.assertEqual(F139_V2_PR, 1869)
        self.assertEqual(F139_V2_BASE, PREVIOUS_OWNER_MAIN)
        self.assertEqual(len(F139_V2_PATHS), 18)
        request = {
            "number": F139_V2_PR, "author_association": "OWNER",
            "user": {"login": "spoonman136668-ai"},
            "head": {"ref": F139_V2_BRANCH, "sha": head,
                     "repo": {"full_name": "spoonman136668-ai/FORGE"}},
            "base": {"ref": "main", "sha": F139_V2_BASE,
                     "repo": {"full_name": "spoonman136668-ai/FORGE"}},
        }
        expected = {
            ("merge-base", F139_V2_BASE, head): F139_V2_BASE,
            ("rev-parse", F139_V2_BASE +
             ":scripts/check_rar_g145_pr_scope.py"): F139_V2_BASE_G145,
            ("rev-parse", head + ":" + F139_V2_WORKFLOW):
                F139_V2_WORKFLOW_BLOB,
            ("diff", "--no-renames", "--name-only",
             F139_V2_BASE, head): "\n".join(sorted(F139_V2_PATHS)),
        }

        def trusted(*args):
            if args not in expected:
                raise AssertionError("UNEXPECTED_GIT_CUSTODY_PATH")
            return expected[args]

        self.assertEqual(admit_f139_v2_source(
            head, F139_V2_BASE, request, trusted), F139_V2_RESULT)
        for field, change in (
            ("number", 1863),
            ("author_association", "CONTRIBUTOR"),
            ("user", {"login": "forged"}),
            ("head", {**request["head"], "ref": "main"}),
            ("base", {**request["base"], "sha": "0" * 40}),
        ):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    admit_f139_v2_source(
                        head, F139_V2_BASE, {**request, field: change},
                        trusted)
        for path, changed in (
            (("merge-base", F139_V2_BASE, head), "1" * 40),
            (("rev-parse", head + ":" + F139_V2_WORKFLOW), "2" * 40),
            (("diff", "--no-renames", "--name-only", F139_V2_BASE, head),
             "\n".join(sorted(F139_V2_PATHS - {F139_V2_WORKFLOW}))),
            (("diff", "--no-renames", "--name-only", F139_V2_BASE, head),
             "\n".join(sorted(F139_V2_PATHS | {".github/workflows/foreign.yml"}))),
        ):
            with self.subTest(path=path, changed=changed):
                with self.assertRaisesRegex(
                        ValueError, "EXACT_WORKFLOW_OR_SOURCE_DRIFT"):
                    admit_f139_v2_source(
                        head, F139_V2_BASE, request,
                        lambda *q: changed if q == path else trusted(*q))

    def test_existing_go_qualifiers_do_not_generalize_v2_workflow_exception(self):
        import os
        from scripts import check_rar_g156_dynamic_base_cache as g156
        from scripts import check_rar_g148_go_cache as g148
        from unittest.mock import patch
        branch = "engineering/f139-history-conditioned-dev-selector-20261122"
        accepted = "EXACT_PR1869_F139_V2_SOURCE_FORWARD_CI_ONLY"
        with patch.dict(os.environ, {"GITHUB_HEAD_REF": branch}):
            with patch.object(g156, "admit_original_pr",
                              return_value=accepted):
                self.assertIsNone(
                    g156._release_scope(PREVIOUS_OWNER_MAIN, "tree", "head"))
                with self.assertRaisesRegex(
                        ValueError, "G156_F139_V2_PROTECTED_SOURCE_REQUIRED"):
                    g156._release_scope("0" * 40, "tree", "head")
            with patch.object(g156, "admit_original_pr",
                              return_value="EXACT_MAIN_ANCESTOR_GENERIC_SOURCE_PR"):
                with self.assertRaisesRegex(
                        ValueError, "G156_F139_V2_PROTECTED_SOURCE_REQUIRED"):
                    g156._release_scope(PREVIOUS_OWNER_MAIN, "tree", "head")
        synthetic_host = {
            "GITHUB_HEAD_REF": branch, "GITHUB_ACTIONS": "true",
            "GITHUB_REPOSITORY": "spoonman136668-ai/FORGE",
            "RUNNER_OS": "Windows", "G148_HEAD": "3" * 40,
            "RUNNER_TEMP": str(self.folder),
            "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_BASE_REF": "main",
        }
        # This is a synthetic branch decision, never a claim about the real
        # Windows runner. The actual host guard stays unchanged in production.
        with patch.dict(os.environ, synthetic_host), patch.object(
            g148.sys, "platform", "win32"
        ), patch.object(g148, "stable"), patch.object(
            g148, "negative_controls"
        ):
            with patch.object(g148, "admit_original_pr",
                              return_value=accepted):
                self.assertEqual(g148.event_mode("3" * 40), "pr")
            with patch.object(g148, "admit_original_pr",
                              return_value="EXACT_MAIN_ANCESTOR_GENERIC_SOURCE_PR"):
                with self.assertRaisesRegex(
                        ValueError, "G148_F139_V2_SCOPED_ORIGINAL_OWNER_SOURCE_REQUIRED"):
                    g148.event_mode("3" * 40)


if __name__ == "__main__":
    unittest.main()
