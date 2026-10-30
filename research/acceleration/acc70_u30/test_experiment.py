import importlib.util,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location("acc70",Path(__file__).with_name("experiment.py"))
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def test_01_source(self):self.assertEqual(m.custody()["registry_blob"],m.BLOB)
 def test_02_prereg(self):self.assertEqual(m.custody()["prereg_commit"],m.PRE_COMMIT)
 def test_03_sizes(self):self.assertEqual(m.NS,(4,6,8,10))
 def test_04_seeds(self):self.assertEqual(m.SEEDS,(30011,30013,30017))
 def test_05_gate_count(self):
  for n in m.NS:self.assertEqual(len(m.gates(n,30011)),12)
 def test_06_no_cnot_self(self):
  for n in m.NS:
   for seed in m.SEEDS:self.assertTrue(all(a!=b for op,a,b in m.gates(n,seed) if op=="CNOT"))
 def test_07_replay(self):self.assertEqual(m.gates(8,30011),m.gates(8,30011))
 def test_08_invalid(self):
  with self.assertRaises(ValueError):m.gates(5,30011)
 def test_09_affine_state(self):
  for n in m.NS:self.assertEqual(len(m.affine(n,30011)[1]),3)
 def test_10_all_exact(self):
  for n in m.NS:
   for seed in m.SEEDS:self.assertEqual(m.affine_probabilities(n,seed),m.dense_probabilities(n,seed))
 def test_11_prob_sum(self):
  for n in m.NS:self.assertAlmostEqual(sum(m.affine_probabilities(n,30013)),1)
 def test_12_support(self):
  for n in m.NS:self.assertEqual(sum(x>0 for x in m.affine_probabilities(n,30013)),8)
 def test_13_no_negative(self):
  for n in m.NS:self.assertTrue(all(v>=0 for v in m.dense_probabilities(n,30013)))
 def test_14_output_size(self):
  for n in m.NS:self.assertEqual(len(m.dense_probabilities(n,30017)),1<<n)
 def test_15_sum_dense(self):
  for n in m.NS:self.assertAlmostEqual(sum(m.dense_probabilities(n,30017)),1)
 def test_16_no_real_model_claim(self):self.assertEqual(m.custody()["claim"],"U30")
if __name__=="__main__":unittest.main()
