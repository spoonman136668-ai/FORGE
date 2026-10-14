"""R36/F3 source and authority safety tests; no scientific workers invoked."""
import copy,hashlib,json,pathlib,subprocess,sys,unittest
from unittest import mock
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import admission as a
def raw():return subprocess.check_output(["git","show","HEAD:research/r36_f3_screen/frozen_portfolio.json"])
class FrozenScreen(unittest.TestCase):
    def test_exact_frozen_source_and_eight_distinct_mechanisms(self):
        frozen=raw();self.assertEqual(a.git_blob(frozen),a.FROZEN_BLOB)
        m=a.verify_portfolio(frozen)
        self.assertEqual(len(m["wingless"]["candidates"]),4)
        self.assertEqual(len(m["yggdrasil"]["candidates"]),4)
        self.assertEqual(len(set(x["method"] for x in m["wingless"]["candidates"])),4)
        self.assertEqual(len(set(x["method"] for x in m["yggdrasil"]["candidates"])),4)
        self.assertEqual(m["constraints"]["new_scientific_dispatches"],0)
        self.assertEqual(m["constraints"]["first_use_claims_created"],0)
        self.assertTrue(m["frozen_selection_requires"]["independent_dev_score_recomputation"])
    def test_mutation_of_sealed_data_or_budget_cannot_inherit_identity(self):
        m=a.load(raw())
        mutations=[
            lambda v:v["yggdrasil"]["reserved_sealed_heldout_seeds"].__setitem__(0,66040),
            lambda v:v["yggdrasil"]["legal_novel_pairs"][0].__setitem__(0,1),
            lambda v:v["wingless"]["candidates"].__setitem__(0,v["wingless"]["candidates"][1]),
            lambda v:v["constraints"].__setitem__("new_scientific_dispatches",1),
            lambda v:v["constraints"].__setitem__("paid_model_calls",1),
            lambda v:v["frozen_selection_requires"].__setitem__("no_scientific_original_created_by_this_portfolio",False)]
        for change in mutations:
            with self.subTest(change=change):
                edited=copy.deepcopy(m);change(edited)
                candidate=(json.dumps(edited)+"\n").encode()
                with self.assertRaisesRegex(ValueError,"FROZEN_BLOB_DRIFT"):
                    a.verify_portfolio(candidate)
                with mock.patch.object(a,"FROZEN_BLOB",a.git_blob(candidate)):
                    with self.assertRaises(ValueError):
                        a.verify_portfolio(candidate)
    def test_parent_review_and_github_execution_must_both_match(self):
        e=a.EXPECTED["wingless"]
        report={"schema":e["schema"],"experiment_id":e["id"],"prereg_blob":e["prereg"],
                "outcome":e["outcome"],"independently_validated":True,
                "original_replay_allowed":False,"original_sha256":"a"*64}
        run={"id":e["run"],"run_attempt":1,"status":"completed","conclusion":"failure"}
        jobs={"jobs":[{"name":e["original_job"],"conclusion":"success"},
                      {"name":e["review_job"],"conclusion":"success"}]}
        artifacts={"artifacts":[{"id":e["original_artifact"],"name":"forge-r35-original","expired":False},
                                {"id":e["review_artifact"],"name":e["review_artifact_name"],"expired":False}]}
        self.assertTrue(a.verify_parent("wingless",json.dumps(report).encode(),run,jobs,artifacts)["independent_review"])
        report["independently_validated"]=False
        with self.assertRaises(ValueError):a.verify_parent("wingless",json.dumps(report).encode(),run,jobs,artifacts)
        report["independently_validated"]=True
        jobs["jobs"][1]["conclusion"]="failure"
        with self.assertRaises(ValueError):a.verify_parent("wingless",json.dumps(report).encode(),run,jobs,artifacts)
        jobs["jobs"][1]["conclusion"]="success"
        artifacts["artifacts"][1]["expired"]=True
        with self.assertRaises(ValueError):a.verify_parent("wingless",json.dumps(report).encode(),run,jobs,artifacts)
    def test_duplicate_json_fields_and_nonfinite_rejected(self):
        with self.assertRaisesRegex(ValueError,"DUPLICATE_KEY"):a.load(b'{"outcome":"a","outcome":"b"}')
        with self.assertRaisesRegex(ValueError,"NONFINITE"):a.load(b'{"value":NaN}')
if __name__=="__main__":unittest.main()
