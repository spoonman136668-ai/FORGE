"""Unit and negative-control tests for nci04_fresh_owner_source_forward_v3."""
from __future__ import annotations

import unittest

from f139.nci04_fresh_owner_source_forward_v2 import FIELDS
from f139.nci04_fresh_owner_source_forward_v3 import (
    NAME, PREVIOUS_NAME, PREVIOUS_OWNER_MAIN, PR_FLOOR, SCHEMA,
    ForwardV3Denied, sign,
)


class ForwardV3ContractTests(unittest.TestCase):
    def test_v3_constants_and_hmac_domain_separation(self):
        self.assertEqual(SCHEMA, "forge.f139.fresh-original-owner-source-forward.v3")
        self.assertEqual(NAME, "fresh-original-owner-source-forward-v3.json")
        self.assertEqual(PREVIOUS_NAME, "fresh-original-owner-source-forward-v2.json")
        self.assertEqual(PREVIOUS_OWNER_MAIN, "32c8d3fcad7209d4331595a7fbad42d361a55b94")
        self.assertGreaterEqual(PR_FLOOR, 1894)

        unsigned = {
            "schema": SCHEMA,
            "admission_source_sha": "a" * 40,
            "worker_release_sha": "b" * 40,
            "previous_certificate_sha256": "c" * 64,
            "previous_owner_source_sha": PREVIOUS_OWNER_MAIN,
            "previous_owner_source_tree": "d" * 40,
            "owner_source_sha": "e" * 40,
            "owner_source_tree": "f" * 40,
            "pr_number": PR_FLOOR,
            "pr_head_sha": "1" * 40,
            "regression_run_id": 100,
            "source_run_id": 101,
            "rehearsal_run_id": 102,
            "owner_run_id": 103,
            "owner_comment_id": 104,
            "terminal_seq": 71,
            "terminal_hash": "2" * 64,
            "terminal_count": 11,
            "last_ticket": "f139-nci04-i1891",
            "task_name": "FORGE-F139-UnifiedController",
            "development_only": True,
            "worker_release_unchanged": True,
            "scientific_first_use": False,
            "paid_model_calls": 0,
        }
        self.assertEqual(set(unsigned), FIELDS - {"owner_signature"})
        key = "k" * 48
        sig_v3 = sign(unsigned, key)
        self.assertEqual(len(sig_v3), 64)
        from f139.nci04_fresh_owner_source_forward_v2 import sign as sign_v2
        self.assertNotEqual(sig_v3, sign_v2(unsigned, key))

    def test_v3_sign_rejects_short_key_or_missing_field(self):
        with self.assertRaisesRegex(ForwardV3Denied, "SIGNING_INPUT_INVALID"):
            sign({}, "k" * 48)


if __name__ == "__main__":
    unittest.main()
