"""H72 original-publisher format shadow; zero owner/provider activity."""
from __future__ import annotations

import hashlib
import importlib
import json
import unittest
from pathlib import Path

from f139.nci04_model_free_owner_response_shadow import (
    OwnerResponseShadowDenied, encode_owner_response_shadow,
)
from f139.nci04_model_proposal import ProposalDenied, validate
from f139.nci04_native_contract import parse_intent
from f139.test_nci04_model_free_grammar import SOURCE, S, T, TREE, META, event
from f139.nci04_model_free_intent_bridge import build_unsigned_native_intents
from f139.nci04_genuine_yggdrasil_p1_fixture import PublicCausalCells
from f139.test_nci04_genuine_yggdrasil_fixture import (
    FIXTURES, ORIGINAL_SHA256,
)
from f139.nci04_model_free_grammar import method_for

OWNER_HEAD = "7" * 64


def run(*, original=SOURCE, metadata=None, history=None, owner_hash=OWNER_HEAD,
        consumed=None, afters=None, before=None, controller=S,
        target=T, tree=TREE):
    return encode_owner_response_shadow(
        controller_source_sha=controller,
        target_commit=target, target_tree_sha=tree,
        frozen_source_sha256=(hashlib.sha256(original).hexdigest()
                              if before is None else before),
        original=original,
        metadata=META if metadata is None else metadata,
        complete_history=[] if history is None else history,
        owner_history_sha256=owner_hash,
        owner_consumed_candidates=set() if consumed is None else consumed,
        owner_consumed_after_hashes=set() if afters is None else afters)


