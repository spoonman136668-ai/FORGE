"""Tests for Gate 18: Generalized V5+ source-forward chain & FORGE self-applied upgrades."""
from __future__ import annotations

import unittest

from f139.nci04_fresh_owner_source_forward_chain import (
    ForwardChainDenied, sign_version, version_domain, version_filename, version_schema,
)
from f139.nci04_fresh_owner_source_forward_v2 import FIELDS
from f139.nci04_method_benchmarks import run_llm_experimental
from f139.nci04_wingless_gen2 import qualify_wingless_gen2_heldout


class Gate18GeneralChainAndSelfUpgradeTests(unittest.TestCase):
    def test_general_chain_domain_separation_and_bounds(self):
        self.assertEqual(
            version_schema(5),
            "forge.f139.fresh-original-owner-source-forward.v5",
        )
        self.assertEqual(
            version_filename(5),
            "fresh-original-owner-source-forward-v5.json",
        )
        self.assertNotEqual(version_domain(5), version_domain(6))
        with self.assertRaises(ForwardChainDenied):
            version_schema(4)

        unsigned = {
            "schema": version_schema(5),
            "admission_source_sha": "a" * 40,
            "worker_release_sha": "b" * 40,
            "previous_certificate_sha256": "c" * 64,
            "previous_owner_source_sha": "5abc755ae369b3d2b36b35902da5742e1d80fac8",
            "previous_owner_source_tree": "d" * 40,
            "owner_source_sha": "e" * 40,
            "owner_source_tree": "f" * 40,
            "pr_number": 1916,
            "pr_head_sha": "1" * 40,
            "regression_run_id": 100,
            "source_run_id": 101,
            "rehearsal_run_id": 102,
            "owner_run_id": 103,
            "owner_comment_id": 104,
            "terminal_seq": 165,
            "terminal_hash": "2" * 64,
            "terminal_count": 23,
            "last_ticket": "f139-nci04-i1914",
            "task_name": "FORGE-F139-UnifiedController",
            "development_only": True,
            "worker_release_unchanged": True,
            "scientific_first_use": False,
            "paid_model_calls": 0,
        }
        self.assertEqual(set(unsigned), FIELDS - {"owner_signature"})
        key = "k" * 48
        sig5 = sign_version(unsigned, key, 5)
        sig6 = sign_version(unsigned, key, 6)
        self.assertEqual(len(sig5), 64)
        self.assertNotEqual(sig5, sig6)

    def test_self_qualified_wingless_z085_improves_heldout_ood_over_v1(self):
        rep = qualify_wingless_gen2_heldout()
        self.assertIn("zscore_causal_085", rep["qualified_policies"])
        self.assertEqual(rep["evaluations"][0]["policy"], "zscore_causal_085")
        self.assertGreaterEqual(rep["evaluations"][0]["total_delta_vs_baseline"], 46)

    def test_llm_experimental_l2_cosine_sgd_beats_sgd_baseline(self):
        base = run_llm_experimental("sgd_baseline")["metrics"]["val_loss"]
        cand = run_llm_experimental("l2_cosine_sgd")["metrics"]["val_loss"]
        self.assertLess(cand, base)


if __name__ == "__main__":
    unittest.main()
