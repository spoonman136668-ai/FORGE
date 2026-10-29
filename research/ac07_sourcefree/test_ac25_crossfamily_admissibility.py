"""AC-25 exact-interface negative tests: no source interactions or DEV training."""
import copy
import unittest
import ac25_crossfamily_admissibility as ac25

def paired():
    return {
        "schema":"itd02.crossmodel.public_environment_contract.v1",
        "environment":{"id":"MiniGrid-Empty-5x5-v0",
         "minigrid_version":"3.0.0","gymnasium_version":"1.2.1",
         "public_observation_fields":["image","direction","mission"],
         "forbidden_access":["env.unwrapped","agent_pos"]},
        "comparison":{"action_semantics":["left","right","forward"],
          "seed_list":[51,52,53],"same_max_steps":24},
        "restrictions":{"reserved_q1_q2_q3_sealed":True,
          "science_first_use":False,"forge_controller_untouched":True}
    }

def mg11():
    return {
        "schema":"itd02.mg11.original-public-selected-novelty.v1",
        "source_farama":"7f5853792ea7f04f75614661006d87fcf949f26d",
        "source_FIT_count":1664,
        "source_FIT_seeds":[50101,50103,50107,50109,50111,50113,50117,50119],
        "development_seeds":[71301,71303,71307],"max_original_steps":192,
        "actual_external_live_actions":0,
        "roles":["wingless_go_dk12","wingless_go_dk11","yggdrasil_r16",
         "yggdrasil_r15","conventional_public_novelty",
         "conventional_seeded_random","frozen_ygg_r16"],
        "new_go":"1b5b3ed525c8905252b0919790e79c632b82c1e1",
        "new_ygg":"63dff5d870e158d4197ef39cf86d9339d3eccc16"
    }

def dtr():
    return {
     "legal_action_ids":[0,1],"timesteps_to_terminal":2,
     "public_event_fields":["action","next_observation","observation",
         "reward","stage","terminated","truncated","valid_actions"]
    }

class AC25NoFalseTransferTests(unittest.TestCase):
    def test_reject_direct_two_action_dtr_to_original_minigrid(self):
        result=ac25.classify(dtr(),paired(),mg11())
        self.assertEqual(result["classification"],ac25.CLASSIFICATION)
        self.assertEqual((result["dtr_action_count"],
            result["paired_empty5_public_action_count"],
            result["mg11_original_doorkey_public_action_count"]),(2,3,7))
        for k in ("valid_native_learned_encoder_for_image_direction_mission",
                  "valid_cross_family_action_mapping_frozen_before_test",
                  "same_original_learning_and_action_interface",
                  "frozen_dtr_reward_predictor_is_minigrid_actor",
                  "scientific_first_use","scientific_transfer_established",
                  "scientific_admission"):
            self.assertIs(result[k],False)

    def test_fail_closed_if_three_action_contract_altered_to_match_binary(self):
        q=paired();q["comparison"]["action_semantics"]=["left","right"]
        with self.assertRaisesRegex(RuntimeError,"AC25_PAIRED_ORIGINAL_MINIGRID_CONTRACT_DRIFT"):
            ac25.classify(dtr(),q,mg11())

    def test_mg11_action_size_and_custody_must_not_confuse_old_contract(self):
        q=mg11();q["max_original_steps"]=24
        with self.assertRaisesRegex(RuntimeError,"AC25_AUTHENTIC_MG11_ORIGINAL_SOURCE_PRE_REG_DRIFT"):
            ac25.classify(dtr(),paired(),q)
        q=mg11();q["new_ygg"]="fabricated"
        with self.assertRaisesRegex(RuntimeError,"AC25_AUTHENTIC_MG11_ORIGINAL_SOURCE_PRE_REG_DRIFT"):
            ac25.classify(dtr(),paired(),q)

    def test_forbid_relabelling_dtr_as_minigrid_actor(self):
        q=dtr();q["legal_action_ids"]=[0,1,2]
        with self.assertRaisesRegex(RuntimeError,"AC25_DTR_INVALID_TRANSFER_START"):
            ac25.classify(q,paired(),mg11())
        q=dtr();q["timesteps_to_terminal"]=192
        with self.assertRaisesRegex(RuntimeError,"AC25_DTR_INVALID_TRANSFER_START"):
            ac25.classify(q,paired(),mg11())

    def test_never_accept_unqualified_fake_parent_report(self):
        with self.assertRaisesRegex(RuntimeError,"AC25_EXACT_AC24_REPORT_SHA256_MISMATCH"):
            ac25.read_existing_ac24(b'{"made_up":true}',"ubuntu-latest")
        with self.assertRaisesRegex(RuntimeError,"AC25_EXACT_AC24_REPORT_SHA256_MISMATCH"):
            ac25.read_existing_ac24(b'{"made_up":true}',"windows-latest")
        with self.assertRaisesRegex(RuntimeError,"AC25_EXACT_AC24_REPORT_SHA256_MISMATCH"):
            ac25.read_existing_ac24(b'{"made_up":true}',"other")

if __name__=="__main__":
    unittest.main()
