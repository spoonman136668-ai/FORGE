"""G98 exact frozen-controls and full-case screening guards, CPU only."""
import unittest

import numpy as np
from threadpoolctl import threadpool_limits

from g98_kv_subspace import (
    DIMENSION, POSITIONS, QUERIES, RANKS, REGIMES, RELATIVE_TOLERANCE,
    SCHEMA, SEEDS, SPEEDUP_FLOOR, TRIALS, compress, compressed_attention,
    dense_attention, screen, workload,
)


class G98Guards(unittest.TestCase):
    def test_frozen_protocol(self):
        self.assertEqual(SEEDS, (9801, 9802, 9803))
        self.assertEqual(REGIMES, ("iid", "lowrank_favorable"))
        self.assertEqual(RANKS, (8,16,32))
        self.assertEqual((POSITIONS,DIMENSION,QUERIES,TRIALS), (512,64,8,7))
        self.assertEqual((RELATIVE_TOLERANCE,SPEEDUP_FLOOR), (1e-3,1.15))

    def test_shape_reconstruction_and_exact_full_rank_limit(self):
        with threadpool_limits(limits=1):
            for regime in REGIMES:
                keys,values,queries=workload(SEEDS[0],regime)
                self.assertEqual(keys.shape,(POSITIONS,DIMENSION))
                self.assertEqual(values.shape,(POSITIONS,DIMENSION))
                self.assertEqual(queries.shape,(QUERIES,DIMENSION))
                for rank in RANKS:
                    ka,kb,ke=compress(keys,rank)
                    va,vb,ve=compress(values,rank)
                    self.assertEqual(ka.shape,(POSITIONS,rank))
                    self.assertEqual(kb.shape,(rank,DIMENSION))
                    self.assertTrue(np.isfinite([ke,ve]).all())
                    estimate=compressed_attention(ka,kb,va,vb,queries[0])
                    self.assertEqual(estimate.shape,(DIMENSION,))
                    self.assertTrue(np.all(np.isfinite(estimate)))
                # r=64 is a correctness-only guard, NOT an experimental
                # candidate rank or part of the frozen 144-case screen.
                ka,kb,ke=compress(keys,64)
                va,vb,ve=compress(values,64)
                base=dense_attention(keys,values,queries[0])
                replay=compressed_attention(ka,kb,va,vb,queries[0])
                self.assertTrue(np.allclose(replay,base,rtol=1e-10,atol=1e-10))

    def test_deliberately_favorable_lowrank_is_not_iid(self):
        keys,values,_=workload(SEEDS[0],"lowrank_favorable")
        ka,kb,kerror=compress(keys,8)
        va,vb,verror=compress(values,8)
        self.assertLess(kerror,0.002)
        self.assertLess(verror,0.002)

    def test_complete_frozen_144_case_screen(self):
        with threadpool_limits(limits=1):
            result=screen()
        self.assertEqual(result["schema"],SCHEMA)
        self.assertEqual(len(result["cases"]),144)
        self.assertEqual(len(result["setup"]),18)
        self.assertTrue(all(np.isfinite(c["speedup"]) and c["finite"] for c in result["cases"]))
        self.assertEqual(result["authentic_checkpoint"],"NOT_RUN")
        self.assertEqual(result["gpu_measured"],"NOT_RUN")
        self.assertEqual(result["scientific_acceptance"],"NOT_GRANTED")
        self.assertIn(result["decision"],("NO_GO_SYNTHETIC_SCREEN",
                                         "CONDITIONAL_CPU_FEASIBILITY_ONLY"))


if __name__=="__main__":
    unittest.main()
