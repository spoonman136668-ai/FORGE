"""H69 source-only integration tests; no owner/provider/real secrets."""
from __future__ import annotations

import hashlib
import json
import unittest
from copy import deepcopy

from f139.nci04_model_free_intent_bridge import (
    BridgeDenied, build_unsigned_native_intents,
)
from f139.nci04_native_contract import NativeContractError, parse_intent
from f139.test_nci04_model_free_grammar import SOURCE, S, T, TREE, META, event


def run(*, original=SOURCE, metadata=None, history=None, source_sha=None):
    return build_unsigned_native_intents(
        controller_source_sha=S, target_commit=T, target_tree_sha=TREE,
        frozen_source_sha256=(hashlib.sha256(SOURCE).hexdigest()
                              if source_sha is None else source_sha),
        original=original, metadata=META if metadata is None else metadata,
        complete_history=[] if history is None else history)


class ModelFreeNativeIntentBridgeTests(unittest.TestCase):
    def test_real_v1_contract_round_trip_without_any_authority(self):
        result = run()
        self.assertEqual(len(result["selected"]), 1)
        item = result["selected"][0]
        candidate = parse_intent(item["unsigned_intent_bytes"],
                                 protected_main=S, target_commit=T,
                                 target_tree_sha=TREE)
        self.assertEqual(candidate.intent_sha256, item["intent_sha256"])
        self.assertEqual(candidate.qualification_key,
                         item["native_qualification_key"])
        self.assertEqual(candidate.after_sha256, item["after_sha256"])
        self.assertEqual(candidate.path, "yggdrasil/public_causal_cells.py")
        self.assertNotEqual(candidate.after_bytes, SOURCE)
        self.assertTrue(candidate.after_bytes.startswith(b"class PublicCausalCells:"))
        self.assertEqual(candidate.after_bytes.count(
            b"def choose_posterior_public_cost_p"), 1)
        payload = json.loads(item["unsigned_intent_bytes"])
        self.assertEqual(payload["toolchain_identity"], "python3.11.11")
        self.assertEqual(payload["worker_mode"], "isolated-candidate-only")
        self.assertNotIn("frozen_split_sha256", payload)
        self.assertNotIn("mechanism_sha256", payload)
        for key in ("scientific_first_use", "source_identity_authenticated",
                    "complete_owner_history_authenticated", "original_owner_signed",
                    "native_qualification_accepted", "frozen_science_authenticated",
                    "dispatch_authorized", "publication_authorized",
                    "new_controller", "new_scheduler", "new_queue"):
            self.assertIs(result[key], False, key)
        self.assertEqual(result["accepted_ref_mutations"], 0)
        self.assertEqual(result["paid_model_calls"], 0)

    def test_identical_inputs_produce_identical_intent_and_no_added_authority(self):
        self.assertEqual(run(), run())
        result = run()
        self.assertEqual(result["abstentions"], [
            {"lane": "Wingless", "reason": "NO_ELIGIBLE_CANDIDATE"}])
        self.assertEqual(len(result["selected"]), 1)

    def test_negative_consumed_next_recipe_and_total_exhaustion(self):
        first = run()["selected"][0]
        history1 = [event(first, 1, "QUARANTINED")]
        second = run(history=history1)["selected"][0]
        self.assertNotEqual(first["candidate_identity"],
                            second["candidate_identity"])
        self.assertNotEqual(first["intent_sha256"], second["intent_sha256"])
        history2 = history1 + [event(second, 2, "VERIFIED")]
        exhausted = run(history=history2)
        self.assertEqual(exhausted["selected"], [])
        self.assertEqual(len(exhausted["abstentions"]), 2)

    def test_ambiguous_start_never_replays_native_intent(self):
        first = run()["selected"][0]
        for outcome in ("START_RISK", "WAIT_PROVIDER", "CONSUMED_INDETERMINATE",
                        "NEGATIVE", "QUARANTINED"):
            with self.subTest(outcome=outcome):
                nxt = run(history=[event(first, 1, outcome)])
                self.assertNotEqual(nxt["selected"][0]["intent_sha256"],
                                    first["intent_sha256"])

    def test_stale_source_or_metadata_or_event_rejected_before_intent(self):
        first = run()["selected"][0]
        evt = event(first, 1)
        for kwargs in (
            {"original": SOURCE+b"extra"},
            {"source_sha": "0"*64},
            {"metadata": dict(META, dependency_sha256="bad")},
            {"metadata": dict(META, scientific_first_use=True)},
            {"history": [evt, evt]},
            {"history": [dict(evt, seq=True)]},
            {"history": [dict(evt, outcome="UNQUALIFIED")]},
        ):
            with self.subTest(case=str(kwargs)[:60]), self.assertRaises(ValueError):
                run(**kwargs)

    def test_native_parser_refuses_unsigned_drift(self):
        item = run()["selected"][0]
        raw = item["unsigned_intent_bytes"]
        original = json.loads(raw)
        for key, value in (("target_tree_sha", "c"*39+"d"),
                           ("accepted_ref_mutations", 1),
                           ("scientific_first_use", True),
                           ("after_sha256", "f"*64)):
            with self.subTest(key=key), self.assertRaises(NativeContractError):
                bad = deepcopy(original)
                bad[key] = value
                parse_intent(json.dumps(bad, sort_keys=True,
                                        separators=(",", ":")).encode(),
                             protected_main=S, target_commit=T,
                             target_tree_sha=TREE)


    def test_h70_authentic_yggdrasil_source_to_unsigned_native_v1(self):
        """Original Git-pinned native bytes, not a synthetic Python class.

        Fixture reconstruction and source identity are independently compared
        against the GitHub original by the reviewer. Synthetic metadata in this
        test MUST NOT be interpreted as an original signed F139 approval.
        """
        import importlib
        from pathlib import Path
        from f139.nci04_model_free_grammar import method_for
        from f139.test_nci04_genuine_yggdrasil_fixture import (
            FIXTURES, ORIGINAL_SHA256,
        )

        source_variants = {}
        for name, prior, expected in FIXTURES:
            raw = Path(importlib.import_module(name).__file__).read_bytes()
            self.assertEqual(len(raw), 7439)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), expected)
            source_variants[prior] = raw
        original = source_variants[1].replace(method_for(1).encode("ascii"),
                                               b"", 1)
        self.assertEqual(len(original), 6067)
        self.assertEqual(hashlib.sha256(original).hexdigest(),
                         ORIGINAL_SHA256)
        self.assertEqual(ORIGINAL_SHA256,
                         "5e6f8a8bfd635c0117fe864f7eb33988b6db319b40dacb29ba44d5a6e2beabac")
        source_sha = "49c7b15343bea3c201fb52b498d8c0f397384afe"
        target_commit = "5e74f8db85b2f5839c42148c0dfba69a88b1a2c9"
        target_tree = "180008502f6bdfe5a06c3d0d6f47f941dd01f20b"

        def build(history):
            return build_unsigned_native_intents(
                controller_source_sha=source_sha,
                target_commit=target_commit, target_tree_sha=target_tree,
                frozen_source_sha256=ORIGINAL_SHA256, original=original,
                metadata=META, complete_history=history)

        first_plan = build([])
        self.assertEqual(first_plan, build([]))
        self.assertEqual(len(first_plan["selected"]), 1)
        first = first_plan["selected"][0]
        self.assertEqual(first["lane"], "Yggdrasil")
        parsed = parse_intent(
            first["unsigned_intent_bytes"],
            protected_main=source_sha,
            target_commit=target_commit, target_tree_sha=target_tree)
        self.assertIn(parsed.after_bytes, source_variants.values())
        self.assertEqual(hashlib.sha256(parsed.after_bytes).hexdigest(),
                         parsed.after_sha256)
        self.assertEqual(first["native_qualification_key"],
                         parsed.qualification_key)
        self.assertEqual(first["candidate_identity"] != parsed.intent_sha256,
                         True)
        self.assertNotIn("mechanism_sha256",
                         json.loads(first["unsigned_intent_bytes"]))
        self.assertNotIn("frozen_split_sha256",
                         json.loads(first["unsigned_intent_bytes"]))
        for flag in ("original_owner_signed", "dispatch_authorized",
                     "publication_authorized", "scientific_first_use",
                     "frozen_science_authenticated",
                     "source_identity_authenticated",
                     "complete_owner_history_authenticated"):
            self.assertIs(first_plan[flag], False)

        # Synthetic history exercises consumption, never original owner custody.
        consumed = event(first, 1, "CONSUMED_INDETERMINATE")
        second_plan = build([consumed])
        self.assertEqual(len(second_plan["selected"]), 1)
        second = second_plan["selected"][0]
        self.assertNotEqual(second["intent_sha256"], first["intent_sha256"])
        second_native = parse_intent(second["unsigned_intent_bytes"],
                                     protected_main=source_sha,
                                     target_commit=target_commit,
                                     target_tree_sha=target_tree)
        self.assertIn(second_native.after_bytes, source_variants.values())
        self.assertNotEqual(parsed.after_bytes, second_native.after_bytes)
        consumed_second = event(second, 2, "QUARANTINED")
        exhausted = build([consumed, consumed_second])
        self.assertEqual(exhausted["selected"], [])
        self.assertEqual(len(exhausted["abstentions"]), 2)
        with self.assertRaises(ValueError):
            build_unsigned_native_intents(
                controller_source_sha=source_sha,
                target_commit=target_commit, target_tree_sha=target_tree,
                frozen_source_sha256=ORIGINAL_SHA256,
                original=original + b"\n# unapproved delta\n",
                metadata=META, complete_history=[])



if __name__ == "__main__":
    unittest.main()
