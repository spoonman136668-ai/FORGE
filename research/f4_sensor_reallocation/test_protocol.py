"""F4 proposal admission checks: no first-use authority and no F3 identity reuse."""
import json
from pathlib import Path
import unittest

PROTOCOL=Path(__file__).with_name("prospective_protocol.json")
F3_DEV=set(range(67200,67208))
F3_SEALED=set(range(67240,67256))
F3_IDENTITIES={"Y-FORGE-F3-EARLY-SENTINEL-01"}
SEED_UNIVERSE=F3_DEV|F3_SEALED

def qualify(record):
    def require(ok,name):
        if not ok:raise ValueError("F4_PROSPECTIVE_"+name)
    require(record.get("schema")=="forge.f4.sensor-reallocation.prospective-preregistration-proposal.v1","SCHEMA")
    require(record.get("status")=="PROPOSED_NOT_FROZEN_NO_SCIENTIFIC_AUTHORITY","AUTHORITY")
    require(record["planned_original_id"] not in F3_IDENTITIES,"IDENTITY_REUSE")
    witness=record["prereg_parent_evidence"]
    require(witness["f3_frozen_portfolio_git_blob"]=="4140cf897c05d27dd6dac01cea796f383fa2ef44","F3_PREREG")
    require(witness["f3_c1_fidelity_classification"]=="REJECTED_NONPERMUTATION_SENSOR_CHANGE","MECHANISM_MISLABEL")
    require(witness["f3_c1_fidelity_rejection_source_sha"]=="7f2f791f98d92ad932e0f530a7d23d0330a15643","F3_SOURCE")
    require(witness["y070_immutable_source_commit"]=="5797a257a75fe139313e8486cd1a1ae79c44b148","Y_SOURCE")
    src=record["source_requirements"]
    require(src["implementation_source_sha"]=="UNRESOLVED_REQUIRED_BEFORE_FREEZE","PREMATURE_FREEZE")
    require(src["independent_mechanism_review_required"] is True,"METHOD_REVIEW")
    require(src["no_model_api_calls"] is True and src["no_new_controller"] is True and src["no_fsa_infrastructure"] is True,"NO_NEW_INFRA")
    seeds=record["proposed_cohorts"]
    development=seeds["development_seeds"]
    sealed=seeds["sealed_candidate_seeds"]
    require(len(development)==8 and len(set(development))==8,"DEV_COHORT")
    require(len(sealed)==16 and len(set(sealed))==16,"SEALED_COHORT")
    require(not set(development)&set(sealed) and not((set(development)|set(sealed))&SEED_UNIVERSE),"COHORT_COLLISION")
    require(seeds["seed_first_use_status"]=="UNVERIFIED_MUST_INDEPENDENTLY_PROVE_UNUSED_BEFORE_CLAIM","FIRST_USE_ASSUMPTION")
    conditions=record["proposed_conditions"]
    pairs=[tuple(p) for p in conditions["prospective_novel_sealed_evaluation_pairs"]]
    require(len(set(pairs))==2 and all(len(p)==2 and p[0]!=p[1] and all(cell not in (0,1) and 0<=cell<16 for cell in p) for p in pairs),"PAIR")
    require(not(set(pairs)&{tuple(p) for p in conditions["development_training_pairs"]}),"NOVELTY")
    require(conditions["train_label_access"]=="development_training_only_never_at_inference","NO_ORACLE")
    arms=record["arms"]
    require([arm["id"] for arm in arms]==["F4-CONTROL","F4-SET","F4-ORDER-CONTROL"],"CONTROLS")
    b=record["budgets"]
    require(b["public_scalar_reads_per_trial"]==10 and b["read_episodes"]==[0,1,3,5,7] and b["active"]==7 and b["retained"]==9 and b["total"]==16,"BUDGET")
    gate=record["selection_and_gate"]
    require(gate["both_control_and_candidate_share_same_public_decoder"] is True,"EQUAL_DECODER")
    require(gate["independent_first_use_and_unused_cohort_proof"] is True,"FIRST_USE_GATE")
    require(gate["no_scientific_original_created_by_this_proposal"] is True,"SCIENTIFIC_ORIGINAL")
    require(gate["frozen_mechanism_fidelity_before_sealed"] is True,"METHOD_GATE")
    return "PROPOSED_ONLY_NONAUTHORIZING"

class ProspectiveTests(unittest.TestCase):
    def setUp(self):self.protocol=json.loads(PROTOCOL.read_text())
    def test_proposal_is_explicitly_non_authorizing(self):
        self.assertEqual(qualify(self.protocol),"PROPOSED_ONLY_NONAUTHORIZING")
    def test_reuse_of_f3_seal_fails_closed(self):
        self.protocol["proposed_cohorts"]["sealed_candidate_seeds"][0]=67240
        with self.assertRaisesRegex(ValueError,"COHORT_COLLISION"):qualify(self.protocol)
    def test_unknown_first_use_cannot_be_relabelled_unused(self):
        self.protocol["proposed_cohorts"]["seed_first_use_status"]="UNUSED"
        with self.assertRaisesRegex(ValueError,"FIRST_USE_ASSUMPTION"):qualify(self.protocol)
    def test_premature_frozen_source_fails(self):
        self.protocol["source_requirements"]["implementation_source_sha"]="7f2f791f98d92ad932e0f530a7d23d0330a15643"
        with self.assertRaisesRegex(ValueError,"PREMATURE_FREEZE"):qualify(self.protocol)
    def test_ablation_needs_equal_decoder(self):
        self.protocol["selection_and_gate"]["both_control_and_candidate_share_same_public_decoder"]=False
        with self.assertRaisesRegex(ValueError,"EQUAL_DECODER"):qualify(self.protocol)

if __name__=="__main__":unittest.main()
