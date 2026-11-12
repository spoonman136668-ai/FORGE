"""F5 nonauthorizing prospective protocol compliance and identity gates."""
import json
from pathlib import Path
import unittest

PATH=Path(__file__).with_name("prospective_protocol.json")
KNOWN={(2,3),(4,5),(8,10),(11,13),(6,9),(12,14)}
ARMS=["F5-FIXED","F5-COVERAGE","F5-MINIMAX","F5-MEMORY"]

def inspect(protocol):
    def require(ok,code):
        if not ok:raise ValueError("F5_PROSPECTIVE_"+code)
    require(protocol.get("schema")=="forge.f5.native-coverage.prospective-preregistration-proposal.v1","SCHEMA")
    require(protocol.get("status")=="PROPOSED_SOURCE_NOT_FROZEN_FIRST_USE_NOT_AUTHORIZED","NONAUTHORITY")
    require(protocol["pinned_parent_scientific_source"]["commit"]=="5797a257a75fe139313e8486cd1a1ae79c44b148","PINNED_SOURCE")
    require([a["id"] for a in protocol["proposed_arms"]]==ARMS,"ARM_IDS")
    b=protocol["limits"]
    require(b["public_scalar_reads_per_trial"]==10 and
            b["public_read_episodes"]==[0,1,3,5,7] and
            b["reads_per_episode"]==2,"READ_BUDGET")
    require(b["active_entities"]==7 and b["retained_max"]==9 and b["memory_max_public_addresses"]==4,"MEMORY_CAPACITY")
    require(b["hidden_pair_during_inference"] is False,"ORACLE")
    dev=protocol["development"]
    sealed=protocol["sealed"]
    require(dev["seeds"]=="UNALLOCATED_CUSTODY_REQUIRED" and sealed["seeds"]=="UNALLOCATED_CUSTODY_REQUIRED","PREMATURE_SEED_RESERVATION")
    require(sealed["pairs"]=="MUST_FREEZE_PREEXECUTION_NO_RESULT_DRIVEN_PAIR_SELECTION","PREMATURE_PAIR_ALLOCATION")
    require({tuple(v) for v in sealed["exclusions_prior_known_pairs"]}==KNOWN,"KNOWN_PAIR_REUSE")
    require(sealed["independent_replay_required"] is True,"INDEPENDENT_REPLAY")
    geometry=protocol["coverage_geometry_control"]
    require(geometry["status"]=="ENGINEERING_ONLY_NOT_SCIENTIFIC_ADMISSION","GEOMETRY_SCIENCE")
    require(geometry["enumerated_all_pairs"]==91 and
            geometry["possible_public_rotation_starts"]==14,"GEOMETRY_UNIVERSE")
    require(geometry["baseline_offsets"]==[0,5,10,1] and
            geometry["minimax_offsets"]==[0,1,4,6],"GEOMETRY_IDENTITY")
    require(geometry["worst_case_pair_exposure_baseline"]==5 and
            geometry["worst_case_pair_exposure_minimax"]==7,"GEOMETRY_BOUND")
    gate=protocol["admission"]
    require(gate["frozen_worker_source_commit"]=="UNRESOLVED" and
            gate["frozen_proposal_identity"]=="UNRESOLVED","SOURCE_FREEZE")
    require(gate["independently_signed_all_lane_first_use_snapshot"]=="MISSING" and
            gate["independent_seed_level_nonreuse_witness"]=="MISSING","CUSTODY")
    require(gate["scientific_execution_authorized"] is False and
            gate["scientific_winner_selected"] is False and
            gate["new_first_use_claims"]==0 and gate["new_originals"]==0,"AUTHORITY")
    require(protocol["budget"]["engineering_F3_used_only"] is True and
            protocol["budget"]["first_original_at_most_once"] is True,"PORTFOLIO_ISOLATION")
    return "PROPOSAL_ONLY_NO_SCIENTIFIC_ADMISSION"

class ProtocolTests(unittest.TestCase):
    def setUp(self):self.p=json.loads(PATH.read_bytes())
    def test_non_authorizing_proposal(self):
        self.assertEqual(inspect(self.p),"PROPOSAL_ONLY_NO_SCIENTIFIC_ADMISSION")
    def test_forged_custody_denied(self):
        self.p["admission"]["independently_signed_all_lane_first_use_snapshot"]="PASS"
        with self.assertRaisesRegex(ValueError,"CUSTODY"):inspect(self.p)
    def test_unverified_seed_must_not_be_used(self):
        self.p["sealed"]["seeds"]=list(range(67840,67856))
        with self.assertRaisesRegex(ValueError,"PREMATURE_SEED_RESERVATION"):inspect(self.p)
    def test_known_pair_exclusion_cannot_be_removed(self):
        self.p["sealed"]["exclusions_prior_known_pairs"].remove([6,9])
        with self.assertRaisesRegex(ValueError,"KNOWN_PAIR_REUSE"):inspect(self.p)
    def test_premature_source_freeze_denied(self):
        self.p["admission"]["frozen_worker_source_commit"]="0"*40
        with self.assertRaisesRegex(ValueError,"SOURCE_FREEZE"):inspect(self.p)
    def test_extra_public_reads_denied(self):
        self.p["limits"]["public_scalar_reads_per_trial"]=11
        with self.assertRaisesRegex(ValueError,"READ_BUDGET"):inspect(self.p)

if __name__=="__main__":unittest.main()
