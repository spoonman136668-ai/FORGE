"""Offline source-only falsification for the finite model-free source grammar."""
from __future__ import annotations

import hashlib
import unittest

from f139.nci04_model_free_grammar import (
    GrammarDenied, generate, method_for,
)

SOURCE = b'''class PublicCausalCells:
    def __init__(self):
        self._counts = [[[0, 0] for _ in range(2)] for _ in range(16)]

    def _address(self, address, retained):
        if type(address) is not int or address < 0 or address >= 7:
            raise ValueError("ADDRESS")
        return address

    def choose(self, address, *, retained=False):
        return None

    def snapshot(self) -> bytes:
        return b"unchanged"
'''
SHA = lambda c: c * 64
S = "a" * 40
T = "b" * 40
TREE = "c" * 40
META = {
    "dependency_sha256": SHA("d"),
    "qualification_harness_sha256": SHA("e"),
    "suite_identity_sha256": SHA("f"),
    "training_config_sha256": SHA("1"),
    "frozen_split_sha256": SHA("2"),
}


def run(*, original=SOURCE, history=None, metadata=None, frozen=None):
    return generate(controller_source_sha=S, target_commit=T,
                    target_tree_sha=TREE,
                    frozen_source_sha256=frozen or hashlib.sha256(SOURCE).hexdigest(),
                    original=original, metadata=META if metadata is None else metadata,
                    complete_history=[] if history is None else history)


def event(item, seq, outcome="QUARANTINED"):
    return {
        "seq": seq, "event_sha256": SHA("3" if seq == 1 else "4"),
        "controller_source_sha": S,
        "lane": item["lane"],
        "candidate_identity": item["candidate_identity"],
        "mechanism_sha256": item["mechanism_sha256"],
        "outcome": outcome, "evidence_sha256": SHA("5"),
    }


