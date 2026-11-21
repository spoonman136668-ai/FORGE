"""Fresh F139 one-shot native-source successor qualification (no live owner)."""
from __future__ import annotations

import base64
import json
import unittest
from unittest.mock import patch

from f139.nci04_native_contract import canonical, digest, parse_intent
from f139.nci04_fresh_worker_protocol import SOURCE, TARGET, TARGET_TREE
from f139.nci04_fresh_successor_producer import (
    FreshProposalDenied, RECIPES, git_blob, propose_one,
)
from f139.nci04_fresh_lifecycle import (
    PUBLISH_KIND, PUBLISH_SCHEMA, FreshLifecycleDenied, read_lifecycle,
    reserve_claim, settle_provider,
)
from f139.nci04_fresh_successor_publication import publish_one
from f139.local_controller import SingleOwner
from f139 import test_nci04_fresh_lifecycle as fixture_module
from f139 import test_nci04_fresh_worker_protocol as seed_fixture

SOURCE_CODE = b'''class PublicCausalCells:
    ACTIVE_SLOTS = 7
    RETAINED_SLOTS = 9
    def __init__(self):
        self._counts = [[[0, 0] for _ in range(2)] for _ in range(16)]
    def _address(self, address, retained):
        return address + (self.ACTIVE_SLOTS if retained else 0)
    def choose(self, address: int, *, retained: bool = False) -> int | None:
        cell = self._address(address, retained)
        (f0, s0), (f1, s1) = self._counts[cell]
        if not f0 + s0 or not f1 + s1:
            return None
        return 0 if s0 * (f1+s1) > s1 * (f0+s0) else 1
'''


class FreshSourceProposalTests(unittest.TestCase):
    def setUp(self):
        holder = seed_fixture.FreshWorkerProtocolTests(
            "test_distinct_release_genuine_low_sequence_and_signed_receipt_identity")
        holder.setUp()
        original = json.loads(holder.raw)
        original["before_sha256"] = digest(SOURCE_CODE)
        self.seed = canonical(original)
        self.blob = git_blob(SOURCE_CODE)

    def proposal(self, consumed=None, source=SOURCE_CODE, raw=None):
        with patch("f139.nci04_fresh_successor_producer.ACCEPTED_NATIVE_BLOB",
                   self.blob):
            return propose_one(
                before=source, seed_intent=self.seed if raw is None else raw,
                consumed_after=set() if consumed is None else consumed)

    def test_two_distinct_finite_nonreplaying_candidates(self):
        first = self.proposal()
        again = self.proposal()
        self.assertEqual(first, again)
        self.assertIn(RECIPES[0][0], first["title"])
        self.assertFalse(first["scientific_first_use"])
        self.assertEqual(first["paid_model_calls"], 0)
        body = json.loads(first["body"])
        raw = base64.b64decode(body["intent_base64"], validate=True)
        candidate = parse_intent(raw, protected_main=SOURCE,
                                 target_commit=TARGET, target_tree_sha=TARGET_TREE)
        self.assertEqual(candidate.after_sha256, first["after_sha256"])
        self.assertEqual(candidate.before_sha256, digest(SOURCE_CODE))
        self.assertEqual(len(candidate.after_bytes.split(b"    def choose(")), 2)
        second = self.proposal({first["after_sha256"]})
        self.assertEqual(second["recipe"], RECIPES[1][0])
        self.assertNotEqual(second["after_sha256"], first["after_sha256"])
        self.assertIsNone(self.proposal({
            first["after_sha256"], second["after_sha256"],
        }))
        for obj in (first, second):
            self.assertNotIn("import os", base64.b64decode(
                json.loads(obj["body"])["intent_base64"]).decode("ascii"))
        self.assertEqual(self.proposal({first["after_sha256"]}), second)

    def test_only_local_readout_and_no_default_mutation(self):
        for consumed, name, expected in (
            (set(), "propose_least_observed_action", 1),
            ({self.proposal()["after_sha256"]}, "choose_laplace", 0),
        ):
            record = self.proposal(consumed)
            raw = base64.b64decode(json.loads(record["body"])["intent_base64"])
            cand = parse_intent(raw, protected_main=SOURCE,
                                target_commit=TARGET, target_tree_sha=TARGET_TREE)
            namespace = {}
            exec(compile(cand.after_bytes, "<source-only-fixture>", "exec"), namespace)
            cells = namespace["PublicCausalCells"]()
            cells._counts[0][0][1] = 4
            cells._counts[0][1][0] = 2
            before = repr(cells._counts)
            self.assertEqual(getattr(cells, name)(0), expected)
            self.assertEqual(before, repr(cells._counts))
            self.assertIsNone(getattr(cells, name)(0, retained=True))
            self.assertIsNone(cells.choose(0, retained=True))

    def test_reject_bad_source_history_and_authority(self):
        with self.assertRaises(FreshProposalDenied):
            self.proposal(source=SOURCE_CODE + b"evil")
        with self.assertRaises(FreshProposalDenied):
            self.proposal(consumed={"invalid"})
        raw = json.loads(self.seed)
        raw["scientific_first_use"] = True
        with self.assertRaises((ValueError, FreshProposalDenied)):
            self.proposal(raw=canonical(raw))
        self.assertEqual(len(RECIPES), 2)


