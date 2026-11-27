"""Adverse tests for the bounded compositional Nature brancher."""
import copy
import hashlib
import unittest
from unittest.mock import patch

from scripts import nature_compositional_brancher as b


def sha(s):
    return hashlib.sha256(s.encode("ascii")).hexdigest()


def event(signals=("sparse-evidence", "retention-loss"), **changes):
    item = {"schema": b.EVENT_SCHEMA, "event_id": "terminal-dev-negative-0001",
            "lane": "Yggdrasil", "parent_sha": "a" * 40,
            "parent_tree_sha": "b" * 40, "evidence_sha256": "c" * 64,
            "receipt_sha256": "d" * 64, "observed_signals": list(signals),
            "partition": "development",
            "terminal_disposition": "VERIFIED_TERMINAL_NEGATIVE"}
    item.update(changes)
    return item


def run(item=None, history=(), consumed=(), **kwargs):
    return b.propose(event() if item is None else item,
                     historical_negatives=history,
                     consumed_mechanism_sha256=consumed, **kwargs)


class CompositionalBranchTests(unittest.TestCase):
    def test_empty_event_fails_closed_without_plan_or_fallback(self):
        got = b.propose(None, historical_negatives=(), consumed_mechanism_sha256=())
        self.assertEqual(got["disposition"], "NO_NEW_HYPOTHESIS_SOURCE")
        self.assertEqual(got["branches"], [])
        self.assertEqual(got["expanded_nodes"], 0)
        self.assertEqual(got["model_calls"], 0)
        self.assertFalse(got["scientific_first_use"])

    def test_search_builds_compositions_beyond_the_nine_fixed_plan_catalogue(self):
        before = event()
        snapshot = copy.deepcopy(before)
        first = run(before)
        self.assertEqual(first, run(before))
        self.assertEqual(before, snapshot)
        self.assertEqual(first["disposition"], "UNTESTED_COMPOSITIONAL_BRANCHES")
        self.assertGreater(len(first["branches"]), 3)
        self.assertTrue(any(x["depth"] >= 2 for x in first["branches"]))
        self.assertTrue(any(x["depth"] == 3 for x in first["branches"]))
        self.assertLessEqual(len(first["branches"]), b.MAX_OUTPUTS)
        self.assertLessEqual(first["expanded_nodes"], b.MAX_EXPANSIONS)
        self.assertTrue(all(x["classification"] == "UNTESTED_ADVISORY_COMPOSITION"
                            for x in first["branches"]))

    def test_failure_dimensions_change_branch_population(self):
        sparse = run(event(("sparse-evidence",)))
        temporal = run(event(("nonstationarity",)))
        sparse_ids = {node["node_id"] for p in sparse["branches"] for node in p["mechanism_nodes"]}
        temporal_ids = {node["node_id"] for p in temporal["branches"] for node in p["mechanism_nodes"]}
        self.assertIn("support_calibration", sparse_ids)
        self.assertIn("change_point_partition", temporal_ids)
        self.assertIn("multi_timescale_memory", temporal_ids)
        self.assertNotEqual(sparse_ids, temporal_ids)

    def test_compositions_preserve_typed_dependency_edges(self):
        got = run(event(("sparse-evidence", "context-interference")))
        match = [p for p in got["branches"]
                 if {n["node_id"] for n in p["mechanism_nodes"]} >=
                 {"support_calibration", "context_partition", "context_scoped_update"}]
        self.assertTrue(match)
        for p in match:
            self.assertIn({"from": "support_calibration", "to": "context_scoped_update",
                           "token": "calibrated_confidence"}, p["dependency_edges"])
            self.assertIn({"from": "context_partition", "to": "context_scoped_update",
                           "token": "context_partition"}, p["dependency_edges"])

    def test_retention_composition_requires_regime_and_temporal_sources(self):
        item = event(("retention-loss", "nonstationarity"))
        sequence = ("change_point_partition", "multi_timescale_memory",
                    "regime_gated_consolidation")
        edges = b._dependencies(sequence)
        self.assertIsNotNone(edges)
        self.assertIn({"from": "change_point_partition",
                       "to": "regime_gated_consolidation",
                       "token": "regime_partition"}, edges)
        self.assertIn({"from": "multi_timescale_memory",
                       "to": "regime_gated_consolidation",
                       "token": "temporal_context"}, edges)
        plan = b._plan(sequence, item, set(item["observed_signals"]), None)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["depth"], 3)
        self.assertEqual(len(plan["causal_hypothesis_components"]), 3)

    def test_relabels_and_duplicate_history_are_not_new_terminal_evidence(self):
        old = event()
        relabeled = event(("sparse-evidence",), event_id="terminal-dev-negative-0002",
                          evidence_sha256="e" * 64)
        self.assertEqual(run(relabeled, history=[old])["disposition"],
                         "BRANCH_DUPLICATE_OR_RELABELED_EVENT")
        with self.assertRaisesRegex(b.BranchSearchRejected, "BRANCH_DUPLICATE_HISTORY"):
            run(relabeled, history=[old, old])

    def test_consumed_composition_is_not_reissued_under_new_event_identity(self):
        first = run()["branches"]
        fresh = event(event_id="terminal-dev-negative-0002",
                      evidence_sha256="e" * 64, receipt_sha256="f" * 64)
        denied = run(fresh, consumed=[p["mechanism_sha256"] for p in first])
        self.assertTrue(all(p["mechanism_sha256"] not in
                            {x["mechanism_sha256"] for x in first}
                            for p in denied["branches"]))
        self.assertFalse({p["mechanism_sha256"] for p in denied["branches"]} &
                         {p["mechanism_sha256"] for p in first})

    def test_holdout_invalid_lane_and_unknown_failure_signal_are_rejected(self):
        for changes in ({"partition": "holdout"}, {"lane": "FORGE"},
                        {"observed_signals": ["unknown-signal"]},
                        {"terminal_disposition": "RUNNING"},
                        {"parent_sha": "main"}):
            with self.subTest(changes=changes), self.assertRaises(b.BranchSearchRejected):
                run(event(**changes))
        self.assertEqual(run(event(("causal-support-gap",)))["disposition"],
                         "UNTESTED_COMPOSITIONAL_BRANCHES")

    def test_budget_is_bounded_and_cannot_be_widened_without_limit(self):
        for kwargs in ({"max_depth": 4}, {"beam_width": 33},
                       {"max_expansions": 65}, {"max_outputs": 25},
                       {"max_depth": True}):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(
                    b.BranchSearchRejected, "BRANCH_BUDGET_INVALID"):
                run(**kwargs)
        small = run(max_depth=1, beam_width=2, max_expansions=4, max_outputs=2)
        self.assertLessEqual(len(small["branches"]), 2)
        self.assertTrue(all(p["depth"] == 1 for p in small["branches"]))

    def test_plan_digest_parent_link_and_authority_flags(self):
        got = run()
        by_id = {p["mechanism_sha256"]: p for p in got["branches"]}
        for p in got["branches"]:
            body = {k: v for k, v in p.items() if k != "plan_sha256"}
            self.assertEqual(p["plan_sha256"], b._digest(body))
            self.assertFalse(p["semantic_novelty_verified"])
            self.assertFalse(p["scientific_first_use"])
            self.assertFalse(p["dispatch_authorized"])
            self.assertFalse(p["scientific_gain_verified"])
            self.assertNotIn("candidate_source", p)
            if p["branch_parent_id"] is not None:
                self.assertIn(p["branch_parent_id"], by_id)

    def test_historical_saturation_negative_generates_two_tier_counter_hypothesis(self):
        # Development-only replay of the historical Yggdrasil issue #856 failure:
        # at-cap value 65535 became 32797 after the candidate halved both counters.
        # It is an engineering regression negative, not a model-science outcome.
        item = event(("saturation-boundary", "nonstationarity"))
        sequence = ("saturation_invariant_guard", "two_tier_recent_evidence",
                    "two_tier_memory_consistency_audit")
        edges = b._dependencies(sequence)
        self.assertIsNotNone(edges)
        self.assertIn({"from": "saturation_invariant_guard",
                       "to": "two_tier_recent_evidence",
                       "token": "monotonic_lifetime_counts"}, edges)
        self.assertIn({"from": "saturation_invariant_guard",
                       "to": "two_tier_memory_consistency_audit",
                       "token": "monotonic_lifetime_counts"}, edges)
        self.assertIn({"from": "two_tier_recent_evidence",
                       "to": "two_tier_memory_consistency_audit",
                       "token": "recent_evidence_window"}, edges)
        plan = b._plan(sequence, item, set(item["observed_signals"]), None)
        searched = run(item)
        self.assertTrue(any(
            {node["node_id"] for node in branch["mechanism_nodes"]} >= set(sequence)
            for branch in searched["branches"]))
        self.assertIsNotNone(plan)
        self.assertEqual(plan["classification"], "UNTESTED_ADVISORY_COMPOSITION")
        self.assertTrue(any("65535" in text for text in plan["counterfactual_predictions"]))
        self.assertTrue(any("decreases" in text or "recede" in text
                            for text in plan["falsification_conditions"]))
        self.assertFalse(plan["scientific_gain_verified"])
        self.assertFalse(plan["semantic_novelty_verified"])

    def test_no_files_network_or_model_execution(self):
        with patch("builtins.open", side_effect=AssertionError("filesystem denied")), \
             patch("builtins.input", side_effect=AssertionError("prompt denied")):
            got = run()
        self.assertEqual(got["model_calls"], 0)
        self.assertEqual(got["paid_api_calls"], 0)


if __name__ == "__main__":
    unittest.main()
