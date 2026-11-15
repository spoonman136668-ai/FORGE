"""No live original-owner calls: synthetic predicate and refusal controls."""
import copy
import inspect
import unittest
from unittest.mock import patch

from f139.nci04_native_contract import canonical, digest
from f139 import nci04_v41_hybrid_event1832_proof_diagnostic as d
from f139 import nci04_v41_hybrid_event1832_successor as successor


class V39DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.req = {
            "readiness_comment_id": 6902399422,
            "backup_run_id": 43769577997,
            "backup_manifest_sha256": "a" * 64,
            "backup_logical_all_tables_sha256": "b" * 64,
            "target_source_sha": d.TARGET,
        }
        self.proof = {k: False for k in successor.FIELDS}
        self.proof.update({
            "schema": successor.SCHEMA,
            "owner_event_id": self.req["readiness_comment_id"],
            "backup_run_id": self.req["backup_run_id"],
            "backup_manifest_sha256": self.req["backup_manifest_sha256"],
            "backup_logical_all_tables_sha256":
                self.req["backup_logical_all_tables_sha256"],
            "to_source_sha": d.TARGET,
        })
        self.req["expected_proof_sha256"] = digest(canonical(self.proof))

    def flags(self, doc=None, req=None, raw=None):
        proof = self.proof if doc is None else doc
        return d.compare_proof(
            proof, self.req if req is None else req,
            canonical(proof).decode("ascii") if raw is None else raw)

    def test_all_proof_predicates_match(self):
        flags = self.flags()
        self.assertEqual(len(flags), 9)
        self.assertTrue(all(flags.values()))

    def test_each_event_proof_difference_is_diagnostic_only(self):
        cases = {
            "field_set": {**self.proof, "unexpected": False},
            "schema": {**self.proof, "schema": "wrong"},
            "owner_event": {**self.proof, "owner_event_id": -1},
            "backup_run": {**self.proof, "backup_run_id": -1},
            "backup_manifest": {
                **self.proof, "backup_manifest_sha256": "0" * 64},
            "backup_logical_tables": {
                **self.proof, "backup_logical_all_tables_sha256": "0" * 64},
            "target_source": {
                **self.proof, "to_source_sha": "0" * 40},
        }
        for flag, changed in cases.items():
            with self.subTest(flag=flag):
                checks = self.flags(doc=changed)
                self.assertFalse(checks[flag])
                self.assertFalse(checks["approved_proof_digest"])
                self.assertTrue(checks["canonical_row_payload"])

    def test_approved_hash_and_canonical_payload_independent(self):
        wrong_req = {**self.req, "expected_proof_sha256": "0" * 64}
        checks = self.flags(req=wrong_req)
        self.assertFalse(checks["approved_proof_digest"])
        self.assertTrue(checks["canonical_row_payload"])
        bad_row = self.flags(raw="{}")
        self.assertFalse(bad_row["canonical_row_payload"])
        self.assertTrue(bad_row["approved_proof_digest"])

    def test_no_original_owner_mutation_or_credential_logging(self):
        source = inspect.getsource(d)
        self.assertNotIn("Set-ScheduledTask", source)
        self.assertNotIn("Start-ScheduledTask", source)
        self.assertNotIn("commit_transition(", source)
        self.assertNotIn("workflow_dispatch", source)
        self.assertNotIn("subprocess.", source)
        self.assertNotIn("GH_TOKEN", source)
        self.assertIn("Database.open_readonly", source)
        self.assertIn("SingleOwner(", source)
        self.assertIn("profile.readback(path)", source)
        self.assertIn("db.conn.total_changes == 0", source)
        self.assertIn("activation_authorized", source)

    def test_unqualified_context_and_forged_event_rejected(self):
        with self.assertRaisesRegex(
                d.DiagnosticDenied, "ORIGINAL_WINDOWS_OWNER_FIRST_ATTEMPT_ONLY"):
            d.authenticate({}, {}, lambda _: {})
        with patch.object(d.sys, "platform", "win32"), \
             patch.object(d.os, "name", "nt"):
            valid = {
                "GITHUB_REPOSITORY": d.REPO,
                "GITHUB_ACTOR": d.OWNER,
                "GITHUB_EVENT_NAME": "issue_comment",
                "GITHUB_REF": "refs/heads/main",
                "RUNNER_NAME": "FORGE-CODEX-REMOTE",
                "GITHUB_RUN_ATTEMPT": "1",
                "GITHUB_SHA": "c" * 40,
                "GITHUB_RUN_ID": "456",
            }
            with self.assertRaisesRegex(
                    d.DiagnosticDenied, "EXACT_NEW_OWNER_DIAGNOSTIC_COMMENT"):
                d.authenticate(valid, {}, lambda _: {})

    def test_request_requires_source_reference_not_postcommit_replay(self):
        self.assertEqual(d.TARGET,
                         "1479f963160001037566e4cef33582c5293fb773")
        self.assertEqual(d.COMMIT_COMMENT_ID, 6902472106)
        self.assertEqual(d.POSTCOMMIT_COMMENT_ID, 6902549450)
        self.assertIn("PROOF_DIAG", d.PREFIX)
        self.assertNotEqual(d.PREFIX, "F139-HYBRID-V39-POSTCOMMIT ")


if __name__ == "__main__":
    unittest.main()
