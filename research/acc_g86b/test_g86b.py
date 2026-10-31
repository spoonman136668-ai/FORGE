import unittest
import numpy as np
from g86b_audit import duplicate_rows, audit
class AuditTests(unittest.TestCase):
    def test_no_duplicates(self):
        self.assertEqual(duplicate_rows(np.array([[1,2],[3,4],[5,6]],dtype=np.float16))['duplicate_rows'],0)
    def test_duplicates(self):
        self.assertEqual(duplicate_rows(np.array([[1,2],[3,4],[1,2]],dtype=np.float16))['duplicate_rows'],1)
    def test_negative_zero_is_not_bitwise_equal(self):
        self.assertEqual(duplicate_rows(np.array([[0.0],[-0.0]],dtype=np.float32))['duplicate_rows'],0)
    def test_rank_guard(self):
        with self.assertRaisesRegex(ValueError,'MATRIX_MUST_BE_2D'): duplicate_rows(np.ones((2,2,2)))
    def test_hash_guard(self):
        with self.assertRaisesRegex(ValueError,'EXPECTED_SHA256_REQUIRED'): audit('not-a-file','bad')
if __name__=='__main__': unittest.main()
