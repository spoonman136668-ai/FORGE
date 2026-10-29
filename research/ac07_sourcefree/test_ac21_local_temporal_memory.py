"""AC-21 focused tests. All input events come from authenticated parent receipts."""
import json
import math
import unittest
import ac21_local_temporal_memory as m

class AC21TemporalTests(unittest.TestCase):
    def test_two_hop_only_and_site5_has_no_past_s1_after_one_round(self):
        x=m.TemporalRingDev()
        early,n1=x.transport((1,1,0,1),1)
        full,n2=x.transport((1,1,0,1),2)
        self.assertNotIn("s1",early)
        self.assertIn("x1",early)
        self.assertEqual(set(full),{"s1","x1"})
        self.assertGreater(n2,n1)
        self.assertTrue(all((i+1)%8 in m.NEIGHBORS[i] for i in range(8)))

    def test_public_source_history_is_sequential_and_no_oracle(self):
        e={"events":[
            {"stage":0,"observation":1,"action":0,"next_observation":0,
             "reward":0,"terminated":False,"truncated":False,"valid_actions":[0,1]},
            {"stage":1,"observation":0,"action":1,"next_observation":None,
             "reward":1,"terminated":True,"truncated":False,"valid_actions":[0,1]}
        ]}
        self.assertEqual(m.history(e),((1,0,0,1),1))
        with self.assertRaisesRegex(ValueError,"AC21_SOURCE_PUBLIC_STAGE_CHAIN_INVALID"):
            m.history({"events":[e["events"][0],dict(e["events"][1],observation=1)]})
        with self.assertRaisesRegex(ValueError,"AC21_INVALID_PUBLIC_S1"):
            m.TemporalRingDev().predict((True,0,1,1))
        with self.assertRaisesRegex(ValueError,"AC21_INVALID_PUBLIC_REWARD"):
            m.TemporalRingDev().observe((1,0,0,1),True)

    def test_train_actual_temporal_parameters_fit_budget(self):
        rows=[((1,1,0,1),1),((0,1,1,0),0),((1,0,0,1),1),((0,0,1,1),0)]
        obj=m.fit(m.TemporalRingDev(),rows)
        self.assertEqual(obj.updates,len(rows)*m.PASSES)
        self.assertNotEqual(obj.weights,list(m.W0))
        self.assertTrue(any(abs(t)>1e-12 for t in obj.gates.values()))
        self.assertEqual(obj.snapshot(),m.TemporalRingDev.restore(obj.snapshot()).snapshot())
        self.assertEqual([obj.predict(h) for h,y in rows],
                         [m.TemporalRingDev.restore(obj.snapshot()).predict(h) for h,y in rows])

    def test_full_history_control_matched_fixed_training_passes(self):
        rows=[((1,1,0,1),1),((0,1,1,0),0)]
        base=m.fit(m.FullHistoryLogisticControl(),rows)
        candidate=m.fit(m.TemporalRingDev(),rows)
        self.assertEqual(base.updates,candidate.updates)
        self.assertEqual(base.updates,len(rows)*m.PASSES)

    def test_all_sixteen_public_history_candidates_use_bounded_probabilities(self):
        x=m.TemporalRingDev()
        for s1 in (0,1):
            for x1 in (0,1):
                for s2 in (0,1):
                    for x2 in (0,1):
                        p=x.predict((s1,x1,s2,x2))
                        self.assertTrue(math.isfinite(p) and 0<=p<=1)
        self.assertEqual(len(x.weights),8)
        self.assertEqual(len(x.gates),2)

    def test_checkpoint_fails_closed_on_source_or_parameter_forgeries(self):
        x=m.TemporalRingDev()
        obj=json.loads(x.snapshot())
        with self.assertRaisesRegex(ValueError,"AC21_INVALID_CHECKPOINT_SCHEMA"):
            m.TemporalRingDev.restore(json.dumps(dict(obj, extra=1)))
        obj=json.loads(x.snapshot());obj["weights"][0]=99.
        with self.assertRaisesRegex(ValueError,"AC21_CHECKPOINT_PARAMETER_BOUNDS"):
            m.TemporalRingDev.restore(json.dumps(obj))
        with self.assertRaisesRegex(ValueError,"AC21_INVALID_CHECKPOINT_LENGTH"):
            m.TemporalRingDev.restore("a"*8193)

    def test_fit_only_controls_and_ablation_differ(self):
        fit=[((1,1,0,1),1),((0,0,1,0),0)]
        dev=[((1,1,0,1),1),((0,0,1,0),0)]
        x=m.fit(m.TemporalRingDev(),fit)
        ab=m.fit(m.TemporalRingDev(),fit,mask="s1")
        pre=x.snapshot()
        results=m.measures(m.predictions(x,dev),dev)
        self.assertEqual(results["n"],2)
        self.assertEqual(x.snapshot(),pre)
        self.assertNotEqual(m.predictions(x,dev),m.predictions(ab,dev,"s1"))

if __name__=="__main__":unittest.main()
