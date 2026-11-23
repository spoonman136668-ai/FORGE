"""R12-H: real HMAC, authenticated shape, and NO original-owner forgery."""
from __future__ import annotations

import base64
import json
import os
import unittest

from f139.local_controller import canonical
from f139.rsi_r12h_worker_entry import (
    PACKET_SCHEMA, CredentialedRSIDenied, packet_from_base64,
    authorize_packet, exact_github_context,
)
from f139.rsi_r12g_pre_dispatch import prepare, sign
from f139.test_rsi_r12b_signed_job import (
    KEY, MAIN, TREE, synthetic_binding,
)
from f139.test_rsi_r12_candidate_binding import CANDIDATE_SOURCE, SOURCE
from f139.rsi_r12c_original_spend import owner_self_policy_allows


def fixture():
    binding, _ = synthetic_binding()
    intent = prepare(
        binding=binding, source_sha=MAIN,
        source_tree_sha=TREE, runner_os="windows-latest")
    policy = {
        "schema": "forge.f139.native-autonomy-feed-owner-policy.v1",
        "enabled": True, "source_sha": SOURCE,
        "title_prefix": "F139 autonomy DEV:",
        "lanes": ["Wingless", "Yggdrasil", "FORGE-self"],
        "max_issue_creations_per_cycle": 2,
        "require_owner_authored_pr": True,
        "require_single_head_commit_delta": True,
        "require_single_allowed_source_file": True,
        "scientific_first_use": False, "paid_model_calls": 0,
        "accepted_ref_mutations": 0, "new_controller": False,
        "new_scheduler": False, "new_queue": False,
    }
    assert owner_self_policy_allows(
        policy, original_source_sha=SOURCE)
    issue = {
        "number": 807, "state": "open", "author_association": "OWNER",
        "user": {"login": "spoonman136668-ai"},
        "body": json.dumps(policy, sort_keys=True, separators=(",", ":")),
    }
    env = {
        "F139_TICKET": intent["ticket"], "F139_LANE": "Qualification",
        "F139_TARGET_PACKAGE": "f139-rsi-self-v1",
        "F139_SOURCE_SHA": MAIN, "F139_RSI_SOURCE_TREE_SHA": TREE,
        "GITHUB_SHA": MAIN, "GITHUB_REPOSITORY": "spoonman136668-ai/FORGE",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_RUN_ID": "42599999998",
        "GITHUB_RUN_ATTEMPT": "1", "GITHUB_ACTOR": "spoonman136668-ai",
        "GITHUB_JOB": "rsi-authorize",
    }
    packet = {
        "schema": PACKET_SCHEMA, "binding": binding, "intent": intent,
        "original_signature": sign(KEY, intent),
        "original_event_seq": binding["reservation_seq"] + 1,
        "original_event_sha256": "a" * 64,
        "candidate_source_base64": base64.b64encode(
            CANDIDATE_SOURCE).decode("ascii"),
    }
    return packet, env, issue


