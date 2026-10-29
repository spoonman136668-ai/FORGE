"""AC-22 FIT-only mechanism checks; no DEV or original environment."""
import itertools
import math
import unittest
import ac22_fit_only_retention_diagnostics as m
import ac21_local_temporal_memory as parent

class AC22FitOnlyTests(unittest.TestCase):
    def test_frozen_half_gate_has_actual_fit_updates_but_no_gate_learning(self):
        obj=m.FrozenGateTemporal(0.)
        rows=[((1,1,0,1),1),((0,0,1,0),0)]
        parent.fit(obj,rows)
        self.assertEqual(obj.updates,48)
        self.assertEqual(obj.gates,{3:0.,4:0.})
        self.assertNotEqual(obj.weights,list(parent.W0))
        self.assertEqual(m.PARAM_COUNTS["fixed_half_local_gates"],8)

    def test_near_unit_gate_is_preregistered_upper_bound_not_tuning(self):
        a=m.FrozenGateTemporal(5.)
        b=m.FrozenGateTemporal(0.)
        h=(1,1,0,1)
        self.assertGreater(a.local_features(h)[1],b.local_features(h)[1])
        self.assertGreater(a.local_features(h)[2],b.local_features(h)[2])
        self.assertAlmostEqual(a.local_features(h)[1],parent.sig(5.))
        self.assertEqual(m.PARAM_COUNTS["fixed_near_unit_local_gates"],8)
        with self.assertRaisesRegex(ValueError,"AC22_UNPREREGISTERED_GATE_INTERVENTION"):
            m.FrozenGateTemporal(-1.)

    def test_ten_parameter_control_updates_all_fitted_features(self):
        obj=m.TenCoefficientFullHistoryLogistic()
        self.assertEqual(len(obj.weights),10)
        h=(1,1,1,1)
        self.assertEqual(len(obj.features(h)),10)
        initial=list(obj.weights)
        parent.fit(obj,[(h,1),((0,0,0,0),0)])
        self.assertEqual(obj.updates,48)
        self.assertNotEqual(obj.weights[-2:],initial[-2:])
        self.assertEqual(m.PARAM_COUNTS["matched_ten_coefficient_full_history_logistic"],10)

    def test_replayed_transport_has_identical_public_features(self):
        for h in itertools.product((0,1),repeat=4):
            for obj in (m.CountingTemporal(),m.FrozenGateTemporal(0.),m.FrozenGateTemporal(5.)):
                packet_features=obj.local_features(h)
                manual=parent.encode_features(h[0]*parent.sig(obj.gates[3]),
                     h[1]*parent.sig(obj.gates[4]),h[2],h[3])
                self.assertEqual(packet_features,manual)
                self.assertGreater(obj.messages_delivered,0)
                self.assertGreater(obj.calls_to_two_hop_transport,0)
        self.assertFalse(hasattr(m.CountingTemporal(),"u"))

    def test_eight_fit_only_left_out_folds_not_dev(self):
        # Synthetic data tests the algorithm's gating, NOT new scientific data.
        rows=[(seed,((i>>3)&1,(i>>2)&1,(i>>1)&1,i&1),i%2)
              for i,seed in enumerate(m.FIT_SEEDS)]
        r=m.diagnose_fit_only(rows)
        self.assertEqual(r["fit_examples_only"],8)
        self.assertEqual(r["leave_one_out_fit_folds"],8)
        self.assertEqual(r["updates_each_model_each_fold"],168)
        self.assertEqual(r["previous_dev_episodes_read"],0)
        self.assertEqual(r["original_dtr_source_imports_or_episodes"],0)
        self.assertFalse(r["scientific_admission"])
        self.assertEqual(set(r["fit_only_left_out_metrics"]),set(m.PARAM_COUNTS))
        for key,model in r["fit_only_fold_predictions"].items():
            self.assertEqual(len(model),8)
            self.assertEqual([row["seed"] for row in model],list(m.FIT_SEEDS))
            self.assertTrue(all(z["trained_updates"]==168 for z in model))
            self.assertTrue(math.isfinite(r["fit_only_left_out_metrics"][key]["brier"]))

    def test_fit_custody_rejects_missing_original_signature(self):
        with self.assertRaisesRegex(RuntimeError,"AC22_AUTHENTIC_PARENT_SOURCE_CUSTODY_NOT_ESTABLISHED"):
            m.original_public_fit_only({"schema":"synthetic"})
        with self.assertRaisesRegex(RuntimeError,"AC22_FIT_ONLY_ROWS_INVALID"):
            m.diagnose_fit_only([])

if __name__=="__main__":
    unittest.main()
