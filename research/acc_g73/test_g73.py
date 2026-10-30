"""Source-only original G73 negative controls. No model or GPU download."""
import importlib.util
from pathlib import Path
import unittest

SRC=Path(__file__).with_name("g73_full_fp32_reference.py")
spec=importlib.util.spec_from_file_location("g73",SRC)
g=importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

def fake_forced(variant):
    rows={}
    for mode in g.LOGITS_MODES:
        if variant=="original_fp16" and mode=="cached_one_by_one":
            argmax,ties=7866,2
        else:argmax,ties=29871,1
        rows[mode]=[{"greedy_argmax_id":argmax,"exact_max_tie_count":ties,
                     "candidate_minus_baseline_logit":0.0} for _ in range(g.REPEATS)]
    return rows

def fake_case(original=False,hybrid_exact=True,fast=True):
    def arm_stats(variant):
        exact=(not original if variant=="original_fp16" else hybrid_exact)
        msecs_baseline=1.0
        msecs_candidate=.7 if fast else 1.0
        return {"comparison":{"exact":exact},
                "median_seconds":{"baseline":msecs_baseline,"candidate":msecs_candidate},
                "peak_allocated_mib":{"candidate":200.0},
                "runs":{"baseline":[{} for _ in range(g.REPEATS)],
                        "candidate":[{} for _ in range(g.REPEATS)]}}
    return {"variants":{v:arm_stats(v) for v in g.MEASURED_VARIANTS}}

def all_good():
    cases=[fake_case(original=True)]+[fake_case() for _ in range(4)]
    forced={v:fake_forced(v) for v in g.VARIANTS}
    return cases,forced

