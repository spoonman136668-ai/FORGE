"""R7 prospective neutral-public FIT/VALID/DEV, leakage and budget checks."""
import copy
import unittest
from unittest import mock
from public_dev import PUBLIC_FAMILIES
from r5_causal_dev import R5CausalWorld
from r4_sequential_controls import RecurrentPolicy
from r7_public_adapter import r4_compatible_public_observation, r7_rollout_public_only
import run_r7_neutral_fit as r7


class R7NeutralPublicDevelopment(unittest.TestCase):
    def test_public_neutral_event_conversion_and_abstraction_disclosure(self):
        for kind in ("feed_pulse", "dependence_pulse", "relay_pulse"):
            w=R5CausalWorld(PUBLIC_FAMILIES[0],"DEV-R7-UNIT",19)
            obs=w.reset()
            node=obs["entities"][0]["id"]
            obs["delayed_events"]=[{"kind":kind,"entity":node,"status":"ready"}]
            out=r4_compatible_public_observation(obs)
            self.assertEqual(out["delayed_events"],
                             [{"kind":"relay_pulse","entity":node,"status":"ready"}])
            self.assertEqual(obs["delayed_events"][0]["kind"],kind)
            self.assertNotIn("source",str(out).lower())
        for legacy in ("private_role","future_outcome"):
            w=R5CausalWorld(PUBLIC_FAMILIES[0],"DEV-R7-REJECT",19)
            obs=w.reset()
            obs["delayed_events"]=[{"kind":legacy,"entity":obs["entities"][0]["id"],
                                    "status":"ready"}]
            with self.assertRaises(ValueError):
                r4_compatible_public_observation(obs)

    def test_fresh_role_namespace_disjoint_from_r6_consumed(self):
        values=set()
        for seed in (17,31,47):
            for role,n in (("FIT",240),("VALID",80),("DEV",80),("ABLATE",40)):
                for fi in (0,1):
                    for i in range(n):
                        v=r7.role_seed(role,seed,fi,i)
                        self.assertGreaterEqual(v,21000000)
                        self.assertNotIn(v,values)
                        values.add(v)
                        self.assertTrue(r7.contract_episode_id(
                            r7.episode_key(role,seed,fi,i)).startswith("DEV-R7-"))
        self.assertEqual(len(values),2640)

    def test_training_uses_only_public_causal_transcripts(self):
        seed=r7.role_seed("FIT",17,0,0)
        rows, sha=r7.public_teacher_trajectory(
            PUBLIC_FAMILIES[0],seed,r7.episode_key("FIT",17,0,0))
        self.assertTrue(rows)
        self.assertEqual(len(sha),64)
        for row in rows:
            self.assertEqual(set(row),{"x","key","y"})
            self.assertEqual(len(row["x"]),24)
            self.assertIn(row["y"],range(10))
        self.assertEqual(rows[-1]["y"],9)

    def test_frozen_seed_budget_and_eval_no_training(self):
        with self.assertRaisesRegex(ValueError,"UNPREREGISTERED_SEED"):
            r7.experiment(19,1,1,1,1)
        with self.assertRaisesRegex(ValueError,"FROZEN_BUDGET_DRIFT"):
            r7.experiment(17,1,1,1,1)
        agent=RecurrentPolicy(17)
        with mock.patch.object(agent,"train",side_effect=AssertionError("DEV_TRAIN")):
            out=r7.score(agent,17,"VALID",1)
        self.assertTrue(all(f in out for f in PUBLIC_FAMILIES))
        with self.assertRaisesRegex(ValueError,"ABLATION_ON_PRIMARY_ROLE"):
            r7.score(agent,17,"DEV",1,mode="erase")

    def test_public_ablations_are_isolated_without_private_causal_source(self):
        a=RecurrentPolicy(17)
        for mode in ("normal","erase","blind_delayed"):
            v=r7_rollout_public_only(
                a,PUBLIC_FAMILIES[1],r7.role_seed("ABLATE",17,1,0),
                r7.contract_episode_id(r7.episode_key("ABLATE",17,1,0)),
                mode=mode)
            self.assertIn(v["reward"],(0,1))
            self.assertLessEqual(v["steps"],41)
            self.assertEqual(len(v["trace_sha256"]),64)

    def test_real_smoke_public_only_models_not_native_science(self):
        out=r7.experiment(7,3,2,2,1,developer_smoke=True)
        self.assertEqual(out["schema"],r7.SCHEMA)
        self.assertEqual(len(out["models"]),3)
        self.assertFalse(out["scientific_first_use"])
        self.assertFalse(out["native_wingless_yggdrasil_executed"])
        self.assertFalse(out["protected_h1_h2_used"])
        self.assertFalse(out["normalized_model_isolated_resource_parity"])
        self.assertEqual(out["input_semantics"],
                         "HUMAN_DESIGNED_PUBLIC_NEUTRAL_EVENT_PROJECTION")
        self.assertTrue(all(m["checkpoint_bytes"]>0 and
                            m["training_updates"]>=0 for m in out["models"]))
        self.assertTrue(out["development_disposition"] in (
            "BENCHMARK_CALIBRATED_PUBLIC_DEV_ONLY",
            "BENCHMARK_NOT_QUALIFIED_RETAIN_NEGATIVE"))


if __name__ == "__main__":
    unittest.main()
