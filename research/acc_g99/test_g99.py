"""G99 frozen INT8 packing, exact byte accounting and 144-case CPU guards."""
import unittest

import numpy as np
from threadpoolctl import threadpool_limits

from g99_outlier_int8 import (
    COLUMNS, ERROR_LIMIT, INJECTED_GAIN, INJECTED_PER_ROW, OUTLIER_K,
    QUERIES, REGIMES, ROWS, SCHEMA, SEEDS, SPEEDUP_FLOOR, STORAGE_LIMIT,
    TRIALS, compress, generate, mixed_matvec, reference, screen,
)


class G99Guards(unittest.TestCase):
    def test_frozen_parameters(self):
        self.assertEqual(SEEDS,(9901,9902,9903))
        self.assertEqual(REGIMES,("iid","injected_outliers"))
        self.assertEqual(OUTLIER_K,(0,2,8))
        self.assertEqual((ROWS,COLUMNS,QUERIES,INJECTED_PER_ROW,INJECTED_GAIN),
                         (512,256,8,4,32.))
        self.assertEqual((TRIALS,ERROR_LIMIT,SPEEDUP_FLOOR,STORAGE_LIMIT),
                         (7,1e-2,1.15,.65))

    def test_byte_count_dtype_and_no_free_decoded_weights(self):
        with threadpool_limits(limits=1):
            w,q=generate(SEEDS[0],"iid")
            self.assertEqual(w.dtype,np.float32)
            self.assertEqual(w.shape,(ROWS,COLUMNS))
            self.assertEqual(q.shape,(QUERIES,COLUMNS))
            for k in OUTLIER_K:
                packed=compress(w,k)
                self.assertEqual(packed["codes"].dtype,np.int8)
                self.assertEqual(packed["scales"].dtype,np.float32)
                self.assertEqual(packed["columns"].dtype,np.uint16)
                self.assertEqual(packed["residual"].dtype,np.float32)
                self.assertEqual(packed["candidate_bytes"],
                                 ROWS*COLUMNS+ROWS*4+ROWS*k*6)
                self.assertEqual(packed["baseline_bytes"],ROWS*COLUMNS*4)
                self.assertLessEqual(packed["stored_fraction"],STORAGE_LIMIT)
                self.assertNotIn("decoded",packed)
                self.assertNotIn("float_weights",packed)
                self.assertEqual(mixed_matvec(packed,q[0]).shape,(ROWS,))

    def test_sparse_float_residual_preserves_original_extremes(self):
        with threadpool_limits(limits=1):
            w,q=generate(SEEDS[0],"injected_outliers")
            packed=compress(w,8)
            rows=np.arange(ROWS)[:,None]
            self.assertTrue(np.array_equal(packed["residual"],
                                           w[rows,packed["columns"]]))
            self.assertTrue(np.all(np.isfinite(mixed_matvec(packed,q[0]))))
            self.assertGreater(float(np.max(np.abs(w))),
                               float(np.max(np.abs(generate(SEEDS[0],"iid")[0]))))

    def test_screen_custody_and_all_cases(self):
        with threadpool_limits(limits=1):
            result=screen()
        self.assertEqual(result["schema"],SCHEMA)
        self.assertEqual(len(result["cases"]),144)
        self.assertEqual(len(result["setup"]),18)
        self.assertTrue(all(c["finite"] and np.isfinite(c["relative_l2"])
                            for c in result["cases"]))
        self.assertEqual(result["gpu_measured"],"NOT_RUN")
        self.assertEqual(result["authentic_checkpoint"],"NOT_RUN")
        self.assertEqual(result["scientific_acceptance"],"NOT_GRANTED")
        self.assertIn(result["decision"],("NO_GO_SYNTHETIC_SCREEN",
                                         "CONDITIONAL_CPU_FEASIBILITY_ONLY"))


if __name__=="__main__":
    unittest.main()
