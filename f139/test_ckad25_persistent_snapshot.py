"""Permanent cross-platform CKAD25 development custody negative controls."""
import copy
from io import BytesIO
import json
import unittest
import zipfile

from f139.ckad25_persistent_snapshot import (
    audit_persisted_ckad25, ORIGINAL_SOURCE, ORIGINAL_TREE, SOURCE_REPO,
    RUN_ID, SNAPSHOT_COMMIT, SNAPSHOT_TREE, PATHS,
)
from f139.ckad25_artifact_bridge import FILES
from f139.ckad_campaign_request import CampaignDenied
from f139.ckad_stage_custody import canonical, digest
from f139.test_ckad25_artifact_bridge import archive


def sample():
    # Use existing owned synthetic 9-file fixture with source metadata rebound
    # to the exact *already consumed* persistent developer result source.
    with zipfile.ZipFile(BytesIO(archive())) as z:
        base = {name:z.read(name) for name in z.namelist()}
    for stage in (1, 2):
        prefix = "stage-0"+str(stage)
        obj = json.loads(base[prefix+".receipt.json"])
        obj["source_commit"] = ORIGINAL_SOURCE
        obj["source_tree"] = ORIGINAL_TREE
        if stage == 2:
            obj["parent_receipt_sha256"] = first_pin
        stable = dict(obj)
        stable.pop("wall_milliseconds")
        stable.pop("stable_receipt_sha256")
        obj["stable_receipt_sha256"] = digest(canonical(stable))
        if stage == 1:
            first_pin = obj["stable_receipt_sha256"]
        else:
            second_pin = obj["stable_receipt_sha256"]
        base[prefix+".receipt.json"] = canonical(obj)
    result = json.loads(base["campaign-result.json"])
    result.update(source_sha=ORIGINAL_SOURCE, source_tree=ORIGINAL_TREE,
                  receipts=[first_pin, second_pin])
    base["campaign-result.json"] = canonical(result)
    files = {"linux/"+p:base[p] for p in FILES}
    files.update({"windows/"+p:base[p] for p in FILES})
    data = {
        "schema":"yggdrasil.ckad.persistent-development-evidence.v1",
        "original_source_sha": ORIGINAL_SOURCE,
        "original_source_tree": ORIGINAL_TREE,
        "github_run_id": RUN_ID,
        "campaign_result_sha256": digest(base["campaign-result.json"]),
        "final_checkpoint_sha256": result["final_checkpoint_sha256"],
        "all_platform_files_sha256": {p:digest(raw) for p,raw in files.items()},
        "scientific_first_use": False, "scientific_pass": False,
        "accepted_native": False, "forge_dispatch_authorized": False,
    }
    return canonical(data), files


def verify(manifest, files, *, commit=SNAPSHOT_COMMIT, tree=SNAPSHOT_TREE):
    return audit_persisted_ckad25(
        manifest,files,repository=SOURCE_REPO,commit=commit,tree=tree)


class CommittedDevelopmentEvidenceTests(unittest.TestCase):
    def test_persisted_checkpoint_continuity_is_not_execution_authority(self):
        a,b=sample();x=verify(a,b)
        self.assertEqual(x["stages_verified_from_committed_files"],2)
        self.assertEqual(x["platform_files_verified"],18)
        self.assertEqual(x["final_checkpoint_sha256"],digest(b["linux/stage-02.native.json"]))
        self.assertFalse(x["owner_permit_verified"])
        self.assertFalse(x["training_execution_authorized"])
        self.assertFalse(x["scientific_pass"])

    def test_git_commit_tree_and_manifest_must_match(self):
        a,b=sample()
        with self.assertRaises(CampaignDenied):
            verify(a,b,commit="0"*40)
        with self.assertRaises(CampaignDenied):
            verify(a,b,tree="0"*40)
        z=json.loads(a);z["scientific_pass"]=True
        with self.assertRaises(CampaignDenied):
            verify(canonical(z),b)
        z=json.loads(a);z["original_source_sha"]="0"*40
        with self.assertRaises(CampaignDenied):
            verify(canonical(z),b)

    def test_missing_file_extra_file_tamper_and_platform_drift(self):
        a,b=sample()
        broken=dict(b);broken.pop("windows/stage-02.native.json")
        with self.assertRaises(CampaignDenied):
            verify(a,broken)
        broken=dict(b);broken["linux/stage-02.native.json"]+=b"\\n"
        with self.assertRaises(CampaignDenied):
            verify(a,broken)
        broken=dict(b);broken["windows/evaluation.json"]=b"new"
        with self.assertRaises(CampaignDenied):
            verify(a,broken)
        z=json.loads(a);z["all_platform_files_sha256"]["windows/stage-02.native.json"]="0"*64
        with self.assertRaises(CampaignDenied):
            verify(canonical(z),b)

    def test_stable_receipt_tamper_even_with_manifest_rehashed(self):
        a,b=sample();broken=dict(b)
        rec=json.loads(broken["linux/stage-02.receipt.json"])
        rec["scientific_pass"]=True
        broken["linux/stage-02.receipt.json"]=canonical(rec)
        z=json.loads(a);z["all_platform_files_sha256"]["linux/stage-02.receipt.json"]=digest(
            broken["linux/stage-02.receipt.json"])
        with self.assertRaises(CampaignDenied):
            verify(canonical(z),broken)


if __name__=="__main__":
    unittest.main()
