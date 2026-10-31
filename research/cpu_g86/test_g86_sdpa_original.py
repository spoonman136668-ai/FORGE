"""G86 deterministic admission tests; no pretrained model download or performance claim."""
import importlib.util
from pathlib import Path
import unittest

P=Path(__file__).with_name("g86_sdpa_original.py")
S=importlib.util.spec_from_file_location("g86_sdpa",P)
g=importlib.util.module_from_spec(S);S.loader.exec_module(g)

class G86SDPAAdmission(unittest.TestCase):
    def test_frozen_identity_and_budget(self):
        g.contract()
        self.assertEqual(g.PREREG,"30b5e1b7cd6e2df40e2923312120dc5808bb1602")
        self.assertEqual((g.OFFSET,g.CASES,g.REPEATS,g.TOKENS,g.CPU_BUDGET),(156,12,4,8,3))
        self.assertEqual(g.ARMS,("eager1","eager2","eager3","sdpa1","sdpa2","sdpa3"))
        self.assertEqual(g.ARM_SPEC,{"eager1":("eager",1),"eager2":("eager",2),"eager3":("eager",3),
                                    "sdpa1":("sdpa",1),"sdpa2":("sdpa",2),"sdpa3":("sdpa",3)})
        self.assertEqual(g.THRESHOLDS,{"speedup_min":1.15,"min_paired":.90,"p95_max":1.10,"rss_max":1.10,"cpu_max":1.25})

    def test_original_model_and_dataset_identity(self):
        self.assertEqual(g.MODEL_REV,"607a30d783dfa663caf39e06633721c8d4cfcd7e")
        self.assertEqual(g.WEIGHTS_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
        self.assertEqual(g.DATA_REV,"3101c7d5072418e28b9008a6636bde82a006892c")
        self.assertEqual(g.DATA_SHA,"3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14")
        self.assertEqual(g.DATA_BYTES,749738)

    def test_rank_boundary_and_disjointness(self):
        records=[{"instruction":f"original question {i}","category":"math"} for i in range(240)]
        chosen=g.rank_original(records,g.OFFSET+g.CASES)
        self.assertEqual(len(chosen),168)
        self.assertEqual(chosen[156]["source_row"],g.rank_original(records,168)[156]["source_row"])
        self.assertEqual(len({x["source_row"] for x in chosen}),168)
        self.assertEqual([x["rank_sha256"] for x in chosen],sorted(x["rank_sha256"] for x in chosen))

    def test_schedule_includes_all_six_arms(self):
        self.assertEqual(len(g.ARMS)*g.CASES*g.REPEATS,288)
        self.assertEqual(len(g.ARMS)*g.CASES*g.REPEATS*g.TOKENS,2304)
        for i in range(g.CASES):
            for rep in range(g.REPEATS):
                self.assertEqual(set(g.schedule(i,rep)),set(g.ARMS))

    def trial(self,i,rep,sdpa_wall=70,eager_wall=100):
        measure={}
        for name in g.ARMS:
            backend,threads=g.ARM_SPEC[name]
            wall=sdpa_wall if backend=="sdpa" else eager_wall
            measure[name]={"wall_ns":wall,"process_cpu_ns":80,
                "rss_sampled":9000,"output_sha256":"same",
                "sdpa_dispatch_calls":12 if backend=="sdpa" else 0,
                "eager_dispatch_calls":0 if backend=="sdpa" else 12,
                "backend_dispatch_calls":12}
        return {"sample_index":i,"rep":rep+1,"order":g.schedule(i,rep),"measure":measure}

    def trials(self,sdpa_wall=70,eager_wall=100):
        return [self.trial(i,rep,sdpa_wall,eager_wall) for i in range(g.CASES) for rep in range(g.REPEATS)]

    def test_frozen_positive_decision_fixture_only(self):
        arms,summary,decision=g.decide(self.trials())
        self.assertEqual(decision,"SDPA_PASS")
        self.assertEqual(summary["timed_authentic_responses"],288)
        self.assertEqual(summary["timed_authentic_generated_tokens"],2304)
        self.assertGreater(summary["primary_median_speedup_sdpa2_vs_eager2"],1.15)

    def test_frozen_negative_decision_fixture_only(self):
        self.assertEqual(g.decide(self.trials(95,100))[2],"SDPA_NO_GO")

    def test_fail_closed_output_mismatch_and_backend_fallback(self):
        trials=self.trials()
        trials[0]["measure"]["sdpa1"]["output_sha256"]="mismatch"
        with self.assertRaisesRegex(RuntimeError,"G86_ORIGINAL_TOKEN_PARITY_ERROR"):
            g.decide(trials)
        trials=self.trials()
        trials[0]["measure"]["sdpa1"]["sdpa_dispatch_calls"]=0
        with self.assertRaisesRegex(RuntimeError,"G86_SDPA_NOT_ACTUALLY_CALLED_sdpa1"):
            g.decide(trials)

    def test_no_promotion_or_weight_change_path(self):
        source=P.read_text(encoding="utf-8")
        for fragment in ('"scientific_acceptance":"NOT_GRANTED"','"promotion_allowed":False',
                         'attn_implementation="eager"','attn_implementation="sdpa"',
                         'G86_SDPA_BACKEND_NOT_EXCLUSIVELY_DISPATCHED',
                         'G86_EAGER_BACKEND_NOT_EXCLUSIVELY_DISPATCHED'):
            self.assertIn(fragment,source)
        self.assertNotIn("model.train(",source)
        self.assertNotIn("model.cuda(",source)

if __name__=="__main__":unittest.main()
