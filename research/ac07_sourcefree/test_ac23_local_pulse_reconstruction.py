"""AC-23 focused tests for reward-blind local retention and no new source use."""
import math
import unittest

import ac21_local_temporal_memory as old
import ac22_fit_only_retention_diagnostics as ac22
import ac23_local_pulse_reconstruction as ac23

class TestLocalPulseReconstruction(unittest.TestCase):
    def test_reconstruction_gradient_exact_predeclared_formula(self):
        m=ac23.LocalPulseReconstruction()
        self.assertEqual(m.local_self_reconstruct(3,1),0.20*0.5*0.5*0.5)
        self.assertAlmostEqual(m.gates[3],0.025)
        self.assertEqual(m.local_self_reconstruct(4,0),0.)
        self.assertEqual(m.gates[4],0.)
        self.assertEqual(m.local_pulse_update_calls,{3:1,4:1})

    def test_gate_update_ignores_terminal_reward_and_future_public_bits(self):
        a=ac23.LocalPulseReconstruction()
        b=ac23.LocalPulseReconstruction()
        a.observe((1,1,0,0),0)
        b.observe((1,1,1,1),1)
        self.assertEqual(a.gates,b.gates)
        self.assertNotEqual(a.weights,b.weights)
        self.assertEqual(a.local_nonzero_pulses,{3:1,4:1})
        self.assertEqual(b.local_nonzero_pulses,{3:1,4:1})

    def test_locality_and_invalid_inputs_reject(self):
        m=ac23.LocalPulseReconstruction()
        with self.assertRaisesRegex(ValueError,"AC23_NONLOCAL_GATE_SITE"):
            m.local_self_reconstruct(5,1)
        with self.assertRaisesRegex(ValueError,"AC21_INVALID_PUBLIC_LOCAL_SITE_PULSE"):
            m.local_self_reconstruct(3,True)
        with self.assertRaisesRegex(ValueError,"AC21_INVALID_PUBLIC_TERMINAL_REWARD"):
            m.observe((1,1,0,1),True)
        with self.assertRaisesRegex(ValueError,"AC23_PUBLIC_TWO_STAGE_HISTORY_INVALID"):
            m.observe((1,1),1)
        early,_=m.transport((1,1,0,1),rounds=1)
        fully,_=m.transport((1,1,0,1),rounds=2)
        self.assertNotIn("s1",early)
        self.assertEqual(set(fully),{"s1","x1"})

    def test_only_local_two_gate_parameters_moved_and_cold_restored(self):
        m=ac23.LocalPulseReconstruction()
        rows=[((1,1,0,1),1),((0,0,1,0),0)]
        old.fit(m,rows)
        self.assertEqual(m.updates,48)
        self.assertEqual(m.local_pulse_update_calls,{3:48,4:48})
        self.assertGreater(m.gates[3],0)
        self.assertGreater(m.gates[4],0)
        r=ac23.LocalPulseReconstruction.restore(m.snapshot())
        self.assertEqual(r.snapshot(),m.snapshot())
        self.assertAlmostEqual(r.predict((1,1,1,0)),m.predict((1,1,1,0)))

    def test_one_gate_never_trains_when_own_pulse_zero(self):
        m=ac23.LocalPulseReconstruction()
        old.fit(m,[((1,0,1,1),1)])
        self.assertGreater(m.gates[3],0)
        self.assertEqual(m.gates[4],0.)
        self.assertEqual(m.local_nonzero_pulses[4],0)
        self.assertEqual(m.local_pulse_update_calls[4],24)

    def test_fixed_eight_fold_fit_only_replay_and_comparison(self):
        # Synthetic fixtures verify protocol only; genuine source FIT data
        # must independently pass archived original SHA/check in workflow.
        rows=[(seed,((i>>3)&1,(i>>2)&1,(i>>1)&1,i&1),i%2)
              for i,seed in enumerate(ac22.FIT_SEEDS)]
        result=ac23.fit_only_diagnostic(rows)
        self.assertEqual(result["metric"]["n"],8)
        self.assertEqual(len(result["folds"]),8)
        self.assertEqual(result["local_pulse_reconstruction_calls_total"],8*2*7*24)
        for receipt in result["folds"]:
            self.assertEqual(receipt["fit_reward_head_updates"],168)
            self.assertEqual(receipt["local_pulse_update_calls"],{"3":168,"4":168} if False else {3:168,4:168})
            self.assertGreater(receipt["checkpoint_bytes"],0)
            self.assertEqual(len(receipt["checkpoint_sha256"]),64)
        self.assertTrue(math.isfinite(result["metric"]["brier"]))
        with self.assertRaisesRegex(RuntimeError,"AC23_SOURCE_FIT_ROWS_NOT_FROZEN"):
            ac23.fit_only_diagnostic(rows[:7])

if __name__=="__main__":
    unittest.main()
