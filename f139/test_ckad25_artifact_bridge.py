"""Exact GitHub run/artifact and cross-platform CKAD campaign negative controls."""
import copy
from io import BytesIO
import zipfile
import unittest

from f139.ckad25_artifact_bridge import audit_github_development_campaign
from f139.ckad_campaign_request import CampaignDenied
from f139.ckad_stage_custody import CKAD25_DEV_SHA, CKAD25_DEV_TREE, digest, canonical
from f139.test_ckad_native_stage_artifact import native


def archive(changed=None):
    data = {"initial.native.json": native(),
            "stage-01.native.json": native(1),
            "stage-02.native.json": native(2)}
    parent = None
    for i in (1, 2):
        prefix = "stage-0" + str(i)
        rows = [[0, 0, 0]] * (8 if i == 1 else 4)
        packet = canonical({
            "source_mode": "engineering_fixture_only",
            "source_kind": "engineering_public_binary_consequence",
            "source_ref": "a"*64, "slot": 0, "rows": rows})
        old = data["initial.native.json"] if i == 1 else data["stage-01.native.json"]
        new = data[prefix+".native.json"]
        rec = {
            "schema": "yggdrasil.ckad.native-development-stage-receipt.v1",
            "campaign_id": "ckad-two-stage-dev-20261118",
            "stage_index": i-1, "stage_id": "learn-stage-0"+str(i),
            "source_commit": CKAD25_DEV_SHA, "source_tree": CKAD25_DEV_TREE,
            "input_checkpoint_sha256": digest(old),
            "output_checkpoint_sha256": digest(new),
            "packet_sha256": digest(packet),
            "observations": len(rows), "wall_milliseconds": 77,
            "checkpoint_changed": True,
            "native_cold_restore_verified": True,
            "development_fixture_training_executed": True,
            "original_source_authenticated": False,
            "scientific_first_use": False, "forge_dispatch_authorized": False,
            "scientific_pass": False, "model_promotion_authorized": False,
            "parent_receipt_sha256": parent,
        }
        stable = digest(canonical({k:v for k,v in rec.items() if k!="wall_milliseconds"}))
        rec["stable_receipt_sha256"] = stable
        parent = stable
        data[prefix+".receipt.json"] = canonical(rec)
        data[prefix+".packet.json"] = packet
    metric = {"held":4, "answered":0, "correct":0, "predictions":[None]*4,
              "constant_zero_correct":4, "constant_one_correct":0}
    ev = {"schema": "yggdrasil.ckad.development-held-evaluation.v1",
          "checkpoint_sha256": digest(data["stage-02.native.json"]),
          "metrics": metric, "scientific_pass":False,
          "independent_science": False}
    data["evaluation.json"] = canonical(ev)
    recs = [__import__("json").loads(data["stage-0"+str(i)+".receipt.json"])
            for i in (1,2)]
    data["campaign-result.json"] = canonical({
        "schema":"yggdrasil.ckad.bounded-development-campaign.v1",
        "campaign_id":"ckad-two-stage-dev-20261118",
        "source_repo":"spoonman136668-ai/Yggdrasil",
        "source_sha":CKAD25_DEV_SHA, "source_tree":CKAD25_DEV_TREE,
        "source_mode":"previously-consumed-engineering-fixture-only",
        "stages_completed":2, "evaluations_completed":1,
        "observations":12, "interventions":0,
        "initial_checkpoint_sha256":digest(data["initial.native.json"]),
        "final_checkpoint_sha256":digest(data["stage-02.native.json"]),
        "evaluation_sha256":digest(data["evaluation.json"]),
        "receipts":[x["stable_receipt_sha256"] for x in recs],
        "held_total":4, "held_correct":0, "held_answered":0,
        "scientific_first_use":False, "scientific_pass":False,
        "forge_dispatch_authorized":False, "accepted_native":False,
    })
    if changed:
        changed(data)
    out=BytesIO()
    with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for k,v in data.items():
            z.writestr(k,v)
    return out.getvalue()


def supplied(a,b):
    run = {"id":44327111378,
           "name":"CKAD25 source-owned bounded development training proof",
           "path":".github/workflows/ckad25-development-campaign.yml",
           "head_branch":"research/ckad-native-stage-dev-20261118",
           "head_sha":CKAD25_DEV_SHA, "event":"push",
           "status":"completed","conclusion":"success","run_attempt":1,
           "actor":{"login":"spoonman136668-ai"}}
    artifacts = {"artifacts":[]}
    for platform, raw in (("ubuntu-latest",a),("windows-2022",b)):
        artifacts["artifacts"].append({
            "name":"ckad25-development-training-"+platform,
            "id":1 if platform=="ubuntu-latest" else 2,
            "size_in_bytes":len(raw), "digest":"sha256:"+digest(raw),
            "expired":False,
            "workflow_run":{"id":run["id"],"head_sha":CKAD25_DEV_SHA}
        })
    return run,artifacts,{"ubuntu-latest":a,"windows-2022":b}


class SourceOwnedArchiveAuditTests(unittest.TestCase):
    def test_both_platforms_match_and_no_new_authority(self):
        x=archive()
        r,a,z=supplied(x,x)
        report=audit_github_development_campaign(r,a,z)
        self.assertEqual(report["training_stages_verified_from_bytes"],2)
        self.assertTrue(report["cross_platform_checkpoint_bytes_equal"])
        self.assertFalse(report["scientific_pass"])
        self.assertFalse(report["forge_dispatch_authorized"])
        self.assertEqual(report["held_correct"],0)

    def test_wrong_run_source_owner_or_artifact_digests_denied(self):
        raw=archive();r,a,z=supplied(raw,raw)
        for key,val in (("run_attempt",2),("head_sha","0"*40),
                        ("status","in_progress"),("event","workflow_dispatch")):
            bad=dict(r,**{key:val})
            with self.subTest(key=key),self.assertRaises(CampaignDenied):
                audit_github_development_campaign(bad,a,z)
        r,a,z=supplied(raw,raw)
        a["artifacts"][1]["digest"]="sha256:"+"0"*64
        with self.assertRaises(CampaignDenied):
            audit_github_development_campaign(r,a,z)

    def test_corrupted_native_state_or_receipt_denied_even_when_zip_rehashed(self):
        raw=archive()
        def corrupt(items):
            items["stage-02.native.json"] += b"\\n"
        damaged=archive(corrupt)
        r,a,z=supplied(raw,damaged)
        with self.assertRaises(CampaignDenied):
            audit_github_development_campaign(r,a,z)

        def forged(items):
            import json
            d=json.loads(items["stage-02.receipt.json"])
            d["scientific_pass"]=True
            items["stage-02.receipt.json"]=canonical(d)
        changed=archive(forged)
        r,a,z=supplied(changed,changed)
        with self.assertRaises(CampaignDenied):
            audit_github_development_campaign(r,a,z)

    def test_untrusted_archive_inventory_denied(self):
        raw=archive()
        with zipfile.ZipFile(BytesIO(raw)) as z:
            members={n:z.read(n) for n in z.namelist()}
        members["extra.txt"]=b"x"
        out=BytesIO()
        with zipfile.ZipFile(out,"w") as z:
            for name,data in members.items():z.writestr(name,data)
        changed=out.getvalue();r,a,z=supplied(changed,changed)
        with self.assertRaises(CampaignDenied):
            audit_github_development_campaign(r,a,z)


if __name__=="__main__":
    unittest.main()