class StrictCredentialedHandoffTests(unittest.TestCase):
    def setUp(self):
        self.packet, self.env, self.issue = fixture()

    def auth(self, packet=None, env=None, issue=None, key=KEY):
        return authorize_packet(
            packet=self.packet if packet is None else packet,
            environment=self.env if env is None else env,
            provider_issue=self.issue if issue is None else issue,
            key=key)

    def test_success_only_proves_hmac_and_provider_not_original_ledger(self):
        p = self.auth()
        self.assertTrue(p["credentialed_hmac_verified"])
        self.assertTrue(p["owner_policy_shape_verified"])
        self.assertEqual(p["ticket"], self.packet["intent"]["ticket"])
        self.assertRegex(p["authorization_sha256"], "^[0-9a-f]{64}$")
        for flag in (
            "original_owner_sqlite_ledger_verified",
            "one_use_original_terminal_receipt_verified",
            "credential_free_worker_admitted",
            "worker_dispatched_by_authorizer",
            "scientific_first_use", "source_promoted",
            "autonomous_rsi_proven",
        ):
            self.assertFalse(p[flag])

    def test_packet_canonical_and_duplicate_json_denied(self):
        raw = canonical(self.packet)
        encoded = base64.b64encode(raw).decode("ascii")
        self.assertEqual(packet_from_base64(encoded), self.packet)
        for candidate in (
            "", "!!", "YQ==", base64.b64encode(
                json.dumps(self.packet).encode("ascii")).decode("ascii"),
            base64.b64encode(
                b'{"schema":1,"schema":2}').decode("ascii"),
        ):
            with self.subTest(candidate=candidate[:20]):
                with self.assertRaises(CredentialedRSIDenied):
                    packet_from_base64(candidate)

    def test_untrusted_packet_tamper_denials(self):
        cases = (
            {"original_signature": "e" * 64},
            {"original_event_seq": 0},
            {"original_event_sha256": "f" * 4},
            {"candidate_source_base64": base64.b64encode(
                b"print('forged')\n").decode("ascii")},
            {"schema": "other"},
            {"extra": True},
            {"intent": {**self.packet["intent"],
                        "source_sha": "f" * 40}},
            {"binding": {**self.packet["binding"],
                         "candidate_sha256": "e" * 64}},
        )
        for variant in cases:
            with self.subTest(keys=list(variant)):
                with self.assertRaises(Exception):
                    self.auth(packet={**self.packet, **variant})
        with self.assertRaises(CredentialedRSIDenied):
            self.auth(key="wrong-secret-" * 4)

    def test_provider_context_not_merely_user_supplied(self):
        for key, value in (
            ("GITHUB_RUN_ID", "0"), ("GITHUB_RUN_ID", "1"),
            ("GITHUB_RUN_ATTEMPT", "2"),
            ("GITHUB_SHA", "f" * 40),
            ("F139_SOURCE_SHA", "f" * 40),
            ("GITHUB_REF", "refs/heads/feature"),
            ("GITHUB_EVENT_NAME", "push"),
            ("GITHUB_ACTOR", "attacker"),
            ("GITHUB_REPOSITORY", "attacker/FORGE"),
            ("GITHUB_JOB", "rsi-execute"),
            ("F139_LANE", "FORGE-self"),
            ("F139_TARGET_PACKAGE", "unknown"),
            ("F139_TICKET", "f139-rsi-forged"),
            ("F139_RSI_SOURCE_TREE_SHA", "f" * 40),
        ):
            with self.subTest(key=key):
                with self.assertRaises(CredentialedRSIDenied):
                    self.auth(env={**self.env, key: value})

    def test_original_policy_required_and_legacy_denied(self):
        for variant in (
            {"number": 808}, {"state": "closed"},
            {"user": {"login": "attacker"}},
            {"author_association": "CONTRIBUTOR"},
            {"pull_request": {"url": "forged"}},
            {"body": "{bad JSON"},
            {"body": json.dumps({
                **json.loads(self.issue["body"]),
                "lanes": ["Wingless", "Yggdrasil"]})},
            {"body": json.dumps({
                **json.loads(self.issue["body"]),
                "source_sha": "f" * 40})},
        ):
            with self.subTest(variant=list(variant)):
                with self.assertRaises(CredentialedRSIDenied):
                    self.auth(issue={**self.issue, **variant})

    def test_original_workflow_route_is_unmodified_and_fail_closed(self):
        from pathlib import Path
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/forge-f139-development-worker.yml"
                    ).read_text("utf-8")
        # Original execution endpoint is deliberately untouched: G145
        # forbids a generic PR from modifying a workflow. No authorization
        # parser may be mistaken for an active worker route.
        self.assertNotIn("rsi-authorize:", workflow)
        self.assertNotIn("rsi-execute:", workflow)
        self.assertNotIn("F139_RSI_NATIVE_BUNDLE", workflow)
        self.assertIn(
            "if: ${{ !startsWith(inputs.ticket, 'f139-nci04-') }}",
            workflow)
        self.assertNotIn("schedule:", workflow)
        from f139.verify_ticket import LANES as WORKER
        self.assertNotIn("FORGE-self", WORKER)
        # No original-only terminal proof is returned by the parser.
        proof = self.auth()
        self.assertFalse(proof["original_owner_sqlite_ledger_verified"])
        self.assertFalse(proof["credential_free_worker_admitted"])


if __name__ == "__main__":
    unittest.main()
