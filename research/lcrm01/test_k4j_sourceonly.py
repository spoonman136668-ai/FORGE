"""K4J primary preregistered positive and no-false-admission guards."""
import copy
import hashlib
import json
import unittest
from k4j_replicate import FROZEN,SCHEMA,frozen,config_from_frozen,action_diversity_gate,primary_decision
from k4j_compare import compare
from k4i_information_sufficiency import partition

def source_evidence():
    p=frozen()
    info={"reaching":{"unique_public_FIT_contexts":12,"best_arm_ids":[1,3],
          "action_ranking_diverse":True}}
    rows=[]
    for i in range(4):
        arm=3 if i in (2,3) else 1
        raw_reward=2.0 if i in (2,3) else 1.0
        rows.append({"family":"reaching","variant":14+i,
            "selected":{"raw_knn":{"arm":arm,"reward":raw_reward},
                "family_mean":{"arm":1,"reward":1.0}}})
    prim=primary_decision(info,rows,p)
    fake={"schema":SCHEMA,"gate":"LCRM01-K4J",
          "protocol_sha256":hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
          "source_commit":p["source"]["upstream_commit"],
          "result":"COMPLETE_ONE_PROCESS_PUBLIC_DEV",
          "FIT_exposures":96,"CHECK_exposures":16,"DEV_exposures":32,
          "CHECK_rows":[{"value":0} for _ in range(16)],
          "DEV_rows":[{"value":0} for _ in range(32)],
          "retention_exact":True,"K4I_model_unchanged":True,
          "original_K4I_outcome_preserved":True,
          "scientific_first_use":False,"scientific_accepted":False,
          "primary_reaching_replication":prim}
    return p,info,rows,fake

class K4JGuards(unittest.TestCase):
    def test_protocol_original_identity_and_new_cohorts(self):
        p=frozen()
        self.assertEqual(len(p["design"]["variants"]),18)
        self.assertEqual(p["design"]["source_seed"],839)
        self.assertFalse(p["governance"]["scientific_first_use"])
        self.assertEqual(p["design"]["process_count"],2)

    def test_explicitly_unchanged_k4i_fitted_sources(self):
        p=frozen();historical,cfg=config_from_frozen(p)
        self.assertEqual(len(partition(historical,"FIT")),12)
        self.assertEqual(len(partition(historical,"CHECK")),2)
        self.assertEqual(len(partition(historical,"DEV")),4)
        self.assertEqual(cfg["world"]["seed"],839)

    def test_fit_information_must_be_diverse(self):
        _,info,_,_=source_evidence()
        self.assertTrue(action_diversity_gate(info))
        info["reaching"]["best_arm_ids"]=[1]
        info["reaching"]["action_ranking_diverse"]=False
        self.assertFalse(action_diversity_gate(info))

    def test_replicable_bounded_positive(self):
        _,_,_,r=source_evidence()
        self.assertEqual(r["primary_reaching_replication"]["result"],
            "REACHING_BOUNDED_POSITIVE_IN_THIS_PROCESS")
        v=compare(r,copy.deepcopy(r))
        self.assertEqual(v["result"],"REPLICATED_BOUNDED_PUBLIC_DEV_REACHING_POSITIVE")
        self.assertFalse(v["independent_host_replicated"])

    def test_one_case_gain_cannot_qualify(self):
        p,info,rows,_=source_evidence()
        rows[2]["selected"]["raw_knn"]["reward"]=1.0
        result=primary_decision(info,rows,p)
        self.assertEqual(result["reaching_strict_improvements"],1)
        self.assertEqual(result["result"],"NO_GO_OR_WEAK_REPLICATION")

    def test_all_contexts_choose_one_action_no_go(self):
        p,info,rows,_=source_evidence()
        for r in rows:r["selected"]["raw_knn"]["arm"]=1
        self.assertFalse(primary_decision(info,rows,p)["raw_actions_context_dependent"])

    def test_different_evidence_cannot_claim_replication(self):
        _,_,_,r=source_evidence()
        b=copy.deepcopy(r)
        b["DEV_rows"][0]["value"]=1
        cmp=compare(r,b)
        self.assertFalse(cmp["exact_original_evidence_match"])
        self.assertEqual(cmp["result"],"NO_INDEPENDENT_REPLICATION_OR_NO_GO")

    def test_timing_variation_excluded_but_not_science(self):
        _,_,_,a=source_evidence();b=copy.deepcopy(a)
        a["whole_run_cost"]={"CPU_seconds":5}
        b["whole_run_cost"]={"CPU_seconds":6}
        self.assertTrue(compare(a,b)["exact_original_evidence_match"])

    def test_false_fsa_acceptance_blocked(self):
        _,_,_,a=source_evidence();b=copy.deepcopy(a)
        b["scientific_accepted"]=True
        with self.assertRaises(ValueError):compare(a,b)

    def test_unconsumed_holdout_retained_at_fit_stop(self):
        p,_,_,a=source_evidence()
        a["result"]="FIT_INFORMATION_NOT_QUALIFIED_HOLDOUT_UNCONSUMED"
        a["CHECK_exposures"]=0;a["DEV_exposures"]=0
        del a["CHECK_rows"];del a["DEV_rows"]
        cmp=compare(a,copy.deepcopy(a))
        self.assertEqual(cmp["result"],"NO_INDEPENDENT_REPLICATION_OR_NO_GO")
        a["DEV_rows"]=[1]
        with self.assertRaises(ValueError):compare(a,copy.deepcopy(a))

if __name__=="__main__":
    unittest.main()
