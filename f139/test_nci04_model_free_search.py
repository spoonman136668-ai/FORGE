"""No-network deterministic search and original-owner publication qualification."""
from __future__ import annotations

import inspect
import base64
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from f139 import nci04_model_free_search as search
from f139 import nci04_free_reasoner_provider as provider
from f139.local_controller import run_once
from f139.nci04_model_owner_publication import ATTEMPT
from f139.test_nci04_owner_model_free_bootstrap import LocalG29OriginalOwnerTests

BEFORE = (Path(__file__).parent / "fixtures/model_free_yggdrasil_992ef.py").read_text(encoding="utf-8").encode("utf-8")


def cell(index=None):
    source = BEFORE if index is None else list(search.candidates(BEFORE))[index][1]
    namespace = {}
    exec(compile(source, "<isolated-public-cell-test>", "exec"), namespace)
    return namespace["PublicCausalCells"]()


class DeterministicOperatorsTests(unittest.TestCase):
    def test_deterministic_structural_candidates_and_frozen_parent(self):
        first = list(search.candidates(BEFORE))
        self.assertEqual(first, list(search.candidates(BEFORE)))
        self.assertEqual(len(first), 3)
        self.assertEqual(len({search.normalized(x[1]) for x in first}), 3)
        for _, source, _, _ in first:
            self.assertNotEqual(search.normalized(source), search.normalized(BEFORE))
        with self.assertRaisesRegex(ValueError, "FROZEN_SOURCE_DRIFT"):
            list(search.candidates(BEFORE + b"\n# drift"))

    def test_shrinkage_can_reverse_imbalanced_empirical_decision(self):
        control, changed = cell(), cell(0)
        for c in (control, changed):
            c._counts[0] = [[0, 1], [1, 8]]
        self.assertEqual(control.choose(0), 0)
        self.assertEqual(changed.choose(0), 1)
        self.assertIsNone(changed.choose(1))

    def test_standard_error_abstains_on_weak_gap_and_retains_strong_signal(self):
        control, changed = cell(), cell(1)
        for c in (control, changed):
            c._counts[0] = [[4, 6], [5, 5]]
        self.assertEqual(control.choose(0), 0)
        self.assertIsNone(changed.choose(0))
        changed._counts[0] = [[0, 20], [20, 0]]
        self.assertEqual(changed.choose(0), 0)

    def test_recency_only_forgets_observed_cell_and_preserves_checkpoint_format(self):
        c = cell(2)
        c._counts[0] = [[12, 8], [10, 2]]
        c._counts[1] = [[2, 3], [4, 5]]
        c._counts[7] = [[8, 8], [6, 6]]
        c.observe(0, 1, 1)
        self.assertEqual(c._counts[0], [[6, 4], [5, 2]])
        self.assertEqual(c._counts[1], [[2, 3], [4, 5]])
        self.assertEqual(c._counts[7], [[8, 8], [6, 6]])
        self.assertEqual(len(c.snapshot()), 164)
        self.assertEqual(type(c).restore(c.snapshot()).snapshot(), c.snapshot())

    def test_every_operator_preserves_address_validation_memory_and_nonmutation_on_choose(self):
        for index in range(3):
            with self.subTest(index=index):
                c = cell(index)
                before = c.snapshot()
                for a, r in ((-1, False), (7, False), (9, True), (True, False)):
                    with self.assertRaises(ValueError):
                        c.observe(a, 0, 1, retained=r)
                    with self.assertRaises(ValueError):
                        c.choose(a, retained=r)
                self.assertIsNone(c.choose(0))
                self.assertEqual(c.snapshot(), before)

    def test_default_and_direct_model_transport_are_disabled_before_any_network_read(self):
        with patch.object(provider.urllib.request, "build_opener", side_effect=AssertionError), \
                patch.object(provider, "_public_get", side_effect=AssertionError), \
                patch.dict("os.environ", {"OPENROUTER_API_KEY": "present-but-not-authority"}):
            with self.assertRaisesRegex(provider.FreeReasonerUnavailable, "DISABLED_BY_OWNER"):
                provider._post_one(b"{}", "present-but-not-authority")
            with self.assertRaisesRegex(provider.FreeReasonerUnavailable, "DISABLED_BY_OWNER"):
                provider.infer_free_once({})
        source = inspect.getsource(run_once)
        self.assertNotIn("run_original_free_reasoner_once", source)
        self.assertNotIn("run_original_renewal_from_natural_tick", source)


