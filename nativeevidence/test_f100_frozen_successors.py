import copy
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import f100_frozen_successors as f100

SHA="b8d9b4ef0e58feaaedd5e12c5a810cd0e5d1c9fc"
def fixtures():
    parent,parent_raw=f100.read_json(f100.F99)
    contract,_=f100.read_json(f100.F100)
    return parent,parent_raw,contract
def run(parent,raw,contract):
    return f100.check_contract(contract,parent,raw)

class F100FrozenDevelopment(unittest.TestCase):
    def test_preregistered_two_lane_candidate_population(self):
        parent,raw,contract=fixtures()
        observed=run(parent,raw,contract)
        self.assertEqual([x["lane"] for x in observed],["Wingless","Yggdrasil"])
        self.assertEqual([x["candidate_ids"] for x in observed],
                         [["W100-C1","W100-C2"],["Y100-C1","Y100-C2"]])
        self.assertEqual(sum(x["authentic_negative_pairs"] for x in observed),288)
        self.assertEqual(sum(x["public_development_seed_count"] for x in observed),96)
        for lane in observed:
            self.assertEqual(lane["retrospective_learned_correct_pairs"],0)
            self.assertEqual(lane["retrospective_coded_control_pairs"],lane["authentic_negative_pairs"])
            self.assertFalse(lane["implementation_started"])
            self.assertFalse(lane["science_first_use_authorized"])
        report=f100.audit(source_sha=SHA)
        self.assertEqual(report["candidates_frozen"],4)
        self.assertEqual(report["new_results_observed"],0)
        self.assertEqual(report["new_experiments_executed"],0)
        self.assertEqual(report["trainable_policy_updates"],0)
        self.assertFalse(report["autonomous_research_established"])
    def test_denied_authority_and_promotion(self):
        for key in ("prospective_scientific_original_authorized",
                    "protected_first_use_authorized","independently_accepted_science",
                    "model_inference_configured","genenv_training_activated",
                    "optimizer_promotion_authorized","new_research_experiment_executed",
                    "ckb_plane_contact"):
            parent,raw,contract=fixtures()
            contract["authorization"][key]=True
            with self.subTest(key=key),self.assertRaises(f100.Rejected):
                run(parent,raw,contract)
        for key in ("accepted_ref_mutations","codex_calls","paid_model_api_calls"):
            parent,raw,contract=fixtures()
            contract["authorization"][key]=1
            with self.subTest(key=key),self.assertRaises(f100.Rejected):
                run(parent,raw,contract)
    def test_frozen_parent_fingerprint_and_negative_results(self):
        for field,new in (("parent_artifact_id",12),("parent_payload_sha256","f"*64),
                          ("parent_experiment","PRETEND-FRESH")):
            parent,raw,contract=fixtures()
            contract["lanes"][0][field]=new
            with self.assertRaises(f100.Rejected):run(parent,raw,contract)
        parent,raw,contract=fixtures()
        contract["lanes"][1]["observed_development_negative"]["frozen_learned_paired_correct"]=192
        with self.assertRaises(f100.Rejected):run(parent,raw,contract)
        parent,raw,contract=fixtures()
        altered=raw+b" "
        with self.assertRaises(f100.Rejected):run(parent,altered,contract)
        parent,raw,contract=fixtures()
        contract["prior_f99_head_sha"]="e"*40
        with self.assertRaises(f100.Rejected):run(parent,raw,contract)
    def test_candidate_diversity_bounded_budget_and_no_cherry_pick(self):
        for how in ("remove","duplicate","oracle","short_circuit","change_threshold","remove_control"):
            parent,raw,contract=fixtures()
            a=contract["lanes"][0]
            if how=="remove":a["candidates"].pop()
            if how=="duplicate":a["candidates"][1]["id"]=a["candidates"][0]["id"]
            if how=="oracle":a["candidates"][0]["no_hardcoded_oracle_in_candidate"]=False
            if how=="short_circuit":a["candidates"][0]["falsifiable_mechanism"]="wins"
            if how=="change_threshold":a["preliminary_development_screen"]["minimum_paired_accuracy"]=0.20
            if how=="remove_control":a["controls"].pop()
            with self.subTest(how=how),self.assertRaises(f100.Rejected):
                run(parent,raw,contract)
    def test_old_seeds_and_overlapping_cohorts_denied(self):
        for how in ("reuse_original","reuse_another_block","grow_cohort","parameter_overrun"):
            parent,raw,contract=fixtures()
            a=contract["lanes"][1]
            if how=="reuse_original":a["public_development_seed_blocks"][0]=[51400,51415]
            if how=="reuse_another_block":a["public_development_seed_blocks"][1]=[63400,63415]
            if how=="grow_cohort":a["public_development_seed_blocks"][0]=[63400,63480]
            if how=="parameter_overrun":a["budget"]["max_trainable_parameters"]=1000000
            with self.subTest(how=how),self.assertRaises(f100.Rejected):
                run(parent,raw,contract)
    def test_invalid_json_duplicate_keys_and_source_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            p=pathlib.Path(td)/"invalid.json"
            for raw in (b'{"schema":"x","schema":"y"}',
                        b'{"metric":NaN}',b'{"metric":Infinity}',b"not json"):
                p.write_bytes(raw)
                with self.assertRaises(f100.Rejected):f100.read_json(p)
        with patch.dict("os.environ",{"GITHUB_SHA":"f"*40}):
            with self.assertRaises(f100.Rejected):f100.audit(source_sha=SHA)
        with patch.dict("os.environ",{"GITHUB_SHA":SHA}):
            self.assertEqual(f100.audit(source_sha=SHA)["forge_source_sha"],SHA)
if __name__=="__main__":
    unittest.main()
