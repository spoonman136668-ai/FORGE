"""G70 source-only guards for independent disjoint GSM8K human question slice."""
import importlib.util
from pathlib import Path
import unittest
p=Path(__file__).with_name("g70_gsm8k_locality.py")
sp=importlib.util.spec_from_file_location("g70_source",p)
m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
class Frozen(unittest.TestCase):
    def test_contract(self):m.contract()
    def test_prereg(self):self.assertEqual(m.PREREG,"672447c13730c5e841956f4e017b0722517b90d3")
    def test_identity(self):
        self.assertEqual(m.MODEL_REV,"607a30d783dfa663caf39e06633721c8d4cfcd7e")
        self.assertEqual(m.WEIGHTS_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
        self.assertEqual(m.DATA_SHA,"3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14")
    def test_original_ranking_seed(self):
        self.assertEqual(m.SEED,b"G68-GPT2-HELDOUT-20261030:")
        self.assertEqual((m.SELECT_OFFSET,m.CASES),(12,12))
    def test_new_rank_slice_disjoint(self):
        x=[{"instruction":f"human verified request {i}","category":"math_word_problem"} for i in range(80)]
        r=m.select_heldout(x)
        self.assertEqual(len(r),12)
        selected={x["instruction"] for x in r}
        ranks=sorted(x,key=lambda a:__import__("hashlib").sha256(m.SEED+a["instruction"].encode()).hexdigest())
        previous={x["instruction"] for x in ranks[:12]}
        nexts={x["instruction"] for x in ranks[12:24]}
        self.assertFalse(selected&previous)
        self.assertEqual(selected,nexts)
    def test_fail_on_short_original(self):
        with self.assertRaises(RuntimeError):
            m.select_heldout([{"instruction":f"record {i}","category":"c"} for i in range(23)])
    def test_duplication_not_substituted(self):
        with self.assertRaises(RuntimeError):
            m.select_heldout([{"instruction":"same","category":"c"}]*80)
    def test_frozen_localities(self):
        self.assertEqual(m.SHARED_COUNT,{"reuse_0":0,"reuse_25":3,"reuse_50":6,"reuse_75":9})
        self.assertEqual(tuple(m.SHARED_COUNT),m.COHORTS)
    def test_all_negative_guards(self):
        self.assertEqual(m.THRESHOLDS,{"reuse_0":0.98,"reuse_25":0.98,"reuse_50":1.10,"reuse_75":1.30,"reuse_75_p95_ratio":1.20})
    def test_unmodified_arms(self):
        self.assertEqual(m.ARMS,("baseline_incremental","hf_generate","shared_prefix"))
    def test_http_and_limits(self):
        import inspect
        src=inspect.getsource(m.main)
        for text in ('"127.0.0.1"','g68_original.select_heldout(rows)','SHARED_COUNT[cohort]','"NOT_GRANTED"','"NOT_INCLUDED"'):
            self.assertIn(text,src)
        self.assertEqual((m.CACHE_ENTRIES,m.CACHE_BYTES),(2,42000000))
    def test_unchanged_original_output_timing(self):
        self.assertEqual((m.CPU_BUDGET,m.REPEATS,m.TOKENS),(3,2,8))
    def test_p95_12(self):
        self.assertEqual(m.p95(list(range(12))),11)
if __name__=="__main__":unittest.main()
