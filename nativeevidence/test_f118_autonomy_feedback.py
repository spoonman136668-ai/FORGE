"""F118 bounded unattended development feedback: adversarial source and state tests."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f118_autonomy_feedback as m

SRC="a"*40
def proposal(lane,offset):
    return {"lane":lane,"source_identity":("a"*40 if lane=="Wingless" else "b"*40),
            "frozen_screen_sha256":"1"*64,
            "prompt_candidates":2,"environment_candidates":2,
            "negative_records":1,"invalid_records":1,"mixed_records":1,
            "proposal_ids":[format(offset+i,"064x") for i in range(4)],
            "all_candidates_untested":True,"full_population_screened":True,
            "advisory_assessment":"BOUNDED_UNTESTED_NOVELTY_PROPOSALS_READY",
            "science_accepted":False,"original_dispatch_authorized":False}
def advisory():
    return {"schema":m.INPUT,"source_commit_sha":SRC,
      "evidence_type":"SYNTHETIC_FROZEN_SOURCE_ONLY_NOT_NEW_SCIENTIFIC_EVIDENCE",
      "lanes":[proposal("Wingless",1),proposal("Yggdrasil",5)],
      "model_invocations":0,"codex_invocations":0,"network_calls":0,
      "new_scientific_originals":0,"scientific_first_use_authorized":False,
      "real_research_progress_established":False,
      "policy_promotion_authorized":False,"accepted_ref_mutations":0}
def fake_pass(package,seconds):
    assert package in [suite for group in m.MAP.values() for suite in group]
    assert seconds==90
    return "PASS",hashlib.sha256(package.encode()).hexdigest(),0
def prior_meta(state):
    return {"id":state["run_id"],"head_sha":state["source_sha"],
            "event":"schedule","head_branch":"main",
            "conclusion":"success","run_attempt":1}

class F118FeedbackTests(unittest.TestCase):
    def setUp(self):
        self._prior_sha=os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"]=SRC

    def tearDown(self):
        if self._prior_sha is None:os.environ.pop("GITHUB_SHA",None)
        else:os.environ["GITHUB_SHA"]=self._prior_sha

    def test_freeze_and_no_sci_authority(self):
        cfg,h=m.frozen()
        self.assertEqual(m.gitblob(m.FROZEN.read_bytes().replace(b"\r\n",b"\n")),m.FROZEN_BLOB)
        self.assertEqual(len(h),64)
        self.assertEqual(cfg["qualification"]["cycles_per_run"],2)
        self.assertTrue(all(cfg["forbidden"].values()))
        self.assertTrue(cfg["first_use_denied"])

    def test_model_free_two_lane_source_input_and_historical_negative(self):
        self.assertEqual(len(m.validate_advisory(advisory(),SRC)),2)
        self.assertEqual(advisory()["lanes"][0]["negative_records"],1)
        self.assertEqual(advisory()["lanes"][1]["invalid_records"],1)
        changed=advisory()
        changed["lanes"][0]["science_accepted"]=True
        with self.assertRaisesRegex(m.Quarantined,"ADVISORY_GENERATOR_UNQUALIFIED"):
            m.validate_advisory(changed,SRC)

    def test_first_run_executes_two_distinct_real_suites(self):
        with mock.patch.dict(os.environ,{"GITHUB_SHA":SRC}):
            report=m.build(advisory(),SRC,100,"pull_request",executor=fake_pass)
        self.assertEqual(report["continuity"],"BOOTSTRAP_NO_PREVIOUS_F118_ARTIFACT")
        self.assertEqual(report["generation"],2)
        self.assertEqual(len(report["evaluations"]),2)
        self.assertEqual({x["lane"] for x in report["evaluations"]},
                         {"Wingless","Yggdrasil"})
        self.assertNotEqual(report["evaluations"][0]["proposal_id"],
                            report["evaluations"][1]["proposal_id"])
        self.assertTrue(report["feedback_available_to_next_run"])
        self.assertFalse(report["qualified_unattended_repetitions"])
        self.assertEqual(report["new_scientific_originals"],0)

    def test_real_scheduled_second_run_consumes_previous_and_rotates(self):
        with mock.patch.dict(os.environ,{"GITHUB_SHA":SRC}):
            first=m.build(advisory(),SRC,100,"schedule",executor=fake_pass)
            second=m.build(advisory(),SRC,101,"schedule",first,prior_meta(first),
                           executor=fake_pass)
            third=m.build(advisory(),SRC,102,"schedule",second,prior_meta(second),
                          executor=fake_pass)
        self.assertEqual(second["continuity"],"VERIFIED_PREVIOUS_SCHEDULED_RESULT")
        self.assertEqual([r["proposal_position"] for r in first["evaluations"]],[0,0])
        self.assertEqual([r["proposal_position"] for r in second["evaluations"]],[1,1])
        self.assertEqual([r["proposal_position"] for r in third["evaluations"]],[2,2])
        self.assertEqual(third["generation"],6)
        self.assertEqual(third["previous_record_sha256"],m.digest(m.canonical(second)))
        self.assertFalse(third["qualified_unattended_repetitions"])

    def test_recent_failure_is_retried_once_and_retained(self):
        calls=[0]
        def failed_once(package,seconds):
            calls[0]+=1
            if calls[0]==1:
                return "FAIL","f"*64,1
            return fake_pass(package,seconds)
        with mock.patch.dict(os.environ,{"GITHUB_SHA":SRC}):
            first=m.build(advisory(),SRC,100,"schedule",executor=failed_once)
            second=m.build(advisory(),SRC,101,"schedule",first,prior_meta(first),
                           executor=fake_pass)
        self.assertEqual(first["evaluations"][0]["outcome"],"FAIL")
        self.assertEqual(first["history"]["Wingless:0"]["failures"],1)
        self.assertEqual(second["evaluations"][0]["proposal_position"],0)
        self.assertEqual(second["history"]["Wingless:0"]["failures"],1)
        self.assertEqual(second["history"]["Wingless:0"]["last"],"PASS")
        self.assertEqual(second["evaluations"][1]["proposal_position"],1)

    def test_unverified_or_replayed_previous_quarantined(self):
        with mock.patch.dict(os.environ,{"GITHUB_SHA":SRC}):
            first=m.build(advisory(),SRC,100,"schedule",executor=fake_pass)
        fake=prior_meta(first)
        fake["conclusion"]="failure"
        with self.assertRaisesRegex(m.Quarantined,"PREVIOUS_SCHEDULED_RUN_UNTRUSTED"):
            m.build(advisory(),SRC,101,"schedule",first,fake,executor=fake_pass)
        with self.assertRaisesRegex(m.Quarantined,"NON_SCHEDULED_CANNOT_CONSUME"):
            m.build(advisory(),SRC,102,"pull_request",first,prior_meta(first),fake_pass)
        with self.assertRaisesRegex(m.Quarantined,"PREVIOUS_SCHEDULED_RUN_UNTRUSTED"):
            m.build(advisory(),SRC,100,"schedule",first,prior_meta(first),fake_pass)

    def test_same_previous_chain_cannot_mutate_research_authority(self):
        first=m.build(advisory(),SRC,100,"schedule",executor=fake_pass)
        modified=dict(first)
        modified["accepted_ref_mutations"]=1
        with self.assertRaisesRegex(m.Quarantined,"PREVIOUS_SCHEDULED_RUN_UNTRUSTED"):
            m.build(advisory(),SRC,101,"schedule",modified,prior_meta(first),
                    executor=fake_pass)

    def test_changed_input_sha_or_proposal_duplicate_quarantines(self):
        bad=advisory()
        bad["lanes"][1]["proposal_ids"][0]=bad["lanes"][0]["proposal_ids"][0]
        with self.assertRaisesRegex(m.Quarantined,"DUPLICATE_OR_MALFORMED_PROPOSALS"):
            m.build(bad,SRC,200,"pull_request",executor=fake_pass)
        with mock.patch.dict(os.environ,{"GITHUB_SHA":"b"*40}):
            with self.assertRaisesRegex(m.Quarantined,"GITHUB_SOURCE_SHA_MISMATCH"):
                m.build(advisory(),SRC,200,"push",executor=fake_pass)

    def test_suite_execution_allowlist_and_bounded_timeout(self):
        with self.assertRaisesRegex(m.Quarantined,"UNAPPROVED_ENGINEERING_CHECK"):
            m.execute_check("./cmd/malicious",90)
        with self.assertRaisesRegex(m.Quarantined,"UNAPPROVED_ENGINEERING_CHECK"):
            m.execute_check("./dreamrsi",999)

if __name__=="__main__":unittest.main()
