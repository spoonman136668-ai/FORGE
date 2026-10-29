"""AC-11 fail-closed no-mock public/source-boundary tests.

No original episode is executed by these unit tests. A successful source
smoke MUST come only from the real authenticated upstream subprocess.
"""
import unittest

import ac11_original_dtr as ac

def sample(seed):
    a={"stage":0,"observation":0,"action":0,"next_observation":1,
       "reward":0,"terminated":False,"truncated":False,"valid_actions":[0,1]}
    b={"stage":1,"observation":1,"action":1,"next_observation":None,
       "reward":1,"terminated":True,"truncated":False,"valid_actions":[0,1]}
    return {"seed":seed,"events":[a,b],"ctf_do_permission_denied":True}

def fake_report():
    # This is a unit-test of the validator, NOT an upstream result or artifact.
    return {"schema":"forge.ac11.actual-upstream-public-smoke.v1",
            "source_owned_episodes":2,"source_owned_actions":4,
            "records":[sample(x) for x in ac.SMOKE_SEEDS],
            "learner_receives_unfiltered_info":False,
            "source_env_exposed_to_learner":False,
            "native_model_trained":False,
            "original_scientific_first_use":False}

class AC11NoPrivilegeGuards(unittest.TestCase):
    def test_fixed_public_seed_partition(self):
        self.assertEqual(ac.SMOKE_SEEDS,(759011,759013))
        self.assertEqual(set(ac.SMOKE_SEEDS),
                         set(ac.ac10.PROTO["public_smoke_seeds"]))
        for k in ("fit_seeds_reserved_not_run",
                  "validation_seeds_reserved_not_run",
                  "dev_seeds_reserved_not_run"):
            self.assertFalse(set(ac.SMOKE_SEEDS)&set(ac.ac10.PROTO[k]))
    def test_success_validator_accepts_only_explicit_whitelist(self):
        ac.validate_smoke(fake_report())
        self.assertEqual(len(ac.PUBLIC_FIELDS),8)
        self.assertNotIn("full_info",ac.PUBLIC_FIELDS)
    def test_rejects_raw_info(self):
        r=fake_report()
        r["records"][0]["events"][0]["info"]={"u":0.1}
        with self.assertRaisesRegex(RuntimeError,"ALLOWLIST"):
            ac.validate_smoke(r)
    def test_rejects_counterfactual_permission(self):
        r=fake_report()
        r["records"][0]["ctf_do_permission_denied"]=False
        with self.assertRaisesRegex(RuntimeError,"COUNTERFACTUAL"):
            ac.validate_smoke(r)
    def test_rejects_seed_drift(self):
        r=fake_report()
        r["records"][0]["seed"]=760000
        with self.assertRaisesRegex(RuntimeError,"SEED_DRIFT"):
            ac.validate_smoke(r)
    def test_rejects_fake_scientific_positive(self):
        r=fake_report()
        r["original_scientific_first_use"]=True
        with self.assertRaisesRegex(RuntimeError,"ILLICIT_SCIENCE"):
            ac.validate_smoke(r)
    def test_rejects_wrong_stage(self):
        r=fake_report()
        r["records"][0]["events"][0]["terminated"]=True
        with self.assertRaisesRegex(RuntimeError,"WRONG_TERMINAL"):
            ac.validate_smoke(r)
    def test_failure_is_reported_not_assumed_hardware_result(self):
        self.assertEqual(ac.classification(b"",True),"UPSTREAM_DEPENDENCY_TIMEOUT")
        self.assertEqual(ac.classification(b"ModuleNotFoundError: numpy",False),"UPSTREAM_MODULE_NOT_FOUND")
        self.assertEqual(ac.classification(b"ERROR: bad dependency",False),"UPSTREAM_INSTALL_ERROR")

if __name__=="__main__":
    unittest.main()