class OwnerResponseShadowTests(unittest.TestCase):
    def test_roundtrip_through_existing_owner_model_validator(self):
        x = run()
        self.assertEqual(len(x["selected"]), 1)
        a = x["selected"][0]
        d = json.loads(a["model_response_bytes"])
        self.assertEqual(d["schema"], "forge.f139.model-proposal.v1")
        self.assertEqual(d["history_sha256"], OWNER_HEAD)
        checked = validate(a["model_response_bytes"],
                           lane="Yggdrasil", target_commit=T,
                           path="yggdrasil/public_causal_cells.py",
                           before=SOURCE,
                           before_sha256=hashlib.sha256(SOURCE).hexdigest(),
                           history_sha256=OWNER_HEAD,
                           consumed_candidates=set(), consumed_after_hashes=set())
        self.assertEqual(checked["record"]["candidate_identity"],
                         a["owner_candidate_identity"])
        self.assertEqual(checked["record"]["after_sha256"], a["after_sha256"])
        self.assertNotEqual(a["owner_candidate_identity"],
                            a["frontier_candidate_identity"])
        self.assertFalse(checked["record"]["publication_authorized"])

    def test_signed_dispatch_and_publication_all_false(self):
        x = run()
        for k in ("source_identity_authenticated",
                  "complete_owner_history_authenticated",
                  "owner_consumption_sets_authenticated",
                  "original_single_owner_witnessed", "original_owner_signed",
                  "original_owner_publication_performed",
                  "owner_v3_dispatch_authorized", "publication_authorized",
                  "dispatch_authorized", "scientific_first_use",
                  "new_controller", "new_scheduler", "new_queue"):
            self.assertIs(x[k], False, k)
        self.assertEqual(x["paid_model_calls"], 0)
        self.assertEqual(x["accepted_ref_mutations"], 0)
        self.assertEqual(run(), x)

    def test_legacy_owner_consumption_never_falls_through_to_other_prior(self):
        first = run()["selected"][0]
        for supplied in ({"consumed": {first["owner_candidate_identity"]}},
                         {"afters": {first["after_sha256"]}}):
            with self.subTest(supplied=supplied), self.assertRaisesRegex(
                    OwnerResponseShadowDenied, "ORIGINAL_OWNER_CONSUMED_NO_REPLAY"):
                run(**supplied)

    def test_frontier_consumption_generates_distinct_legacy_candidate(self):
        a = run()["selected"][0]
        # Different schemas: frontier history IDs must never be silently used
        # as original owner PR candidate IDs.
        bridge = build_unsigned_native_intents(
            controller_source_sha=S, target_commit=T, target_tree_sha=TREE,
            frozen_source_sha256=hashlib.sha256(SOURCE).hexdigest(),
            original=SOURCE, metadata=META, complete_history=[])
        self.assertEqual(bridge["selected"][0]["candidate_identity"],
                         a["frontier_candidate_identity"])
        history = [event(bridge["selected"][0], 1, "START_RISK")]
        b = run(history=history)["selected"][0]
        self.assertNotEqual(a["model_response_sha256"],
                            b["model_response_sha256"])
        self.assertNotEqual(a["owner_candidate_identity"],
                            b["owner_candidate_identity"])
        second = build_unsigned_native_intents(
            controller_source_sha=S, target_commit=T, target_tree_sha=TREE,
            frozen_source_sha256=hashlib.sha256(SOURCE).hexdigest(),
            original=SOURCE, metadata=META, complete_history=history)
        exhausted = run(history=history+[event(second["selected"][0], 2, "QUARANTINED")])
        self.assertEqual(exhausted["selected"], [])
        self.assertEqual(len(exhausted["abstentions"]), 2)

    def test_owner_history_binding_not_inferred_from_frontier(self):
        a = run()["selected"][0]
        b = run(owner_hash="8"*64)["selected"][0]
        self.assertNotEqual(a["model_response_sha256"], b["model_response_sha256"])
        self.assertEqual(a["after_sha256"], b["after_sha256"])
        with self.assertRaisesRegex(OwnerResponseShadowDenied,
                                    "OWNER_HISTORY_DIGEST_MISSING"):
            run(owner_hash="invalid")

    def test_model_validator_rejects_identity_and_consumption_drift(self):
        a = run()["selected"][0]
        for kwargs in (
            {"history_sha256": "8"*64},
            {"target_commit": "f"*40},
            {"consumed_candidates": {a["owner_candidate_identity"]}},
            {"consumed_after_hashes": {a["after_sha256"]}},
        ):
            args = dict(
                lane="Yggdrasil", target_commit=T,
                path="yggdrasil/public_causal_cells.py",
                before=SOURCE, before_sha256=hashlib.sha256(SOURCE).hexdigest(),
                history_sha256=OWNER_HEAD,
                consumed_candidates=set(), consumed_after_hashes=set())
            args.update(kwargs)
            with self.subTest(kwargs=kwargs), self.assertRaises(ProposalDenied):
                validate(a["model_response_bytes"], **args)

    def test_invalid_owner_consumption_types_reject(self):
        cases=({"consumed": ["1"*64]}, {"afters": {"bad"}},
               {"consumed": {True}}, {"afters": {"2"*64, "n"*64}})
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                run(**case)

    def test_genuine_git_pinned_yggdrasil_baseline_and_frozen_variants(self):
        variants={}
        for path, prior, source_hash in FIXTURES:
            raw=Path(importlib.import_module(path).__file__).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),source_hash)
            variants[prior]=raw
        base=variants[1].replace(method_for(1).encode("ascii"), b"", 1)
        self.assertEqual(len(base), 6067)
        self.assertEqual(hashlib.sha256(base).hexdigest(), ORIGINAL_SHA256)
        x = run(original=base, controller="49c7b15343bea3c201fb52b498d8c0f397384afe",
                target="5e74f8db85b2f5839c42148c0dfba69a88b1a2c9",
                tree="180008502f6bdfe5a06c3d0d6f47f941dd01f20b")
        self.assertEqual(len(x["selected"]), 1)
        raw=x["selected"][0]["model_response_bytes"]
        d=json.loads(raw)
        self.assertIn(d["candidate_source"].encode("utf-8"), variants.values())
        self.assertEqual(x["selected"][0]["after_sha256"],
                         hashlib.sha256(d["candidate_source"].encode()).hexdigest())
        self.assertFalse(x["original_owner_signed"])
        self.assertFalse(x["scientific_first_use"])


if __name__ == "__main__":
    unittest.main()
