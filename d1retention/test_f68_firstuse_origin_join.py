"""F68 guard: original artifacts ≠ transport/continuation, no replay permission."""
import importlib.util
from pathlib import Path
import unittest

import f68_firstuse_origin_join as m
from test_f67_dual_lane_readonly import Fixtures

def fixture():
    api=Fixtures()
    pins,sha=m.file_manifest()
    for p in pins:
        rid=p["run_id"]
        repo=p["repo"]
        api.data[(repo,"/actions/runs/"+str(rid))]={
          "id":rid,"head_sha":p["commit_sha"],"status":"completed",
          "conclusion":"success","event":"push",
          "path":".github/workflows/qualify-test-original.yml"}
        api.data[(repo,"/actions/runs/"+str(rid)+"/artifacts?per_page=100")]={
          "artifacts":[{"id":p["artifact_id"],"name":p["artifact_name"],
                        "expired":False,"size_in_bytes":2030,
                        "digest":"sha256:"+"c"*64}]}
    for rid,(kind,path,name) in m.EXPECTED.items():
        status=("pending" if rid==38869660982 else
                "in_progress" if rid==38864578731 else "completed")
        conclusion="failure" if status=="completed" else None
        api.data[(m.YGG,"/actions/runs/"+str(rid))]={
          "id":rid,"name":name,"path":".github/workflows/"+path,
          "status":status,"conclusion":conclusion,"run_attempt":1,
          "head_sha":"d"*40,"head_branch":"main","event":"workflow_dispatch"}
        jobs=([] if status=="pending" else
              [{"name":"pump","status":"in_progress","conclusion":None}]
              if status=="in_progress" else
              [{"name":"cycle","status":"completed","conclusion":"failure"}])
        api.data[(m.YGG,"/actions/runs/"+str(rid)+"/jobs?per_page=100")]={"jobs":jobs}
    return api,(pins,sha)

class F68Tests(unittest.TestCase):
 def test_archived_originals_are_distinct_from_transport_workflows(self):
    api,pins=fixture()
    d=m.audit(api,pins)
    self.assertEqual(len(d["authenticated_archived_original_metadata"]),2)
    self.assertEqual(len(d["classified_ygg_transport_and_continuation"]),3)
    self.assertTrue(d["both_research_lanes_historic_provenance_joined"])
    run={x["run_id"]:x for x in d["classified_ygg_transport_and_continuation"]}
    self.assertEqual(run[38869660982]["status"],"pending")
    self.assertEqual(run[38864578731]["status"],"in_progress")
    self.assertEqual(run[38868746675]["conclusion"],"failure")
    self.assertEqual(run[38868746675]["classification"],
       "FAILED_RESEARCH_CONTINUATION_CAUSE_UNVERIFIED_NO_NEW_RESULT")
    self.assertFalse(run[38868746675]["failure_cause_independently_verified_by_this_api"])
    self.assertFalse(d["complete_both_lanes_scientific_firstuse_seed_ledger_observed"])
    self.assertFalse(d["protected_original_replay_authorized"])
    self.assertFalse(d["deployed_cloudflare_d1_firstuse_claim"])
    self.assertFalse(d["existing_worker_one_use_permit_issued"])
    self.assertFalse(d["independently_authenticated_ckb_science_owner_epoch"])
    self.assertEqual(d["new_protected_originals_dispatched"],0)
    for x in d["authenticated_archived_original_metadata"]:
        self.assertFalse(x["pinned_scientific_raw_sha256_content_verified_now"])
        self.assertFalse(x["independent_signed_original_firstuse_verified"])
    for x in run.values():
        self.assertFalse(x["scientific_original_workflow"])
        self.assertFalse(x["original_firstuse_consumed_by_transport"])
        self.assertFalse(x["retry_of_uncertain_original_authorized"])

 def test_wrong_workflow_role_or_wrong_committed_branch_is_blocked(self):
    for field,value in (
      ("path",".github/workflows/qualify-chatgpt-native-y056-perception.yml"),
      ("head_sha","f"*40),
      ("name","Yggdrasil original science"),
      ("run_attempt",2),("event","push")):
        api,pins=fixture()
        api.data[(m.YGG,"/actions/runs/38864578731")][field]=value
        with self.subTest(field=field),self.assertRaises(m.Denied):
            m.audit(api,pins)

 def test_undeclared_original_and_missing_canonical_artifact_block(self):
    for field,value in (("head_sha","e"*40),("conclusion","failure"),
                        ("path",".github/workflows/research-auto-launch.yml")):
        api,pins=fixture()
        item=pins[0][0]
        api.data[(item["repo"],"/actions/runs/"+str(item["run_id"]))][field]=value
        with self.subTest(field=field),self.assertRaises(m.Denied):
            m.audit(api,pins)
    for field,value in (("expired",True),("id",3),("digest","unknown")):
        api,pins=fixture()
        item=pins[0][1]
        arr=api.data[(item["repo"],"/actions/runs/"+str(item["run_id"])+
                      "/artifacts?per_page=100")]["artifacts"]
        arr[0][field]=value
        with self.subTest(field=field),self.assertRaises(m.Denied):
            m.audit(api,pins)

 def test_pending_run_cannot_be_misclassified_as_completed_sci_original(self):
    api,pins=fixture()
    entry=api.data[(m.YGG,"/actions/runs/38869660982")]
    entry["conclusion"]="success"
    with self.assertRaises(m.Denied):m.audit(api,pins)
    api,pins=fixture()
    entry=api.data[(m.YGG,"/actions/runs/38869660982")]
    entry["status"]="completed"
    entry["conclusion"]="success"
    with self.assertRaises(m.Denied):m.audit(api,pins)

 def test_failed_cycle_cannot_become_success_without_matching_terminal_job(self):
    api,pins=fixture()
    api.data[(m.YGG,"/actions/runs/38868746675")]["conclusion"]="success"
    with self.assertRaises(m.Denied):m.audit(api,pins)
    api,pins=fixture()
    api.data[(m.YGG,"/actions/runs/38868746675/jobs?per_page=100")]["jobs"]=[
      {"name":"scientific_original","status":"completed","conclusion":"failure"}]
    with self.assertRaises(m.Denied):m.audit(api,pins)

 def test_manifest_keeps_two_disjoint_genuine_original_pins(self):
    pins,sha=m.file_manifest()
    self.assertEqual(len(pins),2)
    self.assertEqual({p["lane"] for p in pins},{"Wingless","Yggdrasil"})
    self.assertEqual(len(sha),64)
    self.assertTrue(all(len(p["raw_sha256"])==64 for p in pins))
    self.assertNotEqual(pins[0]["run_id"],pins[1]["run_id"])

if __name__=="__main__":unittest.main()