class ModelFreeGrammarTests(unittest.TestCase):
    def test_immutable_source_generates_only_one_selected_candidate(self):
        x = run()
        self.assertEqual(x["generated_recipe_count"], 2)
        self.assertEqual(len(x["selected"]), 1)
        self.assertEqual(x["selected"][0]["lane"], "Yggdrasil")
        self.assertEqual(x["abstentions"], [
            {"lane": "Wingless", "reason": "NO_ELIGIBLE_CANDIDATE"}])
        self.assertEqual(list(x["source_by_candidate_id"]), [
            x["selected"][0]["candidate_identity"]])
        self.assertFalse(x["publication_authorized"])
        self.assertFalse(x["dispatch_authorized"])
        self.assertFalse(x["scientific_first_use"])
        self.assertFalse(x["new_controller"])
        self.assertFalse(x["new_scheduler"])
        self.assertFalse(x["new_queue"])
        self.assertEqual(x["source_authentication"], "EXTERNAL_OWNER_REQUIRED")
        self.assertEqual(x["qualification"], "NOT_RUN_NOT_ACCEPTED")

    def test_immutable_byte_for_byte_result_on_repeat(self):
        self.assertEqual(run(), run())
        x = run()
        src = list(x["source_by_candidate_id"].values())[0]
        self.assertIs(type(src), bytes)
        self.assertNotEqual(src, SOURCE)
        self.assertEqual(src.count(b"def choose_posterior_public_cost_p"), 1)
        self.assertIn(b"def snapshot(self)", src)
        self.assertIn(b'def choose(self, address', src)

    def test_negative_consumed_then_other_recipe_then_exhaustion(self):
        first = run()
        consumed = event(first["selected"][0], 1, "NEGATIVE")
        second = run(history=[consumed])
        self.assertEqual(len(second["selected"]), 1)
        self.assertNotEqual(first["selected"][0]["candidate_identity"],
                            second["selected"][0]["candidate_identity"])
        second_event = event(second["selected"][0], 2, "VERIFIED")
        exhausted = run(history=[consumed, second_event])
        self.assertEqual(exhausted["selected"], [])
        self.assertEqual(len(exhausted["abstentions"]), 2)
        self.assertEqual(exhausted["source_by_candidate_id"], {})

    def test_ambiguous_and_quarantine_no_replay(self):
        first = run()
        for outcome in ("QUARANTINED", "START_RISK", "WAIT_PROVIDER",
                        "CONSUMED_INDETERMINATE"):
            with self.subTest(outcome=outcome):
                x = run(history=[event(first["selected"][0], 1, outcome)])
                self.assertEqual(len(x["selected"]), 1)
                self.assertNotEqual(x["selected"], first["selected"])

    def test_bad_or_missing_history_fails_closed(self):
        first = run()
        good = event(first["selected"][0], 1)
        for bad in (
            [good, good],
            [dict(good, outcome="UNKNOWN")],
            [dict(good, event_sha256="")],
            [dict(good, seq=True)],
            [dict(good, auth="unknown")],
        ):
            with self.subTest(bad=bad), self.assertRaises(GrammarDenied):
                run(history=bad)

    def test_source_drift_and_invalid_source_shape_reject(self):
        for source in (
            SOURCE + b"\n# untracked edit\n",
            SOURCE.replace(b"PublicCausalCells", b"WrongCells"),
            SOURCE.replace(b"    def snapshot(self) -> bytes:\n", b""),
            SOURCE.replace(b"    def choose(self, address", b"    def renamed(self, address"),
            b"def broken(:\n" + SOURCE,
        ):
            with self.subTest(source=source[:50]), self.assertRaises(GrammarDenied):
                run(original=source, frozen=hashlib.sha256(source).hexdigest()
                    if source != SOURCE + b"\n# untracked edit\n"
                    else hashlib.sha256(SOURCE).hexdigest())

    def test_metadata_authority_and_source_pin_reject(self):
        for metadata in (
            dict(META, scientific_first_use=True),
            dict(META, frozen_split_sha256="bad"),
            {k: v for k, v in META.items() if k != "dependency_sha256"},
            dict(META, paid_model_calls=1),
        ):
            with self.subTest(metadata=metadata), self.assertRaises(GrammarDenied):
                run(metadata=metadata)
        with self.assertRaisesRegex(GrammarDenied, "SOURCE_BYTES_NOT_PINNED"):
            run(frozen=SHA("0"))

    def test_bounded_exact_arithmetic_and_no_memory_mutation(self):
        for prior in (1, 2):
            with self.subTest(prior=prior):
                namespace = {}
                exec(SOURCE.decode().replace(
                    "    def snapshot(self) -> bytes:\n",
                    method_for(prior) + "    def snapshot(self) -> bytes:\n"),
                    namespace)
                cells = namespace["PublicCausalCells"]()
                method = getattr(cells, f"choose_posterior_public_cost_p{prior}")
                self.assertIsNone(method(0, 0, 0))  # no observed evidence
                cells._counts[0][0] = [1, 4]
                cells._counts[0][1] = [4, 1]
                checkpoint = cells.snapshot()
                self.assertEqual(method(0, 0, 0, reward_value=10), 0)
                self.assertEqual(method(0, 10, 0, reward_value=1), 1)
                self.assertEqual(cells.snapshot(), checkpoint)
                for args in ((False, 0), (0, True), (-1, 0), (0, 65536)):
                    with self.assertRaises(ValueError):
                        method(0, *args)
                with self.assertRaises(ValueError):
                    method(0, 0, 0, reward_value=True)
                with self.assertRaises(ValueError):
                    method(0, 0, 0, reward_value=0)

    def test_unknown_recipe_prior_rejected(self):
        for value in (0, 3, True, -1, 1.0):
            with self.subTest(value=value), self.assertRaises(GrammarDenied):
                method_for(value)


if __name__ == "__main__":
    unittest.main()
