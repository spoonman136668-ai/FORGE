import importlib.util,json,hashlib,subprocess,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
def load(path):
    spec=importlib.util.spec_from_file_location("frozen_"+path.parent.name+"_"+path.stem,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
class Freeze(unittest.TestCase):
    def test_both_frozen_disjoint_and_reviews_fail_closed(self):
        ids=[("r32-wingless","W-FORGE-R32-T05-REPLICATION-01","057c14cc786ae3d1a11735c8c8dddde85d339c20"),
             ("r33-wingless","W-FORGE-R33-CONDITIONAL-TEMP-01","b587bf20e5b449cabbccd88568487b07f2674b92")]
        used=set(range(6000,6250))|set(range(7000,8250))
        for folder,ident,digest in ids:
            d=HERE.parent/folder;raw=subprocess.check_output(["git","show",f"HEAD:research/{folder}/prereg.json"]);m=json.loads(raw)
            e=load(d/"execute.py");v=load(d/"review.py")
            self.assertEqual(blob(raw),digest)
            self.assertEqual(e.PREREG_BLOB,v.BLOB)
            self.assertEqual(e.PREREG_BLOB,digest)
            self.assertEqual(e.ID,v.EXPERIMENT)
            self.assertEqual(e.ID,ident)
            self.assertEqual(m["experiment_id"],ident)
            self.assertEqual(m["training_epochs"],32)
            self.assertEqual(m["limits"]["model_calls"],0)
            self.assertEqual(m["first_use"]["retry_forbidden"],True)
            seeds=sum(m["development_blocks"],[])+m["sealed_heldout_seeds"]
            self.assertEqual(len(seeds),96)
            self.assertEqual(len(set(seeds)),96)
            self.assertFalse(used.intersection(seeds))
            used.update(seeds)
            for payload in (b"{}",b"null",b'{"x":1,"x":2}'):
                with self.assertRaises((ValueError,KeyError,TypeError,AttributeError)):
                    v.verify(raw,payload,b'{}')
        d=json.loads((HERE.parent/"r33-wingless"/"prereg.json").read_bytes())
        self.assertEqual(set(d["pre_frozen_decision"]),{"ROBUST_REPLICATION_GAIN","PARTIAL_REPLICATION_GAIN","NO_CONFIRMED_REPLICATION_GAIN"})
    def test_budget_enforces_exact_two_first_uses(self):
        b=load(HERE/"budget_gate.py")
        source="a"*40
        a={"id":7,"body":b.approval_text(source),"user":{"login":"spoonman136668-ai"},
           "author_association":"OWNER","created_at":"t","updated_at":"t"}
        l={"schema":"forge.r32-r33.bounded-start.v1","source_commit":source,"experiments":list(b.IDs),"original_budget":2}
        cs=[{"schema":"forge.r32-r33.first-use-consumed.v1","experiment_id":b.IDs[i],
             "source_commit":source,"prereg_blob":b.PREREG[i],"execute_blob":b.EXECUTE[i],
             "review_blob":b.REVIEW[i],"owner_approval_comment_id":7,"budget_limit":2,
             "first_use_consumed":True,"rerun_allowed":False} for i in range(2)]
        runs={"total_count":1,"workflow_runs":[{"id":10,"head_sha":"b"*40,"run_attempt":1,"event":"push"}]}
        self.assertEqual(len(b.verify(l,cs,a,runs,source,10,"b"*40)["originals_reserved"]),2)
        cs[1]["first_use_consumed"]=False
        with self.assertRaises(ValueError):b.verify(l,cs,a,runs,source,10,"b"*40)
        cs[1]["first_use_consumed"]=True
        runs["total_count"]=2
        with self.assertRaises(ValueError):b.verify(l,cs,a,runs,source,10,"b"*40)
        runs["total_count"]=1
        a["author_association"]="CONTRIBUTOR"
        with self.assertRaises(ValueError):b.verify(l,cs,a,runs,source,10,"b"*40)
if __name__=="__main__":unittest.main()
