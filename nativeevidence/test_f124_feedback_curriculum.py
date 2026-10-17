"""F124 source-only feedback autonomy: adversarial identity and decision tests."""
from __future__ import annotations
import copy
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import f124_feedback_curriculum as m
from test_f120_generated_environment import advisory

SOURCE="a"*40

class F124Autonomy(unittest.TestCase):
    def setUp(self):
        self.old=os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"]=SOURCE
    def tearDown(self):
        if self.old is None: os.environ.pop("GITHUB_SHA",None)
        else:os.environ["GITHUB_SHA"]=self.old

    def test_frozen_parent_exact_blob_and_authority(self):
        self.assertEqual(m.f118.gitblob(m.FREEZE.read_bytes().replace(b"\r\n",b"\n")),
                         m.FREEZE_BLOB)
        self.assertEqual(len(m.freeze()),64)

    def test_source_linked_candidate_mutations_unique_and_bounded(self):
        cand=m.f120.validate(advisory(),SOURCE)
        for lane in m.LANES:
            pool=m.calibration(cand[lane],lane,0)
            self.assertEqual(len(pool),3)
            self.assertEqual(len({x["derived_candidate_sha256"] for x in pool}),3)
            for option in pool:
                self.assertEqual(option["screen"]["cases"],8)
                self.assertEqual(option["screen"]["oracle_correct"],8)
                self.assertEqual(option["screen"]["role_only_correct"],0)
                self.assertEqual(len(option["derived_candidate_sha256"]),64)

    def test_actual_two_round_feedback_changes_choices_and_retains_negatives(self):
        report=m.execute(advisory(),SOURCE,101,"pull_request")
        self.assertEqual(report["schema"],m.SCHEMA)
        self.assertEqual(report["actual_controlled_graph_pairs"],96)
        self.assertEqual(report["bounded_generated_hypothesis_choices"],3)
        self.assertTrue(report["feedback_changes_second_round"])
        self.assertEqual(len(report["rounds"]),4)
        for lane in m.LANES:
            rounds=[x for x in report["rounds"] if x["lane"]==lane]
            self.assertEqual(len(rounds),2)
            self.assertNotEqual(rounds[0]["direction"],rounds[1]["direction"])
            self.assertNotEqual(rounds[0]["selection_history_sha256"],
                                rounds[1]["selection_history_sha256"])
            self.assertTrue(all(x["training"]["cases"]==8 and
                                x["confirmation"]["cases"]==16 for x in rounds))
            self.assertEqual(sum(v["count"] for k,v in report["history"].items()
                                 if k.startswith(lane+":")),2)
        self.assertFalse(report["scientific_hypothesis_invention_proven"])
        self.assertEqual(report["scientific_originals"],0)
        self.assertEqual(report["optimizer_promotions"],0)

    def test_same_exact_source_is_byte_deterministic(self):
        left=m.execute(advisory(),SOURCE,1001,"pull_request")
        right=m.execute(advisory(),SOURCE,1001,"pull_request")
        self.assertEqual(m.canonical(left),m.canonical(right))

    def test_scheduled_previous_feedback_is_verified_and_changes_next_choices(self):
        prior=m.execute(advisory(),SOURCE,101,"schedule")
        meta={"id":101,"head_sha":SOURCE,"event":"schedule",
              "head_branch":"main","run_attempt":1,"conclusion":"success"}
        next_result=m.execute(advisory(),SOURCE,102,"schedule",prior,meta)
        self.assertEqual(next_result["continuity"],"VERIFIED_PREVIOUS_F124_SCHEDULE")
        self.assertEqual(next_result["prior_record_sha256"],m.sha(prior))
        self.assertEqual(next_result["generation"],prior["generation"]+1)
        for lane in m.LANES:
            count=sum(v["count"] for k,v in next_result["history"].items()
                      if k.startswith(lane+":"))
            self.assertEqual(count,4)
        self.assertFalse(next_result["unattended_two_run_continuity_proven"])

    def test_previous_replay_and_source_drift_are_quarantined(self):
        prior=m.execute(advisory(),SOURCE,101,"schedule")
        meta={"id":101,"head_sha":SOURCE,"event":"schedule",
              "head_branch":"main","run_attempt":1,"conclusion":"success"}
        for badmeta in ({**meta,"head_sha":"b"*40},
                        {**meta,"event":"pull_request"},
                        {**meta,"run_attempt":2},
                        {**meta,"conclusion":"failure"}):
            with self.assertRaisesRegex(m.Quarantined,"PREVIOUS_RUN_IDENTITY"):
                m.execute(advisory(),SOURCE,102,"schedule",prior,badmeta)
        with self.assertRaisesRegex(m.Quarantined,"PREVIOUS_RUN_IDENTITY"):
            m.execute(advisory(),SOURCE,101,"schedule",prior,meta)
        with self.assertRaisesRegex(m.Quarantined,"NON_SCHEDULED"):
            m.execute(advisory(),SOURCE,102,"pull_request",prior,meta)

    def test_corrupt_history_and_false_authority_fails_closed(self):
        prior=m.execute(advisory(),SOURCE,101,"schedule")
        meta={"id":101,"head_sha":SOURCE,"event":"schedule",
              "head_branch":"main","run_attempt":1,"conclusion":"success"}
        bad=copy.deepcopy(prior)
        bad["history"]["Wingless:DEPTH_SHORTCUT"]={"count":-1}
        with self.assertRaises(m.Quarantined):
            m.execute(advisory(),SOURCE,102,"schedule",bad,meta)
        bad=copy.deepcopy(prior)
        bad["scientific_originals"]=1
        with self.assertRaisesRegex(m.Quarantined,"PREVIOUS_RUN_IDENTITY"):
            m.execute(advisory(),SOURCE,102,"schedule",bad,meta)

    def test_advisory_source_mismatch_and_disallowed_promotion(self):
        with self.assertRaises((m.f118.Quarantined,m.f120.Invalid)):
            m.execute(advisory(),"b"*40,101,"pull_request")
        bad=copy.deepcopy(advisory())
        bad["accepted_ref_mutations"]=1
        with self.assertRaises((m.f118.Quarantined,m.f120.Invalid)):
            m.execute(bad,SOURCE,101,"pull_request")

if __name__=="__main__":
    unittest.main()
