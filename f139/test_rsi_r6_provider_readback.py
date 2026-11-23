"""Fail-closed provider readback tests for the EXISTING original GitHub GET.

All fixtures are nonproduction. No network, owner state, GitHub write, runner
dispatch, scientific first-use or claims of real unattended repair.
"""
from __future__ import annotations

import base64
from copy import deepcopy
import json
import unittest

from f139.local_controller import GitHub, REPO
from f139.rsi_r6_known_repair_cycle import (
    Evidence, RepairDenied, WORKFLOW_PATH, digest, task_scope,
)
from f139.rsi_r6_provider_readback import acquire, git_blob

HEAD = "a" * 40
RUN = 39782884958
JOB = 119838389983
PATH = "f139/diagnostic.py"
SOURCE = b'''import sqlite3
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as temp:
    path = str(Path(temp) / "state.sqlite")
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE marker(v INTEGER)")
        connection.execute("INSERT INTO marker VALUES (1)")
'''
LOG = (b"Traceback (most recent call last):\n"
       b"PermissionError: [WinError 32] file is used by another process\n"
       b"C:\\FORGE-F139\\state.sqlite\n")
BASE = "repos/" + REPO + "/"
ROUTES = {
    "run": BASE + "actions/runs/" + str(RUN),
    "job": BASE + "actions/jobs/" + str(JOB),
    "source": BASE + "contents/" + PATH + "?ref=" + HEAD,
    "log": BASE + "actions/jobs/" + str(JOB) + "/logs",
}


def fixture():
    return {
        "run": {
            "id": RUN, "head_sha": HEAD, "run_attempt": 1,
            "status": "completed", "conclusion": "failure",
            "event": "push",
            "repository": {"full_name": REPO},
            "head_repository": {"full_name": REPO},
            "actor": {"login": "spoonman136668-ai"},
        },
        "job": {
            "id": JOB, "run_id": RUN, "status": "completed",
            "conclusion": "failure", "name": "original-owner-cold-audit",
        },
        "source": {
            "path": PATH, "encoding": "base64", "size": len(SOURCE),
            "sha": git_blob(SOURCE),
            "content": base64.b64encode(SOURCE).decode("ascii"),
        },
        "log": LOG,
    }


def provider_with(data):
    touched = []
    by_route = {url: data[name] for name, url in ROUTES.items()}

    def runner(argv):
        if type(argv) is not list or len(argv) != 1:
            raise AssertionError("NO_COMMAND_OR_MULTI_ROUTE_PERMIT")
        route = argv[0]
        touched.append(route)
        if route not in by_route:
            raise AssertionError("UNEXPECTED_PROVIDER_ROUTE_" + route)
        raw = by_route[route]
        if type(raw) is bytes:
            return raw
        return json.dumps(raw, sort_keys=True).encode("utf-8")
    return GitHub(runner=runner), touched


def attempt(provider, *, consumed=frozenset(), path=PATH, head=HEAD,
            run=RUN, job=JOB):
    return acquire(provider=provider, run_id=run, job_id=job, path=path,
                   expected_head=head, consumed_scopes=consumed)


