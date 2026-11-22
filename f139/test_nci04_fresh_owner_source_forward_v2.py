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
        return {"head_seq": self.seq}


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
             "stage": "VERIFIED", "negative": None},
            {"record": {"ticket": self.doc["last_ticket"]},
             "stage": "VERIFIED", "negative": None},
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
            ("pr_number", PR + 1),
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


if __name__ == "__main__":
    unittest.main()