class ModelFreeOwnerPublicationTests(unittest.TestCase):
    def setUp(self):
        fixture = LocalG29OriginalOwnerTests("test_one_authentic_source_only_g29_draft_under_original_owner")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.db, self.owner, self.steering = fixture.db, fixture.owner, fixture.steering
        self.owner.parent_data = BEFORE
        for change in (patch("f139.test_nci04_candidate_publisher.SOURCE", BEFORE),
                       patch.object(search, "PARENT", self.owner.parent)):
            change.start()
            self.addCleanup(change.stop)

    def publish(self, witness=lambda: True):
        return search.local_search_once(
            self.db, self.owner.get, self.steering.get, self.owner.write,
            source_sha=self.owner.source, owner_witness=witness)

    def test_real_publisher_and_feeder_accept_deterministic_draft_without_inference(self):
        from f139.nci04_autonomy_feed import prepare_feed
        with patch.object(provider, "_post_one", side_effect=AssertionError("MODEL MUST NOT RUN")):
            result = self.publish()
        self.assertEqual(result["disposition"], "MODEL_DRAFT_AUTHENTICATED")
        self.assertEqual(result["generator"], "DETERMINISTIC_SOURCE_SEARCH")
        self.assertEqual(result["operator"], search.OPERATORS[0][0])
        self.assertEqual(result["model_calls"], 0)
        self.assertFalse(result["scientific_first_use"])
        def get(route):
            if route.startswith("repos/spoonman136668-ai/Wingless/pulls?"):
                return []
            return self.owner.get(route)
        feed = prepare_feed(get, source_sha=self.owner.source, existing_candidate_identities=set())
        self.assertEqual(len(feed["candidates"]), 1)
        self.assertFalse(feed["candidates"][0]["scientific_first_use"])
        self.db.verify()

    def test_sticky_remote_ambiguity_never_consumes_next_operator(self):
        self.owner.fail_after_reference = True
        first = self.publish()
        self.assertEqual(first["disposition"], "MODEL_DRAFT_REMOTE_AMBIGUOUS_NO_RETRY")
        head = self.db.meta().copy()
        writes = len(self.owner.write_calls)
        second = self.publish()
        self.assertEqual(second["disposition"], "MODEL_DRAFT_UNRESOLVED_NO_REPLAY")
        self.assertEqual(self.db.meta(), head)
        self.assertEqual(len(self.owner.write_calls), writes)

    def test_exhausted_search_is_read_only_and_never_calls_provider(self):
        prepared = search.owner_request(
            self.db, self.owner.get, self.steering.get, source_sha=self.owner.source,
            lane="Yggdrasil", target_commit=self.owner.parent, path=search.PATH,
            owner_witness=lambda: True)
        prepared["consumed_after_hashes"].update(
            search.digest(source) for _, source, _, _ in search.candidates(BEFORE))
        head = self.db.meta().copy()
        with patch.object(search, "owner_request", return_value=prepared), \
                patch.object(provider, "_post_one", side_effect=AssertionError):
            got = self.publish()
        self.assertEqual(got["disposition"], "MODEL_FREE_SEARCH_EXHAUSTED_NO_FRESH_CANDIDATE")
        self.assertEqual(self.db.meta(), head)
        self.assertEqual(self.owner.write_calls, [])

    def test_semantically_consumed_negative_is_not_republished_with_new_comments(self):
        first = list(search.candidates(BEFORE))[0][1] + b"\n# historical negative\n"
        intent = {"lane": "Yggdrasil", "path": search.PATH,
                  "after_base64": base64.b64encode(first).decode("ascii")}
        event = {"native_intent_base64": base64.b64encode(
            search.canonical(intent)).decode("ascii")}
        with patch.object(search, "native_events", return_value=[event]):
            got = self.publish()
        self.assertEqual(got["operator"], search.OPERATORS[1][0])
        self.assertNotIn(b"historical negative", self.owner.head_data)
        self.db.verify()

    def test_false_owner_witness_cannot_publish_or_consume_work(self):
        head = self.db.meta().copy()
        with self.assertRaises(ValueError):
            self.publish(witness=lambda: False)
        self.assertEqual(self.db.meta(), head)
        self.assertEqual(self.owner.write_calls, [])


if __name__ == "__main__":
    unittest.main()
