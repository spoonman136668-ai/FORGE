"""G87 deterministic CPU Inductor admission tests; no model download or execution."""
import importlib.util
from pathlib import Path
import unittest

P=Path(__file__).with_name("g87_inductor_original.py")
S=importlib.util.spec_from_file_location("g87_inductor",P)
g=importlib.util.module_from_spec(S);S.loader.exec_module(g)

class G87InductorAdmission(unittest.TestCase):
    def test_frozen_identity_budget_and_thresholds(self):
        g.contract()
        self.assertEqual(g.PREREG,"7f2cfff5f2348a28141df4c63792a3bfb659175c")
        self.assertEqual((g.OFFSET,g.CASES,g.REPEATS,g.TOKENS,g.CPU_BUDGET,g.HORIZON),(168,12,4,8,3,1000))
        self.assertEqual(g.ARMS,("eager2","inductor2"))
        self.assertEqual(g.THRESHOLDS,{"speedup_min":1.15,"min_paired":.90,
            "p95_max":1.10,"rss_max":1.10,"cpu_max":1.25,
            "compile_seconds_max":300.0,"break_even_max":1000,"horizon_ratio_max":.95})

    def test_model_and_dataset_identity(self):
        self.assertEqual(g.MODEL_REV,"607a30d783dfa663caf39e06633721c8d4cfcd7e")
        self.assertEqual(g.WEIGHTS_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
        self.assertEqual(g.DATA_REV,"3101c7d5072418e28b9008a6636bde82a006892c")
        self.assertEqual(g.DATA_SHA,"3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14")
        self.assertEqual(g.DATA_BYTES,749738)

    def test_rank_boundary_and_disjointness(self):
        records=[{"instruction":f"original question {i}","category":"math"} for i in range(220)]
        chosen=g.rank_original(records,g.OFFSET+g.CASES)
        self.assertEqual(len(chosen),180)
        self.assertEqual(len({x["source_row"] for x in chosen}),180)
        self.assertEqual([x["rank_sha256"] for x in chosen],
                         sorted(x["rank_sha256"] for x in chosen))

    def trial(self,i,rep,eager_ns=100_000_000,compiled_ns=70_000_000):
        measures={
          "eager2":{"wall_ns":eager_ns,"process_cpu_ns":80_000_000,
                    "rss_sampled":9000,"output_sha256":"same"},
          "inductor2":{"wall_ns":compiled_ns,"process_cpu_ns":80_000_000,
                       "rss_sampled":9000,"output_sha256":"same"}}
        return {"sample_index":i,"rep":rep+1,"order":g.schedule(i,rep),"measure":measures}

    def trials(self,eager_ns=100_000_000,compiled_ns=70_000_000):
        return [self.trial(i,rep,eager_ns,compiled_ns)
                for i in range(g.CASES) for rep in range(g.REPEATS)]

    def test_positive_fixture_decision_and_startup_amortization(self):
        arms,summary,decision=g.decide(self.trials(),.001,1,0)
        self.assertEqual(decision,"INDUCTOR_PASS")
        self.assertEqual(summary["timed_authentic_responses"],96)
        self.assertEqual(summary["timed_authentic_generated_tokens"],768)
        self.assertLessEqual(summary["break_even_full_responses"],1000)
        self.assertLessEqual(summary["amortized_total_wall_ratio_at_1000_responses"],.95)

    def test_negative_fixture_decision(self):
        self.assertEqual(g.decide(self.trials(100_000_000,95_000_000),.001,1,0)[2],
                         "INDUCTOR_NO_GO")

    def test_startup_cost_is_not_ignored(self):
        decision=g.decide(self.trials(),100.0,1,0)[2]
        self.assertEqual(decision,"INDUCTOR_NO_GO")

    def test_fail_closed_token_mismatch_graph_count_and_graph_break(self):
        rows=self.trials()
        rows[0]["measure"]["inductor2"]["output_sha256"]="different"
        with self.assertRaisesRegex(RuntimeError,"G87_ORIGINAL_TOKEN_PARITY_ERROR"):
            g.decide(rows,.001,1,0)
        with self.assertRaisesRegex(RuntimeError,"G87_INDUCTOR_GRAPH_COUNT_OUT_OF_BOUNDS"):
            g.decide(self.trials(),.001,5,0)
        with self.assertRaisesRegex(RuntimeError,"G87_DYNAMO_GRAPH_BREAKS"):
            g.decide(self.trials(),.001,1,1)

    def test_no_promotion_or_weight_change_path(self):
        source=P.read_text(encoding="utf-8")
        for item in ('"scientific_acceptance":"NOT_GRANTED"',
                     '"promotion_allowed":False','fullgraph=True','dynamic=True',
                     'backend=counted_inductor','THRESHOLDS["speedup_min"]'):
            self.assertIn(item,source)
        self.assertNotIn("model.train(",source)
        self.assertNotIn("model.cuda(",source)

if __name__=="__main__":unittest.main()
