"""Adversarial developer-only R5 causal chains and isolation qualification."""
import inspect
import unittest
from public_dev import PUBLIC_FAMILIES,ContractViolation,action,canonical
from r5_causal_dev import R5CausalWorld,public_causal_oracle,run_public_policy
from r5_history_boundary import isolated_public_view,r5_rollout_public_only
from r4_public_experience import PublicTranscript,public_training
from r4_sequential_controls import (RecurrentPolicy,PredictiveTransitionPlanner,
                                    ExplicitTrajectoryMemory,model_sha)
from run_r5_calibration import run


class R5DevelopmentTests(unittest.TestCase):
    def make(self,family=PUBLIC_FAMILIES[0],seed=17):
        return R5CausalWorld(family,"DEV-R5-TEST-"+str(seed),seed)

    def test_unmodified_public_interface_single_reset(self):
        for family in PUBLIC_FAMILIES:
            w=self.make(family)
            ob=w.reset()
            self.assertEqual(ob["schema"],"itd01.observe.v1")
            self.assertEqual(len(ob["entities"]),4)
            self.assertTrue(all(key not in ob for key in ("_source","_relay","_sink","_decoy","hidden_roles")))
            self.assertNotIn("relay_role",canonical(ob).decode())
            self.assertEqual(ob["interaction_budget_remaining"],40)
            with self.assertRaises(ContractViolation):w.reset()
            self.assertFalse(w.public_trace_receipt()["scientific_first_use"])

    def test_two_distinct_latency_threshold_mechanisms(self):
        for family in PUBLIC_FAMILIES:
            w=self.make(family)
            obs=w.reset()
            source=w._labels[w._source]
            val=obs["entities"][0]["legal_values"][0]
            first=w.step(action("intervene",source,val))
            self.assertEqual(first["observation"]["delayed_events"],[])
            arrived=[]
            lag=2 if family==PUBLIC_FAMILIES[0] else 3
            for t in range(lag):
                arrived.append(w.step(action("wait"))["observation"]["delayed_events"])
            self.assertEqual(arrived[-1][0]["kind"],"feed_pulse")
            self.assertEqual(arrived[-1][0]["entity"],w._labels[w._relay])
            self.assertEqual(arrived[-1][0]["status"],
                             "ready" if family==PUBLIC_FAMILIES[0] else "partial")
            self.assertFalse(w._relay_ready)
            if family==PUBLIC_FAMILIES[1]:
                w.step(action("intervene",source,val))
                for _ in range(3):
                    events=w.step(action("wait"))["observation"]["delayed_events"]
                self.assertEqual(events[0]["status"],"ready")

    def test_three_stage_causal_order_not_open_loop(self):
        for family in PUBLIC_FAMILIES:
            w=self.make(family)
            obs=w.reset()
            val=obs["entities"][0]["legal_values"][0]
            for role in (w._source,w._relay,w._sink):
                w.step(action("intervene",w._labels[role],val))
            for _ in range(3):w.step(action("wait"))
            self.assertEqual(w.step(action("commit"))["reward"],0)

    def test_open_loop_control_loses_all_dev_tasks(self):
        for family in PUBLIC_FAMILIES:
            outcomes=[run_public_policy(family,510000+i,"fixed",
                           "DEV-R5-TEST-FIXED-"+str(i)) for i in range(25)]
            self.assertEqual(sum(v["reward"] for v in outcomes),0)

    def test_public_oracle_solves_both_families_under_limits(self):
        for family in PUBLIC_FAMILIES:
            for i in range(80):
                x=run_public_policy(family,520000+i,"oracle",
                                    "DEV-R5-TEST-ORACLE-"+str(i))
                self.assertEqual(x["reward"],1,(family,i,x))
                self.assertLessEqual(x["steps"],40)

    def test_public_oracle_no_private_identity_access(self):
        x=inspect.getsource(public_causal_oracle)
        for priv in ("._source","._relay","._sink","._states",
                     "._pending","._rng","._lookup","._family","._required"):
            self.assertNotIn(priv,x)
        self.assertIn('"feed_pulse"',x)
        self.assertIn('"dependence_pulse"',x)

    def test_public_hash_deterministic_and_role_not_leaked(self):
        for family in PUBLIC_FAMILIES:
            a=run_public_policy(family,8281,"oracle","DEV-R5-REPLAY")
            b=run_public_policy(family,8281,"oracle","DEV-R5-REPLAY")
            self.assertEqual(a,b)
            self.assertEqual(len(a["sha256"]),64)

    def test_invalid_action_terminal_even_under_r5(self):
        w=self.make()
        w.reset()
        r=w.step({"schema":"itd01.act.v1","verb":"read_secret",
                  "target":None,"value":None})
        self.assertEqual(r["reward"],0)
        self.assertTrue(r["done"])
        with self.assertRaises(ContractViolation):w.step(action("wait"))

    def test_erased_history_really_erases_both_numeric_and_object(self):
        w=self.make()
        ob=w.reset()
        h=PublicTranscript(ob)
        chosen=action("intervene",ob["entities"][0]["id"],"activate")
        x=w.step(chosen)
        h.ingest(chosen,x["observation"])
        # Maliciously simulate information learned before ablation.
        h.public_ready=ob["entities"][0]["id"]
        h.public_partial=ob["entities"][1]["id"]
        h.public_confirmed=ob["entities"][2]["id"]
        h.active_events=[{"kind":"feed_pulse","entity":ob["entities"][0]["id"],"status":"ready"}]
        full=isolated_public_view(h,"normal")
        erased=isolated_public_view(h,"erase")
        blind=isolated_public_view(h,"blind_delayed")
        self.assertNotEqual(full.features(),erased.features())
        self.assertEqual(sum(erased.features()[:20]),0.)
        self.assertIsNone(erased.public_ready)
        self.assertIsNone(erased.public_partial)
        self.assertIsNone(erased.public_confirmed)
        self.assertEqual(erased.active_events,[])
        self.assertEqual(erased.latest_observation["delayed_events"],[])
        self.assertIsNone(blind.public_ready)
        self.assertIsNone(blind.public_partial)
        self.assertIsNone(blind.public_confirmed)
        self.assertEqual(blind.active_events,[])
        self.assertGreater(sum(blind.on),0)
        full.on[0]=999
        self.assertNotEqual(h.on[0],999)
        self.assertEqual(erased.memory_key()[3],-1)

    def test_history_modes_apply_to_all_three_agent_classes(self):
        rows,_=public_training(17,4)
        for constructor in (lambda:RecurrentPolicy(17),
                            PredictiveTransitionPlanner,ExplicitTrajectoryMemory):
            m=constructor()
            m.train(rows)
            before=model_sha(m)
            for mode in ("normal","erase","blind_delayed"):
                result=r5_rollout_public_only(m,PUBLIC_FAMILIES[0],
                                            599222,"DEV-R5-AB-"+str(len(m.name))+"-"+mode,mode)
                self.assertLessEqual(result["steps"],40)
                self.assertEqual(result["reward"] in (0,1),True)
            self.assertEqual(model_sha(m),before)

    def test_aggregate_receipt_is_explicitly_dev_only(self):
        report=run(17,4,8,3,2)
        self.assertFalse(report["scientific_first_use"])
        self.assertFalse(report["protected_H1_H2_used"])
        self.assertFalse(report["native_wingless_yggdrasil_executed"])
        self.assertEqual(report["authority"],"NONE_DEV_ONLY")
        self.assertEqual(len(report["models"]),3)
        self.assertTrue(all(x["r5_fit_updates"]==0 for x in report["models"]))
        self.assertEqual(report["developer_eligibility"],
                         "PUBLIC_WORLD_SOLVABLE_R5_BASELINE_ELIGIBILITY_NOT_QUALIFIED")


if __name__=="__main__":
    unittest.main()
