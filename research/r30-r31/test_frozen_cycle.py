import importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def load(path):
    spec=importlib.util.spec_from_file_location("frozen_"+path.stem,path)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m
class Source(unittest.TestCase):
    def test_identity_disjoint_and_reviews_fail_closed(self):
        all_seeds=set()
        for folder,blob,ident in (
          ("r30-wingless","835def227a9db297424509bbe44d1d5eaec2a6c5","W-FORGE-R30-NORMALIZED-GRADIENT-01"),
          ("r31-wingless","70ff7d722f0e3814e9fba777bdfa1a4134eaf59d","W-FORGE-R31-CONDITIONAL-REPLICATION-01")):
            d=ROOT.parent/folder
            m=json.loads((d/"prereg.json").read_bytes())
            exe=load(d/"execute.py");review=load(d/"review.py")
            self.assertEqual(m["experiment_id"],ident)
            self.assertEqual(exe.ID,ident)
            self.assertEqual(review.EXPERIMENT,ident)
            self.assertEqual(exe.PREREG_BLOB,blob)
            self.assertEqual(review.BLOB,blob)
            self.assertEqual(m["training_epochs"],32)
            self.assertEqual(m["limits"]["model_calls"],0)
            seeds=sum(m["development_blocks"],[])+m["sealed_heldout_seeds"]
            self.assertEqual(len(seeds),96)
            self.assertEqual(len(set(seeds)),96)
            self.assertFalse(all_seeds.intersection(seeds))
            all_seeds.update(seeds)
            for malformed in (b'{}',b'null',b'{"a":1,"a":2}'):
                with self.assertRaises((ValueError,KeyError,TypeError,AttributeError)):
                    if folder=="r30-wingless":review.verify((d/"prereg.json").read_bytes(),malformed)
                    else:review.verify((d/"prereg.json").read_bytes(),malformed,b'{}')
        self.assertFalse(any(x in set(range(6000,6250)) for x in all_seeds))
    def test_budget_negative_cases(self):
        g=load(ROOT/"budget_gate.py")
        source="a"*40
        approval={"id":1,"body":g.approval_text(source),"user":{"login":"spoonman136668-ai"},
                  "author_association":"OWNER","created_at":"t","updated_at":"t"}
        launch={"schema":"forge.r30-r31.bounded-start.v1","source_commit":source,"experiments":list(g.IDs),"original_budget":2}
        claims=[{"schema":"forge.r30-r31.first-use-consumed.v1","experiment_id":g.IDs[i],
           "source_commit":source,"prereg_blob":g.PREREG[i],"execute_blob":g.EXECUTE[i],
           "review_blob":g.REVIEW[i],"owner_approval_comment_id":1,"budget_limit":2,
           "first_use_consumed":True,"rerun_allowed":False} for i in range(2)]
        runs={"total_count":1,"workflow_runs":[{"id":10,"head_sha":"b"*40,"run_attempt":1,"event":"push"}]}
        self.assertEqual(g.verify(launch,claims,approval,runs,source,10,"b"*40)["originals_reserved"],list(g.IDs))
        claims[1]["first_use_consumed"]=False
        with self.assertRaises(ValueError):g.verify(launch,claims,approval,runs,source,10,"b"*40)
        claims[1]["first_use_consumed"]=True
        runs["total_count"]=2
        with self.assertRaises(ValueError):g.verify(launch,claims,approval,runs,source,10,"b"*40)
        runs["total_count"]=1
        approval["author_association"]="CONTRIBUTOR"
        with self.assertRaises(ValueError):g.verify(launch,claims,approval,runs,source,10,"b"*40)
if __name__=="__main__":unittest.main()
