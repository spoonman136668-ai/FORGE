"""No pretrained model or network required for frozen G67 source controls."""
import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).with_name("g67_heldout_http.py")
spec=importlib.util.spec_from_file_location("g67_heldout_http",path)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class G67Frozen(unittest.TestCase):
    def test_contract(self):m.contract()
    def test_model_revision(self):
        self.assertEqual(m.MODEL_REV,"607a30d783dfa663caf39e06633721c8d4cfcd7e")
        self.assertEqual(m.WEIGHTS_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
    def test_dataset_revision(self):
        self.assertEqual(m.DATA_REV,"2fab627bd77969fb4c73ba6a7e48cefc615b04ba")
        self.assertEqual(m.DATA_SHA,"8419d2c537511d5dd7565ecbb1890bc9e5aeafc6c34aebc9d208447045a168e4")
    def test_prereg(self):
        self.assertEqual(m.PREREG,"928e50853ada4b30ebb81f4825e534dc1cef7275")
    def test_no_false_few_records(self):
        with self.assertRaises(RuntimeError):m.select_heldout([{"instruction":"A","category":"x"}])
    def test_duplicates_not_validated(self):
        with self.assertRaises(RuntimeError):
            m.select_heldout([{"instruction":"SAME","category":"x"}]*40)
    def test_deterministic_reordering(self):
        records=[{"instruction":f"human question {i}","category":"open_qa"} for i in range(100)]
        out=m.select_heldout(records)
        self.assertEqual([x["instruction"] for x in out],
                        [x["instruction"] for x in m.select_heldout(records)])
        self.assertEqual(len(set(x["instruction"] for x in out)),12)
    def test_p95(self):
        self.assertEqual(m.p95([7,1,3,6,2,8,0,4,5,9,10,11]),11)
    def test_first_sighting_never_admits(self):
        seen=set()
        self.assertFalse(m.observe_cache(seen,(1,2)))
        self.assertTrue(m.observe_cache(seen,(1,2)))
    def test_exact_kv_caps(self):
        self.assertEqual((m.CACHE_ENTRIES,m.CACHE_BYTES),(2,42000000))
    def test_arms(self):
        self.assertEqual(m.ARMS,("baseline_incremental","hf_generate","shared_prefix"))
    def test_frozen_thresholds(self):
        self.assertEqual(m.THRESHOLDS,{"high_vs_fastest":1.10,"unique_vs_fastest":0.98,"high_p95_ratio":1.20})
    def test_nonpromotion(self):
        import inspect
        s=inspect.getsource(m.main)
        self.assertIn('"promotion_allowed":False',s)
        self.assertIn('"scientific_acceptance":"NOT_GRANTED"',s)
        self.assertIn('127.0.0.1',s)

if __name__=="__main__":
    unittest.main()
