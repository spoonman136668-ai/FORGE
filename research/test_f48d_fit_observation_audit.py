"""F48D diagnostic tests: only original F48 FIT transcript, no heldout."""
import inspect
import math
import unittest

import f48_regime_reset_credit_dev as f48
import f48d_fit_observation_audit as d


class F48DFitAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worlds, cls.coverage = f48.fit_data()
        cls.fit = f48.fit_shared(cls.worlds)

    def test_exact_frozen_fit_and_complete_disjoint_protected_cohorts(self):
        self.assertEqual(tuple(f48.FIT), d.FIT)
        self.assertEqual(8,len(d.FIT))
        self.assertEqual(768,sum(len(e) for w in self.worlds for e in w))
        self.assertEqual([288,288,192],self.coverage)
        self.assertFalse(set(d.FIT)&(set(f48.TRANSFER)|set(f48.RETENTION)
                                      |set(f48.FORBIDDEN)))
        self.assertEqual("2e2c9665fb6557a682cf788d678f6818e51fd995",
                         d.SOURCE_BLOB)
        self.assertEqual("84a4db4dfd8bc84f68f3a7c43cec005ecce0af90",
                         d.PROTOCOL_BLOB)

    def test_delayed_credit_assigned_to_previous_physical_action(self):
        seed,ep,t=d.FIT[0],0,1
        record=self.worlds[0][ep][t]
        self.assertNotEqual(record[1],record[2])
        policy=f48.Policy("stable-working-reset",self.fit)
        row=d.audit_transition(seed,ep,t,record,policy)
        self.assertEqual(row["surprise"],bool(row["reset"]))
        self.assertEqual(1,policy.observations)
        self.assertLess(0.2/3,d.CUTOFF)

    def test_real_source_disturbance_and_witness_consistency(self):
        for i,seed in enumerate(d.FIT):
            for ep,records in enumerate(self.worlds[i]):
                for t,r in enumerate(records):
                    before,pending,requested,after,witness,reward,done=r
                    noise,flip=f48.exogenous(seed,ep,t)
                    mode=seed%6
                    effect=f48.EFFECTS[mode][pending] if pending!=2 else 0
                    self.assertEqual(noise,before^after^effect)
                    self.assertEqual((int(mode>=3)^int(flip)) if pending==2 else -1,
                                     witness)
        self.assertTrue(all(len(w)==12 for w in self.worlds))

    def test_invalid_and_consumed_holdout_seed_refused_before_replay(self):
        record=self.worlds[0][0][0]
        for seed in (59,83,f48.TRANSFER[0],f48.RETENTION[0]):
            with self.assertRaisesRegex(ValueError,"NON_FIT_SEED_REFUSED"):
                d.audit_transition(seed,0,0,record,
                    f48.Policy("stable-working-reset",self.fit))
        with self.assertRaisesRegex(ValueError,"NON_FIT_STEP_REFUSED"):
            d.audit_transition(d.FIT[0],0,8,record,
                f48.Policy("stable-working-reset",self.fit))
        bad=list(record)
        bad[3]^=1
        with self.assertRaisesRegex(ValueError,"SOURCE_DELAY_OR_NOISE_MISMATCH"):
            d.audit_transition(d.FIT[0],0,0,bad,
                f48.Policy("stable-working-reset",self.fit))

    def test_policy_does_not_accept_mode_noise_or_source_truth(self):
        self.assertEqual(["self","before","pending","requested","after","witness"],
                         list(inspect.signature(f48.Policy.observe).parameters))
        self.assertEqual(["self","state","goal","pending","t"],
                         list(inspect.signature(f48.Policy.decide).parameters))
        self.assertNotIn("mode",list(inspect.signature(d.audit_transition).parameters))
        self.assertIn("seed",list(inspect.signature(d.audit_transition).parameters))
        self.assertEqual(96,len(self.worlds)*len(self.worlds[0]))

    def test_complete_training_only_audit_and_canonical_sha(self):
        x=d.audit_fit()
        self.assertEqual(d.SCHEMA,x["schema"])
        self.assertTrue(x["fit_only"])
        self.assertFalse(x["heldout_scoring_performed"])
        self.assertFalse(x["first_use_consumed"])
        self.assertFalse(x["scientific_accepted"])
        self.assertFalse(x["owner_eligible"])
        self.assertEqual("F48_DEV_NO_GO",x["science_f48_classification_preserved"])
        self.assertEqual(768,x["source_record_count"])
        self.assertEqual(96,x["stationary_policy_replays"])
        self.assertEqual([288,288,192],x["fit_action_coverage"])
        c=x["counters"]
        self.assertEqual(c["source_steps"],768)
        self.assertEqual(c["reset_count_in_fixed_worlds"],c["surprise_flag_count"])
        self.assertEqual(c["reset_count_in_fixed_worlds"],
                         c["reset_with_noise"]+c["reset_without_noise"])
        self.assertEqual(c["correct_credit_higher"]+c["wrong_credit_higher"]
                         +c["same_credit_likelihood"],768)
        self.assertTrue(math.isfinite(x["mean_nll_correct_delayed_credit"]))
        self.assertTrue(math.isfinite(x["mean_nll_wrong_current_action_credit"]))
        self.assertGreater(c["sensor_steps"],0)
        self.assertEqual(x["report_sha256"],f48.digest(
            {k:v for k,v in x.items() if k!="report_sha256"}))
        self.assertIn(x["diagnosis"],
            ("F48D_FIT_FALSE_RESET_DETECTED",
             "F48D_FIT_FALSE_RESET_NOT_OBSERVED"))


if __name__=="__main__":
    unittest.main(verbosity=2)
