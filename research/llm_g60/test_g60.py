"""Pre-inference G60 contract tests; source-authentic model loaded only on runner."""
import importlib.util
from pathlib import Path
import unittest
p=Path(__file__).with_name("g60_concurrent.py")
spec=importlib.util.spec_from_file_location("g60",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Controls(unittest.TestCase):
    def test_identity(self):
        self.assertEqual(m.REV,"607a30d783dfa663caf39e06633721c8d4cfcd7e")
        self.assertEqual(m.WEIGHT_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
    def test_prereg_committed(self):
        self.assertEqual(m.PREREG_COMMIT,"3b9707887e73a2e38486c65bcc0da37af2ac9dd3")
    def test_arms(self):
        self.assertEqual(m.ARMS,("no_cache","second_seen","adaptive"))
    def test_workload(self):
        self.assertEqual(m.STREAMS["high_locality"],(0,0,0,0,1,1))
        self.assertEqual(m.STREAMS["unique_only"],(0,1,2,3,4,5))
        self.assertEqual(m.STREAMS["thrash"],(0,1,2,0,1,2))
    def test_same_sizes(self):
        self.assertTrue(all(len(x)==6 for x in m.STREAMS.values()))
    def test_tokens_and_trials(self):
        self.assertEqual((m.TOKENS,m.REPEATS,m.WORKERS),(16,3,2))
    def test_cache_budget(self):
        self.assertEqual((m.CAP_ENTRIES,m.CAP_BYTES),(2,42_000_000))
    def test_frozen_screen(self):
        self.assertEqual(m.THRESHOLDS,{"high_locality":1.10,"unique_only":0.95})
    def test_two_concurrent_requests_per_wave(self):
        self.assertEqual(6%m.WORKERS,0)
        self.assertEqual(m.WORKERS,2)
if __name__=="__main__":unittest.main()
