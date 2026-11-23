"""V19 release readiness: all injected GitHub/owner data, no real writes."""
from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner
from f139.nci04_autonomy_feed import POLICY_SCHEMA, TITLE_PREFIX
from f139.nci04_v19_original_release_readonly_preflight import (
    FORGE, PR, REQUIRED_RUNS, SCHEMA, SOURCE, TARGET,
    V19ReleasePreflightDenied, v19_original_release_readonly_preflight,
)


class V19OriginalReadinessTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="v19-release-nowrite-")
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "state.sqlite"
        self.db = object.__new__(Database)
        self.db.filename = self.path
        self.calls = []
        self._state = {
            "source_sha": SOURCE, "head_seq": 292,
            "head_sha256": "a" * 64,
            "v18_transition_sha256": "b" * 64,
        }
        self.policy_enabled = True
        self.main_sha = SOURCE
        self.pr_sha = TARGET
        self.pr_draft = False
        self.pr_base_sha = SOURCE
        self.bad_run = None

    def remote(self, route):
        self.calls.append(route)
        if route == f"repos/{FORGE}/issues/807":
            return {
                "number": 807, "state": "open",
                "user": {"login": "spoonman136668-ai"},
                "author_association": "OWNER",
                "body": json.dumps({
                    "schema": POLICY_SCHEMA, "enabled": self.policy_enabled,
                    "source_sha": SOURCE, "title_prefix": TITLE_PREFIX,
                    "lanes": ["Wingless", "Yggdrasil"],
                    "max_issue_creations_per_cycle": 2,
                    "require_owner_authored_pr": True,
                    "require_single_head_commit_delta": True,
                    "require_single_allowed_source_file": True,
                    "scientific_first_use": False, "paid_model_calls": 0,
                    "accepted_ref_mutations": 0, "new_controller": False,
                    "new_scheduler": False, "new_queue": False,
                }),
            }
        if route == f"repos/{FORGE}/branches/main":
            return {"protected": True, "commit": {"sha": self.main_sha}}
        if route == f"repos/{FORGE}/pulls/{PR}":
            return {
                "number": PR, "state": "open", "draft": self.pr_draft,
                "merged_at": None, "user": {"login": "spoonman136668-ai"},
                "head": {"sha": self.pr_sha, "ref":
                         "release/f139-v19-mainline-source-integration-20261028"},
                "base": {"sha": self.pr_base_sha, "ref": "main"},
            }
        for run_id in REQUIRED_RUNS:
            if route == f"repos/{FORGE}/actions/runs/{run_id}":
                return {"id": run_id, "head_sha": TARGET,
                        "status": "completed",
                        "conclusion": ("failure" if self.bad_run == run_id
                                       else "success")}
        raise AssertionError("UNEXPECTED_OR_MUTATING_ROUTE " + route)

    def read(self, *, witness=None):
        if witness is None:
            witness = lambda: True
        return v19_original_release_readonly_preflight(
            self.db, original_get=self.remote, owner_witness=witness)

    def test_exact_release_state_still_never_authorizes_cutover(self):
        import f139.nci04_v19_original_release_readonly_preflight as module
        with SingleOwner(self.path.with_suffix(".lock")), patch.object(
                module, "_original_state", return_value=self._state):
            proof = self.read()
        self.assertEqual(proof["schema"], SCHEMA)
        self.assertEqual(proof["from_source_sha"], SOURCE)
        self.assertEqual(proof["candidate_source_sha"], TARGET)
        self.assertEqual(proof["original_head_seq"], 292)
        self.assertEqual(proof["qualified_run_ids"], list(REQUIRED_RUNS))
        self.assertEqual(len(self.calls), 2 + 1 + 3 + 2)
        self.assertTrue(proof["read_only"])
        for key in (
            "runtime_cutover_authorized", "source_transition_to_v19_implemented",
            "installed_checkout_verified", "scheduled_task_quiescence_verified",
            "immutable_original_backup_verified", "rollback_rehearsal_verified",
            "scientific_first_use", "new_controller", "new_scheduler", "new_queue",
        ):
            self.assertIs(proof[key], False, key)
        for key in ("original_sqlite_writes", "github_writes",
                    "provider_requests", "paid_api_calls",
                    "accepted_ref_mutations"):
            self.assertEqual(proof[key], 0, key)
        source = inspect.getsource(module)
        for token in ("db.event(", "transition_source(", "db.transaction(",
                      'get("POST"', 'get("PUT"', "requests.post("):
            self.assertNotIn(token, source)

    def test_no_mutex_or_witness_denied_before_remote_reads(self):
        import f139.nci04_v19_original_release_readonly_preflight as module
        with patch.object(module, "_original_state",
                          side_effect=V19ReleasePreflightDenied(
                              "F139_V19_RELEASE_NOWRITE_EXISTING_ORIGINAL_MUTEX_REQUIRED")):
            with self.assertRaisesRegex(
                    V19ReleasePreflightDenied, "MUTEX_REQUIRED"):
                self.read()
        with self.assertRaisesRegex(
                V19ReleasePreflightDenied, "ORIGINAL_OWNER_OR_AUTHENTICATED_GET"):
            self.read(witness=lambda: False)
        self.assertEqual(self.calls, [])

    def test_owner_policy_main_pr_ci_negative_cases_fail_closed(self):
        import f139.nci04_v19_original_release_readonly_preflight as module
        cases = [
            ("policy_enabled", False),
            ("main_sha", "f" * 40),
            ("pr_sha", "f" * 40),
            ("pr_draft", True),
            ("pr_base_sha", "f" * 40),
            ("bad_run", REQUIRED_RUNS[-1]),
        ]
        with SingleOwner(self.path.with_suffix(".lock")), patch.object(
                module, "_original_state", return_value=self._state):
            for key, value in cases:
                with self.subTest(negative=key):
                    old = getattr(self, key)
                    setattr(self, key, value)
                    try:
                        with self.assertRaises(Exception):
                            self.read()
                    finally:
                        setattr(self, key, old)

    def test_owner_or_original_head_moves_during_remote_read(self):
        import f139.nci04_v19_original_release_readonly_preflight as module
        with SingleOwner(self.path.with_suffix(".lock")):
            with patch.object(module, "_original_state",
                              side_effect=[self._state,
                                           {**self._state,
                                            "head_sha256": "f" * 64}]):
                with self.assertRaisesRegex(
                        V19ReleasePreflightDenied, "HEAD_OR_OWNER_MOVED"):
                    self.read()
            count = []
            def witness():
                count.append(1)
                return len(count) < 2
            with patch.object(module, "_original_state", return_value=self._state):
                with self.assertRaisesRegex(
                        V19ReleasePreflightDenied, "HEAD_OR_OWNER_MOVED"):
                    self.read(witness=witness)

    def test_real_disposable_sqlite_without_v18_custody_fails_before_github(self):
        import f139.nci04_v19_original_release_readonly_preflight as module
        writable = Database.initialize(self.path, SOURCE)
        writable.close()
        with SingleOwner(self.path.with_suffix(".lock")):
            db = Database.open_readonly(self.path)
            try:
                with self.assertRaisesRegex(
                        V19ReleasePreflightDenied, "ORIGINAL_V18_SOURCE_OR_LEDGER_HEAD"):
                    v19_original_release_readonly_preflight(
                        db, original_get=self.remote, owner_witness=lambda: True)
                db.verify()
            finally:
                db.close()
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
