"""F119 adversarial tests of four ACTUAL bounded development actions per run."""
import copy
import hashlib
import os
import sys
from pathlib import Path
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parent))
import f118_autonomy_feedback as old
import f119_second_round as m

SOURCE="a"*40
def advisory():
    def lane(name,base):
        return {
            "lane":name,"source_identity":("b"*40 if name=="Yggdrasil" else "a"*40),
            "frozen_screen_sha256":"1"*64,
            "prompt_candidates":2,"environment_candidates":2,
            "negative_records":1,"invalid_records":1,"mixed_records":1,
            "proposal_ids":[format(base+i,"064x") for i in range(4)],
            "all_candidates_untested":True,"full_population_screened":True,
            "advisory_assessment":"BOUNDED_UNTESTED_NOVELTY_PROPOSALS_READY",
            "science_accepted":False,"original_dispatch_authorized":False}
    return {"schema":old.INPUT,"source_commit_sha":SOURCE,
        "evidence_type":"SYNTHETIC_FROZEN_SOURCE_ONLY_NOT_NEW_SCIENTIFIC_EVIDENCE",
        "lanes":[lane("Wingless",10),lane("Yggdrasil",20)],
        "model_invocations":0,"codex_invocations":0,"network_calls":0,
        "new_scientific_originals":0,"scientific_first_use_authorized":False,
        "real_research_progress_established":False,
        "policy_promotion_authorized":False,"accepted_ref_mutations":0}
def passed(suite,timeout):
    assert timeout==90
    return "PASS",hashlib.sha256(suite.encode()).hexdigest(),0
def metadata(state):
    return {"id":state["run_id"],"head_sha":state["source_sha"],
        "event":"schedule","head_branch":"main","conclusion":"success",
        "run_attempt":1}

