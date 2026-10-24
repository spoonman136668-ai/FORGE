import unittest
from o19_capacity import optimum,replay,periodic,periodic_source_writer

class CapacityGate(unittest.TestCase):
 def test_optimum_7_4_51(self):
  p=optimum(); self.assertEqual((p['steps'],p['scored'],p['max_guaranteed_retrievable']),(51,44,26))
 def test_dp_constructive_replay(self):
  p=optimum();r=replay(p['choices']);self.assertEqual(r['guaranteed_hit_count'],p['max_guaranteed_retrievable']);self.assertLessEqual(r['peak_slots'],4)
 def test_periodic_source_writer_constructive(self):
  p=periodic_source_writer();self.assertEqual(p['guaranteed_hit_count'],26);self.assertEqual(p['peak_slots'],4)
 def test_no_oracle_timestamp_schedule(self):
  self.assertEqual(periodic()['guaranteed_hit_times'],periodic_source_writer()['times'])
 def test_capacity_monotonic(self):
  for k in (2,3,4):self.assertLessEqual(optimum(cap=k)['max_guaranteed_retrievable'],optimum(cap=4)['max_guaranteed_retrievable'])
 def test_full_capacity(self):
  self.assertEqual(optimum(cap=7)['max_guaranteed_retrievable'],44)
 def test_one_slot_upper(self):
  self.assertEqual(optimum(cap=1)['max_guaranteed_retrievable'],7)

if __name__=='__main__':unittest.main()
