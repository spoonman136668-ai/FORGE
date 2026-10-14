"""Frozen E1/E2 source and tuple/list cross-runtime regression negatives."""
import hashlib,importlib.util,json,subprocess,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def read_module(name):
    spec=importlib.util.spec_from_file_location("ygg_b_"+name,ROOT/(name+".py"))
    x=importlib.util.module_from_spec(spec);spec.loader.exec_module(x)
    return x
class Freeze(unittest.TestCase):
    def test_manifest_and_new_disjoint_cohorts(self):
        raw=subprocess.check_output(["git","show","HEAD:research/forge-ygg-parity-e/prereg.json"])
        gitsha=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()
        self.assertEqual(gitsha,"4fba6ffe85e5f75e9a6c69c91e93a05cc0dd0e28")
        m=json.loads(raw)
        ids=[x["experiment_id"] for x in m["studies"]]
        self.assertEqual(ids,["Y-FORGE-PARITY-E1-ONSET1","Y-FORGE-PARITY-E2-ONSET1"])
        used=set(range(8224,8272))|set(range(61000,63200))
        for row in m["studies"]:
            seeds=row["dev_seeds"]+row["sealed_seeds"]
            self.assertEqual((len(row["dev_seeds"]),len(row["sealed_seeds"])),(8,16))
            self.assertEqual(len(set(seeds)),24)
            self.assertFalse(used.intersection(seeds))
            used.update(seeds)
        budget=read_module("budget_gate")
        self.assertEqual(budget.MANIFEST,gitsha)
        worker_blob=subprocess.check_output(["git","rev-parse","HEAD:research/forge-ygg-parity-e/run_original.py"]).decode().strip()
        review_blob=subprocess.check_output(["git","rev-parse","HEAD:research/forge-ygg-parity-e/independent_review.py"]).decode().strip()
        self.assertEqual(budget.WORKER,worker_blob)
        self.assertEqual(budget.REVIEWER,review_blob)
        self.assertEqual(m["limit"]["max_originals"],2)
        self.assertEqual(m["limit"]["external_model_calls"],0)
    def test_tuple_list_regression_and_science_negative(self):
        mod=read_module("run_original")
        self.assertEqual(mod.IDS,("Y-FORGE-PARITY-E1-ONSET1","Y-FORGE-PARITY-E2-ONSET1"))
        src=(ROOT/"run_original.py").read_text()
        self.assertIn('list(result["sealed_heldout_seeds"])!=list(x["sealed_seeds"])',src)
        self.assertIn('list(result["development_seeds"])!=list(x["dev_seeds"])',src)
        self.assertEqual(list((1,2,3)),[1,2,3])
        reviewer=read_module("independent_review")
        raw=subprocess.check_output(["git","show","HEAD:research/forge-ygg-parity-e/prereg.json"])
        for value in (b"{}",b"null",b'{"a":1,"a":2}'):
            with self.assertRaises((ValueError,TypeError,KeyError,AttributeError)):
                reviewer.verify(raw,value,mod.IDS[0])
    def test_budget_negative_and_positive(self):
        m=read_module("budget_gate")
        source="a"*40
        a={"id":7,"body":m.approval_text(source),"user":{"login":"spoonman136668-ai"},"author_association":"OWNER","created_at":"t","updated_at":"t"}
        l={"schema":"forge.yggdrasil.parity-e.single-launch.v1","source_commit":source,"experiments":list(m.IDS),"original_budget":2}
        c=[{"schema":"forge.yggdrasil.e-first-use-consumed.v1","experiment_id":m.IDS[i],
            "source_commit":source,"prereg_blob":m.MANIFEST,"worker_blob":m.WORKER,
            "reviewer_blob":m.REVIEWER,"operator_approval_comment_id":7,
            "first_use_consumed":True,"rerun_allowed":False,"budget_claims":2} for i in range(2)]
        runs={"total_count":1,"workflow_runs":[{"id":1,"head_sha":"b"*40,"run_attempt":1,"event":"push"}]}
        self.assertEqual(len(m.verify(l,c,a,runs,source,1,"b"*40)["originals_consumed"]),2)
        c[1]["rerun_allowed"]=True
        with self.assertRaises(ValueError):m.verify(l,c,a,runs,source,1,"b"*40)
        c[1]["rerun_allowed"]=False
        runs["total_count"]=2
        with self.assertRaises(ValueError):m.verify(l,c,a,runs,source,1,"b"*40)
if __name__=="__main__":unittest.main()
