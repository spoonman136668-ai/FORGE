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


if __name__ == "__main__":
    unittest.main()
