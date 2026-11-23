"""No-network adversarial tests for bounded R7 authentic failure intake."""
from __future__ import annotations

import base64
from hashlib import sha256
import json
import unittest

from f139.local_controller import GitHub, REPO
from f139.rsi_r6_known_repair_cycle import (
    Evidence, WORKFLOW_PATH, task_scope,
)
from f139.rsi_r6_provider_readback import git_blob
from f139.rsi_r7_fresh_failure import DiscoveryDenied, scan

RUN = 42530000000
JOB = 128880000000
HEAD = "b" * 40
BEFORE = "2026-11-08T21:54:00Z"
PATH = "f139/diagnostic.py"
SOURCE = (b"import sqlite3\nimport tempfile\n"
          b"with tempfile.TemporaryDirectory() as folder:\n"
          b"    with sqlite3.connect(folder + '/state.sqlite') as db:\n"
          b"        db.execute('CREATE TABLE t(v INTEGER)')\n")
LOG = (b"PermissionError: [WinError 32] another process owns "
       b"C:\\FORGE\\state.sqlite\n")
BASE = "repos/" + REPO + "/"
LIST1 = BASE + "actions/runs?branch=main&event=push&status=failure&per_page=30&page=1"
LIST2 = BASE + "actions/runs?branch=main&event=push&status=failure&per_page=30&page=2"
INDEX = BASE + "actions/runs/" + str(RUN) + "/jobs?per_page=100"
RUN_URL = BASE + "actions/runs/" + str(RUN)
JOB_URL = BASE + "actions/jobs/" + str(JOB)
SOURCE_URL = BASE + "contents/" + PATH + "?ref=" + HEAD
LOG_URL = BASE + "actions/jobs/" + str(JOB) + "/logs"


def fixture():
    run = {
        "id": RUN, "created_at": "2026-11-08T22:30:00Z",
        "head_sha": HEAD, "event": "push", "head_branch": "main",
        "run_attempt": 1, "status": "completed", "conclusion": "failure",
        "repository": {"full_name": REPO},
        "head_repository": {"full_name": REPO},
        "actor": {"login": "spoonman136668-ai"},
    }
    job = {"id": JOB, "run_id": RUN, "name": "windows_native",
           "status": "completed", "conclusion": "failure"}
    return {
        LIST1: {"workflow_runs": [run]},
        LIST2: {"workflow_runs": []},
        INDEX: {"total_count": 1, "jobs": [job]},
        RUN_URL: run,
        JOB_URL: job,
        SOURCE_URL: {
            "path": PATH, "encoding": "base64", "size": len(SOURCE),
            "sha": git_blob(SOURCE),
            "content": base64.b64encode(SOURCE).decode("ascii"),
        },
        LOG_URL: LOG,
    }


def fake(routes):
    seen = []
    def runner(argv):
        if type(argv) is not list or len(argv) != 1:
            raise AssertionError("NON_GET_OR_EXTRA_CALL")
        url = argv[0]
        seen.append(url)
        if url not in routes:
            raise AssertionError("UNEXPECTED_PROVIDER_ROUTE_" + url)
        item = routes[url]
        return item if type(item) is bytes else json.dumps(item).encode()
    return GitHub(runner=runner), seen


def inspect(routes, *, consumed=frozenset(), after=RUN-1,
            target=PATH, cutoff=BEFORE):
    provider, seen = fake(routes)
    report = scan(provider=provider, after_run_id=after,
                  not_before_utc=cutoff, target_path=target,
                  consumed_scopes=consumed)
    return report, seen


