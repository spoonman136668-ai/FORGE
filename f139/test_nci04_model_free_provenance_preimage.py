"""H35: no real key, original owner or scientific results are used in these tests."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import hmac
import unittest

from f139.nci04_model_free_provenance_preimage import (
    DOMAIN, ProvenanceDenied, make_unsigned_preimage,
    verify_detached_mac_math_only,
)


def sample():
    source = "a" * 40
    native_intent = "1" * 64
    proposal = {
        "lane": "Yggdrasil",
        "controller_source_sha": source,
        "target_commit": "b" * 40,
        "target_tree_sha": "c" * 40,
        "path": "yggdrasil/public_causal_cells.py",
        "before_sha256": "0" * 64,
        "after_sha256": "9" * 64,
        "mechanism_sha256": "8" * 64,
        "dependency_sha256": "d" * 64,
        "qualification_harness_sha256": "e" * 64,
        "suite_identity_sha256": "f" * 64,
        "training_config_sha256": "3" * 64,
        "toolchain_identity": "python3.11.11",
        "frozen_split_sha256": "2" * 64,
        "scientific_first_use": False,
        "protected_holdouts_accessed": 0,
        "paid_model_calls": 0,
        "accepted_ref_mutations": 0,
        "optimizer_policy_mutations": 0,
    }
    owner = {
        "source_sha": source,
        "owner_epoch": 7,
        "native_ticket": f"f139-nci04-i1290-{source[:12]}-{native_intent[:8]}",
        "issue_number": 1290,
        "issue_id": 50001290,
        "issue_body_sha256": "4" * 64,
        "ledger_head_seq": 346,
        "ledger_head_sha256": "5" * 64,
        "ledger_history_sha256": "6" * 64,
        "ledger_history_count": 2,
    }
    native = {
        "intent_sha256": native_intent,
        "qualification_key": "7" * 64,
        "native_authorization_sha256": "a" * 64,
    }
    frozen = {
        "seeds_sha256": "b" * 64,
        "resource_budget_sha256": "c" * 64,
        "evaluation_controls_sha256": "d" * 64,
        "preregistration_sha256": "e" * 64,
    }
    return {"proposal": proposal, "owner": owner,
            "native": native, "frozen": frozen}


class FrozenLineagePreimageTests(unittest.TestCase):
    def test_repeatable_domain_separated_preimage_without_authority(self):
        sample_record = sample()
        a = make_unsigned_preimage(**sample_record)
        self.assertEqual(a, make_unsigned_preimage(**deepcopy(sample_record)))
        self.assertTrue(a.startswith(DOMAIN))
        self.assertNotIn(b"owner_hmac_key", a)
        self.assertIn(b'"dispatch_authorized":false', a)
        self.assertIn(b'"scientific_first_use":false', a)
        self.assertIn(b'"owner_identity_authenticated":false', a)

    def test_mechanism_split_owner_history_and_native_binding_all_change(self):
        base = sample()
        starting = make_unsigned_preimage(**base)
        cases = (
            ("proposal", "mechanism_sha256", "1" * 64),
            ("proposal", "frozen_split_sha256", "3" * 64),
            ("proposal", "after_sha256", "4" * 64),
            ("proposal", "target_tree_sha", "d" * 40),
            ("owner", "owner_epoch", 8),
            ("owner", "ledger_head_sha256", "c" * 64),
            ("owner", "ledger_history_sha256", "0" * 64),
            ("owner", "ledger_history_count", 3),
            ("native", "qualification_key", "0" * 64),
            ("native", "native_authorization_sha256", "0" * 64),
            ("frozen", "seeds_sha256", "a" * 64),
            ("frozen", "resource_budget_sha256", "a" * 64),
            ("frozen", "evaluation_controls_sha256", "a" * 64),
            ("frozen", "preregistration_sha256", "a" * 64),
        )
        for category, key, changed in cases:
            with self.subTest(category=category, key=key):
                other = deepcopy(base)
                other[category][key] = changed
                self.assertNotEqual(make_unsigned_preimage(**other), starting)
        # Native v26 qualification key stays the same even when science
        # mechanism/split are altered: H35 preimage correctly distinguishes.
        differing = deepcopy(base)
        differing["proposal"]["mechanism_sha256"] = "1" * 64
        differing["proposal"]["frozen_split_sha256"] = "3" * 64
        self.assertEqual(differing["native"], base["native"])
        self.assertNotEqual(make_unsigned_preimage(**differing), starting)

    def test_missing_claims_or_ticket_source_drift_fail_closed(self):
        for group, key, value in (
            ("owner", "source_sha", "b" * 40),
            ("owner", "native_ticket", "f139-nci04-i1290-fake-11111111"),
            ("owner", "ledger_head_seq", 0),
            ("owner", "owner_epoch", True),
            ("owner", "issue_number", 1291),
            ("owner", "ledger_history_count", 347),
            ("native", "intent_sha256", "2" * 64),
            ("native", "qualification_key", "broken"),
            ("proposal", "scientific_first_use", True),
            ("proposal", "paid_model_calls", 1),
            ("frozen", "seeds_sha256", "bad"),
        ):
            with self.subTest(group=group, key=key), self.assertRaises(ProvenanceDenied):
                x = sample()
                x[group][key] = value
                make_unsigned_preimage(**x)
        for group in ("owner", "native", "frozen", "proposal"):
            with self.subTest(group=group), self.assertRaises(ProvenanceDenied):
                x = sample()
                x[group].pop(next(iter(x[group])))
                make_unsigned_preimage(**x)

    def test_synthetic_detached_mac_never_authenticates_owner(self):
        preimage = make_unsigned_preimage(**sample())
        artificial_test_key = b"K" * 32  # not an owner secret or real signature
        mac = hmac.new(artificial_test_key, preimage, hashlib.sha256).hexdigest()
        evidence = verify_detached_mac_math_only(
            preimage=preimage, expected_preimage=preimage,
            detached_mac_hex=mac, verification_key=artificial_test_key)
        self.assertTrue(evidence["mac_mathematically_matches_supplied_key"])
        for key in ("original_owner_authenticated",
                    "ledger_completeness_authenticated",
                    "native_qualification_accepted", "scientific_first_use",
                    "publication_authorized", "dispatch_authorized",
                    "signed_owner_provenance_accepted"):
            self.assertIs(evidence[key], False)
        for mutation in ("mac", "key", "preimage", "expected"):
            with self.subTest(mutation=mutation), self.assertRaises(ProvenanceDenied):
                other = dict(preimage=preimage, expected_preimage=preimage,
                             detached_mac_hex=mac, verification_key=artificial_test_key)
                if mutation == "mac":
                    other["detached_mac_hex"] = "0" * 64
                elif mutation == "key":
                    other["verification_key"] = b"X" * 32
                elif mutation == "preimage":
                    other["preimage"] = preimage + b"x"
                else:
                    other["expected_preimage"] = preimage + b"x"
                verify_detached_mac_math_only(**other)



def native_synthetic_example():
    """Artificial offline test bytes. Never original owner data or signatures."""
    import base64
    import json

    from f139.nci04_native_contract import (
        SCHEMA, parse_intent,
    )

    r = sample()
    before = b"class PublicCausalCells:\n    pass\n"
    after = b"class PublicCausalCells:\n    def choose(self):\n        return 0\n"
    r["proposal"]["before_sha256"] = hashlib.sha256(before).hexdigest()
    r["proposal"]["after_sha256"] = hashlib.sha256(after).hexdigest()
    row = r["proposal"]
    intent = {
        "schema": SCHEMA,
        "controller_source_sha": row["controller_source_sha"],
        "lane": row["lane"],
        "target_repository": "spoonman136668-ai/Yggdrasil",
        "target_commit": row["target_commit"],
        "target_tree_sha": row["target_tree_sha"],
        "dependency_sha256": row["dependency_sha256"],
        "qualification_harness_sha256": row["qualification_harness_sha256"],
        "training_config_sha256": row["training_config_sha256"],
        "toolchain_identity": row["toolchain_identity"],
        "suite_identity_sha256": row["suite_identity_sha256"],
        "path": row["path"],
        "before_sha256": row["before_sha256"],
        "after_sha256": row["after_sha256"],
        "after_base64": base64.b64encode(after).decode("ascii"),
        "worker_mode": "isolated-candidate-only",
        "scientific_first_use": False,
        "paid_api_calls": 0,
        "accepted_ref_mutations": 0,
        "optimizer_policy_mutations": 0,
        "protected_holdouts_accessed": 0,
    }
    raw = json.dumps(intent, sort_keys=True,
                     separators=(",", ":")).encode("ascii")
    parsed = parse_intent(
        raw, protected_main=row["controller_source_sha"],
        target_commit=row["target_commit"],
        target_tree_sha=row["target_tree_sha"])
    r["native"]["intent_sha256"] = parsed.intent_sha256
    r["native"]["qualification_key"] = parsed.qualification_key
    r["owner"]["native_ticket"] = (
        f'f139-nci04-i{r["owner"]["issue_number"]}-'
        f'{row["controller_source_sha"][:12]}-{parsed.intent_sha256[:8]}')
    return r, raw, before


class H37NativeIntentBridgeTests(unittest.TestCase):
    def test_exact_synthetic_native_key_recomputed_without_any_authority(self):
        from f139.nci04_model_free_provenance_preimage import (
            cross_check_native_intent_math_only,
        )

        rec, raw, original = native_synthetic_example()
        report = cross_check_native_intent_math_only(
            native_intent_raw=raw, original_source_bytes=original, **rec)
        self.assertTrue(report["native_source_bytes_mathematically_consistent"])
        self.assertEqual(report["recomputed_native_qualification_key"],
                         rec["native"]["qualification_key"])
        for label in ("original_owner_authenticated",
                      "native_authorization_authenticated",
                      "original_ledger_complete_authenticated",
                      "frozen_experiment_authenticated",
                      "scientific_first_use", "native_qualification_accepted",
                      "publication_authorized", "dispatch_authorized",
                      "signed_owner_provenance_accepted"):
            self.assertIs(report[label], False)

    def test_h37_semantic_negative_changes_fail_closed(self):
        from f139.nci04_model_free_provenance_preimage import (
            cross_check_native_intent_math_only,
        )

        rec, raw, original = native_synthetic_example()
        variants = (
            ("native", "qualification_key", "e" * 64),
            ("native", "intent_sha256", "e" * 64),
            ("proposal", "before_sha256", "f" * 64),
            ("proposal", "after_sha256", "f" * 64),
            ("proposal", "target_tree_sha", "d" * 40),
            ("proposal", "path", "yggdrasil/other.py"),
            ("proposal", "dependency_sha256", "a" * 64),
            ("proposal", "training_config_sha256", "a" * 64),
            ("proposal", "suite_identity_sha256", "a" * 64),
            ("proposal", "qualification_harness_sha256", "a" * 64),
        )
        for group, key, value in variants:
            with self.subTest(group=group, key=key), self.assertRaises(ProvenanceDenied):
                other = deepcopy(rec)
                other[group][key] = value
                cross_check_native_intent_math_only(
                    native_intent_raw=raw,
                    original_source_bytes=original, **other)
        with self.assertRaises(ProvenanceDenied):
            cross_check_native_intent_math_only(
                native_intent_raw=raw, original_source_bytes=original + b"x",
                **rec)
        with self.assertRaises(ProvenanceDenied):
            cross_check_native_intent_math_only(
                native_intent_raw=raw[:-1] + b"x",
                original_source_bytes=original, **rec)

    def test_h37_mechanism_or_split_drift_is_not_externally_attested(self):
        from f139.nci04_model_free_provenance_preimage import (
            cross_check_native_intent_math_only,
        )

        rec, raw, original = native_synthetic_example()
        base = cross_check_native_intent_math_only(
            native_intent_raw=raw, original_source_bytes=original, **rec)
        for key in ("mechanism_sha256", "frozen_split_sha256"):
            altered = deepcopy(rec)
            altered["proposal"][key] = "a" * 64
            report = cross_check_native_intent_math_only(
                native_intent_raw=raw,
                original_source_bytes=original, **altered)
            self.assertEqual(
                report["recomputed_native_qualification_key"],
                base["recomputed_native_qualification_key"])
            self.assertNotEqual(
                report["unsigned_lineage_preimage_sha256"],
                base["unsigned_lineage_preimage_sha256"])
            self.assertIs(report["frozen_experiment_authenticated"], False)
            self.assertIs(report["signed_owner_provenance_accepted"], False)

if __name__ == "__main__":
    unittest.main()
