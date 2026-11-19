"""Pure offline F139 model-free frontier admission/falsification tests."""
from __future__ import annotations

import unittest

from f139.nci04_model_free_frontier import (
    FrontierDenied, choose_frontier, digest, verify_proposal,
)

S = "a" * 40
SHA = lambda char: char * 64


def proposal(lane: str, seed: str) -> dict:
    return {
        "lane": lane, "controller_source_sha": S,
        "target_commit": "b" * 40, "target_tree_sha": "c" * 40,
        "path": "cognition/continual.go" if lane == "Wingless"
                else "yggdrasil/public_causal_cells.py",
        "before_sha256": SHA("0"), "after_sha256": SHA(seed),
        "mechanism_sha256": SHA(seed.upper().lower()),
        "dependency_sha256": SHA("d"), "qualification_harness_sha256": SHA("e"),
        "suite_identity_sha256": SHA("f"), "training_config_sha256": SHA("1"),
        "toolchain_identity": "go1.25.0" if lane == "Wingless" else "python3.11.11",
        "frozen_split_sha256": SHA("2"),
        "scientific_first_use": False, "protected_holdouts_accessed": 0,
        "paid_model_calls": 0, "accepted_ref_mutations": 0,
        "optimizer_policy_mutations": 0,
    }


def history(p: dict, seq: int, outcome: str = "QUARANTINED") -> dict:
    return {
        "seq": seq, "event_sha256": SHA("3") if seq == 1 else SHA("4"),
        "controller_source_sha": S, "lane": p["lane"],
        "candidate_identity": digest(p), "mechanism_sha256": p["mechanism_sha256"],
        "outcome": outcome, "evidence_sha256": SHA("5"),
    }


class ModelFreeFrontierTests(unittest.TestCase):
    def setUp(self):
        self.w = proposal("Wingless", "6")
        self.y = proposal("Yggdrasil", "7")

    def plan(self, catalog=None, events=None):
        return choose_frontier(source_sha=S,
                               catalog=[self.w, self.y] if catalog is None else catalog,
                               history=[] if events is None else events)

    def test_exactly_one_per_lane_no_authority(self):
        result = self.plan()
        self.assertEqual({s["lane"] for s in result["selected"]},
                         {"Wingless", "Yggdrasil"})
        self.assertFalse(result["publication_authorized"])
        self.assertFalse(result["dispatch_authorized"])
        self.assertFalse(result["scientific_first_use"])
        self.assertFalse(result["source_generation_performed"])
        self.assertEqual(result["independent_source_authentication"], "CALLER_REQUIRED")
        self.assertFalse(result["new_controller"])
        self.assertFalse(result["new_scheduler"])
        self.assertFalse(result["new_queue"])
        self.assertEqual(result["paid_model_calls"], 0)
        self.assertEqual(result["accepted_ref_mutations"], 0)

    def test_permutation_changes_snapshot_digest_not_selected(self):
        first = self.plan()
        swapped = self.plan([self.y, self.w])
        self.assertEqual(first["selected"], swapped["selected"])
        self.assertNotEqual(first["catalog_sha256"], swapped["catalog_sha256"])
        self.assertEqual(first, self.plan())

    def test_retained_negative_prevents_replay_but_other_lane_eligible(self):
        event = history(self.y, 1, "QUARANTINED")
        result = self.plan(events=[event])
        self.assertEqual([s["lane"] for s in result["selected"]], ["Wingless"])
        self.assertEqual(result["abstentions"], [
            {"lane": "Yggdrasil", "reason": "NO_ELIGIBLE_CANDIDATE"}])
        self.assertEqual(result["terminal_history_count_by_lane"]["Yggdrasil"]["QUARANTINED"], 1)
        self.assertEqual(result["excluded_count_by_lane"]["Yggdrasil"], 1)

    def test_success_also_consumed_and_total_exhaustion_abstains(self):
        result = self.plan(events=[history(self.w, 1, "VERIFIED"),
                                   history(self.y, 2, "NEGATIVE")])
        self.assertEqual(result["selected"], [])
        self.assertEqual(len(result["abstentions"]), 2)
        self.assertEqual(result["consumed_history_count"], 2)

    def test_ambiguous_and_inflight_status_are_never_retried(self):
        for outcome in ("START_RISK", "WAIT_PROVIDER", "CONSUMED_INDETERMINATE"):
            with self.subTest(outcome=outcome):
                out = self.plan(events=[history(self.w, 1, outcome)])
                self.assertEqual([x["lane"] for x in out["selected"]], ["Yggdrasil"])

    def test_mechanism_consumed_across_identity_and_source_revision(self):
        old = history(self.y, 1)
        old["candidate_identity"] = SHA("8")
        old["controller_source_sha"] = "9" * 40
        out = self.plan(events=[old])
        self.assertEqual([x["lane"] for x in out["selected"]], ["Wingless"])

    def test_history_fails_closed_missing_event_or_duplicate_replay(self):
        old = history(self.y, 1)
        for malformed in (
            [old, old], [dict(old, seq=True)],
            [dict(old, outcome="UNKNOWN")], [dict(old, outcome=[])],
            [dict(old, evidence_sha256="")],
            [dict(old, source="invalid")],
        ):
            with self.subTest(malformed=malformed), self.assertRaises(FrontierDenied):
                self.plan(events=malformed)

    def test_proposal_authority_fences_and_source_drift(self):
        for key, value in (
            ("paid_model_calls", 1), ("accepted_ref_mutations", 1),
            ("protected_holdouts_accessed", 1), ("optimizer_policy_mutations", 1),
            ("scientific_first_use", True), ("paid_model_calls", False),
            ("controller_source_sha", "8" * 40),
            ("target_tree_sha", "bad"), ("after_sha256", SHA("0")),
            ("toolchain_identity", "python3.12"), ("path", "../escape.py"),
        ):
            c = dict(self.y, **{key: value})
            with self.subTest(key=key, value=value), self.assertRaises(FrontierDenied):
                self.plan(catalog=[c])

    def test_duplicate_mechanisms_and_duplicate_catalog_records_reject(self):
        for items in ([self.w, self.w],
                      [self.y, dict(self.y, after_sha256=SHA("a"))]):
            with self.assertRaisesRegex(FrontierDenied, "CATALOG_DUPLICATE"):
                self.plan(catalog=items)

    def test_unknown_fields_and_boolean_sequence_reject(self):
        with self.assertRaises(FrontierDenied):
            self.plan(catalog=[dict(self.w, actor="forbidden")])
        with self.assertRaises(FrontierDenied):
            self.plan(events=[dict(history(self.w, 1), seq=True)])
        with self.assertRaises(FrontierDenied):
            choose_frontier(source_sha="broken", catalog=[], history=[])

    def test_history_capacity_and_catalog_capacity_fail_closed(self):
        with self.assertRaisesRegex(FrontierDenied, "UNBOUNDED_INPUT"):
            self.plan(catalog=[self.w] * 129)
        with self.assertRaisesRegex(FrontierDenied, "UNBOUNDED_INPUT"):
            self.plan(events=[history(self.y, 1)] * 10001)

    def test_zero_catalog_is_honest_abstention(self):
        p = self.plan(catalog=[])
        self.assertEqual(p["selected"], [])
        self.assertEqual([x["lane"] for x in p["abstentions"]], ["Wingless", "Yggdrasil"])


if __name__ == "__main__":
    unittest.main()
