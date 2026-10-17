"""F125 adversarial proof: authentic-source identity, negatives, and actual feedback routing."""
import copy
import json
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parent))
import f125_authentic_feedback as m
from test_f120_generated_environment import advisory

SOURCE="a"*40
RUN=39038465506
NEW=39040000000

def fixture(negative=True):
    protocol,_=m.frozen()
    protocol=copy.deepcopy(protocol)
    pinned=protocol["historical_pr_evidence"]
    def sample(lane,direction,score,index):
        return {"lane":lane,"round":index,"direction":direction,
                "feedback_discrimination":score,
                "generated_vector":[2,3,1] if index==1 else [1,1,3],
                "confirmation":{"cases":16,"oracle_correct":16,
                                "discrimination":score,"sha256":format(index+20,"064x")}}
    last=0 if negative else 16
    state={"schema":m.f124.SCHEMA,"run_id":RUN,
           "source_sha":pinned["checked_merge_source_sha"],"event":"pull_request",
           "scientific_originals":0,"accepted_ref_mutations":0,
           "optimizer_promotions":0,"scientific_hypothesis_invention_proven":False,
           "unattended_two_run_continuity_proven":False,
           "actual_controlled_graph_pairs":96,
           "model_free_source_only_challenge_selection":True,
           "history":{},"rounds":[]}
    for lane in ("Wingless","Yggdrasil"):
        state["history"][lane+":DISTRACTOR_SHORTCUT"]={
            "count":1,"last_discrimination":16,"negatives":0,
            "total_discrimination":16}
        state["history"][lane+":ROLE_ALIAS_SHORTCUT"]={
            "count":1,"last_discrimination":last,"negatives":int(last==0),
            "total_discrimination":last}
    for index,direction,score in ((1,"DISTRACTOR_SHORTCUT",16),
                                   (2,"ROLE_ALIAS_SHORTCUT",last)):
        for lane in ("Wingless","Yggdrasil"):
            state["rounds"].append(sample(lane,direction,score,index))
    data=m.canonical(state)
    pinned["report_sha256"]=m.sha_bytes(data)
    meta={"id":RUN,"repository":{"full_name":pinned["repository"]},
          "head_repository":{"full_name":pinned["repository"]},
          "head_sha":pinned["run_head_sha"],
          "head_branch":"research/f124-autonomy-feedback-curriculum",
          "path":pinned["workflow_path"],"status":"completed",
          "conclusion":"success","run_attempt":1,"event":"pull_request",
          "pull_requests":[{"number":435,"head":{"sha":pinned["run_head_sha"]}}]}
    arts=[]
    for k in ("artifact_ubuntu","artifact_windows"):
        row=pinned[k]
        arts.append({"id":row["id"],"name":row["name"],
                     "digest":"sha256:"+row["zip_sha256"],
                     "expired":False,"size_in_bytes":20000,
                     "workflow_run":{"id":RUN,"head_sha":pinned["run_head_sha"]}})
    artifact_list={"total_count":2,"artifacts":arts}
    receipt=(m.sha_bytes(data)+"  state.json\n").encode()
    return protocol,meta,artifact_list,data,receipt

def read(package):
    p,r,a,b,receipt=package
    return m.read_evidence(r,a,b,receipt,b,receipt,NEW,"pull_request",p)

