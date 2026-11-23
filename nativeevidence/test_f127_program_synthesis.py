"""F127 adversarial tests: real evidence boundary and bounded program synthesis."""
from __future__ import annotations
import copy
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import f127_program_synthesis as m

CURRENT="a"*40
PRIOR={"verified_prior_run":39041234945,
       "verified_artifact_sha256":"034c8f016918c8bdcd9a64cd8564a0b3ce4070f477a48343ec88391b2fa77d62",
       "selected_development_problem":{"source_experiment":"F117-O",
          "mechanism_problem":"SHARED_NODE_BINDING","priority_gap_millionths":205031},
       "source_original_losses":[{"experiment":"F116-O","unrecovered_loss_millionths":38333},
                                 {"experiment":"F117-O","unrecovered_loss_millionths":205031}],
       "development_only":True,"scheduled_cross_run_real":False}

class F127Tests(unittest.TestCase):
    def setUp(self):
        self.old=os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"]=CURRENT
    def tearDown(self):
        if self.old is None:os.environ.pop("GITHUB_SHA",None)
        else:os.environ["GITHUB_SHA"]=self.old

    def test_frozen_before_implementation_and_scientific_denials(self):
        f,d=m.frozen()
        self.assertEqual(m.f118.gitblob(m.FREEZE.read_bytes().replace(b"\r\n",b"\n")),m.FREEZE_BLOB)
        self.assertEqual(len(d),64)
        self.assertTrue(all(f["limits"].values()))
        self.assertEqual(f["source"]["prior_run_id"],39041234945)

    def test_generated_all_eight_executable_distinct_ast_candidates(self):
        p=m.generated_programs()
        self.assertEqual(len(p),8)
        self.assertEqual(len({r["ast_sha256"] for r in p}),8)
        self.assertEqual(sorted(r["complexity"] for r in p),[0,1,1,1,2,2,2,3])
        self.assertTrue(all(set(r["ast"])==
            {"grammar","start_anchor","bind_intermediate_nodes","target_anchor"} for r in p))

    def test_independent_confirm_cohort_joint_identity_and_marginals(self):
        for seed,phase in ((140000,"TRAIN"),(140007,"TRAIN"),
                           (140100,"CONFIRM"),(140101,"CONFIRM"),(140163,"CONFIRM")):
            g=m.challenge(seed,phase)
            role_hist=lambda edges:sorted(e[1] for e in edges)
            degrees=lambda edges:(sorted(e[0] for e in edges),
                                   sorted(e[2] for e in edges))
            self.assertEqual(role_hist(g["positive"]),role_hist(g["negative"]))
            self.assertEqual(degrees(g["positive"]),degrees(g["negative"]))
            full=[p for p in m.generated_programs() if p["complexity"]==3][0]
            self.assertTrue(m.execute_ast(full["ast"],g,g["positive"]))
            self.assertFalse(m.execute_ast(full["ast"],g,g["negative"]))

    def test_missing_either_anchor_or_intermediate_node_binding_is_falsified(self):
        g=m.challenge(140100,"CONFIRM")
        for p in m.generated_programs():
            yes=m.execute_ast(p["ast"],g,g["positive"])
            no=m.execute_ast(p["ast"],g,g["negative"])
            self.assertTrue(yes)
            if p["complexity"]==3:self.assertFalse(no)
            else:self.assertTrue(no)

    def test_training_only_program_selection_and_fresh_confirmation(self):
        report=m.synthesize(PRIOR,CURRENT,39050000000,"pull_request")
        self.assertEqual(report["program_count"],8)
        self.assertTrue(report["selection_from_training_only"])
        self.assertEqual(report["selected_complexity"],3)
        self.assertEqual(report["source_only_heldout"]["count"],64)
        self.assertEqual(report["source_only_heldout"]["paired_correct"],64)
        self.assertEqual(report["exact_symbolic_ceiling"]["paired_correct"],64)
        self.assertTrue(report["frozen_heldout_mechanism_criterion_passed"])
        self.assertEqual(report["scientific_originals_dispatched"],0)
        self.assertEqual(report["accepted_ref_mutations"],0)
        self.assertFalse(report["independent_scientific_mechanism_invented"])
        self.assertFalse(report["genuine_two_scheduled_run_continuity_proven"])

    def test_repeated_original_source_program_generation_is_bit_identical(self):
        a=m.synthesize(PRIOR,CURRENT,39050000000,"pull_request")
        b=m.synthesize(PRIOR,CURRENT,39050000000,"pull_request")
        self.assertEqual(m.canonical(a),m.canonical(b))

    def test_fail_closed_on_missing_original_problem_or_source_drift(self):
        corrupt=copy.deepcopy(PRIOR)
        corrupt["selected_development_problem"]["mechanism_problem"]="OTHER"
        with self.assertRaisesRegex(m.Blocked,"CURRENT_SOURCE"):
            m.synthesize(corrupt,CURRENT,39050000000,"pull_request")
        with self.assertRaisesRegex(m.Blocked,"CURRENT_SOURCE"):
            m.synthesize(PRIOR,"b"*40,39050000000,"pull_request")

    def test_previous_pr_cannot_impersonate_main_schedule(self):
        with self.assertRaisesRegex(m.Blocked,"PR_RUN_CANNOT_CLAIM"):
            m.synthesize(PRIOR,CURRENT,39050000000,"schedule")
        changed=copy.deepcopy(PRIOR)
        changed["scheduled_cross_run_real"]=True
        with self.assertRaisesRegex(m.Blocked,"SCHEDULED_STATE"):
            m.synthesize(changed,CURRENT,39050000000,"pull_request")

    def test_unqualified_grammar_program_quarantined(self):
        g=m.challenge(140100,"CONFIRM")
        with self.assertRaisesRegex(m.Blocked,"UNQUALIFIED_GENERATED"):
            m.execute_ast({"grammar":"execute-shell","start_anchor":True,
                           "bind_intermediate_nodes":True,"target_anchor":True},
                          g,g["positive"])

    def test_prior_github_run_identity_and_digest_fail_closed(self):
        protocol,_=m.frozen()
        old={"id":39041234945,"status":"completed","conclusion":"failure",
             "event":"pull_request","run_attempt":1,
             "repository":{"full_name":"spoonman136668-ai/FORGE"},
             "head_repository":{"full_name":"spoonman136668-ai/FORGE"},
             "head_sha":"82f9641734df9940c1498d59b0c98bef0205b991",
             "head_branch":"research/f126-original-negative-to-agenda",
             "path":".github/workflows/forge-integrated-synthetic-cycle.yml",
             "pull_requests":[{"number":437,"head":{"sha":
               "82f9641734df9940c1498d59b0c98bef0205b991"}}]}
        with self.assertRaisesRegex(m.Blocked,"UNAUTHENTIC_GITHUB"):
            m.read_previous(old,{"artifacts":[]},b"",b"",b"",b"",
                            39050000000,"pull_request",protocol)

if __name__=="__main__": unittest.main()
