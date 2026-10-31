"""G81 standalone frozen original pretrained source-only negative controls."""
import importlib.util
from pathlib import Path
import unittest

P=Path(__file__).with_name("g81_phase_threads.py")
S=importlib.util.spec_from_file_location("cpu_g81_original",P)
g=importlib.util.module_from_spec(S);S.loader.exec_module(g)

class G81OriginalCPUChecks(unittest.TestCase):
    def test_freeze_before_implementation(self):
        g.contract()
        self.assertEqual(g.PREREG,"60c5ebf4fccae6097e7786aba377c6fdedd226a0")
        self.assertEqual((g.OFFSET,g.CASES,g.REPEATS,g.TOKENS,g.CPU_BUDGET),(132,12,3,8,3))
    def test_original_custody(self):
        self.assertEqual(g.WEIGHTS_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
        self.assertEqual(g.DATA_SHA,"3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14")
        self.assertEqual(g.DATA_BYTES,749738)
    def test_original_disjoint_new_cohort(self):
        rows=[{"instruction":f"real-like independent question {i}","category":"math"} for i in range(155)]
        selected=g.rank_original(rows,144)
        self.assertEqual(len(selected),144)
        self.assertEqual(len({x["source_row"] for x in selected}),144)
        self.assertTrue({x["source_row"] for x in selected[132:144]}.isdisjoint(
            {x["source_row"] for x in selected[:132]}))
        with self.assertRaisesRegex(RuntimeError,"G81_INSUFFICIENT_ORIGINAL_HELDOUT"):
            g.rank_original([{"instruction":"same","category":"math"}]*150,144)
    def test_arms_and_affinity(self):
        self.assertEqual(g.ARMS,{"uniform1":(1,1),"uniform2":(2,2),"uniform3":(3,3),"phase3to1":(3,1)})
        self.assertTrue(all(max(a)<=g.CPU_BUDGET for a in g.ARMS.values()))
        self.assertEqual(g.CASES*g.REPEATS*len(g.ARMS),144)
        self.assertEqual(g.CASES*g.REPEATS*len(g.ARMS)*g.TOKENS,1152)
    def test_rotated_and_reversed(self):
        for sample in range(g.CASES):
            for rep in range(g.REPEATS):
                order=g.schedule(sample,rep)
                self.assertEqual(len(order),4)
                self.assertEqual(set(order),set(g.ARMS))
    def trial(self,i,rep,ratio=1):
        entry={}
        for arm in g.ARMS:
            wall=1000 if arm!="phase3to1" else int(1000/ratio)
            entry[arm]={"wall_ns":wall,"process_cpu_ns":1000,
              "rss_sampled":10000,"prefill_ns":wall//2,"cached_decode_ns":wall//3,
              "output_sha256":"same"}
        return {"sample_index":i,"source_row":i+1,"rep":rep+1,
            "order":g.schedule(i,rep),"measure":entry}
    def test_synthetic_only_decision_fixture_go(self):
        trials=[self.trial(i,r,1.4) for i in range(g.CASES) for r in range(g.REPEATS)]
        arms,out,decision=g.decide(trials)
        self.assertEqual(decision,"GO")
        self.assertGreater(out["median_candidate_speedup"],1.15)
        self.assertEqual(out["timed_authentic_responses"],144)
    def test_synthetic_only_decision_fixture_no_go(self):
        trials=[self.trial(i,r,1.01) for i in range(g.CASES) for r in range(g.REPEATS)]
        self.assertEqual(g.decide(trials)[2],"NO_GO")
    def test_fail_closed_no_reference_parity(self):
        trials=[self.trial(i,r,1.4) for i in range(g.CASES) for r in range(g.REPEATS)]
        trials[0]["measure"]["phase3to1"]["output_sha256"]="mismatch"
        with self.assertRaisesRegex(RuntimeError,"G81_ORIGINAL_TOKEN_PARITY_ERROR"):
            g.decide(trials)
    def test_negative_timing_and_missing_trials(self):
        trials=[self.trial(i,r,1.4) for i in range(g.CASES) for r in range(g.REPEATS)]
        with self.assertRaisesRegex(RuntimeError,"G81_INCOMPLETE_ORIGINAL_PAIRED_TRIALS"):
            g.decide(trials[:-1])
        trials[0]["measure"]["uniform1"]["wall_ns"]=-1
        with self.assertRaisesRegex(RuntimeError,"G81_INVALID_CPU_WALL_OR_RSS_TIMING"):
            g.decide(trials)
    def test_control_original_and_no_promotion(self):
        source=P.read_text(encoding="utf-8")
        for snippet in ("torch.set_num_threads(pre)","torch.set_num_threads(dec)",
            'if dec!=pre:', 'strongest_original_uniform_control',
            '"scientific_acceptance":"NOT_GRANTED"','"promotion_allowed":False',
            "G81_EXACT_ORIGINAL_TOKEN_MISMATCH_","G81_G55_MODEL_IDENTITY_DRIFT"):
            self.assertIn(snippet,source)
        self.assertNotIn("model.train(",source)
        self.assertNotIn("model.cuda(",source)

if __name__=="__main__":unittest.main()
