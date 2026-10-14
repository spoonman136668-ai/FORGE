import importlib.util,json,pathlib,subprocess,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import budget_gate as gate

def get(path):
    return subprocess.check_output(["git","show","HEAD:"+path])
def blob(path):
    return subprocess.check_output(["git","rev-parse","HEAD:"+path]).decode().strip()
def module(path):
    spec=importlib.util.spec_from_file_location(path.parent.name+"_"+path.stem,path)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj)
    return obj
class Source(unittest.TestCase):
    def test_exact_source_manifests_and_reviewers(self):
        prefixes=("r34-wingless","e3-yggdrasil")
        paths=(("execute.py","review.py"),("run_original.py","independent_review.py"))
        for i,root in enumerate(prefixes):
            folder="research/"+root+"/"
            self.assertEqual(blob(folder+"prereg.json"),gate.PREREG[i])
            self.assertEqual(blob(folder+paths[i][0]),gate.WORKER[i])
            self.assertEqual(blob(folder+paths[i][1]),gate.REVIEWER[i])
            self.assertEqual(len(get(folder+"prereg.json")),len(get(folder+"prereg.json")))
            worker=module(ROOT.parent/root/paths[i][0])
            review=module(ROOT.parent/root/paths[i][1])
            self.assertIsNotNone(worker)
            self.assertIsNotNone(review)
        self.assertEqual(len(set(gate.IDS)),2)
    def test_no_prior_data_or_pair_overlap(self):
        w=json.loads(get("research/r34-wingless/prereg.json"))
        y=json.loads(get("research/e3-yggdrasil/prereg.json"))
        wseeds=sum(w["development_blocks"],[])+w["sealed_heldout_seeds"]
        ys=y["studies"][0]["dev_seeds"]+y["studies"][0]["sealed_seeds"]
        self.assertEqual(len(wseeds),96)
        self.assertEqual(len(set(wseeds)),96)
        self.assertEqual(len(ys),24)
        self.assertEqual(len(set(ys)),24)
        self.assertGreater(min(wseeds),11000)
        self.assertGreater(min(ys),64000)
        self.assertEqual(w["first_use"]["claim_before_worker"],True)
        self.assertEqual(y["limit"]["max_originals"],1)
    def test_bound_approval_and_negative_attempts(self):
        source="a"*40
        launch={"schema":"forge.dual-r34-e3.single-launch.v1",
                "source_commit":source,"experiments":list(gate.IDS),"original_budget":2}
        owner={"id":99,"body":gate.approval_text(source),
               "user":{"login":"spoonman136668-ai"},"author_association":"OWNER",
               "created_at":"t","updated_at":"t"}
        claims=[{"schema":gate.SCHEMA,"experiment_id":gate.IDS[i],
                 "source_commit":source,"prereg_blob":gate.PREREG[i],
                 "worker_blob":gate.WORKER[i],"reviewer_blob":gate.REVIEWER[i],
                 "owner_approval_comment_id":99,"budget_limit":2,
                 "first_use_consumed":True,"rerun_allowed":False} for i in range(2)]
        runs={"total_count":1,"workflow_runs":[{"id":4,"head_sha":"b"*40,
                "run_attempt":1,"event":"push"}]}
        self.assertEqual(gate.verify(launch,claims,owner,runs,source,4,"b"*40)["first_uses_consumed"],2)
        claims[0]["rerun_allowed"]=True
        with self.assertRaises(ValueError):gate.verify(launch,claims,owner,runs,source,4,"b"*40)
        claims[0]["rerun_allowed"]=False
        runs["total_count"]=2
        with self.assertRaises(ValueError):gate.verify(launch,claims,owner,runs,source,4,"b"*40)
        runs["total_count"]=1
        owner["body"]="fabricated approval"
        with self.assertRaises(ValueError):gate.verify(launch,claims,owner,runs,source,4,"b"*40)
    def test_reviewer_does_not_accept_forged_science(self):
        w=module(ROOT.parent/"r34-wingless"/"review.py")
        y=module(ROOT.parent/"e3-yggdrasil"/"independent_review.py")
        with self.assertRaises(Exception):
            w.verify(get("research/r34-wingless/prereg.json"),b"{}",b"{}")
        with self.assertRaises(Exception):
            y.verify(get("research/e3-yggdrasil/prereg.json"),b"{}",gate.IDS[1],b"{}")
if __name__=="__main__":unittest.main()
