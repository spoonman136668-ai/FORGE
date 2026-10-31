"""H72 original-publisher format shadow; zero owner/provider activity."""
from __future__ import annotations

import hashlib
import importlib
import json
import unittest
from pathlib import Path

from f139.nci04_model_free_owner_response_shadow import (
    OwnerResponseShadowDenied, encode_owner_response_shadow,
    validate_research_lineage,
)
from f139.nci04_model_proposal import ProposalDenied, validate
from f139.nci04_native_contract import parse_intent
from f139.test_nci04_model_free_grammar import SOURCE, S, T, TREE, META as GRAMMAR_META, event
from f139.nci04_model_free_intent_bridge import build_unsigned_native_intents
from f139.nci04_genuine_yggdrasil_p1_fixture import PublicCausalCells
from f139.test_nci04_genuine_yggdrasil_fixture import (
    FIXTURES, ORIGINAL_SHA256,
)
from f139.nci04_model_free_grammar import method_for
from f139.nci04_autonomy_feed import _semantic_identities

TEST_META = {
    **_semantic_identities(S, "Yggdrasil", TREE, "yggdrasil/public_causal_cells.py"),
    "frozen_split_sha256": GRAMMAR_META["frozen_split_sha256"],
}

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
        metadata=TEST_META if metadata is None else metadata,
        complete_history=[] if history is None else history,
        owner_history_sha256=owner_hash,
        owner_consumed_candidates=set() if consumed is None else consumed,
        owner_consumed_after_hashes=set() if afters is None else afters)


