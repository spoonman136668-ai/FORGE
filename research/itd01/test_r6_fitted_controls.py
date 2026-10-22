"""R6 PUBLIC-only preregistered fit/eval/ablation negative retention tests."""
import copy
import unittest
from unittest import mock
import run_r6_fitted_controls as r
from public_dev import PUBLIC_FAMILIES


class R6PublicFittedControls(unittest.TestCase):
    def test_disjoint_frozen_role_and_seed_namespace(self):
        seeds=set()
        for seed in (17,31,47):
            for role,n in (("FIT",240),("VALID",80),("DEV",80),("ABLATE",40)):
                for fi in (0,1):
                    for i in range(n):
                        val=r.role_seed(role,seed,fi,i)
                        self.assertNotIn(val,seeds)
                        seeds.add(val)
                        self.assertGreater(val, 6000000)
        self.assertEqual(len(seeds),3*2*(240+80+80+40))
        with self.assertRaises(ValueError):
            r.role_seed("H1",17,0,0)

    def test_public_teacher_traces_have_no_privileged_key(self):
        rows,trace=r.public_teacher_trajectory(
            PUBLIC_FAMILIES[0],r.role_seed("FIT",17,0,0),
            r.episode_key("FIT",17,0,0))
        self.assertEqual(len(trace),64)
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(set(row),{"x","key","y"})
            self.assertEqual(len(row["x"]),24)
            self.assertTrue(0<=row["y"]<10)
            self.assertNotIn("private",str(row).lower())
        self.assertEqual(rows[-1]["y"],9)

    def test_frozen_counts_and_seed_not_tunable_at_dev(self):
        with self.assertRaisesRegex(ValueError,"UNPREREGISTERED_SEED"):
            r.experiment(19,train_n=1,val_n=1,dev_n=1,ablate_n=1)
        with self.assertRaisesRegex(ValueError,"FROZEN_BUDGET_DRIFT"):
            r.experiment(17,train_n=1,val_n=1,dev_n=1,ablate_n=1)
        with self.assertRaises(ValueError):
            r.score(None,17,"FIT",1)

    def test_source_free_real_smoke_all_three_classes_fit_and_keep_weights(self):
        # Seed 7 is explicitly outside the preregistered 17/31/47 cohort.
        # This consumes only a tiny public developer smoke; never H1/H2.
        x=r.experiment(7,3,2,2,1,developer_smoke=True)
        self.assertEqual(x["schema"],r.SCHEMA)
        self.assertEqual(x["scientific_admission"],"NOT_GRANTED_BY_THIS_DEV_MODULE")
        self.assertFalse(x["scientific_first_use"])
        self.assertFalse(x["native_wingless_yggdrasil_executed"])
        self.assertEqual(len(x["models"]),3)
        self.assertEqual({m["class"] for m in x["models"]},{
            "trained_bptt_recurrent",
            "trained_public_transition_structured_planner",
            "trained_explicit_trajectory_memory"})
        self.assertTrue(all(m["training_updates"]>0 and
                            m["checkpoint_bytes"]>0 for m in x["models"]))
        self.assertTrue(all(f in m["development"] for m in x["models"]
                            for f in PUBLIC_FAMILIES))
        self.assertGreater(x["all_in_process_cpu_seconds"],0)
        self.assertTrue(x["development_disposition"] in (
            "BENCHMARK_CALIBRATED_PUBLIC_DEV_ONLY",
            "BENCHMARK_NOT_QUALIFIED_RETAIN_NEGATIVE"))

    def test_development_evaluator_does_not_fit(self):
        from r4_sequential_controls import RecurrentPolicy
        model=RecurrentPolicy(17)
        with mock.patch.object(model,"train",side_effect=AssertionError("DEV_FIT")):
            trials=r.score(model,17,"VALID",1)
        self.assertTrue(all(f in trials for f in PUBLIC_FAMILIES))
        with self.assertRaisesRegex(ValueError,"ABLATION_ON_PRIMARY_ROLE"):
            r.score(model,17,"DEV",1,"erase")

    def test_no_clandestine_experiment_on_import_or_protected_cli(self):
        import inspect
        code=inspect.getsource(r)
        self.assertIn("if __name__==\"__main__\":",code)
        self.assertNotIn("scientific_first_use\":True",code)
        self.assertNotIn("h1_h2_used\":True",code)


if __name__=="__main__":
    unittest.main()
