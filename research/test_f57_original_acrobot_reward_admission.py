"""Source-only F57 Acrobot reward trial contract. No original episodes."""
import ast
import hashlib
import inspect
from pathlib import Path
import shutil
import tempfile
import unittest

import f57_original_acrobot_reward_admission as f57


class F57NoScientificExecution(unittest.TestCase):
    def test_frozen_spec_is_exact_and_deterministic(self):
        a=f57.frozen_proposal()
        b=f57.frozen_proposal()
        self.assertEqual(f57.digest(a),f57.digest(b))
        self.assertTrue(f57.validate_structure(a))
        self.assertEqual(a["protocol_commit"],f57.PROTOCOL_COMMIT)
        self.assertEqual(a["parent_sha"],f57.SOURCE_PARENT)
        self.assertEqual(a["historical_fit_sha256"],f57.OLD_FIT_SHA256)
        self.assertEqual(a["historical_40pass_fqi_sha256"],f57.OLD_FQI_SHA256)
        self.assertEqual(a["historical_fit_records"],8974)
        self.assertEqual(a["historical_fit_episodes"],48)
        self.assertEqual(a["original_acrobot_blob"],
                         "28c440af281858c30e95fb6023f19923065d64fe")

    def test_exact_seven_arms_and_actual_reward_splits(self):
        m=f57.frozen_proposal()
        self.assertEqual(len(m["arms"]),7)
        self.assertEqual(m["conventional"],["momentum-rule","frozen-fqi","always-td"] if isinstance(m["conventional"],list) else
                         ("momentum-rule","frozen-fqi","always-td"))
        self.assertEqual(m["negative_control"],"rotated-credit")
        self.assertIn("quantile-supported",m["arms"])
        self.assertEqual(m["new_scored_episodes"],168)
        self.assertEqual(m["cold_replay_episodes"],168)
        self.assertEqual(m["cold_replay_required_exact"],168)
        self.assertEqual(m["max_original_steps_per_episode"],500)
        self.assertFalse(m["candidate_online_learning_allowed"])

    def test_full_local_cohort_overlap_rejected(self):
        m=f57.frozen_proposal()
        scored=(*m["proposed_transfer_nips_seeds"],*m["proposed_retention_book_seeds"])
        old=(*f57.OLD_FIT_ROOTS,*f57.F51_TRANSFER,*f57.F51_RETENTION,
             *f57.F53_TRANSFER,*f57.F53_RETENTION,*f57.PROTECTED)
        self.assertEqual(len(scored),24)
        self.assertEqual(len(set(scored)),24)
        self.assertFalse(set(scored)&set(old))
        self.assertFalse(set(m["proposed_transfer_nips_seeds"])&
                         set(m["proposed_retention_book_seeds"]))
        self.assertFalse(m["global_cohort_ledger_verified"])

    def test_immutable_thresholds_and_controls_fail_closed(self):
        m=f57.frozen_proposal()
        for k,v in {
            "min_mean_transfer_gain":15.,
            "min_paired_strict_wins":12,
            "nondegraded_transfer_success":True,
            "min_negative_credit_margin":15.,
            "min_retention_margin":-10.,
            "min_transfer_seeds_with_action_deviation":4,
            "require_exact_replays":168,
            "measure_absolute_and_ratio_compute":True,
        }.items():
            self.assertEqual(m["frozen_development_thresholds"][k],v)
        for key,mutant in (
            ("new_scored_episodes",169),
            ("arms",("momentum-rule",)),
            ("proposed_transfer_nips_seeds",(*f57.PROPOSED_TRANSFER[:-1],f57.PROTECTED[0])),
            ("scientific_acceptance",True),
        ):
            changed=f57.frozen_proposal()
            changed[key]=mutant
            with self.subTest(key=key),self.assertRaises(ValueError):
                f57.validate_structure(changed)
        changed=f57.frozen_proposal()
        changed["frozen_development_thresholds"]["min_mean_transfer_gain"]=0.
        with self.assertRaises(ValueError):
            f57.validate_structure(changed)

    def test_pinned_original_source_bytes_and_no_leak(self):
        observed=f57.inspect_source_pins()
        self.assertEqual(observed,f57.PINNED_FILES)
        self.assertEqual(len(observed),7)
        self.assertEqual(observed["research/f56_original_acrobot_fit_ips_proxy.py"],
                         "00a6901daa1b479e96d923bf46daa5a1f1be45b4")
        self.assertEqual(observed["AGENTS.md"],
                         "39926d2277ac01c8114f03561bd8e001fcc3b582")

    def test_local_tamper_or_missing_file_never_grants_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for name in f57.PINNED_FILES:
                (root/name).parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(f57.PROJECT/name,root/name)
            before=f57.preflight(root)
            self.assertFalse(before["ready_for_live_scored_execution"])
            path=root/"research/f56_original_acrobot_fit_ips_proxy.py"
            path.write_bytes(path.read_bytes()+b"\n# deliberate test modification\n")
            with self.assertRaisesRegex(RuntimeError,"PIN_MISMATCH"):
                f57.preflight(root)
            path.unlink()
            with self.assertRaisesRegex(RuntimeError,"SOURCE_ONLY_PREFLIGHT_UNVERIFIED"):
                f57.preflight(root)

    def test_no_boolean_or_fake_grant_can_dispatch(self):
        for values in ((True,),({"authorized":True},),
                       ({"fsa_signed":True,"start_receipt":"fake"},),()):
            with self.subTest(values=values),self.assertRaisesRegex(
                    PermissionError,"F57_AUTHORITY_BLOCKED_NO_FIRST_USE"):
                f57.start_scientific_experiment(*values)
        with self.assertRaises(PermissionError):
            f57.start_scientific_experiment(authorized=True,force=True)

    def test_final_preflight_marks_all_unverified(self):
        r=f57.preflight()
        self.assertEqual(r["disposition"],f57.F57_ERROR)
        self.assertTrue(r["local_original_source_blobs_match"])
        self.assertTrue(r["local_internal_seed_disjointness_verified"])
        for key in ("independent_global_seed_ledger_checked",
                    "fsa_authenticated_execution_grant_present",
                    "signed_original_start_receipt_present",
                    "fsa_authenticated_durable_monotonic_witness_present",
                    "fsa_worker_authorized","science_accepted",
                    "ready_for_live_scored_execution"):
            self.assertFalse(r[key],key)
        self.assertEqual(r["fresh_scored_episodes_executed"],0)
        self.assertEqual(r["proposed_manifest_sha256"],f57.digest(f57.frozen_proposal()))

    def test_source_only_stdlib_no_eval_environment_or_network(self):
        tree=ast.parse(inspect.getsource(f57))
        imports=set()
        forbidden_calls=set()
        for n in ast.walk(tree):
            if isinstance(n,ast.Import):
                imports.update(a.name for a in n.names)
            elif isinstance(n,ast.ImportFrom):
                imports.add(n.module or "")
            elif isinstance(n,ast.Call):
                if isinstance(n.func,ast.Name):
                    forbidden_calls.add(n.func.id)
                elif isinstance(n.func,ast.Attribute):
                    forbidden_calls.add(n.func.attr)
        self.assertEqual(imports,{"hashlib","json","pathlib","sys"})
        self.assertFalse({"gym","gymnasium","requests","subprocess","socket"}&imports)
        self.assertFalse({"make","step","reset","evaluate","score","run_workflow",
                          "dispatch","compare_and_swap"}&forbidden_calls)
        self.assertNotIn("f51_original_acrobot_transfer_dev",imports)
        self.assertNotIn("f53_original_acrobot_supported_residual_dev",imports)


if __name__=="__main__":
    unittest.main()