class OwnerResponseShadowTests(unittest.TestCase):
    def test_owner_semantic_metadata_drift_rejects_before_candidate_generation(self):
        bad = dict(TEST_META, dependency_sha256="8" * 64)
        with self.assertRaisesRegex(
                OwnerResponseShadowDenied, "OWNER_SEMANTIC_IDENTITIES_MISMATCH"):
            run(metadata=bad)
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
            original=SOURCE, metadata=TEST_META, complete_history=[])
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
            original=SOURCE, metadata=TEST_META, complete_history=history)
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


    def test_h76_first_negative_allows_distinct_second_only_with_explicit_history(self):
        """Replay barrier remains intact across frontier and owner identity schemas.

        All records are synthetic and externally supplied; this test does not
        certify their origin as an authentic original-owner SQLite history.
        """
        first_bridge = build_unsigned_native_intents(
            controller_source_sha=S, target_commit=T, target_tree_sha=TREE,
            frozen_source_sha256=hashlib.sha256(SOURCE).hexdigest(),
            original=SOURCE, metadata=TEST_META, complete_history=[])
        first = run()["selected"][0]
        self.assertEqual(first_bridge["selected"][0]["candidate_identity"],
                         first["frontier_candidate_identity"])
        negative = event(first_bridge["selected"][0], 1, "QUARANTINED")
        original_ids = {first["owner_candidate_identity"]}
        original_afters = {first["after_sha256"]}
        second = run(history=[negative], consumed=original_ids,
                     afters=original_afters)
        self.assertEqual(len(second["selected"]), 1)
        later = second["selected"][0]
        self.assertNotEqual(first["frontier_candidate_identity"],
                            later["frontier_candidate_identity"])
        self.assertNotEqual(first["owner_candidate_identity"],
                            later["owner_candidate_identity"])
        self.assertNotEqual(first["after_sha256"], later["after_sha256"])
        checked = validate(
            later["model_response_bytes"], lane="Yggdrasil",
            target_commit=T, path="yggdrasil/public_causal_cells.py",
            before=SOURCE, before_sha256=hashlib.sha256(SOURCE).hexdigest(),
            history_sha256=OWNER_HEAD,
            consumed_candidates=original_ids,
            consumed_after_hashes=original_afters)
        self.assertEqual(checked["record"]["candidate_identity"],
                         later["owner_candidate_identity"])
        self.assertEqual(checked["record"]["after_sha256"],
                         later["after_sha256"])
        self.assertFalse(second["publication_authorized"])
        self.assertFalse(second["original_single_owner_witnessed"])
        self.assertFalse(second["scientific_first_use"])

    def test_h76_second_original_owner_consumption_rejects_without_fallback(self):
        first = run()["selected"][0]
        initial = build_unsigned_native_intents(
            controller_source_sha=S, target_commit=T, target_tree_sha=TREE,
            frozen_source_sha256=hashlib.sha256(SOURCE).hexdigest(),
            original=SOURCE, metadata=TEST_META, complete_history=[])
        negative = event(initial["selected"][0], 1, "NEGATIVE")
        successor = run(history=[negative])["selected"][0]
        for pair in (
            {"consumed": {successor["owner_candidate_identity"]}},
            {"afters": {successor["after_sha256"]}},
        ):
            with self.subTest(pair=pair), self.assertRaisesRegex(
                    OwnerResponseShadowDenied, "ORIGINAL_OWNER_CONSUMED_NO_REPLAY"):
                run(history=[negative], **pair)
        # A complete frontier history explicitly consuming both proposals
        # exhausts the finite grammar; no third recipe or worker is invented.
        succ_bridge = build_unsigned_native_intents(
            controller_source_sha=S, target_commit=T, target_tree_sha=TREE,
            frozen_source_sha256=hashlib.sha256(SOURCE).hexdigest(),
            original=SOURCE, metadata=TEST_META, complete_history=[negative])
        complete = [negative, event(succ_bridge["selected"][0], 2, "VERIFIED")]
        result = run(
            history=complete,
            consumed={first["owner_candidate_identity"],
                      successor["owner_candidate_identity"]},
            afters={first["after_sha256"], successor["after_sha256"]})
        self.assertEqual(result["selected"], [])
        self.assertEqual(len(result["abstentions"]), 2)
        self.assertFalse(result["original_owner_publication_performed"])
        self.assertFalse(result["dispatch_authorized"])


    def test_h77_pinned_original_yggdrasil_two_recipe_succession(self):
        """Independent frozen source bytes, two finite recipes, no science claim."""
        variants = {}
        for module, prior, sha in FIXTURES:
            raw = Path(importlib.import_module(module).__file__).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), sha)
            variants[prior] = raw
        original = variants[1].replace(method_for(1).encode("ascii"), b"", 1)
        self.assertEqual(hashlib.sha256(original).hexdigest(), ORIGINAL_SHA256)
        source = "49c7b15343bea3c201fb52b498d8c0f397384afe"
        target = "5e74f8db85b2f5839c42148c0dfba69a88b1a2c9"
        tree = "180008502f6bdfe5a06c3d0d6f47f941dd01f20b"
        args = dict(original=original, controller=source,
                    target=target, tree=tree)
        first = run(**args)["selected"][0]
        first_source = json.loads(first["model_response_bytes"])["candidate_source"]
        self.assertIn(first_source.encode(), variants.values())
        initial = build_unsigned_native_intents(
            controller_source_sha=source, target_commit=target,
            target_tree_sha=tree, frozen_source_sha256=ORIGINAL_SHA256,
            original=original, metadata=TEST_META, complete_history=[])
        negative = event(initial["selected"][0], 1, "QUARANTINED")
        negative["controller_source_sha"] = source
        ids, afters = {first["owner_candidate_identity"]}, {first["after_sha256"]}
        second = run(history=[negative], consumed=ids, afters=afters,
                     **args)["selected"][0]
        self.assertNotEqual(second["after_sha256"], first["after_sha256"])
        second_bytes = json.loads(second["model_response_bytes"])[
            "candidate_source"].encode()
        self.assertIn(second_bytes, variants.values())
        self.assertNotEqual(second_bytes, first_source.encode())
        checked = validate(
            second["model_response_bytes"], lane="Yggdrasil",
            target_commit=target, path="yggdrasil/public_causal_cells.py",
            before=original, before_sha256=ORIGINAL_SHA256,
            history_sha256=OWNER_HEAD, consumed_candidates=ids,
            consumed_after_hashes=afters)
        self.assertEqual(checked["record"]["candidate_identity"],
                         second["owner_candidate_identity"])
        succ = build_unsigned_native_intents(
            controller_source_sha=source, target_commit=target,
            target_tree_sha=tree, frozen_source_sha256=ORIGINAL_SHA256,
            original=original, metadata=TEST_META, complete_history=[negative])
        verified = event(succ["selected"][0], 2, "VERIFIED")
        verified["controller_source_sha"] = source
        empty = run(history=[negative, verified],
                    consumed=ids | {second["owner_candidate_identity"]},
                    afters=afters | {second["after_sha256"]}, **args)
        self.assertEqual(empty["selected"], [])
        self.assertFalse(empty["original_owner_signed"])
        self.assertFalse(empty["scientific_first_use"])


    def test_h78_advisory_lineage_binds_split_and_mechanism_beyond_native_v1(self):
        x = run()
        self.assertEqual(len(x["selected"]), 1)
        first = x["selected"][0]
        line = first["research_lineage_record"]
        self.assertEqual(line["schema"], "forge.f139.model-free-research-lineage.v1")
        self.assertEqual(line["mechanism_sha256"], first["mechanism_sha256"])
        self.assertEqual(line["frozen_split_sha256"], TEST_META["frozen_split_sha256"])
        self.assertEqual(line["owner_history_sha256"], OWNER_HEAD)
        self.assertEqual(line["frontier_candidate_identity"],
                         first["frontier_candidate_identity"])
        self.assertEqual(line["owner_candidate_identity"],
                         first["owner_candidate_identity"])
        self.assertEqual(first["research_lineage_sha256"],
                         hashlib.sha256(json.dumps(
                             line, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True).encode("ascii")).hexdigest())
        self.assertIs(first["research_lineage_authenticated"], False)
        self.assertIs(first["native_v1_scientific_lineage_bound"], False)
        # Frontier selection itself hashes the split: a changed split may
        # choose the *other* recipe. Compare the same native candidate before
        # concluding its V1 qualifier lacks scientific lineage.
        second, selected_split = None, None
        for digit in "3456789abcdef0":
            candidate_split = digit * 64
            possible = run(metadata=dict(TEST_META,
                         frozen_split_sha256=candidate_split))["selected"][0]
            if possible["after_sha256"] == first["after_sha256"]:
                second, selected_split = possible, candidate_split
                break
        self.assertIsNotNone(second, "SAME_RECIPE_SPLIT_CONTROL_NOT_FOUND")
        # Exact source and V1 qualifier match, but their split lineage differs.
        self.assertEqual(first["native_qualification_key"],
                         second["native_qualification_key"])
        self.assertEqual(first["native_intent_sha256"],
                         second["native_intent_sha256"])
        self.assertEqual(first["model_response_sha256"],
                         second["model_response_sha256"])
        self.assertNotEqual(first["research_lineage_sha256"],
                            second["research_lineage_sha256"])
        self.assertEqual(second["research_lineage_record"]["frozen_split_sha256"],
                         selected_split)
        moved_history = run(owner_hash="8" * 64)["selected"][0]
        self.assertEqual(first["native_qualification_key"],
                         moved_history["native_qualification_key"])
        self.assertNotEqual(first["research_lineage_sha256"],
                            moved_history["research_lineage_sha256"])

    def test_h78_lineage_follows_finite_successor_without_claiming_custody(self):
        first = run()["selected"][0]
        initial = build_unsigned_native_intents(
            controller_source_sha=S, target_commit=T, target_tree_sha=TREE,
            frozen_source_sha256=hashlib.sha256(SOURCE).hexdigest(),
            original=SOURCE, metadata=TEST_META, complete_history=[])
        negative = event(initial["selected"][0], 1, "QUARANTINED")
        second = run(history=[negative],
                     consumed={first["owner_candidate_identity"]},
                     afters={first["after_sha256"]})["selected"][0]
        l0, l1 = first["research_lineage_record"], second["research_lineage_record"]
        self.assertNotEqual(first["research_lineage_sha256"],
                            second["research_lineage_sha256"])
        self.assertNotEqual(l0["mechanism_sha256"], l1["mechanism_sha256"])
        self.assertNotEqual(l0["after_sha256"], l1["after_sha256"])
        self.assertNotEqual(l0["frontier_history_sha256"],
                            l1["frontier_history_sha256"])
        self.assertEqual(l1["frozen_split_sha256"], TEST_META["frozen_split_sha256"])
        self.assertIs(second["research_lineage_authenticated"], False)
        self.assertIs(second["native_v1_scientific_lineage_bound"], False)
        self.assertIs(run(history=[negative])["publication_authorized"], False)


    def test_h79_lineage_validator_roundtrips_and_preserves_non_authority(self):
        item = run()["selected"][0]
        line = item["research_lineage_record"]
        checked = validate_research_lineage(
            record=line, declared_sha256=item["research_lineage_sha256"],
            model_response_sha256=item["model_response_sha256"],
            native_intent_sha256=item["native_intent_sha256"],
            native_qualification_key=item["native_qualification_key"],
            after_sha256=item["after_sha256"],
            frontier_candidate_identity=item["frontier_candidate_identity"],
            owner_candidate_identity=item["owner_candidate_identity"],
            controller_source_sha=S, target_commit=T, target_tree_sha=TREE,
            mechanism_sha256=item["mechanism_sha256"],
            frozen_split_sha256=item["frozen_split_sha256"],
            owner_history_sha256=OWNER_HEAD,
            before_sha256=hashlib.sha256(SOURCE).hexdigest(),
            dependency_sha256=TEST_META["dependency_sha256"],
            qualification_harness_sha256=TEST_META["qualification_harness_sha256"],
            suite_identity_sha256=TEST_META["suite_identity_sha256"],
            training_config_sha256=TEST_META["training_config_sha256"],
            frontier_history_sha256=line["frontier_history_sha256"])
        self.assertEqual(checked["record"], line)
        self.assertTrue(checked["self_consistency_verified"])
        for key in ("source_identity_authenticated",
                    "frozen_science_authenticated", "owner_history_authenticated",
                    "scientific_first_use", "publication_authorized",
                    "dispatch_authorized"):
            self.assertIs(checked[key], False, key)

    def test_h79_lineage_validator_rejects_tamper_even_with_rehashed_claims(self):
        item = run()["selected"][0]
        line = item["research_lineage_record"]
        args = dict(
            record=line, declared_sha256=item["research_lineage_sha256"],
            model_response_sha256=item["model_response_sha256"],
            native_intent_sha256=item["native_intent_sha256"],
            native_qualification_key=item["native_qualification_key"],
            after_sha256=item["after_sha256"],
            frontier_candidate_identity=item["frontier_candidate_identity"],
            owner_candidate_identity=item["owner_candidate_identity"],
            controller_source_sha=S, target_commit=T, target_tree_sha=TREE,
            mechanism_sha256=item["mechanism_sha256"],
            frozen_split_sha256=item["frozen_split_sha256"],
            owner_history_sha256=OWNER_HEAD,
            before_sha256=hashlib.sha256(SOURCE).hexdigest(),
            dependency_sha256=TEST_META["dependency_sha256"],
            qualification_harness_sha256=TEST_META["qualification_harness_sha256"],
            suite_identity_sha256=TEST_META["suite_identity_sha256"],
            training_config_sha256=TEST_META["training_config_sha256"],
            frontier_history_sha256=line["frontier_history_sha256"])
        bad = dict(line, mechanism_sha256="8"*64)
        import hashlib as _hashlib
        import json as _json
        with self.assertRaisesRegex(OwnerResponseShadowDenied,
                                    "RESEARCH_LINEAGE_DIGEST_INVALID"):
            validate_research_lineage(**dict(args, record=bad))
        # Rehashing tampered content does not make it match the candidate or
        # owner response the caller actually supplied.
        bad_hash = _hashlib.sha256(_json.dumps(
            bad, sort_keys=True, separators=(",", ":"),
            ensure_ascii=True).encode("ascii")).hexdigest()
        with self.assertRaisesRegex(OwnerResponseShadowDenied,
                                    "RESEARCH_LINEAGE_RESPONSE_LINK_MISMATCH"):
            validate_research_lineage(**dict(args, record=bad,
                                              declared_sha256=bad_hash))
        for field, value in (("scientific_first_use", True),
                             ("unexpected_authority", True)):
            changed = dict(line, **{field: value})
            changed_hash = _hashlib.sha256(_json.dumps(
                changed, sort_keys=True, separators=(",", ":"),
                ensure_ascii=True).encode("ascii")).hexdigest()
            with self.subTest(field=field), self.assertRaises(
                    OwnerResponseShadowDenied):
                validate_research_lineage(**dict(args, record=changed,
                                                  declared_sha256=changed_hash))


    def test_h79_lineage_validator_rejects_external_baseline_split_and_history_drift(self):
        item = run()["selected"][0]
        line = item["research_lineage_record"]
        args = dict(
            record=line, declared_sha256=item["research_lineage_sha256"],
            model_response_sha256=item["model_response_sha256"],
            native_intent_sha256=item["native_intent_sha256"],
            native_qualification_key=item["native_qualification_key"],
            after_sha256=item["after_sha256"],
            frontier_candidate_identity=item["frontier_candidate_identity"],
            owner_candidate_identity=item["owner_candidate_identity"],
            controller_source_sha=S, target_commit=T, target_tree_sha=TREE,
            mechanism_sha256=item["mechanism_sha256"],
            frozen_split_sha256=item["frozen_split_sha256"],
            owner_history_sha256=OWNER_HEAD,
            before_sha256=hashlib.sha256(SOURCE).hexdigest(),
            dependency_sha256=TEST_META["dependency_sha256"],
            qualification_harness_sha256=TEST_META["qualification_harness_sha256"],
            suite_identity_sha256=TEST_META["suite_identity_sha256"],
            training_config_sha256=TEST_META["training_config_sha256"],
            frontier_history_sha256=line["frontier_history_sha256"])
        for key, wrong in (
            ("before_sha256", "1"*64),
            ("frozen_split_sha256", "9"*64),
            ("dependency_sha256", "3"*64),
            ("qualification_harness_sha256", "4"*64),
            ("suite_identity_sha256", "5"*64),
            ("training_config_sha256", "6"*64),
            ("frontier_history_sha256", "7"*64),
            ("owner_history_sha256", "8"*64),
        ):
            with self.subTest(key=key):
                self.assertNotEqual(wrong, args[key], "negative sentinel must differ from fixture")
                with self.assertRaisesRegex(
                        OwnerResponseShadowDenied, "RESEARCH_LINEAGE_RESPONSE_LINK_MISMATCH"):
                    validate_research_lineage(**dict(args, **{key: wrong}))


if __name__ == "__main__":
    unittest.main()
