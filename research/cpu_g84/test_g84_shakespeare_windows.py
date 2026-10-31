"""G84 frozen standalone source and decision replication controls. No model download."""
import importlib.util
from pathlib import Path
import unittest

P=Path(__file__).with_name("g84_shakespeare_transfer.py")
S=importlib.util.spec_from_file_location("g84_original",P)
g=importlib.util.module_from_spec(S);S.loader.exec_module(g)

class G84ReplicationAdmission(unittest.TestCase):
    def test_frozen_identity(self):
        g.contract()
        self.assertEqual(g.PREREG,"d914a0e2fcb0653a167158489bf89b3e5bce5af4")
        self.assertEqual((g.CASES,g.REPEATS,g.TOKENS,g.CPU_BUDGET,g.PROMPT_TOKENS),(12,5,8,2,96))
        self.assertEqual(g.ARMS,{"uniform1":(1,1),"uniform3":(3,3),"uniform2":(2,2)})
        self.assertEqual(g.THRESHOLDS,{"speedup_vs_uniform1_min":1.35,
            "speedup_vs_uniform3_min":1.05,"min_paired_vs_uniform3":.90,
            "p95_ratio_vs_uniform3_max":1.10,"rss_ratio_vs_uniform3_max":1.10,
            "cpu_ratio_vs_uniform3_max":1.25})
    def test_authentic_original_model_source(self):
        self.assertEqual(g.MODEL_REV,"607a30d783dfa663caf39e06633721c8d4cfcd7e")
        self.assertEqual(g.WEIGHTS_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
        self.assertEqual(g.DATA_SHA,"86c4e6aa9db7c042ec79f339dcb96d42b0075e16b8fc2e86bf0ca57e2dc565ed")
        self.assertEqual(g.DATA_BYTES,1115394)
        self.assertEqual(g.DATA_REV,"370cbcd448eb7daf32f21a6be560b70e0b33c4e3")
        self.assertEqual(g.CPU_BUDGET,2)
        self.assertIn('os.name != "nt"',P.read_text(encoding="utf-8"))
        self.assertIn('"os_name":os.name',P.read_text(encoding="utf-8"))
        self.assertIn('cpu_g84_windows_result.json',P.read_text(encoding="utf-8"))
    def test_nonoverlapping_pinned_source_tail(self):
        original="".join(chr(32+(i%91)) for i in range(1000000))
        picked=g.select_original_spans(original)
        self.assertEqual(len(picked),12)
        self.assertEqual([x["source_offset"] for x in picked],[i*3072 for i in range(12)])
        self.assertEqual(len({x["original_span_sha256"] for x in picked}),12)
        self.assertTrue(all(len(x["segment"])==2048 for x in picked))
        self.assertTrue(all("segment" not in {k:v for k,v in x.items() if k!="segment"} for x in picked))
    def test_fail_closed_missing_or_duplicate_source(self):
        with self.assertRaisesRegex(RuntimeError,"G84_EMPTY_AUTHENTIC_SOURCE_TEXT"):
            g.select_original_spans("")
        with self.assertRaisesRegex(RuntimeError,"G84_INSUFFICIENT_ORIGINAL_TAIL"):
            g.select_original_spans("a"*5000)
        with self.assertRaisesRegex(RuntimeError,"G84_DUPLICATED_SOURCE_SPANS"):
            g.select_original_spans("a"*1000000)
    def test_rotated_reversed_schedules(self):
        self.assertEqual(len(g.ARMS)*g.CASES*g.REPEATS,180)
        self.assertEqual(len(g.ARMS)*g.CASES*g.REPEATS*g.TOKENS,1440)
        for i in range(g.CASES):
            for r in range(g.REPEATS):
                self.assertEqual(set(g.schedule(i,r)),set(g.ARMS))
    def trial(self,i,rep,candidate_ns=700,one_ns=1200,three_ns=900):
        vals={}
        for name,wall in (("uniform1",one_ns),("uniform3",three_ns),("uniform2",candidate_ns)):
            vals[name]={"wall_ns":wall,"process_cpu_ns":900,"rss_sampled":8000,
              "prefill_ns":wall//2,"cached_decode_ns":wall//3,"output_sha256":"same"}
        return {"sample_index":i,"rep":rep+1,"order":g.schedule(i,rep),"measure":vals}
    def trials(self,*a):
        return [self.trial(i,rep,*a) for i in range(g.CASES) for rep in range(g.REPEATS)]
    def test_positive_fixture_not_real_model(self):
        arms,summary,verdict=g.decide(self.trials())
        self.assertEqual(verdict,"REPLICATION_PASS")
        self.assertEqual(summary["timed_authentic_responses"],180)
        self.assertGreater(summary["median_speedup_vs_uniform3"],1.05)
    def test_negative_fixture_not_real_model(self):
        self.assertEqual(g.decide(self.trials(875,1200,900))[2],"REPLICATION_FAIL")
    def test_fail_closed_parity(self):
        trials=self.trials()
        trials[0]["measure"]["uniform2"]["output_sha256"]="wrong"
        with self.assertRaisesRegex(RuntimeError,"G84_ORIGINAL_TOKEN_PARITY_ERROR"):
            g.decide(trials)
    def test_fail_closed_missing_timing(self):
        trials=self.trials()
        with self.assertRaisesRegex(RuntimeError,"G84_INCOMPLETE_ORIGINAL_PAIRED_TRIALS"):
            g.decide(trials[:-1])
        trials[0]["measure"]["uniform1"]["wall_ns"]=-1
        with self.assertRaisesRegex(RuntimeError,"G84_INVALID_CPU_WALL_OR_RSS_TIMING"):
            g.decide(trials)
    def test_no_promotion_and_cpu_bound(self):
        s=P.read_text(encoding="utf-8")
        for fragment in ('"scientific_acceptance":"NOT_GRANTED"','"promotion_allowed":False',
                         'torch.set_num_threads(pre)','G84_EXACT_ORIGINAL_TOKEN_MISMATCH_',
                         'G84_G55_MODEL_IDENTITY_DRIFT','"transfer":"UNVERIFIED"'):
            self.assertIn(fragment,s)
        self.assertNotIn("model.cuda(",s)
        self.assertNotIn("model.train(",s)
if __name__=="__main__":unittest.main()
