"""Fail-closed AC-15 FIT/DEV source and learnt checkpoint contract tests.

These deterministic fixtures are only validator negatives, NEVER scientific
source evidence or substitutes for the actual original DTR subprocess.
"""
import unittest
from unittest.mock import patch
import ac15_native_public_adapter as a

def fixture(phase):
    seeds=a.FIT if phase=="FIT" else a.DEV
    rows=[]
    for i,seed in enumerate(seeds):
        s0=i%2
        events=[
            {"stage":0,"observation":i%2,"action":s0,
             "next_observation":(i+1)%2,"reward":0,
             "terminated":False,"truncated":False,"valid_actions":[0,1]},
            {"stage":1,"observation":(i+1)%2,"action":(i//2)%2,
             "next_observation":None,"reward":i%2,
             "terminated":True,"truncated":False,"valid_actions":[0,1]}
        ]
        rows.append({"seed":seed,"ctf_do_permission_denied":True,
                     "events":events})
    return {"schema":a.SOURCE_SCHEMA,"phase":phase,"source_owned_episodes":len(rows),
            "source_owned_actions":len(rows)*2,
            "episodes":rows,"learner_received_privileged_info":False,
            "scientific_first_use":False}

class AC15GuardTests(unittest.TestCase):
    def test_original_existing_ygg_model_pinned_not_synthetic(self):
        self.assertEqual(a.YGG_COMMIT,"992ef142aaa551156749a1de484a971b9a0c092f")
        self.assertEqual(a.YGG_BLOB,"f2fda603fbed965a3b4e7cc28844b2246bf8ac2b")
        self.assertEqual(a.YGG_PATH,"yggdrasil/public_causal_cells.py")
    def test_seed_prep_declared_without_first_use(self):
        self.assertEqual(len(a.FIT),8)
        self.assertEqual(len(a.DEV),4)
        self.assertEqual(len(a.VALID),4)
        for x,y in ((a.FIT,a.DEV),(a.DEV,a.VALID),(a.VALID,a.FIT)):
            self.assertTrue(set(x).isdisjoint(y))
        self.assertFalse(a.ac10.PROTO["protected_original_first_use"])
    def test_trivial_fake_record_is_only_validator_sample(self):
        for p in ("FIT","DEV"):
            a.validate_source(fixture(p),p)
    def test_reject_oracle_exposure(self):
        r=fixture("FIT")
        r["episodes"][0]["events"][0]["info"]={"u":1}
        with self.assertRaisesRegex(RuntimeError,"RAW_ORACLE"):
            a.validate_source(r,"FIT")
    def test_reject_modified_behavior_policy(self):
        r=fixture("DEV")
        r["episodes"][0]["events"][0]["action"]=1
        with self.assertRaisesRegex(RuntimeError,"FIXED_SCRIPT"):
            a.validate_source(r,"DEV")
    def test_reject_source_privileged_permission(self):
        r=fixture("DEV")
        r["episodes"][0]["ctf_do_permission_denied"]=False
        with self.assertRaisesRegex(RuntimeError,"PRIVILEGED_DTR"):
            a.validate_source(r,"DEV")
    def test_reject_unmatched_phase_or_seed_count(self):
        r=fixture("DEV")
        with self.assertRaises(RuntimeError):
            a.validate_source(r,"FIT")
        r["episodes"][0]["seed"]=760000
        with self.assertRaisesRegex(RuntimeError,"SEED_IDENTITY_DRIFT"):
            a.validate_source(r,"DEV")
    def test_reject_invalid_public_outcome_or_stage(self):
        r=fixture("FIT")
        r["episodes"][0]["events"][1]["reward"]=2
        with self.assertRaisesRegex(RuntimeError,"PUBLIC_REWARD"):
            a.validate_source(r,"FIT")
        r=fixture("FIT")
        r["episodes"][0]["events"][1]["observation"]=0
        with self.assertRaisesRegex(RuntimeError,"STAGE_CHAIN"):
            a.validate_source(r,"FIT")
    def test_equal_information_tabular_control_math(self):
        c={(0,0):[2,6],(0,1):[4,1]}
        self.assertEqual(a.choose_counts(c,0),0)
        self.assertIsNone(a.choose_counts(c,1))
        c={(0,0):[1,1],(0,1):[3,3]}
        self.assertIsNone(a.choose_counts(c,0))
    def test_public_binary_address_outcome(self):
        for stage in (0,1):
            for obs in (0,1):
                e={"stage":stage,"observation":obs,
                   "next_observation":1,"reward":0}
                self.assertEqual(a.address(e),2*stage+obs)
                self.assertEqual(a.outcome(e),1 if stage==0 else 0)
    def test_original_source_failure_not_fabricated_zero(self):
        with patch.object(a.ac11,"run_cmd",
               return_value=(1,b"",b"Traceback",0,False)):
            with self.assertRaisesRegex(RuntimeError,"UNKNOWN_EXECUTION"):
                a.source_phase(a.Path("."),a.Path("python"),{},"FIT")

if __name__=="__main__":
    unittest.main()
