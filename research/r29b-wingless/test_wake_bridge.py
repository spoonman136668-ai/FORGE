import copy
import importlib.util
import unittest
from pathlib import Path

p=Path(__file__).with_name("wake_bridge.py")
spec=importlib.util.spec_from_file_location("r29b_bridge",p)
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
SOURCE="a"*40
RUN=123456
SHA="b"*40
def fixture():
    wake_id=38487981631
    comment_id=6157848096
    claim={"schema":"forge.r29b.operator-single-original-claim.v1",
           "experiment_id":b.EXPERIMENT,"source_commit":SOURCE,
           "prereg_blob":b.PREREG,"execute_blob":b.EXECUTE,
           "review_blob":b.REVIEW,"operator_approval_comment_id":comment_id,
           "wake_run_id":wake_id,"first_use_consumed":True,"rerun_allowed":False}
    launch={"schema":"forge.r29b.single-start.v1","experiment_id":b.EXPERIMENT,
            "source_commit":SOURCE,"prereg_blob":b.PREREG}
    approval={"id":comment_id,"body":b.approval_text(SOURCE,wake_id),
              "user":{"login":b.OWNER},"author_association":"OWNER",
              "created_at":"2026-10-13T23:00:00Z","updated_at":"2026-10-13T23:00:00Z"}
    runs={"total_count":1,"workflow_runs":[{"id":RUN,"head_sha":SHA,"run_attempt":1}]}
    return [claim,launch,approval,runs]
class Gate(unittest.TestCase):
    def test_exact_one_shot(self):
        self.assertTrue(b.verify(*fixture(),SOURCE,RUN,SHA)["may_start_once"])
    def negative(self,index,key,value):
        a=fixture()
        a[index][key]=value
        with self.assertRaises(ValueError):b.verify(*a,SOURCE,RUN,SHA)
    def test_fail_closed(self):
        self.negative(0,"first_use_consumed",False)
        self.negative(0,"rerun_allowed",True)
        self.negative(0,"source_commit","c"*40)
        self.negative(0,"operator_approval_comment_id",0)
        self.negative(2,"author_association","CONTRIBUTOR")
        self.negative(2,"created_at","2026-10-13T22:00:00Z")
        self.negative(2,"body","forged")
        self.negative(3,"total_count",2)
        self.negative(3,"workflow_runs",[])
        a=fixture();a[2]["user"]["login"]="not-owner"
        with self.assertRaises(ValueError):b.verify(*a,SOURCE,RUN,SHA)
        a=fixture()
        with self.assertRaises(ValueError):b.verify(*a,SOURCE,RUN+1,SHA)
    def test_duplicate_json_rejected(self):
        with self.assertRaises(ValueError):b.strict('{"id":1,"id":2}')
if __name__=="__main__":unittest.main()
