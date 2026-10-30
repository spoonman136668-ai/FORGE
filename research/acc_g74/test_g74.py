"""ACC G74 source-only frozen first-use falsification tests. No GPU or source downloads."""
import importlib.util
from pathlib import Path
import unittest

SRC=Path(__file__).with_name("g74_firstuse_austen.py")
spec=importlib.util.spec_from_file_location("g74",SRC)
g=importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

def forced(precision):
    result={}
    for mode in g.LOGITS_MODES:
        if precision=="original_fp16" and mode=="cached_one_by_one":
            arg,tie=7866,2
        else:arg,tie=29871,1
        result[mode]=[{"greedy_argmax_id":arg,"exact_max_tie_count":tie,
                      "candidate_minus_baseline_logit":0.0} for _ in range(g.REPEATS)]
    return result

def case(i,prec_exact=True,match_greedy=True,fast=True):
    results={}
    for precision in g.VARIANTS:
        is_fp32=precision=="original_fp32_full"
        exact=(prec_exact if is_fp32 else i!=0)
        fp16_hash="same-"+str(i)
        h=fp16_hash if (not is_fp32 or match_greedy) else "precision-different-"+str(i)
        results[precision]={
            "comparison":{"exact":exact},
            "baseline_sha256":h,
            "candidate_sha256":h if exact else "spec-different-"+str(i),
            "median_seconds":{"baseline":1.0,"candidate":.5 if fast else 1.0},
            "peak_allocated_mib":{"candidate":200.0},
            "runs":{"baseline":[{} for _ in range(g.REPEATS)],
                    "candidate":[{} for _ in range(g.REPEATS)]}
        }
    return {"source":"original_exposed_wikitext2" if i==0 else "g74_firstuse_austen_git_pin",
            "variants":results}

def good():
    return [case(i) for i in range(5)],{v:forced(v) for v in g.VARIANTS}

