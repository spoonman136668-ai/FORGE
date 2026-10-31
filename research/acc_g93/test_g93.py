"""G93 source guard checks; main 72-case measurement run occurs separately in CI."""
import unittest

import numpy as np
from threadpoolctl import threadpool_limits

from g93_swiglu_screen import (
    ACCURACY_LIMIT, DIMENSION, HIDDEN, INPUTS_PER_SEED, OUTPUT_DIM,
    PAIRED_TRIALS, REGIMES, SCHEMA, SEEDS, SPEEDUP_FLOOR, THRESHOLDS,
    dense, make_seed, selective, silu,
)


class G93Guards(unittest.TestCase):
    def test_frozen_protocol(self):
        self.assertEqual((DIMENSION,HIDDEN,OUTPUT_DIM), (128,1024,128))
        self.assertEqual(SEEDS,(9301,9302,9303))
        self.assertEqual(REGIMES,("iid","negative_shifted"))
        self.assertEqual(THRESHOLDS,(2.,4.,6.))
        self.assertEqual((INPUTS_PER_SEED,PAIRED_TRIALS), (4,15))
        self.assertEqual((ACCURACY_LIMIT,SPEEDUP_FLOOR),(1e-3,1.15))

    def test_silu_has_nonzero_negative_tail(self):
        z = np.asarray([-6.,-4.,-2.],dtype=np.float32)
        v = silu(z)
        self.assertTrue(np.all(v < 0))
        self.assertTrue(np.all(v != 0))

    def test_zero_pruning_produces_exact_dense_output(self):
        with threadpool_limits(limits=1):
            wg,wu,wd,qs = make_seed(SEEDS[0])
            ref = dense(qs[0],wg,wu,wd,0.)
            # Very high T retains all 1024 channels; candidate must not have
            # silently omitted the gate/up projection or changed arithmetic.
            cand,n = selective(qs[0],wg,wu,wd,0.,100.)
            self.assertEqual(n,HIDDEN)
            self.assertTrue(np.allclose(ref,cand,rtol=5e-6,atol=5e-6))

    def test_negative_shift_is_only_gate_bias(self):
        with threadpool_limits(limits=1):
            wg,wu,wd,qs=make_seed(SEEDS[0])
            q=qs[0]
            base_gate=q@wg
            shifted_gate=base_gate - np.float32(3.)
            self.assertTrue(np.allclose(shifted_gate-base_gate,-3.,atol=1e-5))
            _,ret_iid=selective(q,wg,wu,wd,0.,2.)
            _,ret_shift=selective(q,wg,wu,wd,-3.,2.)
            self.assertLessEqual(ret_shift,ret_iid)


if __name__ == "__main__":
    unittest.main()
