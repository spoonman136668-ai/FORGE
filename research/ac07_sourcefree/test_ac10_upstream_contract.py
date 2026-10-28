"""Fail-closed AC-10 exact-original static-contract tests (no original episodes)."""
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import ac10_upstream_contract as ac

class TestAC10Upstream(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=os.environ.get("AC10_UPSTREAM_ROOT")
        if not root:
            raise RuntimeError("AC10_EXACT_UPSTREAM_ROOT_REQUIRED_NO_FIXTURE_FALLBACK")
        cls.root=Path(root).resolve(strict=True)
        cls.source=ac.inspect_upstream(cls.root)

    def test_exact_original_code_and_dependency_boundary(self):
        self.assertEqual(self.source["sha"],ac.SOURCE_COMMIT)
        self.assertEqual(self.source["tree"],ac.SOURCE_TREE)
        self.assertEqual(self.source["verified_git_blobs"],ac.BLOBS)
        self.assertGreaterEqual(self.source["root_import_fanout"],10)
        self.assertEqual(self.source["source_native_episodes_executed"],0)

    def test_real_unmodified_dtr_and_permission_api_exists(self):
        self.assertIn("do",self.source["dtr_pch_methods"])
        self.assertIn("ctf_do",self.source["dtr_pch_methods"])
        self.assertIn("reset",self.source["dtr_scm_methods"])
        self.assertIn("step",self.source["dtr_scm_methods"])
        self.assertTrue(self.source["pch_permission_methods_verified"])

    def test_reserved_seeds_are_not_used_in_a_preflight(self):
        p=ac.PROTO
        a,b,c=(set(p[x]) for x in ("fit_seeds_reserved_not_run",
                  "validation_seeds_reserved_not_run","dev_seeds_reserved_not_run"))
        smoke=set(p["public_smoke_seeds"])
        self.assertTrue(a.isdisjoint(b) and b.isdisjoint(c) and c.isdisjoint(a))
        self.assertTrue(all(smoke.isdisjoint(x) for x in (a,b,c)))
        self.assertTrue(p["frozen_before_source_interactions"])
        self.assertFalse(p["model_fitted"])
        self.assertFalse(p["protected_original_first_use"])

    def test_public_data_whitelist_denies_privileged_source(self):
        p=ac.PROTO
        self.assertEqual(p["allowed_calls"],["reset","do"])
        self.assertIn("stage",p["allowed_event_fields"])
        self.assertIn("valid_actions",p["allowed_event_fields"])
        self.assertTrue({"env","u","get_graph","ctf_do","full_info","oracle"}.issubset(
            p["forbidden_to_learner"]))
        self.assertFalse(set(p["allowed_calls"])&set(p["forbidden_to_learner"]))

    def test_drifted_upstream_head_fails_before_import(self):
        original=ac.git
        def fake(repo,*args):
            if args==("rev-parse","HEAD"):
                return "0"*40
            return original(repo,*args)
        with patch.object(ac,"git",side_effect=fake):
            with self.assertRaisesRegex(RuntimeError,"EXACT_UPSTREAM_COMMIT"):
                ac.inspect_upstream(self.root)

    def test_import_result_reports_success_or_blocker_not_model_success(self):
        p=ac.import_probe(self.root)
        self.assertIn(p["status"],("UPSTREAM_IMPORT_OK_NO_EPISODES",
                                   "UPSTREAM_IMPORT_BLOCKED",
                                   "UPSTREAM_IMPORT_TIMEOUT"))
        self.assertFalse(p["upstream_code_modified"])
        self.assertFalse(p.get("episode_executed",False))

    def test_source_contract_report_denies_science_and_native_training(self):
        r=ac.run(self.root)
        self.assertEqual(r["original_source_interactions_performed"],0)
        self.assertFalse(r["native_model_training_performed"])
        self.assertFalse(r["scientific_first_use"])
        self.assertFalse(r["original_source_birth_attested"])
        self.assertFalse(r["controller_or_f139_queue_changed"])
        self.assertFalse(r["accepted_science_or_native_models_changed"])
        self.assertIsNone(r["public_dev_fit_or_control_results"])
        self.assertEqual(r["schema"],ac.SCHEMA)
        self.assertEqual(json.loads(json.dumps(r,sort_keys=True))["schema"],ac.SCHEMA)

if __name__=="__main__":
    unittest.main()