class G74Frozen(unittest.TestCase):
    def test_original_source_identity(self):
        p=g.source_identity()
        self.assertEqual(p["g73_source_git_blob"],g.G73_SOURCE_GIT_BLOB)
        self.assertEqual(p["g73_final_git_blob"],g.G73_FINAL_GIT_BLOB)
    def test_source_is_independent_and_commit_pinned(self):
        self.assertEqual(g.AUSTEN_REPO_COMMIT,"81db45c9c48c592f0b77f01fc59e677ad0a5634e")
        self.assertEqual(g.AUSTEN_GIT_BLOB,"0a7d439c2f34b0dfacb88b7116429a9575b5735c")
        self.assertIn("GITenberg/Pride-and-Prejudice_1342",g.AUSTEN_URL)
        self.assertNotIn("master",g.AUSTEN_URL)
        self.assertNotIn("shakespeare",g.AUSTEN_URL.lower())
    def test_first_use_character_offsets_frozen(self):
        self.assertEqual(g.FRESH_WINDOWS,((24576,512),(49152,512),(98304,1536),(196608,1536)))
        self.assertEqual(g.REPEATS,3)
        self.assertEqual(g.WARMUPS,2)
    def test_original_models_not_selectively_modified(self):
        s=SRC.read_text("utf-8")
        self.assertIn('dtype=torch.float32 if variant=="original_fp32_full" else torch.float16',s)
        self.assertNotIn("rowwise_q_only(model)",s)
        self.assertNotIn("fp32_q_only(model)",s)
        self.assertIn("torch.backends.cuda.matmul.allow_tf32=False",s)
        self.assertIn('snapshot_download(repo_id=g63.REPO,revision=g63.REV',s)
    def test_exact_good_passes_reference_and_cross(self):
        a,b=good()
        d=g.adjudicate(a,b)
        self.assertEqual(d["firstuse_fp32_reference_screen"],"FRESH_FP32_REFERENCE_PASS_ONLY")
        self.assertEqual(d["cross_precision_practical_screen"],"CROSS_PRECISION_PRACTICAL_PASS_ONLY")
        self.assertFalse(d["pretraining_heldout_proven"])
        self.assertEqual(d["scientific_acceptance"],"NOT_GRANTED")
    def test_nonidentical_greedy_disqualifies_cross_only(self):
        a,b=good()
        a[2]["variants"]["original_fp32_full"]["baseline_sha256"]="different"
        d=g.adjudicate(a,b)
        self.assertEqual(d["firstuse_fp32_reference_screen"],"FRESH_FP32_REFERENCE_PASS_ONLY")
        self.assertEqual(d["cross_precision_practical_screen"],"NO_GO_CROSS_PRECISION")
        self.assertFalse(d["firstuse_fp16_fp32_greedy_equivalence_4_of_4"])
    def test_fp32_spec_mismatch_no_go(self):
        a,b=good()
        a[3]["variants"]["original_fp32_full"]["comparison"]["exact"]=False
        d=g.adjudicate(a,b)
        self.assertEqual(d["firstuse_fp32_reference_screen"],"NO_GO_REFERENCE")
        self.assertEqual(d["cross_precision_practical_screen"],"NO_GO_CROSS_PRECISION")
    def test_fp32_speed_bound_no_go(self):
        a,b=good()
        for x in a[1:]:x["variants"]["original_fp32_full"]["median_seconds"]["candidate"]=1.0
        self.assertEqual(g.adjudicate(a,b)["firstuse_fp32_reference_screen"],"NO_GO_REFERENCE")
    def test_cross_speed_bound_independent_of_reference(self):
        a,b=good()
        for x in a[1:]:
            x["variants"]["original_fp16"]["median_seconds"]["baseline"]=.3
        d=g.adjudicate(a,b)
        self.assertEqual(d["firstuse_fp32_reference_screen"],"FRESH_FP32_REFERENCE_PASS_ONLY")
        self.assertEqual(d["cross_precision_practical_screen"],"NO_GO_CROSS_PRECISION")
    def test_memory_limit_no_go(self):
        a,b=good()
        a[4]["variants"]["original_fp32_full"]["peak_allocated_mib"]["candidate"]=500.01
        self.assertEqual(g.adjudicate(a,b)["firstuse_fp32_reference_screen"],"NO_GO_REFERENCE")
    def test_latency_limit_no_go(self):
        a,b=good()
        a[2]["variants"]["original_fp32_full"]["median_seconds"]["baseline"]=2.501
        self.assertEqual(g.adjudicate(a,b)["firstuse_fp32_reference_screen"],"NO_GO_REFERENCE")
    def test_wrong_source_family_blocks(self):
        a,b=good()
        a[3]["source"]="new_shakespeare_pinned_git"
        with self.assertRaises(ValueError):g.adjudicate(a,b)
    def test_bad_canary_blocks(self):
        a,b=good()
        a[0]["variants"]["original_fp16"]["comparison"]["exact"]=True
        with self.assertRaises(ValueError):g.adjudicate(a,b)
    def test_wrong_original_fp16_forced_blocks(self):
        a,b=good()
        b["original_fp16"]["cached_one_by_one"][0]["greedy_argmax_id"]=29871
        with self.assertRaises(ValueError):g.adjudicate(a,b)
    def test_wrong_original_fp32_forced_blocks(self):
        a,b=good()
        b["original_fp32_full"]["cached_one_by_one"][0]["exact_max_tie_count"]=2
        with self.assertRaises(ValueError):g.adjudicate(a,b)
    def test_missing_fresh_case_blocks(self):
        a,b=good()
        a.pop()
        with self.assertRaises(ValueError):g.adjudicate(a,b)
    def test_missing_repetition_blocks(self):
        a,b=good()
        a[1]["variants"]["original_fp32_full"]["runs"]["candidate"].pop()
        with self.assertRaises(ValueError):g.adjudicate(a,b)
    def test_no_science_or_production_approval(self):
        a,b=good()
        x=g.adjudicate(a,b)
        self.assertFalse(x["qualified_novel_acceleration"])
        self.assertEqual(x["scientific_acceptance"],"NOT_GRANTED")
        self.assertEqual(x["original_g63"],"FAIL_NO_GO_UNCHANGED")
        self.assertEqual(x["original_g73"],"REFERENCE_ONLY_PASS_NOT_SCIENTIFIC")

if __name__=="__main__":
    unittest.main()
