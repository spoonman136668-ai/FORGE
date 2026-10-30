"""G61 source pin and benchmark validity: no package/network required."""
import importlib.util
import tempfile
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location("g61",Path(__file__).with_name("g61_tinyllama_sdpa.py"))
g=importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
class G61FalsificationTests(unittest.TestCase):
 def test_authentic_checksum(self):
  self.assertEqual(g.WEIGHT_SHA,"6e6001da2106d4757498752a021df6c2bdc332c650aae4bae6b0c004dcf14933")
  self.assertEqual(g.WEIGHT_SIZE,2200119864)
 def test_frozen_git_identity(self):
  self.assertEqual(g.REV,"c13e4efb205d7a8e5d13c088aa10a9dabac9b96a")
  self.assertEqual(g.REPO,"TinyLlama/TinyLlama-1.1B-Chat-v1.0")
 def test_both_backends_and_windows(self):
  self.assertEqual(g.BACKENDS,("eager","sdpa"))
  self.assertEqual(g.CONTEXTS,(128,512,1536))
  self.assertTrue(all(n+g.GENERATED<=2048 for n in g.CONTEXTS))
 def test_paired_alternating_order(self):
  self.assertEqual([g.repetition_order(i) for i in range(5)],[("eager","sdpa"),("sdpa","eager"),("eager","sdpa"),("sdpa","eager"),("eager","sdpa")])
 def test_paired_medians(self):
  vals=[{"prefill_s":n,"decode_32_s":n*2,"total_s":n*3} for n in (3,1,2)]
  self.assertEqual(g.median_times(vals),{"prefill_s":2,"decode_32_s":4,"total_s":6})
 def test_reject_tampered_weights(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"model.safetensors";p.write_bytes(b"not a checkpoint")
   with self.assertRaises(RuntimeError):g.source_guard(p)
 def test_no_novel_speed_claim(self):
  s=Path(__file__).with_name("g61_tinyllama_sdpa.py").read_text(encoding="utf-8")
  self.assertIn('"new_acceleration_discovered":False',s)
  self.assertIn('ATTENTION_KERNEL_GREEDY_OUTPUT_DIVERGENCE',s)
  self.assertIn('GPU_MODEL_CPU_FALLBACK',s)
  self.assertIn('REAL_ATTENTION_DISPATCH_MISMATCH',s)
  self.assertIn('actual_attention_operator_proof',s)
if __name__=="__main__":unittest.main()
