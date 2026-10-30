import importlib.util
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('g55',Path(__file__).with_name('g55_gpt2_exact_reuse.py'))
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
class ExactReuseTests(unittest.TestCase):
 def test_hash_detects_duplicate(self):
  self.assertEqual(m.exact_row_reuse([(1,b'x'),(1,b'x'),(2,b'x')])['duplicate_rows'],1)
 def test_nonprefix_cross_layer_not_same(self):
  self.assertEqual(m.exact_row_reuse([(1,b'x'),(2,b'x')])['duplicate_rows'],0)
 def test_block_zeros(self):
  r=m.zero_block_counts([0,0,4,0],2)
  self.assertEqual((r['exact_zero_values'],r['all_zero_blocks']),(3,1))
 def test_block_misalignment(self):
  with self.assertRaises(ValueError):m.zero_block_counts([1,2,3],2)
 def test_cross_layer_equal_bytes(self):
  r=m.duplicate_cross_layer_blocks([(1,b'1234abcd'),(2,b'1234ZZZZ')],4)
  self.assertEqual((r['cross_layer_duplicate_blocks'],r['eligible_blocks']),(1,4))
 def test_same_layer_not_counted_cross_layer(self):
  r=m.duplicate_cross_layer_blocks([(1,b'12341234')],4)
  self.assertEqual((r['cross_layer_duplicate_blocks'],r['same_layer_duplicate_blocks']),(0,1))
 def test_zero_blocks_boundary(self):
  r=m.zero_block_counts([0]*8,4)
  self.assertEqual(r['all_zero_blocks'],2)
if __name__=='__main__':unittest.main()
