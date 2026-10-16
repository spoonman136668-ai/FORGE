import copy
import json
import pathlib
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from f98_historical_shadow import SPECS, SCHEMA, Blocked, assess, strict_loads

SOURCE = "8" * 40

def setup():
    pairs=[]
    for i,s in enumerate(SPECS):
        run=dict(id=s["run_id"],repository=dict(full_name=s["repository"]),
                 head_repository=dict(full_name=s["repository"]),head_sha=s["source_sha"],
                 path=s["workflow_path"],event="push",status="completed",
                 conclusion="success",run_attempt=1,workflow_id=380000001+i)
        item=dict(id=s["artifact_id"],name=s["artifact_name"],expired=False,
                  digest="sha256:"+s["zip_sha256"],size_in_bytes=8000,
                  workflow_run=dict(id=s["run_id"],head_sha=s["source_sha"]))
        pairs.append((run,dict(artifacts=[item],total_count=1)))
    return pairs

class F98(unittest.TestCase):
    def test_exact_two_real_lane_shadow_is_strictly_non_authorizing(self):
        r=assess(setup(),SOURCE)
        self.assertEqual(r["schema"],SCHEMA)
        self.assertEqual([x["lane"] for x in r["historical_reviewed_records"]],
                         ["Wingless","Yggdrasil"])
        self.assertEqual(r["genuinely_observed_lanes"],2)
        self.assertEqual(r["new_trainable_genenv_records"],0)
        for k in ("optimizer_promotion_authorized","sealed_original_first_use_authorized",
                  "experiment_worker_dispatched","ckb_plane_accessed","external_api_billing"):
            self.assertIs(r[k],False)
        for rec in r["historical_reviewed_records"]:
            self.assertTrue(rec["github_run_metadata_verified"])
            self.assertTrue(rec["artifact_metadata_zip_digest_verified"])
            for key in ("actual_zip_bytes_downloaded_and_rehashed",
                        "contained_row_data_reaudited_now",
                        "authenticated_train_only_feature_vectors_available",
                        "genenv_train_history_admitted","original_science_accepted"):
                self.assertIs(rec[key],False)
        self.assertEqual(r["model_calls"],r["codex_calls"])
        self.assertEqual(r["new_scientific_originals_executed"],0)
    def test_source_clock_run_identity_and_success_quarantined(self):
        for index in (0,1):
            for field,v in (("head_sha","a"*40),("event","workflow_dispatch"),
                            ("run_attempt",2),("status","in_progress"),
                            ("conclusion","failure"),("path",".github/workflows/foreign.yml"),
                            ("workflow_id",0)):
                pairs=setup()
                pairs[index][0][field]=v
                with self.subTest(index=index,field=field),self.assertRaises(Blocked):
                    assess(pairs,SOURCE)
    def test_artifact_digest_expiry_linkage_spoof_unsupported(self):
        for index in (0,1):
            for field,v in (("digest","sha256:"+"1"*64),("expired",True),
                            ("name","not-the-original"),("id",991),("size_in_bytes",0)):
                pairs=setup()
                pairs[index][1]["artifacts"][0][field]=v
                with self.subTest(index=index,field=field),self.assertRaises(Blocked):
                    assess(pairs,SOURCE)
            pairs=setup()
            pairs[index][1]["artifacts"][0]["workflow_run"]["head_sha"]="f"*40
            with self.assertRaises(Blocked):assess(pairs,SOURCE)
            pairs=setup()
            pairs[index][1]["artifacts"].append(
                copy.deepcopy(pairs[index][1]["artifacts"][0]))
            pairs[index][1]["total_count"]=2
            with self.assertRaises(Blocked):assess(pairs,SOURCE)
    def test_missing_artifacts_wrong_source_and_list_incomplete(self):
        for mutate in (
            lambda p:p.pop(),
            lambda p:p.reverse(),
            lambda p:p[0][1].__setitem__("total_count",2),
            lambda p:p[1][1].__setitem__("artifacts",[]),
            lambda p:p[0][0]["repository"].__setitem__("full_name","spoonman136668-ai/CKB"),
        ):
            pairs=setup()
            mutate(pairs)
            with self.assertRaises(Blocked):assess(pairs,SOURCE)
        for source in ("0","A"*40,"",None):
            with self.assertRaises(Blocked):assess(setup(),source)
    def test_duplicate_keys_and_nonfinite_rejected(self):
        for raw in (b'{"id":1,"id":2}',b'{"x":NaN}',b'{}'*300000):
            with self.assertRaises(Blocked):strict_loads(raw)
        self.assertEqual(strict_loads(b'{"ok":true}')["ok"],True)
    def test_determinism_and_no_privilege_escalation(self):
        a=assess(setup(),SOURCE)
        b=assess(setup(),SOURCE)
        self.assertEqual(json.dumps(a,sort_keys=True),json.dumps(b,sort_keys=True))
        self.assertEqual(a["accepted_reference_mutations"],0)
        self.assertFalse(a["sealed_original_first_use_authorized"])
if __name__=="__main__":
    unittest.main()