class Frozen(unittest.TestCase):
    def test_original_parent_hashes_and_prereg(self):
        meta=g.source_identity()
        self.assertEqual(meta["g71_source_git_blob"],g.G71_SOURCE_GIT_BLOB)
        self.assertEqual(meta["g71_final_git_blob"],g.G71_FINAL_GIT_BLOB)
        self.assertEqual(meta["g72_final_git_blob"],g.G72_FINAL_GIT_BLOB)
    def test_external_data_identity_and_four_windows(self):
        self.assertEqual(g.SHAKESPEARE_GIT_BLOB,"7dcb3a2d4cc3b48b6283dd46870bfeb78f88aac9")
        self.assertEqual(g.SHAKESPEARE_REPO_COMMIT,"6f9487a6fe5b420b7ca9afb0d7c078e37c1d1b4e")
        self.assertEqual(g.FRESH_WINDOWS,((1024,512),(8192,512),(16384,1536),(32768,1536)))
        self.assertNotIn("wikitext",g.SHAKESPEARE_URL)
    def test_original_model_and_source_hashes(self):
        self.assertEqual(g.g63.WEIGHT_SHA,"6e6001da2106d4757498752a021df6c2bdc332c650aae4bae6b0c004dcf14933")
        self.assertEqual(g.g64.G63_CORPUS_SHA256,"d790b833ef8cf03a90db7bf1271b7520b83c45ce07ba3c1a9699df81e239eca0")
        self.assertEqual(g.original.G64_PROMPT_HASH,"19a85c78f14d5470d79d51c83a25d69a9b54953eb0024d223e82e34376529c59")
    def test_full_measurement_budget_and_variants(self):
        self.assertEqual(g.VARIANTS,("original_fp16","original_fp32_full"))
        self.assertEqual(g.REPEATS,3)
        self.assertEqual(g.WARMUPS,2)
        self.assertEqual(g.LOGITS_MODES,("cached_one_by_one","cached_chunk_48","full_no_cache"))
    def test_pass_is_engineering_only(self):
        a,b=all_good()
        out=g.adjudicate(a,b)
        self.assertEqual(out["reference_screen"],"REFERENCE_PRECISION_SCREEN_PASS_ONLY")
        self.assertEqual(out["scientific_acceptance"],"NOT_GRANTED")
        self.assertFalse(out["qualified_novel_acceleration"])
        self.assertEqual(out["prior_g63_original_generalization"],"FAIL_NO_GO_UNCHANGED")
    def test_original_control_not_matching_is_blocked(self):
        a,b=all_good()
        b["original_fp16"]["cached_one_by_one"][0]["greedy_argmax_id"]=29871
        with self.assertRaises(ValueError):g.adjudicate(a,b)
    def test_full_fp32_control_not_matching_is_blocked(self):
        a,b=all_good()
        b["original_fp32_full"]["cached_chunk_48"][0]["greedy_argmax_id"]=7866
        with self.assertRaises(ValueError):g.adjudicate(a,b)
    def test_hybrid_nonunique_logit_no_go(self):
        a,b=all_good()
        for x in b["original_fp32_full"]["cached_one_by_one"]:x["exact_max_tie_count"]=2
        with self.assertRaises(ValueError):g.adjudicate(a,b)
    def test_hybrid_bad_known_case_no_go(self):
        a,b=all_good()
        a[0]["variants"]["original_fp32_full"]["comparison"]["exact"]=False
        self.assertEqual(g.adjudicate(a,b)["reference_screen"],"NO_GO_REFERENCE")
    def test_external_exact_mismatch_no_go(self):
        a,b=all_good()
        a[3]["variants"]["original_fp32_full"]["comparison"]["exact"]=False
        self.assertEqual(g.adjudicate(a,b)["reference_screen"],"NO_GO_REFERENCE")
    def test_latency_limit_no_go(self):
        a,b=all_good()
        a[2]["variants"]["original_fp32_full"]["median_seconds"]["baseline"]=2.6
        self.assertEqual(g.adjudicate(a,b)["reference_screen"],"NO_GO_REFERENCE")
    def test_memory_limit_no_go(self):
        a,b=all_good()
        a[2]["variants"]["original_fp32_full"]["peak_allocated_mib"]["candidate"]=600.
        self.assertEqual(g.adjudicate(a,b)["reference_screen"],"NO_GO_REFERENCE")
    def test_speed_limit_no_go(self):
        a,b=all_good()
        for c in a[1:]:
            c["variants"]["original_fp32_full"]["median_seconds"]["candidate"]=1.0
        self.assertEqual(g.adjudicate(a,b)["reference_screen"],"NO_GO_REFERENCE")
    def test_incomplete_missing_case_blocks(self):
        a,b=all_good()
        a.pop()
        with self.assertRaises(ValueError):g.adjudicate(a,b)
    def test_nondeterministic_original_forced_blocks(self):
        a,b=all_good()
        b["original_fp16"]["full_no_cache"][1]["candidate_minus_baseline_logit"]=1.0
        with self.assertRaises(ValueError):g.adjudicate(a,b)
    def test_full_fp32_reference_is_unmodified_model(self):
        source=SRC.read_text(encoding="utf-8")
        self.assertNotIn("fp32_q_only(model)",source)
        self.assertNotIn("rowwise_q_only(model)",source)
        self.assertNotIn("class FP32Q0",source)
        self.assertNotIn("class RowwiseQ0",source)
        self.assertIn('dtype=torch.float32 if variant=="original_fp32_full" else torch.float16',source)
        self.assertIn('"scientific_acceptance":"NOT_GRANTED"',source)
        self.assertIn('"original_g72":"NO_GO_ENGINEERING"',source)
        self.assertIn('torch.backends.cuda.matmul.allow_tf32=False',source)
    def test_frozen_no_science_promotion(self):
        a,b=all_good()
        r=g.adjudicate(a,b)
        self.assertEqual(r["reference_screen"],"REFERENCE_PRECISION_SCREEN_PASS_ONLY")
        self.assertEqual(r["scientific_acceptance"],"NOT_GRANTED")
        self.assertFalse(r["qualified_novel_acceleration"])

if __name__=="__main__":
    unittest.main()
