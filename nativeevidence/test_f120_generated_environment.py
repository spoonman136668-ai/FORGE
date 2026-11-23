"""F120 adversarial candidate-specific development evaluation and anti-leakage."""
import copy
import hashlib
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parent))
import f120_generated_environment as m

SRC="a"*40
def lane(name,offset):
    ids=[format(offset+i,"064x") for i in range(4)]
    mechanisms=[format(offset+100+i,"064x") for i in range(4)]
    return {
        "lane":name,
        "source_identity":"b"*40 if name=="Yggdrasil" else "a"*40,
        "frozen_screen_sha256":"1"*64,
        "prompt_candidates":2,"environment_candidates":2,
        "negative_records":1,"invalid_records":1,"mixed_records":1,
        "proposal_ids":mechanisms,
        "generator_candidate_sha256":ids,
        "public_prompt_artifacts":[
            {"candidate_sha256":ids[0],"classification":"UNTESTED","prompt":"reason with verified evidence"},
            {"candidate_sha256":ids[1],"classification":"UNTESTED","prompt":"with reason bounded evidence"}],
        "public_environment_artifacts":[
            {"id":"new-case-a","environment_sha256":ids[2],
             "vector":[1,1,2],"historical_distance":1,
             "classification":"UNTESTED_PROPOSAL"},
            {"id":"new-case-b","environment_sha256":ids[3],
             "vector":[2,2,1],"historical_distance":1,
             "classification":"UNTESTED_PROPOSAL"}],
        "all_candidates_untested":True,"full_population_screened":True,
        "advisory_assessment":"BOUNDED_UNTESTED_NOVELTY_PROPOSALS_READY",
        "science_accepted":False,"original_dispatch_authorized":False}

def advisory():
    return {"schema":m.f118.INPUT,"source_commit_sha":SRC,
        "evidence_type":"SYNTHETIC_FROZEN_SOURCE_ONLY_NOT_NEW_SCIENTIFIC_EVIDENCE",
        "lanes":[lane("Wingless",1),lane("Yggdrasil",50)],
        "model_invocations":0,"codex_invocations":0,"network_calls":0,
        "new_scientific_originals":0,"scientific_first_use_authorized":False,
        "real_research_progress_established":False,
        "policy_promotion_authorized":False,"accepted_ref_mutations":0}

