"""Synthetic V2 original-owner issue publication, never live GitHub."""
from __future__ import annotations

from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from f139.local_controller import SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_fresh_lifecycle import (
    PUBLISH_KIND, PUBLISH_SCHEMA_STRUCTURED, read_lifecycle,
    reserve_claim, settle_provider, admit_next_successor,
)
from f139.nci04_fresh_successor_publication import (
    publish_one, preflight_structured_dev_plan,
)
from f139.nci04_owner_issue import LABEL
from f139 import test_nci04_fresh_lifecycle as native_fixture
from f139 import test_nci04_fresh_structured_dev as generator_fixture


class StructuredV2OwnerPublicationTests(unittest.TestCase):
    def setUp(self):
        fixture = native_fixture.FreshLifecycleTests(
            "test_original_inert_prefix_stays_valid_but_cannot_claim_without_release")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.install_synthetic_release()
        self.fixture = fixture

        source = generator_fixture.StructuredDevSourceTests(
            "test_both_old_recipes_consumed_still_produce_eight_distinct_new_methods")
        source.setUp()
        self.plan = source.pool()[0]["plan"]

    def terminal(self):
        fixture = self.fixture
        claim, raw = reserve_claim(
            fixture.db, fixture, fixture.key, now=fixture.now)
        fixture.prepare_provider(claim, raw)
        settle_provider(
            fixture.db, fixture, fixture.key,
            run_id=fixture.rid, now=fixture.finished)

    def test_v2_generated_issue_prepost_exact_binding(self):
        preflight_structured_dev_plan(self.plan)
        for key, value in (
            ("recipe", "support-3-v2"),
            ("title", "unrelated"),
            ("after_sha256", "f" * 64),
            ("intent_sha256", "f" * 64),
            ("body_sha256", "f" * 64),
            ("scientific_first_use", True),
            ("paid_model_calls", 1),
        ):
            with self.subTest(key=key):
                changed = dict(self.plan, **{key: value})
                with self.assertRaises(ValueError):
                    preflight_structured_dev_plan(changed)
        body = json.loads(self.plan["body"])
        body["paid_model_calls"] = 1
        invalid = dict(self.plan, body=canonical(body).decode("ascii"),
                       body_sha256=digest(canonical(body)))
        with self.assertRaises(ValueError):
            preflight_structured_dev_plan(invalid)

    def test_v2_remote_post_lost_ack_is_consumed_once_and_cold_reopens(self):
        fixture = self.fixture
        n_posts = []
        def lost_ack(**kwargs):
            n_posts.append(kwargs)
            raise OSError("V2 SYNTHETIC REMOTE POST OUTCOME UNKNOWN")
        fixture.create_native_feed_issue = lost_ack
        with SingleOwner(fixture.path.with_suffix(".lock")):
            self.terminal()
            before = fixture.db.meta()["head_seq"]
            with patch(
                "f139.nci04_fresh_successor_publication.authenticate_runtime_owner"
            ), patch(
                "f139.nci04_fresh_successor_publication.propose_from_original_owner",
                return_value=None,
            ) as legacy, patch(
                "f139.nci04_fresh_successor_publication.plan_next_structured_dev_from_original_owner",
                return_value=self.plan,
            ) as planner:
                with self.assertRaisesRegex(
                    OSError, "SYNTHETIC REMOTE POST OUTCOME UNKNOWN"):
                    publish_one(fixture.db, fixture, fixture.key)
                self.assertEqual(fixture.db.meta()["head_seq"], before + 1)
                _, entries = read_lifecycle(fixture.db, fixture.key)
                self.assertEqual(entries[-1]["publication_attempt"]["schema"],
                                 PUBLISH_SCHEMA_STRUCTURED)
                self.assertEqual(entries[-1]["publication_attempt"]["recipe"],
                                 self.plan["recipe"])
                self.assertIsNone(publish_one(fixture.db, fixture, fixture.key))
                self.assertEqual(len(n_posts), 1)
                self.assertEqual(legacy.call_count, 1)
                self.assertEqual(planner.call_count, 1)
        fixture.reopen()
        with SingleOwner(fixture.path.with_suffix(".lock")):
            _, entries = read_lifecycle(fixture.db, fixture.key)
            self.assertEqual(entries[-1]["publication_attempt"]["schema"],
                             PUBLISH_SCHEMA_STRUCTURED)
            self.assertEqual(fixture.db.conn.execute(
                "SELECT COUNT(*) FROM events WHERE kind=?", (PUBLISH_KIND,)
            ).fetchone()[0], 1)

    def test_v2_malformed_plan_never_consumes_post_or_ledger(self):
        fixture = self.fixture
        called = []
        fixture.create_native_feed_issue = lambda **kw: called.append(kw)
        with SingleOwner(fixture.path.with_suffix(".lock")):
            self.terminal()
            original = fixture.db.meta()["head_hash"]
            rejected = dict(self.plan, recipe="support-3-v2")
            with patch(
                "f139.nci04_fresh_successor_publication.authenticate_runtime_owner"
            ), patch(
                "f139.nci04_fresh_successor_publication.propose_from_original_owner",
                return_value=None,
            ), patch(
                "f139.nci04_fresh_successor_publication.plan_next_structured_dev_from_original_owner",
                return_value=rejected,
            ):
                with self.assertRaises(ValueError):
                    publish_one(fixture.db, fixture, fixture.key)
            self.assertEqual(fixture.db.meta()["head_hash"], original)
            self.assertEqual(called, [])

    def test_v2_publish_readback_admit_one_distinct_native_ticket(self):
        fixture = self.fixture
        repo = "repos/spoonman136668-ai/FORGE"
        issue_number = 1917
        remote = dict(deepcopy(fixture.fixture.raw_issue),
                      number=issue_number, id=91917,
                      url="https://api.github.com/" + repo +
                          "/issues/" + str(issue_number),
                      body=self.plan["body"])
        fixture.routes[repo + "/issues/" + str(issue_number)] = remote
        fixture.routes[
            repo + "/issues?state=open&labels=" + LABEL + "&per_page=100&page=1"
        ] = [remote]
        fixture.create_native_feed_issue = lambda **kw: deepcopy(remote)
        with SingleOwner(fixture.path.with_suffix(".lock")):
            self.terminal()
            with patch(
                "f139.nci04_fresh_successor_publication.authenticate_runtime_owner"
            ), patch(
                "f139.nci04_fresh_successor_publication.propose_from_original_owner",
                return_value=None,
            ), patch(
                "f139.nci04_fresh_successor_publication.plan_next_structured_dev_from_original_owner",
                return_value=self.plan,
            ):
                self.assertEqual(
                    publish_one(fixture.db, fixture, fixture.key), issue_number)
            admitted = admit_next_successor(fixture.db, fixture, fixture.key)
            self.assertEqual(admitted["issue_number"], issue_number)
            self.assertEqual(admitted["after_sha256"], self.plan["after_sha256"])
            _, entries = read_lifecycle(fixture.db, fixture.key)
            self.assertEqual(entries[0]["publication_attempt"]["schema"],
                             PUBLISH_SCHEMA_STRUCTURED)
            self.assertEqual(entries[-1]["stage"], "READY")
            self.assertEqual(len(entries), 2)


if __name__ == "__main__":
    unittest.main()
