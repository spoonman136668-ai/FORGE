"""No network or model; synthetic bytes and independent native V1 contract."""
from __future__ import annotations

import base64
import json
import unittest
from unittest.mock import patch

from f139.nci04_native_contract import parse_intent
from f139.nci04_fresh_worker_protocol import SOURCE, TARGET, TARGET_TREE
from f139.nci04_fresh_curriculum import select_next
from f139.nci04_fresh_structured_dev import (
    FAMILIES, PARAMETERS, generate_dev_pool, matching_plan, method_for,
)
from f139.nci04_fresh_successor_producer import FreshProposalDenied
from f139 import test_nci04_fresh_successor_producer as proposal_fixture


class StructuredDevSourceTests(unittest.TestCase):
    def setUp(self):
        fixture = proposal_fixture.FreshSourceProposalTests(
            "test_two_distinct_finite_nonreplaying_candidates")
        fixture.setUp()
        self.fixture = fixture
        first = fixture.proposal()
        second = fixture.proposal({first["after_sha256"]})
        self.spent = {first["after_sha256"], second["after_sha256"]}
        self.last_verified = second["after_sha256"]
        self.first = first
        self.second = second

    def pool(self, *, before=proposal_fixture.SOURCE_CODE, seed=None, spent=None, latest=None):
        with patch("f139.nci04_fresh_structured_dev.ACCEPTED_NATIVE_BLOB",
                   self.fixture.blob):
            return generate_dev_pool(
                before=before, seed_intent=self.fixture.seed if seed is None else seed,
                consumed_after=self.spent if spent is None else spent,
                last_verified_after=self.last_verified if latest is None else latest)

    def test_both_old_recipes_consumed_still_produce_eight_distinct_new_methods(self):
        pool = self.pool()
        self.assertEqual(len(pool), len(FAMILIES) * len(PARAMETERS))
        self.assertEqual(pool, self.pool())
        self.assertEqual(len({r["plan"]["after_sha256"] for r in pool}), 8)
        self.assertEqual(len({r["plan"]["intent_sha256"] for r in pool}), 8)
        self.assertFalse(self.spent.intersection(
            {r["plan"]["after_sha256"] for r in pool}))
        self.assertTrue(all(r["selection"]["prerequisites"] ==
                            [self.last_verified] for r in pool))

    def test_each_generated_plan_reparses_in_existing_frozen_native_contract(self):
        for variant in self.pool():
            with self.subTest(recipe=variant["plan"]["recipe"]):
                plan = variant["plan"]
                body = json.loads(plan["body"])
                self.assertFalse(body["scientific_first_use"])
                self.assertEqual(body["paid_model_calls"], 0)
                raw = base64.b64decode(body["intent_base64"], validate=True)
                candidate = parse_intent(
                    raw, protected_main=SOURCE, target_commit=TARGET,
                    target_tree_sha=TARGET_TREE)
                self.assertEqual(plan["after_sha256"], candidate.after_sha256)
                self.assertEqual(plan["intent_sha256"], candidate.intent_sha256)
                self.assertEqual(candidate.before_sha256,
                                 json.loads(self.fixture.seed)["before_sha256"])
                self.assertEqual(len(candidate.after_bytes.split(b"    def choose(")), 2)
                self.assertNotIn(b"import os", candidate.after_bytes)
                self.assertNotIn(b"subprocess", candidate.after_bytes)

    def test_selector_matches_generated_plan_after_verified_history(self):
        pool = self.pool()
        proposals = [variant["selection"] for variant in reversed(pool)]
        historic = [
            {"after_sha256": self.first["after_sha256"],
             "intent_sha256": self.first["intent_sha256"],
             "stage": "VERIFIED", "terminal_evidence_sha256": "a" * 64},
            {"after_sha256": self.second["after_sha256"],
             "intent_sha256": self.second["intent_sha256"],
             "stage": "VERIFIED", "terminal_evidence_sha256": "b" * 64},
        ]
        result = select_next(
            history=historic, proposals=proposals, source_sha=SOURCE,
            target_tree_sha=TARGET_TREE, remaining_cost_units=2,
            spent_after_sha256=frozenset(self.spent))
        self.assertIsNotNone(result)
        issued = matching_plan(pool, result)
        self.assertEqual(issued["after_sha256"], result["after_sha256"])
        self.assertEqual(issued["intent_sha256"], result["intent_sha256"])
        self.assertTrue(issued["title"].startswith("F139 auto-feed"))
        again = self.pool(spent=self.spent | {issued["after_sha256"]})
        self.assertEqual(len(again), 7)
        self.assertEqual(len(self.pool(spent=self.spent |
                              {v["plan"]["after_sha256"] for v in pool})), 0)

    def test_real_generated_methods_only_read_public_counts(self):
        for variant in self.pool():
            body = json.loads(variant["plan"]["body"])
            raw = base64.b64decode(body["intent_base64"], validate=True)
            native = parse_intent(
                raw, protected_main=SOURCE, target_commit=TARGET,
                target_tree_sha=TARGET_TREE)
            namespace = {}
            exec(compile(native.after_bytes, "<frozen-test-candidate>", "exec"),
                 namespace)
            cells = namespace["PublicCausalCells"]()
            cells._counts[0][0][1] = 32
            cells._counts[0][1][0] = 32
            before = repr(cells._counts)
            method_name = "choose_" + (
                "support_floor_" if "-support-" in variant["plan"]["recipe"]
                else "symmetric_prior_"
            )
            # Label uses support-2-v2 / symmetric-prior-2-v2.
            label = variant["plan"]["recipe"]
            if label.startswith("support-"):
                method_name = "choose_support_floor_" + label.split("-")[1]
            else:
                method_name = "choose_symmetric_prior_" + label.split("-")[2]
            self.assertEqual(getattr(cells, method_name)(0), 0)
            self.assertIsNone(getattr(cells, method_name)(0, retained=True))
            self.assertEqual(cells.choose(0), 0)
            self.assertEqual(before, repr(cells._counts))

    def test_reject_unverified_latest_or_spent_hash(self):
        with self.assertRaises(FreshProposalDenied):
            self.pool(latest="f" * 64)
        with self.assertRaises(FreshProposalDenied):
            self.pool(spent={"not-a-sha"})
        with self.assertRaises(FreshProposalDenied):
            self.pool(before=proposal_fixture.SOURCE_CODE + b"\n# changed baseline\n")

    def test_reject_unqualified_science_and_paid_flags(self):
        seed = json.loads(self.fixture.seed)
        for key, value in (
            ("scientific_first_use", True), ("paid_api_calls", 1),
            ("accepted_ref_mutations", 1), ("protected_holdouts_accessed", 1),
        ):
            with self.subTest(key=key):
                modified = dict(seed, **{key: value})
                from f139.nci04_native_contract import canonical
                with self.assertRaises(ValueError):
                    self.pool(seed=canonical(modified))

    def test_grammar_parameter_and_nonexistent_plan_fail_closed(self):
        with self.assertRaises(FreshProposalDenied):
            method_for("support", 1)
        with self.assertRaises(FreshProposalDenied):
            method_for("arbitrary-python", 2)
        p = self.pool()
        nonexistent = dict(p[0]["selection"], after_sha256="c" * 64)
        with self.assertRaises(FreshProposalDenied):
            matching_plan(p, nonexistent)


    def test_original_owner_readback_verifies_target_main_tree_blob_and_seed(self):
        from f139.nci04_fresh_structured_dev import generate_from_original_owner
        from f139.nci04_fresh_successor_producer import REPO
        from f139.nci04_fresh_yggdrasil_boundary import ACCEPTED_NATIVE_PATH

        base = "repos/" + REPO
        main_route = base + "/branches/main"
        commit_route = base + "/git/commits/" + TARGET
        contents_route = (base + "/contents/" + ACCEPTED_NATIVE_PATH +
                          "?ref=" + TARGET)
        main = {"name": "main", "protected": True, "commit": {"sha": TARGET}}
        commit = {"sha": TARGET, "tree": {"sha": TARGET_TREE}}
        blob = {
            "type": "file", "sha": self.fixture.blob, "encoding": "base64",
            "size": len(proposal_fixture.SOURCE_CODE),
            "content": base64.b64encode(proposal_fixture.SOURCE_CODE).decode("ascii"),
        }

        class Fake:
            def __init__(self):
                self.routes = {
                    main_route: main,
                    commit_route: commit,
                    contents_route: blob,
                }
                self.calls = []

            def native_repo_get(self, route):
                from copy import deepcopy
                self.calls.append(route)
                return deepcopy(self.routes[route])

        record = {"native_intent_base64":
                  base64.b64encode(self.fixture.seed).decode("ascii")}
        api = Fake()
        with patch("f139.nci04_fresh_structured_dev.ACCEPTED_NATIVE_BLOB",
                   self.fixture.blob):
            generated = generate_from_original_owner(
                api=api, initial_record=record, consumed_after=self.spent,
                last_verified_after=self.last_verified)
            self.assertEqual(len(generated), 8)
            self.assertEqual(
                api.calls, [main_route, commit_route, contents_route, main_route])
            for target, variant in (
                (main_route, {"protected": False}),
                (commit_route, {"tree": {"sha": "0" * 40}}),
                (contents_route, {"sha": "0" * 40}),
            ):
                other = Fake()
                other.routes[target] = dict(other.routes[target], **variant)
                with self.subTest(target=target), self.assertRaises(ValueError):
                    generate_from_original_owner(
                        api=other, initial_record=record,
                        consumed_after=self.spent,
                        last_verified_after=self.last_verified)
            with self.assertRaises(ValueError):
                generate_from_original_owner(
                    api=Fake(), initial_record={"native_intent_base64": "!"},
                    consumed_after=self.spent,
                    last_verified_after=self.last_verified)



if __name__ == "__main__":
    unittest.main()
