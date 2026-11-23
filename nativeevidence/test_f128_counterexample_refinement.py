"""F128 failure-driven operator expansion provenance, challenge and autonomy tests."""
from __future__ import annotations
import copy
import os
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f128_counterexample_refinement as m

SOURCE="a"*40
PRIOR={"prior_run_id":39043407682,
       "prior_sha256":"74c74d66db98e5119c1d2db3f25e7f228966ba7464bd2ab5d698bf167307ff5e",
       "prior_ast":{"grammar":"typed-3-hop-join-v1","start_anchor":True,
                    "bind_intermediate_nodes":True,"target_anchor":True},
       "prior_ast_sha256":"64120bae535e163454eb2ea8ed77b32366bcfab20984cc67cf3735658905c26e",
       "prior_problem":{"source_experiment":"F117-O","mechanism_problem":"SHARED_NODE_BINDING",
                        "priority_gap_millionths":205031},
       "scheduled_lineage":False,"development_only":True}

class F128Qualification(unittest.TestCase):
    def setUp(self):
        self.was=os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"]=SOURCE
    def tearDown(self):
        if self.was is None:os.environ.pop("GITHUB_SHA",None)
        else:os.environ["GITHUB_SHA"]=self.was

    def test_preregistered_before_first_mechanism_and_authorities(self):
        p,d=m.freeze()
        self.assertEqual(m.f118.gitblob(m.FREEZE.read_bytes().replace(b"\r\n",b"\n")),m.BLOB)
        self.assertEqual(len(d),64)
        self.assertTrue(all(p["boundaries"].values()))
        self.assertEqual(p["cohorts"]["heldout_generator_b_seeds_inclusive"],[161100,161139])

    def test_prior_compiled_program_actually_fails_train_counterexamples(self):
        baseline=PRIOR["prior_ast"]
        for i in range(160000,160016):
            graph=m.challenge(i,"TRAIN")
            query={"roles":graph["path_roles"],"start":graph["start"],"target":graph["target"]}
            self.assertTrue(m.f127.execute_ast(baseline,query,graph["positive"]))
            self.assertTrue(m.f127.execute_ast(baseline,query,graph["negative"]))

    def test_generated_new_branch_role_operators_are_discovered_from_graphs(self):
        cohort=[m.challenge(s,"TRAIN") for s in range(160000,160016)]
        pairs=m.observed_role_pairs(cohort)
        self.assertIn(("aux-first","aux-last"),pairs)
        progs=m.programs(cohort)
        self.assertEqual(len(progs),16)
        self.assertEqual(len({p["sha256"] for p in progs}),16)
        self.assertEqual({p["ast"]["grammar"] for p in progs},
                         {"f128-two-hop-branch-refinement-v1"})

    def test_independent_a_b_sources_preserve_role_and_degree_histograms(self):
        for seed,phase in ((160000,"TRAIN"),(160015,"TRAIN"),(160100,"A"),
                           (160139,"A"),(161100,"B"),(161139,"B")):
            g=m.challenge(seed,phase)
            self.assertEqual(sorted(s for s,_,_ in g["positive"]),
                             sorted(s for s,_,_ in g["negative"]))
            self.assertEqual(sorted(t for _,_,t in g["positive"]),
                             sorted(t for _,_,t in g["negative"]))
            self.assertEqual(sorted(r for _,r,_ in g["positive"]),
                             sorted(r for _,r,_ in g["negative"]))
            self.assertTrue(m.strong_control(g,g["positive"]))
            self.assertFalse(m.strong_control(g,g["negative"]))

    def test_unanchored_partial_branches_are_falsified(self):
        g=m.challenge(160101,"A")
        for root in range(4):
            for end in range(4):
                p={"grammar":"f128-two-hop-branch-refinement-v1",
                   "prior_base":"typed-3-hop-join-v1",
                   "left_role":"aux-first","right_role":"aux-last",
                   "branch_start_path_index":root,"branch_end_path_index":end}
                yes=m.execute_ast(p,g,g["positive"])
                no=m.execute_ast(p,g,g["negative"])
                if (root,end)==(1,3):
                    self.assertTrue(yes)
                    self.assertFalse(no)
                else:
                    self.assertFalse(yes and not no)

    def test_eight_train_and_two_fresh_challenge_generators(self):
        report=m.synthesize(PRIOR,SOURCE,39050000000,"pull_request")
        self.assertEqual(report["prior_linear_program_train_paired_correct"],0)
        self.assertEqual(report["candidate_count"],16)
        self.assertEqual(report["selected_train"]["paired_correct"],16)
        self.assertEqual(report["train_only_selected_ast"]["branch_start_path_index"],1)
        self.assertEqual(report["train_only_selected_ast"]["branch_end_path_index"],3)
        self.assertEqual(report["heldout_generator_a"]["paired_correct"],40)
        self.assertEqual(report["heldout_generator_b"]["paired_correct"],40)
        self.assertEqual(report["exact_conjunctive_oracle"],{"A":40,"B":40})
        self.assertTrue(report["development_refinement_passed"])
        self.assertFalse(report["unbounded_scientific_invention_proven"])
        self.assertFalse(report["two_genuine_unattended_scheduled_cycles_proven"])
        self.assertEqual(report["scientific_originals_dispatched"],0)

    def test_repeat_same_source_is_byte_exact(self):
        a=m.synthesize(PRIOR,SOURCE,39050000000,"pull_request")
        b=m.synthesize(PRIOR,SOURCE,39050000000,"pull_request")
        self.assertEqual(m.canonical(a),m.canonical(b))

    def test_falsification_failure_blocks_operator_expansion(self):
        fake=copy.deepcopy(PRIOR)
        fake["prior_ast"]["start_anchor"]=False
        with self.assertRaisesRegex(m.Blocked,"CURRENT_AUTHORITY"):
            m.synthesize(fake,SOURCE,39050000000,"pull_request")

    def test_pr_does_not_impersonate_scheduled_main(self):
        with self.assertRaisesRegex(m.Blocked,"SCHEDULED_RUN_LINEAGE"):
            m.synthesize(PRIOR,SOURCE,39050000000,"schedule")
        fake={**PRIOR,"scheduled_lineage":True}
        with self.assertRaisesRegex(m.Blocked,"SCHEDULED_RUN_LINEAGE"):
            m.synthesize(fake,SOURCE,39050000000,"pull_request")

    def test_arbitrary_source_code_or_invalid_ast_rejected(self):
        g=m.challenge(160100,"A")
        with self.assertRaisesRegex(m.Blocked,"UNQUALIFIED_SYNTHESIZED"):
            m.execute_ast({"grammar":"python-exec","prior_base":"typed-3-hop-join-v1",
                           "left_role":"aux-first","right_role":"aux-last",
                           "branch_start_path_index":1,"branch_end_path_index":3},
                          g,g["positive"])

    def test_prior_run_failure_cannot_be_admitted(self):
        p,_=m.freeze()
        bad={"id":39043407682,"status":"completed","conclusion":"failure",
             "run_attempt":1,"event":"pull_request"}
        with self.assertRaisesRegex(m.Blocked,"PREVIOUS_RUN_NOT_GENUINE"):
            m.read_previous(bad,{"artifacts":[]},b"",b"",b"",b"",
                            39050000000,"pull_request",p)

if __name__=="__main__":
    unittest.main()
