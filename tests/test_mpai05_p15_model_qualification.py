"""P15 source/model/selection negative controls, no network/model inference."""
from pathlib import Path
import copy
import inspect
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import mpai05_p15_model_qualification as p15

def fake_cohort():
    rows=[]
    small={}
    kinds=sorted(p15.p9.TYPES)
    for i in range(210):
        qid=f"question_{i:04d}"
        domain="web" if i%2==0 else "enterprise"
        rows.append({"id":qid,"domain":domain,"image":None,
                     "question_type":kinds[i%len(kinds)],
                     "question":"private question never used","answer":"gold must not be used",
                     "eval_function":"deliberately wrong"})
        small[qid]=[f"trajectory_{i:04d}_{j:03d}" for j in range(100)]
    previous={"cohort_sha256":p15.PRIOR_COHORT_SHA,
              "cohort":[{"id":r["id"]} for r in rows[:16]]}
    return rows,small,previous

class P15Controls(unittest.TestCase):
    def test_exact_public_model_custody(self):
        self.assertEqual(p15.MODEL_REVISION,
           "72da00985aa7cb57cd436a6172be99c3bd906d9c")
        self.assertEqual(p15.MODEL_SHA256,
           "77665ea4815999596525c636fbeb56ba8b080b46ae85efef4f0d986a139834d7")
        self.assertEqual(p15.MODEL_EXACT_BYTES,1055609824)
        self.assertEqual(p15.MODEL_LICENSE,"apache-2.0")
        self.assertIn(p15.MODEL_REVISION,p15.MODEL_URL)
        self.assertNotIn("/main/",p15.MODEL_URL)
    def test_balanced_new_cohort_excludes_old(self):
        rows,small,old=fake_cohort()
        with patch.object(p15.p9,"choose",return_value=old):
            got=p15.new_cohort(rows,small)
        self.assertEqual(got["prior_excluded"],16)
        self.assertEqual(got["overlap"],0)
        self.assertEqual(got["domain_counts"],{"enterprise":8,"web":8})
        self.assertEqual(len(got["selected"]),16)
        self.assertTrue({r["id"] for r in got["selected"]}.isdisjoint(
            {r["id"] for r in old["cohort"]}))
    def test_new_cohort_deterministic(self):
        rows,small,old=fake_cohort()
        with patch.object(p15.p9,"choose",return_value=old):
            one=p15.new_cohort(rows,small)
            two=p15.new_cohort(rows,small)
        self.assertEqual(one,two)
        self.assertEqual(len(one["digest"]),64)
    def test_mutating_gold_question_and_grader_no_effect(self):
        rows,small,old=fake_cohort()
        with patch.object(p15.p9,"choose",return_value=old):
            before=p15.new_cohort(rows,small)["digest"]
            for row in rows:
                row["answer"]="new fake gold"
                row["question"]="altered hidden prompt"
                row["eval_function"]="different"
            after=p15.new_cohort(rows,small)["digest"]
        self.assertEqual(before,after)
    def test_upstream_old_hash_drift_denied(self):
        rows,small,old=fake_cohort()
        old["cohort_sha256"]="0"*64
        with patch.object(p15.p9,"choose",return_value=old):
            with self.assertRaisesRegex(RuntimeError,"PRIOR_COHORT_DRIFT"):
                p15.new_cohort(rows,small)
    def test_small_haystack_duplicate_denied(self):
        rows,small,old=fake_cohort()
        with patch.object(p15.p9,"choose",return_value=old):
            chosen=p15.new_cohort(rows,small)
            target=chosen["selected"][0]["id"]
            small[target]=["duplicate"]*100
            with self.assertRaisesRegex(RuntimeError,"SMALL_HAYSTACK_DRIFT"):
                p15.new_cohort(rows,small)
    def test_fresh_selection_has_no_gold_parameters(self):
        self.assertEqual(list(inspect.signature(p15.new_cohort).parameters),
                         ["rows","small"])
    def test_no_paid_qwen_or_production_writer(self):
        script=Path(p15.__file__).read_text("utf-8")
        for forbidden in ("openai.OpenAI(", "write_accepted_ice(",
                 "Qwen2", "model_promotion_authorized=True", "pip install"):
            self.assertNotIn(forbidden,script)
        self.assertIn("MPAI05_P15_FIRST_USE_HOLDOUT=FALSE",script)
    def test_resource_bound_regression(self):
        self.assertEqual(p15.MAX_CPU_INFERENCE_SECONDS,120)
        self.assertEqual(p15.MAX_PEAK_WORKING_SET_BYTES,5000000000)
        self.assertIn("GetProcessMemoryInfo",inspect.getsource(p15.windows_peak_working_set))
    def test_zero_previous_development_question_use_in_model_prompt(self):
        txt=inspect.getsource(p15.smoke)
        self.assertIn("seven plus five",txt)
        self.assertNotIn("selected",txt)
        self.assertNotIn("question_type",txt)

if __name__=="__main__":
    unittest.main()