class F125Qualification(unittest.TestCase):
    def setUp(self):
        self.prior=os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"]=SOURCE
    def tearDown(self):
        if self.prior is None:os.environ.pop("GITHUB_SHA",None)
        else:os.environ["GITHUB_SHA"]=self.prior

    def test_preimplementation_frozen_source_and_permissions(self):
        self.assertEqual(m.f118.gitblob(m.FREEZE.read_bytes().replace(b"\r\n",b"\n")),m.BLOB)
        p,d=m.frozen()
        self.assertEqual(p["historical_pr_evidence"]["run_id"],RUN)
        self.assertEqual(len(d),64)
        self.assertTrue(all(p["authority"].values()))

    def test_authentic_prior_negative_drives_new_genenv_family(self):
        e=read(fixture())
        out=m.execute(advisory(),SOURCE,NEW,"pull_request",e)
        self.assertTrue(out["authenticated_prior_development_outcomes_consumed"])
        self.assertEqual(out["actual_confirmed_development_pairs"],32)
        for x in out["lanes"]:
            self.assertEqual(x["negative_observations_preserved"],1)
            self.assertEqual(x["positive_observations_preserved"],1)
            self.assertEqual(x["chosen_from_prior_development_outcome"],"ROLE_ALIAS_SHORTCUT")
            self.assertTrue(x["source_derived_proposals"])
            self.assertEqual(x["confirmation"]["pairs"],16)
            self.assertEqual(x["confirmation"]["oracle_correct"],16)
            self.assertNotIn([1,1,3],[y["vector"] for y in x["source_derived_proposals"]])
            self.assertFalse(x["scientifically_validated_model_mechanism"])
        self.assertFalse(out["new_autonomous_mechanism_discovered"])
        self.assertEqual(out["optimizer_promotions"],0)

    def test_changed_real_feedback_changes_next_research_direction(self):
        neg=m.execute(advisory(),SOURCE,NEW,"pull_request",read(fixture(True)))
        pos=m.execute(advisory(),SOURCE,NEW,"pull_request",read(fixture(False)))
        for a,b in zip(neg["lanes"],pos["lanes"]):
            self.assertEqual(a["chosen_from_prior_development_outcome"],"ROLE_ALIAS_SHORTCUT")
            self.assertEqual(b["chosen_from_prior_development_outcome"],"DEPTH_SHORTCUT")
            self.assertNotEqual(a["train_only_winner_sha256"],b["train_only_winner_sha256"])

    def test_cross_os_tamper_or_receipt_replay_fail_closed(self):
        p,meta,art,data,receipt=fixture()
        for bad in (data+b"\n",data.replace(b"ROLE_ALIAS_SHORTCUT",b"ROLE_ALIAZ_SHORTCUT")):
            with self.assertRaisesRegex(m.Quarantined,"CROSS_OS_RECORDS"):
                bad_receipt=(m.sha_bytes(bad)+"  state.json\n").encode()
                m.read_evidence(meta,art,data,receipt,bad,bad_receipt,NEW,"pull_request",p)
        with self.assertRaisesRegex(m.Quarantined,"RECEIPT"):
            m.read_evidence(meta,art,data,b"0"*64,data,receipt,NEW,"pull_request",p)

    def test_run_attempt_source_and_zip_digests_cannot_be_spoofed(self):
        for field,value in (("run_attempt",2),("conclusion","failure"),
                            ("head_sha","b"*40),("event","schedule")):
            p,meta,art,data,rec=fixture()
            meta[field]=value
            with self.assertRaises(m.Quarantined):
                m.read_evidence(meta,art,data,rec,data,rec,NEW,"pull_request",p)
        p,meta,art,data,rec=fixture()
        art["artifacts"][0]["digest"]="sha256:"+"f"*64
        with self.assertRaisesRegex(m.Quarantined,"FROZEN_ARTIFACT_DIGEST"):
            m.read_evidence(meta,art,data,rec,data,rec,NEW,"pull_request",p)

    def test_historical_negative_cannot_disappear_or_be_relabelled(self):
        p,meta,art,data,receipt=fixture()
        state=json.loads(data)
        state["history"]["Wingless:ROLE_ALIAS_SHORTCUT"]["negatives"]=0
        tampered=m.canonical(state)
        p["historical_pr_evidence"]["report_sha256"]=m.sha_bytes(tampered)
        r=(m.sha_bytes(tampered)+"  state.json\n").encode()
        with self.assertRaisesRegex(m.Quarantined,"HISTORICAL_NEGATIVE"):
            m.read_evidence(meta,art,tampered,r,tampered,r,NEW,"pull_request",p)

    def test_pr_cannot_impersonate_main_scheduled_run(self):
        p,meta,art,data,receipt=fixture()
        with self.assertRaisesRegex(m.Quarantined,"PR_RUN_CANNOT_IMPERSONATE_SCHEDULE"):
            m.read_evidence(meta,art,data,receipt,data,receipt,NEW,"schedule",p)
        e=read(fixture())
        with self.assertRaisesRegex(m.Quarantined,"PR_PREVIEW_CANNOT"):
            m.execute(advisory(),SOURCE,NEW,"schedule",e)

    def test_reject_duplicate_keys_and_scientific_promotions(self):
        with self.assertRaisesRegex(m.Quarantined,"JSON_DUPLICATE_KEY"):
            m.strict_json(b'{"run_id":1,"run_id":2}')
        bad=advisory()
        bad["accepted_ref_mutations"]=1
        with self.assertRaises(m.f118.Quarantined):
            m.execute(bad,SOURCE,NEW,"pull_request",read(fixture()))

if __name__=="__main__":unittest.main()