class F120Qualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg,cls.dig=m.frozen()
    def setUp(self):
        self.prior=os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"]=SRC
    def tearDown(self):
        if self.prior is None:os.environ.pop("GITHUB_SHA",None)
        else:os.environ["GITHUB_SHA"]=self.prior

    def test_preimplementation_source_and_denied_authority(self):
        self.assertEqual(m.blob(m.FREEZE.read_bytes().replace(b"\r\n",b"\n")),
                         m.FREEZE_BLOB)
        self.assertEqual(self.cfg["parent_exact_main_head"],
                         "07e9e0903064226f7903c83b12a3bce631ae17bb")
        self.assertEqual(len(self.dig),64)
        self.assertTrue(all(self.cfg["safety"].values()))
        self.assertTrue(self.cfg["selection"]["train_only"])

    def test_source_generator_hash_links_not_fabricated_mechanism_executables(self):
        details=m.validate(advisory(),SRC)
        self.assertEqual([v["candidate_index"] for v in details["Wingless"]],[2,3])
        self.assertNotEqual(details["Wingless"][0]["source_candidate_sha256"],
                            details["Wingless"][0]["proposed_mechanism_sha256"])
        bad=advisory()
        bad["lanes"][0]["public_environment_artifacts"][0]["environment_sha256"]="f"*64
        with self.assertRaisesRegex(m.Invalid,"ENVIRONMENT_VECTOR_OR_GENERATOR_SHA_MISMATCH"):
            m.validate(bad,SRC)

    def test_counterfactual_graph_has_only_one_path_variable_break(self):
        for vec in ([1,1,2],[2,2,1]):
            for seed in (88000,88007,88100,89000,89147):
                case=m.graph(seed,vec)
                self.assertEqual(case["hops"],vec[0]+1)
                self.assertEqual(len(case["positive"]),vec[0]+1+2*vec[1])
                self.assertTrue(m.binding_solver(case,case["positive"]))
                self.assertFalse(m.binding_solver(case,case["negative"]))
                self.assertTrue(m.role_only(case,case["positive"]))
                self.assertTrue(m.role_only(case,case["negative"]))
                # Graph edge topology/role sequence is paired: only one
                # variable value differs in exactly one real edge.
                def topology(edges):return sorted((a,b,r) for a,b,r,_,_ in edges)
                self.assertEqual(topology(case["positive"]),
                                 topology(case["negative"]))

    def test_depth_two_control_solves_shorter_while_missing_long(self):
        small=m.graph(88001,[1,1,2])
        large=m.graph(88001,[2,2,1])
        self.assertTrue(m.readout(small,lambda c,e:m.binding_solver(c,e,max_hops=2))[
                        "paired_correct"])
        self.assertFalse(m.readout(large,lambda c,e:m.binding_solver(c,e,max_hops=2))[
                         "paired_correct"])

    def test_no_confirmation_leak_in_training_selector(self):
        candidates=m.validate(advisory(),SRC)["Wingless"]
        train=[m.evaluate_candidate("Wingless",x,"TRAIN") for x in candidates]
        self.assertEqual([x["pairs"] for x in train],[24,24])
        self.assertEqual([x["depth_limited_gap"] for x in train],[0,24])
        self.assertEqual(m.select(train),3)
        # Altering any confirmation records cannot affect the selection,
        # since the selector accepts only two training summary objects.
        confirm=[m.evaluate_candidate("Wingless",x,"CONFIRM") for x in candidates]
        self.assertEqual([x["pairs"] for x in confirm],[48,48])
        self.assertEqual(m.select(train),3)

    def test_independent_identity_and_predeclared_4_arms(self):
        self.assertTrue(set(m.SEEDS["Wingless"]["TRAIN"]).isdisjoint(
                        m.SEEDS["Wingless"]["CONFIRM"]))
        self.assertTrue(set(m.SEEDS["Yggdrasil"]["TRAIN"]).isdisjoint(
                        m.SEEDS["Yggdrasil"]["CONFIRM"]))
        self.assertEqual(m.SEEDS["Wingless"]["TRAIN"].stop-
                         m.SEEDS["Wingless"]["TRAIN"].start,24)

    def test_full_actual_generated_vector_development_report(self):
        proof=m.execute(advisory(),SRC,100,"pull_request")
        self.assertEqual(proof["actual_generated_environments_executed"],4)
        self.assertEqual(proof["paired_training_graphs"],96)
        self.assertEqual(proof["paired_disjoint_confirmation_graphs"],192)
        self.assertEqual([x["selected_generated_environment_index"]
                          for x in proof["lanes"]],[3,3])
        for lane in proof["lanes"]:
            self.assertEqual(lane["confirmation_chosen_gap"],48)
            self.assertEqual(lane["confirmation_other_gap"],0)
            self.assertTrue(lane["selected_mechanism_claim_is_untested"])
            self.assertFalse(lane["novel_scientific_mechanism_validated"])
            for exp in lane["training"]+lane["confirmation"]:
                self.assertEqual(len(exp["paired_records"]),exp["pairs"])
                self.assertEqual(exp["counts"]["exact_binding_oracle"],exp["pairs"])
                self.assertEqual(exp["counts"]["role_only_control"],0)
        self.assertEqual(proof["optimizer_promotions"],0)
        self.assertFalse(proof["scientific_first_use_authorized"])

    def test_mismatched_github_source_or_corrupted_candidates_quarantine(self):
        with mock.patch.dict(os.environ,{"GITHUB_SHA":"b"*40}):
            with self.assertRaisesRegex(m.Invalid,"RUN_ID_OR_SOURCE_NOT_QUALIFIED"):
                m.execute(advisory(),SRC,100,"push")
        bad=advisory()
        bad["lanes"][0]["public_environment_artifacts"][0]["vector"]=[8,0,0]
        with self.assertRaisesRegex(m.Invalid,"ENVIRONMENT_VECTOR_OR_GENERATOR_SHA_MISMATCH"):
            m.execute(bad,SRC,100,"push")

if __name__=="__main__":unittest.main()