class FreshOwnerPublicationTests(unittest.TestCase):
    def test_prepublished_attempt_is_durable_no_retry_after_uncertain_post(self):
        fixture = fixture_module.FreshLifecycleTests(
            "test_original_inert_prefix_stays_valid_but_cannot_claim_without_release")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.install_synthetic_release()
        with SingleOwner(fixture.path.with_suffix(".lock")):
            claim, raw = reserve_claim(fixture.db, fixture, fixture.key, now=fixture.now)
            fixture.prepare_provider(claim, raw)
            settle_provider(fixture.db, fixture, fixture.key,
                            run_id=fixture.rid, now=fixture.finished)
            original_head = fixture.db.meta()["head_seq"]
            plan = {
                "title": "F139 auto-feed fresh Yggdrasil DEV: test",
                "body": '{"test":true}', "body_sha256": "a" * 64,
                "recipe": "least-observed-local-arm-v1",
                "mechanism_sha256": "b" * 64,
                "after_sha256": "c" * 64, "intent_sha256": "d" * 64,
                "scientific_first_use": False, "paid_model_calls": 0,
            }
            def lost_ack(**kwargs):
                raise OSError("synthetic remote POST outcome unknown")
            fixture.create_native_feed_issue = lost_ack
            with patch(
                "f139.nci04_fresh_successor_publication.authenticate_runtime_owner"
            ), patch(
                "f139.nci04_fresh_successor_publication.propose_from_original_owner",
                return_value=plan,
            ):
                with self.assertRaises(OSError):
                    publish_one(fixture.db, fixture, fixture.key)
                self.assertEqual(fixture.db.meta()["head_seq"], original_head + 1)
                _, entries = read_lifecycle(fixture.db, fixture.key)
                self.assertEqual(
                    entries[-1]["publication_attempt"]["after_sha256"],
                    plan["after_sha256"])
                self.assertIsNone(publish_one(fixture.db, fixture, fixture.key))
                self.assertEqual(fixture.db.meta()["head_seq"], original_head + 1)
                self.assertEqual(fixture.db.conn.execute(
                    "SELECT COUNT(*) FROM events WHERE kind=?", (PUBLISH_KIND,)
                ).fetchone()[0], 1)
            fixture.reopen()
            with SingleOwner(fixture.path.with_suffix(".lock")):
                _, entries = read_lifecycle(fixture.db, fixture.key)
                self.assertEqual(entries[-1]["publication_attempt"]["recipe"],
                                 plan["recipe"])

    def test_malformed_or_duplicate_attempt_rejected_by_cold_audit(self):
        self.assertEqual(PUBLISH_SCHEMA,
                         "forge.f139.fresh-owner-publication-attempt.v1")


if __name__ == "__main__":
    unittest.main()
