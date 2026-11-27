"""Deterministic adverse qualification of the isolated advisory comparator."""
import copy
import unittest
from unittest.mock import patch

from f139 import nature_failure_guided_comparator as c


def example(**updates):
    event = {"schema": c.EVENT_SCHEMA, "event_id": "terminal-original-0001",
             "lane": "Yggdrasil", "parent_sha": "a" * 40,
             "parent_tree_sha": "b" * 40, "evidence_sha256": "c" * 64,
             "receipt_sha256": "d" * 64,
             "failure_class": "sparse-evidence-overconfidence",
             "partition": "development",
             "terminal_disposition": "VERIFIED_TERMINAL_NEGATIVE"}
    event.update(updates)
    return event


def run(event=None, history=(), consumed=()):
    return c.propose(example() if event is None else event,
                     historical_negatives=history,
                     consumed_mechanism_sha256=consumed)


class NaturePlanTests(unittest.TestCase):
    def test_empty_event_is_exhaustion_not_model_fallback(self):
        got = c.propose(None, historical_negatives=(), consumed_mechanism_sha256=())
        self.assertEqual(got["disposition"], "NO_NEW_HYPOTHESIS_SOURCE")
        self.assertEqual(got["plans"], [])
        self.assertEqual(got["model_calls"], 0)
        self.assertFalse(got["scientific_first_use"])

    def test_pure_stable_bounded_plans_with_traceable_source_and_no_authority(self):
        before = example()
        snapshot = copy.deepcopy(before)
        first = run(before)
        self.assertEqual(first, run(before))
        self.assertEqual(before, snapshot)
        self.assertEqual(first["disposition"], "UNTESTED_ADVISORY_PLANS")
        self.assertEqual(len(first["plans"]), 3)
        self.assertEqual({p["depth"] for p in first["plans"]}, {1, 2})
        self.assertEqual(len({p["mechanism_sha256"] for p in first["plans"]}), 3)
        self.assertEqual(len({p["plan_sha256"] for p in first["plans"]}), 3)
        for p in first["plans"]:
            self.assertEqual(p["origin_event_id"], before["event_id"])
            self.assertEqual(p["parent_tree_sha"], before["parent_tree_sha"])
            self.assertEqual(p["plan_sha256"], c._digest({k:v for k,v in p.items() if k != "plan_sha256"}))
            self.assertFalse(p["novelty_verified"])
            self.assertFalse(p["scientific_first_use"])
            self.assertFalse(p["dispatch_authorized"])
            self.assertNotIn("candidate_source", p)

    def test_consumed_mechanism_is_never_reissued_on_new_receipt(self):
        first = run()["plans"]
        revised = example(event_id="terminal-original-0002",
                          evidence_sha256="e" * 64, receipt_sha256="f" * 64,
                          parent_sha="f" * 40)
        self.assertEqual([p["mechanism_sha256"] for p in run(revised)["plans"]],
                         [p["mechanism_sha256"] for p in first])
        got = run(revised, consumed=[p["mechanism_sha256"] for p in first])
        self.assertEqual(got["disposition"], "MECHANISMS_ALREADY_CONSUMED")
        self.assertEqual(got["plans"], [])

    def test_duplicate_negative_and_relabel_across_lanes_fail_closed(self):
        old = example()
        fresh_label = example(event_id="terminal-original-0002", lane="Wingless")
        self.assertEqual(run(fresh_label, history=[old])["disposition"],
                         "DUPLICATE_OR_RELABELED_EVENT")
        for event in (example(receipt_sha256="e" * 64),
                      example(evidence_sha256="e" * 64)):
            self.assertEqual(run(event, history=[old])["disposition"],
                             "DUPLICATE_OR_RELABELED_EVENT")
        with self.assertRaisesRegex(ValueError, "DUPLICATE_HISTORY"):
            run(fresh_label, history=[old, old])

    def test_invalid_custody_holdout_and_protected_authority_are_denied(self):
        for mutation in ({"partition": "sealed-holdout"},
                         {"terminal_disposition": "RUNNING"},
                         {"receipt_sha256": ""},
                         {"parent_sha": "main"},
                         {"lane": "KTRADE"},
                         {"event_id": "reused"},
                         {"schema": "untrusted"},
                         {"partition": True}):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                run(example(**mutation))
        with self.assertRaisesRegex(ValueError, "FIELDS_INVALID"):
            run({**example(), "executing": True})
        with self.assertRaises(ValueError):
            run(example(), history=[example(partition="sealed-holdout")])

    def test_unknown_class_and_disallowed_mechanism_digest(self):
        self.assertEqual(run(example(failure_class="unclassified"))["disposition"],
                         "NO_NEW_HYPOTHESIS_SOURCE")
        with self.assertRaisesRegex(ValueError, "CONSUMED_MECHANISM_INVALID"):
            run(consumed=["not-hex"])
        with self.assertRaisesRegex(ValueError, "HISTORY_BOUND_INVALID"):
            run(history=[example()] * 4097)

    def test_all_recipe_families_bounded_and_no_import_side_effects(self):
        for failure in c.RECIPES:
            with self.subTest(failure=failure):
                got = run(example(failure_class=failure))
                self.assertGreaterEqual(len(got["plans"]), 1)
                self.assertLessEqual(len(got["plans"]), 3)
                self.assertLessEqual(max(p["depth"] for p in got["plans"]), 2)
                self.assertEqual(got["paid_api_calls"], 0)
                self.assertEqual(got["accepted_ref_mutations"], 0)
        with patch("builtins.open", side_effect=AssertionError("no I/O")), \
             patch("builtins.input", side_effect=AssertionError("no prompting")):
            self.assertEqual(run()["disposition"], "UNTESTED_ADVISORY_PLANS")


if __name__ == "__main__":
    unittest.main()
