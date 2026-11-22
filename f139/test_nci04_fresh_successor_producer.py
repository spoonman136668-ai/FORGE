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
                "schema": "forge.f139.fresh-owner-source-proposal.v1",
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
        # Cold-reopen only AFTER releasing the original kernel mutex.
        fixture.reopen()
        with SingleOwner(fixture.path.with_suffix(".lock")):
            _, entries = read_lifecycle(fixture.db, fixture.key)
            self.assertEqual(entries[-1]["publication_attempt"]["recipe"],
                             plan["recipe"])

    def test_two_distinct_successors_publish_admit_and_cold_restore(self):
        # This is a SYNTHETIC owner provider + SQLite test, NOT deployment.
        from copy import deepcopy
        from f139.nci04_owner_issue import LABEL
        from f139.nci04_fresh_lifecycle import admit_next_successor

        fixture = fixture_module.FreshLifecycleTests(
            "test_original_inert_prefix_stays_valid_but_cannot_claim_without_release")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.install_synthetic_release()
        builder = FreshSourceProposalTests("test_two_distinct_finite_nonreplaying_candidates")
        builder.setUp()
        first = builder.proposal()
        second = builder.proposal({first["after_sha256"]})
        self.assertNotEqual(first["after_sha256"], second["after_sha256"])

        issue_base = deepcopy(fixture.fixture.raw_issue)
        prefix = "repos/spoonman136668-ai/FORGE"
        issue_list = prefix + "/issues?state=open&labels=" + LABEL + "&per_page=100&page=1"
        original_head = [(r["seq"], r["sha"]) for r in fixture.db.conn.execute(
            "SELECT seq,sha FROM events WHERE seq<=4 ORDER BY seq")]

        with patch("f139.nci04_fresh_successor_publication.authenticate_runtime_owner"):
            with SingleOwner(fixture.path.with_suffix(".lock")):
                claim, raw = reserve_claim(fixture.db, fixture, fixture.key,
                                            now=fixture.now)
                fixture.prepare_provider(claim, raw)
                settle_provider(fixture.db, fixture, fixture.key,
                                run_id=fixture.rid, now=fixture.finished)
                for step, plan in enumerate((first, second), start=1):
                    number = 1850 + step
                    remote = dict(issue_base,
                                  number=number, id=91850 + step,
                                  url="https://api.github.com/" + prefix + "/issues/" + str(number),
                                  body=plan["body"])
                    fixture.routes[prefix + "/issues/" + str(number)] = remote
                    fixture.routes[issue_list] = [remote]
                    posts = []
                    def create_issue(*, title, body):
                        posts.append((title, body))
                        self.assertEqual(body, plan["body"])
                        self.assertEqual(title, plan["title"])
                        return deepcopy(remote)
                    fixture.create_native_feed_issue = create_issue
                    with patch(
                        "f139.nci04_fresh_successor_publication.propose_from_original_owner",
                        return_value=plan,
                    ):
                        published = publish_one(fixture.db, fixture, fixture.key)
                        self.assertEqual(published, number)
                        self.assertEqual(len(posts), 1)
                        self.assertIsNone(publish_one(fixture.db, fixture, fixture.key))
                        self.assertEqual(len(posts), 1)
                    admitted = admit_next_successor(fixture.db, fixture, fixture.key)
                    self.assertEqual(admitted["issue_number"], number)
                    self.assertEqual(admitted["after_sha256"], plan["after_sha256"])
                    self.assertEqual(fixture.db.ready()["ticket"], admitted["ticket"])
                    start = "2026-11-21T08:" + str(step * 20).zfill(2) + ":00Z"
                    finish = "2026-11-21T08:" + str(step * 20 + 5).zfill(2) + ":00Z"
                    fixture.rid = 123456 + step
                    # The synthetic provider must carry the exact second
                    # ticket's committed START time, not the first fixture's
                    # 08:00 timestamp; production requires this custody match.
                    fixture.now = start
                    claim, raw = reserve_claim(fixture.db, fixture, fixture.key,
                                                now=start)
                    fixture.prepare_provider(claim, raw)
                    # The existing original API fixture hardcodes the first
                    # ticket; this synthetic second-ticket reader is GET-only.
                    def provider_lookup(ticket, started_at, source):
                        self.assertEqual(ticket, admitted["ticket"])
                        self.assertEqual(started_at, start)
                        self.assertEqual(source, fixture.fixture.release)
                        return fixture.get(prefix + "/actions/runs/" + str(fixture.rid))
                    fixture.candidates_for_source = provider_lookup
                    settle_provider(fixture.db, fixture, fixture.key,
                                    run_id=fixture.rid, now=finish)
                    self.assertIsNone(fixture.db.ready())
                self.assertEqual(fixture.db.conn.execute(
                    "SELECT COUNT(*) FROM events WHERE kind=?", (PUBLISH_KIND,)
                ).fetchone()[0], 2)
                self.assertEqual(fixture.db.conn.execute(
                    "SELECT COUNT(*) FROM tasks WHERE stage='VERIFIED'"
                ).fetchone()[0], 3)
                self.assertEqual([(r["seq"], r["sha"]) for r in fixture.db.conn.execute(
                    "SELECT seq,sha FROM events WHERE seq<=4 ORDER BY seq")],
                    original_head)
        fixture.reopen()
        with SingleOwner(fixture.path.with_suffix(".lock")):
            _, entries = read_lifecycle(fixture.db, fixture.key)
            self.assertEqual([e["record"]["issue_number"] for e in entries],
                             [1849, 1851, 1852])
            self.assertTrue(all(e["stage"] == "VERIFIED" for e in entries))
            self.assertEqual([e["publication_attempt"]["recipe"] for e in entries[:2]],
                             [first["recipe"], second["recipe"]])

    def test_malformed_or_duplicate_attempt_rejected_by_cold_audit(self):
        self.assertEqual(PUBLISH_SCHEMA,
                         "forge.f139.fresh-owner-publication-attempt.v1")


if __name__ == "__main__":
    unittest.main()
