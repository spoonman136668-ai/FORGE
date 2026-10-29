"""AC-24 original-source protocol and training checks, with NO source calls here."""
import copy, itertools, math, unittest
import ac24_fresh_original_dtr_public as a

def fixture(phase):
    seeds=a.FIT if phase=="FIT" else a.DEV
    episodes=[]
    for i,seed in enumerate(seeds):
        s1=(i//4)%2;s2=(i//8)%2
        ev=[
          {"stage":0,"observation":s1,"action":i%2,"next_observation":s2,
           "reward":0,"terminated":False,"truncated":False,"valid_actions":[0,1]},
          {"stage":1,"observation":s2,"action":(i//2)%2,"next_observation":None,
           "reward":(i//4)%2,"terminated":True,"truncated":False,"valid_actions":[0,1]}
        ]
        episodes.append({"seed":seed,"events":ev,"ctf_do_permission_denied":True})
    return {"schema":a.SOURCE_SCHEMA,"phase":phase,"source_owned_episodes":len(seeds),
            "source_owned_actions":2*len(seeds),"episodes":episodes,
            "learner_received_privileged_info":False,"scientific_first_use":False}

class AC24SourceContractTests(unittest.TestCase):
    def test_new_source_seeds_are_frozen_disjoint_and_actions_balanced(self):
        self.assertEqual(len(a.FIT),64)
        self.assertEqual(len(a.DEV),32)
        self.assertFalse(set(a.FIT)&set(a.DEV))
        self.assertTrue(set(a.FIT).isdisjoint(range(759000,761000)))
        self.assertTrue(set(a.DEV).isdisjoint(range(759000,761000)))
        for phase in ("FIT","DEV"):
            doc=a.validate_source(fixture(phase),phase)
            acts=[(r["events"][0]["action"],r["events"][1]["action"]) for r in doc["episodes"]]
            self.assertEqual(set(acts),set(itertools.product((0,1),repeat=2)))
            self.assertEqual(len(set(acts)),4)

    def test_original_public_fields_preserve_terminal_reward_and_none(self):
        doc=a.validate_source(fixture("FIT"),"FIT")
        self.assertEqual(doc["episodes"][0]["events"][1]["next_observation"],None)
        self.assertTrue(all(set(e)==set(a.ALLOWED) for row in doc["episodes"] for e in row["events"]))
        self.assertEqual(a.history(doc["episodes"][1]),((0,1,0,0),0))
        self.assertNotIn("u",a.ALLOWED)

    def test_source_private_and_permission_forgery_fail_closed(self):
        x=fixture("FIT");x["episodes"][0]["events"][1]["u"]=0.1
        with self.assertRaisesRegex(RuntimeError,"AC24_PUBLIC_SOURCE_EVENT_FIELD_OR_ACTION_DRIFT"):
            a.validate_source(x,"FIT")
        x=fixture("FIT");x["episodes"][0]["ctf_do_permission_denied"]=False
        with self.assertRaisesRegex(RuntimeError,"AC24_SOURCE_PERMISSIONS_OR_EVENTS_INVALID"):
            a.validate_source(x,"FIT")
        x=fixture("FIT");x["episodes"][1]["events"][1]["reward"]=10
        with self.assertRaisesRegex(RuntimeError,"AC24_PUBLIC_SOURCE_EVENT_FIELD_OR_ACTION_DRIFT"):
            a.validate_source(x,"FIT")
        x=fixture("FIT");x["episodes"][0]["events"][1]["next_observation"]=0
        with self.assertRaisesRegex(RuntimeError,"AC24_ORIGINAL_STAGE_OR_TERMINAL_DRIFT"):
            a.validate_source(x,"FIT")

    def test_dev_source_not_relabelled_as_fit(self):
        with self.assertRaisesRegex(RuntimeError,"AC24_SOURCE_SEED_OR_EPISODE_DRIFT"):
            a.validate_source(fixture("DEV"),"FIT")
        x=fixture("DEV");x["episodes"][0]["seed"]=a.FIT[0]
        with self.assertRaisesRegex(RuntimeError,"AC24_SOURCE_SEED_OR_EPISODE_DRIFT"):
            a.validate_source(x,"DEV")
        x=fixture("FIT");x["learner_received_privileged_info"]=True
        with self.assertRaisesRegex(RuntimeError,"AC24_ORIGINAL_SOURCE_CONTRACT_DRIFT"):
            a.validate_source(x,"FIT")

    def test_fully_frozen_matched_control_pipeline_from_synthetic_fixture_only(self):
        # This unit test is NOT original-source evidence. Only an actual
        # verified SOURCE subprocess qualifies a source-owned result.
        fit=fixture("FIT");dev=fixture("DEV")
        x=a.evaluate(fit,dev)
        self.assertEqual(len(x["prediction_rows"]),32)
        self.assertEqual(x["resource_and_checkpoint_census"]["local_self_reconstruction"]["fit_updates"],1536)
        self.assertEqual(x["resource_and_checkpoint_census"]["direct_ten_parameter_logistic"]["fit_updates"],1536)
        self.assertEqual(x["resource_and_checkpoint_census"]["local_self_reconstruction"]["local_pulse_update_calls"],3072)
        self.assertEqual(x["resource_and_checkpoint_census"]["local_near_unit_fixed_diagnostic"]["trained_parameter_count"],8)
        self.assertEqual(set(x["metrics"]),{
            "local_self_reconstruction","local_reward_modulated",
            "local_near_unit_fixed_diagnostic","direct_eight_parameter_logistic",
            "direct_ten_parameter_logistic","full_history_laplace",
            "full_history_ema","pooled_fit_prior"})
        self.assertTrue(all(v["n"]==32 and math.isfinite(v["brier"]) for v in x["metrics"].values()))

if __name__=="__main__":
    unittest.main()
