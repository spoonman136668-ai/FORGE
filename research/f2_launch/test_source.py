import importlib.util,json,pathlib,subprocess,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import budget_gate as gate
def source(path):return subprocess.check_output(["git","show","HEAD:"+path])
def blob(path):return subprocess.check_output(["git","rev-parse","HEAD:"+path]).decode().strip()
class F2Qualification(unittest.TestCase):
    def test_exact_source_identity_and_legal_new_pairs(self):
        base="research/f2-yggdrasil/"
        self.assertEqual(blob(base+"prereg.json"),gate.PREREG)
        self.assertEqual(blob(base+"run_original.py"),gate.WORKER)
        self.assertEqual(blob(base+"independent_review.py"),gate.REVIEWER)
        m=json.loads(source(base+"prereg.json"))
        self.assertEqual([s["experiment_id"] for s in m["studies"]],[gate.ID])
        self.assertEqual(m["pairs"],[[2,6],[3,7]])
        used=set()
        for pair in m["pairs"]:
            self.assertEqual(len(pair),2)
            self.assertEqual(len(set(pair)),2)
            self.assertFalse(set(pair).intersection({0,1}))
            self.assertTrue(all(2<=n<=15 for n in pair))
            self.assertFalse(used.intersection(pair))
            used.update(pair)
        ss=m["studies"][0]
        self.assertEqual(len(ss["dev_seeds"]),8)
        self.assertEqual(len(ss["sealed_seeds"]),16)
        self.assertEqual(len(set(ss["dev_seeds"]+ss["sealed_seeds"])),24)
        self.assertGreaterEqual(min(ss["dev_seeds"]+ss["sealed_seeds"]),66000)
        self.assertEqual(m["parent"]["experiment_id"],"Y-FORGE-E3-ONSET-LATENCY-01")
        self.assertEqual(m["parent"]["required_outcome"],"LATENCY_DOMINANT_PARTIAL_GAIN")
        self.assertIn("Y-FORGE-F1-CROSS-PAIR-LATENCY-01",[a["experiment_id"] for a in m["prior_consumed_attempts"]])
        w=source(base+"run_original.py").decode()
        self.assertIn("F2_PINNED_Y058_ILLEGAL_TRANSPOSITION_PAIR",w)
        self.assertIn('z.PAIRS=tuple(tuple(p) for p in m["pairs"])',w)
    def test_immutable_one_use_and_negative_cases(self):
        source="a"*40
        approval={"id":11,"body":gate.approval_text(source),
                  "user":{"login":"spoonman136668-ai"},"author_association":"OWNER",
                  "created_at":"t","updated_at":"t"}
        launch={"schema":"forge.ygg.f2.single-start.v1","experiment_id":gate.ID,"source_commit":source,"original_budget":1}
        claim={"schema":gate.SCHEMA,"experiment_id":gate.ID,"source_commit":source,
               "prereg_blob":gate.PREREG,"worker_blob":gate.WORKER,
               "reviewer_blob":gate.REVIEWER,"owner_approval_comment_id":11,
               "budget_limit":1,"first_use_consumed":True,"rerun_allowed":False}
        runs={"total_count":1,"workflow_runs":[{"id":7,"head_sha":"b"*40,"event":"push","run_attempt":1}]}
        self.assertTrue(gate.verify(launch,claim,approval,runs,source,7,"b"*40)["original_consumed"])
        claim["rerun_allowed"]=True
        with self.assertRaises(ValueError):gate.verify(launch,claim,approval,runs,source,7,"b"*40)
        claim["rerun_allowed"]=False
        runs["total_count"]=2
        with self.assertRaises(ValueError):gate.verify(launch,claim,approval,runs,source,7,"b"*40)
        runs["total_count"]=1
        runs["workflow_runs"][0]["run_attempt"]=2
        with self.assertRaises(ValueError):gate.verify(launch,claim,approval,runs,source,7,"b"*40)
    def test_independent_reviewer_fails_closed_on_forged_original(self):
        path=ROOT.parent/"f2-yggdrasil"/"independent_review.py"
        spec=importlib.util.spec_from_file_location("f2_reviewer",path)
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        with self.assertRaises(Exception):
            m.verify(source("research/f2-yggdrasil/prereg.json"),b'{}',gate.ID,b'{}')
if __name__=="__main__":unittest.main()
