"""Synthetic-only automatic evidence->successor contract tests.

All real F5 historical measurements remain in pinned GitHub Actions;
fixtures below are constructed local records, NOT scientific outcomes.
"""
import copy
import json
from pathlib import Path
import unittest
from auto_successor import prepare,canonical
from verify_auto_successor import verify

OPTIONS=Path(__file__).with_name("successor_options.json").read_bytes()
SOURCE="5797a257a75fe139313e8486cd1a1ae79c44b148"
ARMS=("F5-FIXED","F5-COVERAGE","F5-MINIMAX","F5-MEMORY")

def synthetic(memory_reprobe=True,minimax_worse=True,memory_gain=False):
    data=[]
    for pair in ((8,10),(11,13)):
        for regime in ("steady","onset1"):
            for family in ((1,3,5),(2,4,6),(3,5,7),(4,6,8)):
                for seed in (67204,67205,67206,67207):
                    for policy in ("p0","p1","p2"):
                        for arm in ARMS:
                            n={"F5-FIXED":3,"F5-COVERAGE":2,
                               "F5-MINIMAX":3 if minimax_worse else 1,
                               "F5-MEMORY":1 if memory_gain else 2}[arm]
                            if regime=="steady":n=0
                            trace=[[0,1],[0,1],[0,1],[2,4],[3,5]]
                            if arm=="F5-MEMORY" and memory_reprobe:
                                trace[-1]=trace[-2].copy()
                            data.append({
                              "arm":arm,"pair":list(pair),"seed":seed,
                              "regime":regime,"family":list(family),
                              "matching_policy":policy,"first_detection":None,
                              "pre_mismatch":n,"post_mismatch":0,
                              "public_reads":10,
                              "sample_trace":{"addresses":trace},
                              "decoder":"F5-GENERALIZED-PUBLIC-V1"})
    record={
       "schema":"forge.f5.historical-adaptive-coverage-engineering.v1",
       "status":"F3_USED_DATA_ONLY_NOT_PROSPECTIVE_SCIENCE",
       "source_commit":SOURCE,
       "historical_seeds":[67204,67205,67206,67207],
       "historical_pairs":[[8,10],[11,13]],
       "arms":list(ARMS),
       "records":data,"new_f5_dev_cohort_accesses":0,
       "new_f5_sealed_cohort_accesses":0,"first_use_claims_consumed":0,
       "scientific_originals_executed":0,"scientific_winner_selected":False,
       "scientific_authority":False,
    }
    group={arm:{"cases":0,"pre":0,"post":0,"detections":0,
                 "steady_errors":0,"memory_reprobe_cases":0} for arm in ARMS}
    for item in data:
        score=group[item["arm"]]
        score["cases"]+=1
        score["pre"]+=item["pre_mismatch"]
        score["post"]+=item["post_mismatch"]
        if item["regime"]=="steady":
            score["steady_errors"]+=item["pre_mismatch"]+item["post_mismatch"]
        if set(item["sample_trace"]["addresses"][3])==set(
                item["sample_trace"]["addresses"][4]):
            score["memory_reprobe_cases"]+=1
    record["groups"]=group
    witness={
        "schema":"forge.f5.independent-historical-engineering-review.v1",
        "status":"HISTORICAL_SOURCE_REPLAY_ONLY_NO_NEW_FIRST_USE",
        "source_commit":SOURCE,"replayed_records":768,
        "groups":copy.deepcopy(record["groups"]),
        "new_f5_cohort_accesses":0,"first_use_claims_consumed":0,
        "scientific_authority":False}
    geometry={"schema":"forge.f5.public-coverage-geometry.v1",
        "status":"SOURCE_ONLY_NO_NEW_SCIENTIFIC_DATA",
        "baseline_offsets":[0,1,5,10],"optimal_offsets":[0,1,4,6],
        "baseline":{"worst_pair_exposure":5},
        "optimal":{"worst_pair_exposure":7},
        "nonanchor_pair_count":91,"enumerated_offset_patterns":286,
        "new_first_use_claims":0,
        "prospective_scientific_execution_authorized":False}
    return tuple(canonical(x) for x in (record,witness,geometry))+(OPTIONS,)

