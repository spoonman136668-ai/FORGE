"""CPU G75 frozen source-only negative controls: no inference models or network."""
import importlib.util
from pathlib import Path
import unittest

P=Path(__file__).with_name("g75_kv_codec.py")
s=importlib.util.spec_from_file_location("cpu_g75_codec",P)
g=importlib.util.module_from_spec(s)
s.loader.exec_module(g)

class G75NativeShapedFeasibility(unittest.TestCase):
    def test_frozen_prereg_before_code(self):
        g.contract()
        self.assertEqual(g.PREREG,"64db89c76b93581d36dae3cc90800535d866612e")
        self.assertEqual(g.SEED,751975)
        self.assertEqual((g.N_REPS,g.N_WARMUPS),(10,5))
    def test_original_native_gpt2_shape_only(self):
        import numpy as np
        xs=g.seed_inputs(64,np)
        g.validate(xs,np)
        self.assertEqual(len(xs),24)
        self.assertEqual(xs[0].shape,(1,12,64,64))
    def test_deterministic_frozen_input(self):
        import numpy as np
        xs=g.seed_inputs(64,np)
        self.assertEqual(g.original_digest(xs),g.original_digest(g.seed_inputs(64,np)))
        self.assertNotEqual(g.original_digest(xs),g.original_digest(g.seed_inputs(256,np)))
    def test_readonly_is_alias_not_deepcopy(self):
        import numpy as np
        xs=g.seed_inputs(64,np)
        a=g.readonly(xs);b=g.deepcopy(xs,np)
        self.assertTrue(all(np.shares_memory(x,y) for x,y in zip(xs,a)))
        self.assertTrue(all(not np.shares_memory(x,y) and np.array_equal(x,y)
                            for x,y in zip(xs,b)))
    def test_codec_is_compressed_but_lossy(self):
        import numpy as np
        xs=g.seed_inputs(64,np)
        packed=g.codec(xs,np)
        recovered=g.decode(packed,np)
        self.assertLessEqual(g.payload_bytes(packed)/sum(t.nbytes for t in xs),.30)
        self.assertTrue(any(not np.array_equal(x,y) for x,y in zip(xs,recovered)))
        self.assertLessEqual(max(float(np.max(np.abs(x-y))) for x,y in zip(xs,recovered)),.05)
    def test_zero_safely_round_trips(self):
        import numpy as np
        xs=tuple(np.zeros((1,12,1,64),dtype=np.float32) for _ in range(24))
        packed=g.codec(xs,np)
        self.assertTrue(all(float(scale)==1.0 for _,scale in packed))
        self.assertTrue(all(np.array_equal(a,b) for a,b in zip(xs,g.decode(packed,np))))
    def test_nonfinite_and_shape_rejection(self):
        import numpy as np
        xs=list(g.seed_inputs(64,np))
        xs[0][0,0,0,0]=np.nan
        with self.assertRaisesRegex(ValueError,"G75_NONFINITE_ORIGINAL_INPUT"):
            g.validate(tuple(xs),np)
        with self.assertRaisesRegex(ValueError,"G75_NATIVE_SHAPE_DTYPE_INVALID"):
            g.validate(tuple(xs[:-1]+[np.ones((2,3),dtype=np.float32)]),np)
    def test_p95_and_precise_gate(self):
        self.assertEqual(g.p95(list(range(10))),9)
        self.assertEqual(g.THRESHOLDS,{"max_abs_error":0.05,"max_payload_ratio":0.30,
          "speedup_256_min":1.15,"min_pair_256":0.90,"rss_ratio_256_max":1.10,
          "slowdown_64_512_max":1.20})
    def test_no_original_model_or_promotion(self):
        v=P.read_text()
        self.assertIn('"original_pretrained_model_executed":False',v)
        self.assertIn('"scientific_acceptance":"NOT_GRANTED"',v)
        self.assertIn('"promotion_allowed":False',v)
        self.assertIn('else "NO_GO_FEASIBILITY"',v)
        self.assertNotIn("from transformers",v)
        self.assertNotIn("model.generate(",v)

if __name__=="__main__":unittest.main()