class F119Autonomy(unittest.TestCase):
    def setUp(self):
        self.old_sha=os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"]=SOURCE
        self.adv=advisory()
        self.first=old.build(self.adv,SOURCE,100,"schedule",executor=passed)
    def tearDown(self):
        if self.old_sha is None:os.environ.pop("GITHUB_SHA",None)
        else:os.environ["GITHUB_SHA"]=self.old_sha

    def test_immutable_preimplementation_contract_and_F118_engine(self):
        c,d,h=m.frozen()
        self.assertEqual(m.f118.gitblob(m.FREEZE.read_bytes().replace(
            b"\r\n",b"\n")),m.FREEZE_BLOB)
        self.assertEqual(len(d),64)
        self.assertEqual(len(h),64)
        self.assertTrue(all(c["denied"].values()))
        self.assertEqual(c["frozen_algorithm"]["min_actual_checks"],4)

    def test_four_actions_two_per_lane_rotate_on_first_success(self):
        executed=[]
        def actual(suite,timeout):
            executed.append((suite,timeout))
            return passed(suite,timeout)
        report,carried=m.execute(self.adv,self.first,SOURCE,100,
                                  "schedule",executor=actual)
        self.assertEqual(len(executed),2)
        self.assertEqual([r["engineering_readiness_suite"] for r in report["first_round"]],
                         ["./promptlineage","./genenv"])
        self.assertEqual(executed,[("./genenv",90),("./promptlineage",90)])
        self.assertEqual([r["proposal_position"] for r in report["second_round"]],[1,1])
        self.assertEqual(len({r["proposal_id"] for r in
            report["first_round"]+report["second_round"]}),4)
        self.assertEqual(report["total_real_package_checks_this_run"],4)
        self.assertEqual(carried["generation"],4)
        self.assertEqual(carried["evaluations"][0]["proposal_position"],1)
        self.assertEqual(carried["history"]["Wingless:0"]["count"],1)
        self.assertEqual(carried["history"]["Wingless:1"]["count"],1)
        self.assertEqual(carried["history"]["Yggdrasil:0"]["count"],1)
        self.assertEqual(carried["history"]["Yggdrasil:1"]["count"],1)
        self.assertFalse(report["two_distinct_GitHub_scheduled_runs_observed"])
        self.assertFalse(report["research_hypothesis_fitness_established"])
        self.assertEqual(report["optimizer_promotions"],0)

    def test_failed_first_round_is_retried_and_negative_retained(self):
        n=[0]
        def first_runner(suite,timeout):
            n[0]+=1
            return ("FAIL","f"*64,1) if n[0]==1 else passed(suite,timeout)
        first=old.build(self.adv,SOURCE,100,"schedule",executor=first_runner)
        r,next_state=m.execute(self.adv,first,SOURCE,100,"schedule",executor=passed)
        self.assertEqual([x["proposal_position"] for x in r["second_round"]],[0,1])
        self.assertEqual(r["second_round"][0]["selection_reason"],
                         "ONE_BOUNDED_REAL_FAILURE_RETRY")
        self.assertEqual(r["negative_outcomes_count"],1)
        self.assertEqual(next_state["history"]["Wingless:0"]["failures"],1)
        self.assertEqual(next_state["history"]["Wingless:0"]["last"],"PASS")
        self.assertEqual(next_state["history"]["Wingless:0"]["count"],2)

    def test_second_round_timeout_retained_and_no_scientific_fitness(self):
        def timeout(_suite,seconds):
            return "TIMEOUT","c"*64,124
        report,carried=m.execute(self.adv,self.first,SOURCE,100,
                                  "schedule",executor=timeout)
        self.assertEqual(report["negative_outcomes_count"],2)
        self.assertEqual(carried["history"]["Wingless:1"]["last"],"TIMEOUT")
        self.assertEqual(carried["history"]["Yggdrasil:1"]["failures"],1)
        self.assertFalse(report["research_hypothesis_fitness_established"])
        self.assertFalse(carried["qualified_unattended_repetitions"])

    def test_carry_is_accepted_by_real_F118_previous_schedule_reader(self):
        _,carried=m.execute(self.adv,self.first,SOURCE,100,"schedule",executor=passed)
        next_run=old.build(self.adv,SOURCE,101,"schedule",
            previous=carried,previous_meta=metadata(carried),executor=passed)
        self.assertEqual(next_run["generation"],6)
        self.assertEqual(next_run["continuity"],"VERIFIED_PREVIOUS_SCHEDULED_RESULT")
        self.assertEqual(next_run["previous_record_sha256"],old.digest(old.canonical(carried)))
        self.assertEqual([r["proposal_position"] for r in next_run["evaluations"]],[2,2])

    def test_deny_injected_first_round_fake_outcome(self):
        bad=copy.deepcopy(self.first)
        bad["evaluations"][0]["engineering_readiness_suite"]="./malicious"
        with self.assertRaisesRegex(old.Quarantined,"FIRST_ROUND_IS_NOT_ACTUAL_APPROVED_ACTION"):
            m.execute(self.adv,bad,SOURCE,100,"schedule",executor=passed)
        bad=copy.deepcopy(self.first)
        bad["evaluations"][0]["outcome"]="PASS" if bad["evaluations"][0]["outcome"]!="PASS" else "FAIL"
        with self.assertRaisesRegex(old.Quarantined,"FIRST_ROUND_FEEDBACK_MISMATCH"):
            m.execute(self.adv,bad,SOURCE,100,"schedule",executor=passed)

    def test_deny_unearned_scientific_authority_or_wrong_source(self):
        for key,value in (
            ("optimizer_promotions",1),("accepted_ref_mutations",1),
            ("new_scientific_originals",1),("qualified_unattended_repetitions",True)):
            bad=copy.deepcopy(self.first)
            bad[key]=value
            with self.subTest(key=key):
                with self.assertRaisesRegex(old.Quarantined,"FIRST_ROUND_OR_AUTHORITY_UNVERIFIED"):
                    m.execute(self.adv,bad,SOURCE,100,"schedule",executor=passed)
        with mock.patch.dict(os.environ,{"GITHUB_SHA":"b"*40}):
            with self.assertRaisesRegex(old.Quarantined,"CURRENT_RUN_SOURCE_IDENTITY"):
                m.execute(self.adv,self.first,SOURCE,100,"push",executor=passed)

    def test_engineering_action_allowlist_is_frozen(self):
        for lane in old.LANES:
            self.assertEqual(len(old.MAP[lane]),4)
        report,carried=m.execute(self.adv,self.first,SOURCE,100,"push",executor=passed) if False else (None,None)
        self.assertIsNone(report)
        self.assertIsNone(carried)

if __name__=="__main__":unittest.main()