class ReadonlyDiscoveryTests(unittest.TestCase):
    def test_authentic_bounded_proposal_no_owner_permissions(self):
        row, seen = inspect(fixture())
        self.assertEqual(row.examined_run_ids, (RUN,))
        self.assertEqual(row.rejection_codes, ())
        self.assertEqual(len(row.proposals), 1)
        self.assertIn(b"contextlib.closing(", row.proposals[0].proposal.source)
        self.assertEqual(seen, [LIST1, INDEX, RUN_URL, JOB_URL,
                                SOURCE_URL, LOG_URL, LIST2])
        self.assertFalse(row.complete_repository_history)
        self.assertFalse(row.original_owner_admitted)
        self.assertFalse(row.authorized_to_dispatch)
        self.assertFalse(row.deployed)
        self.assertFalse(row.autonomous_rsi_proven)

    def test_cutoffs_never_replay_old_or_equal_runs(self):
        for mode in ("run", "time"):
            with self.subTest(mode=mode):
                data = fixture()
                if mode == "time":
                    data[LIST1]["workflow_runs"][0]["created_at"] = BEFORE
                    row, seen = inspect(data)
                else:
                    row, seen = inspect(data, after=RUN)
                self.assertEqual(row.proposals, ())
                self.assertEqual(row.examined_run_ids, ())
                self.assertEqual(seen, [LIST1, LIST2])

    def test_unrelated_failure_retained_as_negative(self):
        data = fixture()
        data[LOG_URL] = b"python build failed unrelated test\n"
        report, _ = inspect(data)
        self.assertEqual(report.proposals, ())
        self.assertEqual(len(report.rejection_codes), 1)
        self.assertIn("FAILURE_SIGNATURE_MISMATCH",
                      report.rejection_codes[0][1])

    def test_consumed_scope_denied_even_for_matching_run(self):
        scope = task_scope(Evidence(
            HEAD, RUN, JOB, "WINDOWS_SQLITE_OPEN_HANDLE_CLEANUP",
            sha256(LOG).hexdigest(), LOG, PATH, sha256(SOURCE).hexdigest()))
        report, _ = inspect(fixture(), consumed=frozenset({scope}))
        self.assertEqual(report.proposals, ())
        self.assertIn("SCOPE_ALREADY_CONSUMED", report.rejection_codes[0][1])

    def test_disallowed_target_and_untrusted_cutoff(self):
        provider, calls = fake(fixture())
        for target in ("../owner.py", ".github/workflows/qualify.yml"):
            with self.assertRaises(DiscoveryDenied):
                scan(provider=provider, after_run_id=RUN-1,
                     not_before_utc=BEFORE, target_path=target,
                     consumed_scopes=frozenset())
        with self.assertRaises(DiscoveryDenied):
            scan(provider=provider, after_run_id=RUN-1,
                 not_before_utc="last week", target_path=PATH,
                 consumed_scopes=frozenset())
        self.assertEqual(calls, [])

    def test_duplicate_runs_fail_closed(self):
        data = fixture()
        data[LIST2]["workflow_runs"] = data[LIST1]["workflow_runs"][:]
        with self.assertRaisesRegex(DiscoveryDenied, "DUPLICATE"):
            inspect(data)

    def test_failed_provider_job_cannot_be_ambiguous(self):
        data = fixture()
        other = dict(data[INDEX]["jobs"][0])
        other["id"] = JOB + 1
        data[INDEX] = {"total_count": 2, "jobs": [data[INDEX]["jobs"][0], other]}
        with self.assertRaisesRegex(DiscoveryDenied, "AMBIGUOUS"):
            inspect(data)

    def test_run_and_job_provenance_drift_fail_closed(self):
        for location, key, value in (
            (LIST1, "run_attempt", 2),
            (LIST1, "actor", {"login": "external"}),
            (LIST1, "head_repository", {"full_name": "external/FORGE"}),
            (INDEX, "run_id", RUN + 1),
        ):
            with self.subTest(location=location, key=key):
                data = fixture()
                if location == LIST1:
                    data[LIST1]["workflow_runs"][0][key] = value
                else:
                    data[INDEX]["jobs"][0][key] = value
                with self.assertRaises(DiscoveryDenied):
                    inspect(data)

    def test_incomplete_jobs_or_excess_candidates_not_silently_accepted(self):
        data = fixture()
        data[INDEX]["total_count"] = 101
        with self.assertRaisesRegex(DiscoveryDenied, "INCOMPLETE"):
            inspect(data)
        data = fixture()
        rows = data[LIST1]["workflow_runs"]
        for n in range(8):
            fresh = dict(rows[0])
            fresh["id"] = RUN + n + 1
            rows.append(fresh)
            data[BASE + "actions/runs/" + str(fresh["id"]) +
                 "/jobs?per_page=100"] = {"total_count": 0, "jobs": []}
        with self.assertRaisesRegex(DiscoveryDenied, "BOUND_REACHED"):
            inspect(data)

    def test_empty_filtered_catalog_has_no_fabricated_proposals(self):
        data = fixture()
        data[LIST1]["workflow_runs"] = []
        report, seen = inspect(data)
        self.assertEqual(report.proposals, ())
        self.assertEqual(report.examined_run_ids, ())
        self.assertEqual(seen, [LIST1, LIST2])

    def test_filtered_catalog_must_enforce_main_push_failed_origin(self):
        # Reject off-scope entries even when their run ID predates the cutoff;
        # otherwise an ignored provider filter can silently hide real failures.
        for field, wrong in (
            ("head_branch", "foreign"),
            ("event", "pull_request"),
            ("status", "in_progress"),
            ("conclusion", "success"),
        ):
            for old in (False, True):
                with self.subTest(field=field, old=old):
                    data = fixture()
                    run = data[LIST1]["workflow_runs"][0]
                    run[field] = wrong
                    if old:
                        run["id"] = RUN - 10
                    with self.assertRaisesRegex(
                        DiscoveryDenied, "FILTERED_RUN_SCOPE_DRIFT"
                    ):
                        inspect(data)


if __name__ == "__main__":
    unittest.main()