class SuccessorTests(unittest.TestCase):
    def test_memory_recheck_no_gain_selects_bounded_successor(self):
        args=synthetic()
        plan=prepare(*args)
        self.assertEqual(plan["selection_rule"],"PUBLIC_MEMORY_RECHECK_NO_GAIN")
        self.assertEqual(plan["selected"]["proposal_id"],
                         "Y-FORGE-F6-UNCERTAINTY-CALIBRATION-PROPOSAL")
        self.assertFalse(plan["scientific_dispatch_authorized"])
        self.assertEqual(plan["new_first_use_claims"],0)
        self.assertEqual(plan,prepare(*args))
        check=verify(plan,*args)
        self.assertEqual(check["status"],"PROPOSAL_HONESTLY_PREPARED_NO_ORIGINAL_AUTHORITY")
        self.assertEqual(check["parent_replayed_records"],768)

    def test_minimax_tradeoff_successor_without_recheck(self):
        plan=prepare(*synthetic(memory_reprobe=False))
        self.assertEqual(plan["selection_rule"],
                         "WORST_CASE_GEOMETRY_VS_HISTORICAL_TRADEOFF")

    def test_inconclusive_recommendation_without_preferring_historical_winner(self):
        plan=prepare(*synthetic(memory_reprobe=False,minimax_worse=False))
        self.assertEqual(plan["selection_rule"],"HISTORICAL_EVIDENCE_NOT_DECISIVE")
        self.assertTrue(plan["not_a_scientific_winner"])

    def test_recheck_with_gain_does_not_claim_no_gain(self):
        plan=prepare(*synthetic(memory_gain=True))
        self.assertNotEqual(plan["selection_rule"],"PUBLIC_MEMORY_RECHECK_NO_GAIN")

    def test_metric_mutation_blocks_even_with_unchanged_summary(self):
        args=list(synthetic())
        record=json.loads(args[0])
        record["records"][0]["pre_mismatch"]+=1
        args[0]=canonical(record)
        with self.assertRaisesRegex(ValueError,"FORGED_SUMMARY"):
            prepare(*args)

    def test_unauthorized_seed_blocks(self):
        args=list(synthetic())
        record=json.loads(args[0])
        record["historical_seeds"][-1]=67640
        args[0]=canonical(record)
        with self.assertRaisesRegex(ValueError,"REUSED_F3_SEEDS"):
            prepare(*args)

    def test_witness_changed_blocks(self):
        args=list(synthetic())
        w=json.loads(args[1])
        w["groups"]["F5-COVERAGE"]["pre"]+=1
        args[1]=canonical(w)
        with self.assertRaisesRegex(ValueError,"WITNESS"):
            prepare(*args)

    def test_options_substitution_blocks(self):
        args=list(synthetic())
        options=json.loads(args[3])
        options["hypotheses"][0]["rule"]="HIDDEN_ORACLE"
        args[3]=canonical(options)
        with self.assertRaisesRegex(ValueError,"CATALOGUE"):
            prepare(*args)

    def test_no_external_custody_claim_can_be_added(self):
        args=synthetic()
        plan=prepare(*args)
        plan["scientific_dispatch_authorized"]=True
        with self.assertRaisesRegex(ValueError,"NO_FALSE_AUTONOMY"):
            verify(plan,*args)

    def test_source_evidence_hash_tamper_blocks(self):
        args=synthetic()
        plan=prepare(*args)
        plan["evidence_sha256"]["record"]="0"*64
        with self.assertRaisesRegex(ValueError,"PROVENANCE"):
            verify(plan,*args)

    def test_replayed_case_duplicate_blocks(self):
        args=list(synthetic())
        record=json.loads(args[0])
        record["records"][1]=copy.deepcopy(record["records"][0])
        args[0]=canonical(record)
        with self.assertRaisesRegex(ValueError,"REPLAY_OR_DUPLICATE_CASE"):
            prepare(*args)

if __name__=="__main__":unittest.main()
