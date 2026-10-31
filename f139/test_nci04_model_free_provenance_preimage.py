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


if __name__ == "__main__":
    unittest.main()