class ProviderReadbackTests(unittest.TestCase):
    def test_four_exact_original_read_routes_and_repaired_bytes(self):
        client, seen = provider_with(fixture())
        record = attempt(client)
        self.assertEqual(seen, list(ROUTES.values()))
        self.assertEqual(record.source_git_blob_sha, git_blob(SOURCE))
        self.assertEqual(record.log_sha256, digest(LOG))
        self.assertEqual(record.original_head_sha, HEAD)
        self.assertEqual(record.proposal.mechanism, "r16-direct")
        self.assertIn(b"contextlib.closing(", record.proposal.source)
        self.assertNotEqual(record.proposal.candidate_sha256, digest(SOURCE))
        self.assertFalse(record.original_owner_admitted)
        self.assertFalse(record.source_regression_pass)
        self.assertFalse(record.production_release)
        self.assertFalse(record.scientific_first_use)
        self.assertFalse(record.proposal.eligible_for_owner)

    def test_original_r13_path_uses_original_provider_contract(self):
        workflow = (
            "name: R13 scoped source-only test\n"
            "run: |\n"
            "          $script = @'\n"
            "          import sqlite3, tempfile\n"
            "          with tempfile.TemporaryDirectory() as folder:\n"
            "              with sqlite3.connect(folder + '/state.sqlite') as db:\n"
            "                  db.execute('CREATE TABLE t(v INTEGER)')\n"
            "          '@\n"
        ).encode("ascii")
        state = fixture()
        state["source"] = {
            "path": WORKFLOW_PATH, "encoding": "base64",
            "size": len(workflow), "sha": git_blob(workflow),
            "content": base64.b64encode(workflow).decode("ascii"),
        }
        selected = dict(ROUTES)
        selected["source"] = (
            BASE + "contents/" + WORKFLOW_PATH + "?ref=" + HEAD)
        dictionary = {selected[key]: state[key] for key in selected}
        observed = []
        def read_only_router(argv):
            self.assertEqual(type(argv), list)
            self.assertEqual(len(argv), 1)
            route = argv[0]
            observed.append(route)
            if route not in dictionary:
                raise AssertionError("UNKNOWN_PROVIDER_ROUTE")
            answer = dictionary[route]
            return answer if type(answer) is bytes else json.dumps(answer).encode()
        result = attempt(GitHub(runner=read_only_router), path=WORKFLOW_PATH)
        self.assertEqual(observed, list(selected.values()))
        self.assertEqual(result.proposal.mechanism, "r16-embedded-workflow")
        self.assertIn(b"contextlib.closing(sqlite3.connect(", result.proposal.source)
        self.assertFalse(result.original_owner_admitted)
        self.assertFalse(result.proposal.deployed)

    def test_original_failed_job_and_commit_are_required(self):
        changes = (
            ("run", "id", RUN + 1), ("run", "head_sha", "b" * 40),
            ("run", "run_attempt", 2), ("run", "run_attempt", True),
            ("run", "event", "workflow_dispatch"),
            ("run", "status", "in_progress"),
            ("run", "conclusion", "success"),
            ("job", "run_id", RUN + 2),
            ("job", "id", JOB + 1),
            ("job", "conclusion", "success"),
            ("job", "status", "queued"),
            ("job", "name", "linux"),
        )
        for section, key, value in changes:
            with self.subTest(section=section, key=key):
                state = fixture()
                state[section][key] = value
                with self.assertRaises(RepairDenied):
                    attempt(provider_with(state)[0])

    def test_owner_repository_proof_and_actor_are_required(self):
        for section, key, value in (
            ("run", "repository", {"full_name": "attacker/other"}),
            ("run", "head_repository", {"full_name": "attacker/other"}),
            ("run", "actor", {"login": "attacker"}),
            ("run", "head_repository", None),
        ):
            with self.subTest(section=section, key=key, value=value):
                state = fixture()
                state[section][key] = value
                with self.assertRaises(RepairDenied):
                    attempt(provider_with(state)[0])

    def test_source_blob_and_provider_path_cannot_drift(self):
        for key, value in (
            ("sha", "0" * 40), ("encoding", "raw"), ("size", len(SOURCE) + 1),
            ("path", "f139/other.py"),
            ("content", base64.b64encode(SOURCE+b"corruption").decode("ascii")),
            ("content", "not!!base64"),
            ("content", "a"*200000),
        ):
            with self.subTest(key=key):
                state = fixture()
                state["source"][key] = value
                with self.assertRaises(RepairDenied):
                    attempt(provider_with(state)[0])

    def test_failed_log_must_reproduce_known_class(self):
        for data in (
            b"FAILED unrelated test", b"PermissionError: [WinError 32]",
            b"state.sqlite", b"", LOG + b"x"*130000,
        ):
            with self.subTest(log_length=len(data)):
                state = fixture()
                state["log"] = data
                with self.assertRaises(RepairDenied):
                    attempt(provider_with(state)[0])

    def test_consumed_scope_and_unscoped_targets_rejected(self):
        e = Evidence(HEAD, RUN, JOB, "WINDOWS_SQLITE_OPEN_HANDLE_CLEANUP",
                     digest(LOG), LOG, PATH, digest(SOURCE))
        consumed = frozenset({task_scope(e)})
        with self.assertRaisesRegex(RepairDenied, "SCOPE_ALREADY_CONSUMED"):
            attempt(provider_with(fixture())[0], consumed=consumed)
        for bad in ("/f139/diagnostic.py", "f139/../../owner.py",
                    ".github/workflows/forge-release.yml", "f139/test.sh"):
            with self.subTest(path=bad), self.assertRaises(RepairDenied):
                attempt(provider_with(fixture())[0], path=bad)

    def test_no_synthetic_witness_can_grant_original_owner_permission(self):
        record = attempt(provider_with(fixture())[0])
        self.assertEqual(record.proposal.schema,
                         "forge.f139.rsi-r6.source-only-known-repair.v1")
        self.assertFalse(record.proposal.qualified)
        self.assertFalse(record.proposal.deployed)
        self.assertFalse(record.proposal.autonomous_rsi_proven)


if __name__ == "__main__":
    unittest.main()
