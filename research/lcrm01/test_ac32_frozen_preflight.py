"""AC32 original-source preexecution static contract gate; NEVER calls env.reset/step."""
from __future__ import annotations
import ast,json,pathlib,re,unittest
HERE=pathlib.Path(__file__).resolve().parent
DATA=json.loads((HERE/"ac32_frozen_original_worlds.json").read_text(encoding="utf-8"))
SOURCE=(HERE/"ac32_original_multifamily.py").read_text(encoding="utf-8")
BRIDGE=(HERE/"ac31_native_go_bridge.go").read_text(encoding="utf-8")
COMP=(HERE/"ac32_original_compare.py").read_text(encoding="utf-8")

class AC32PreExecutionContract(unittest.TestCase):
    def test_source_pre_registration_before_code_and_exact_parents(self):
        self.assertEqual(DATA["phase"],"PREREGISTERED_BEFORE_SOURCE_EXECUTABLE_OR_RESET")
        self.assertEqual(DATA["frozen_parent_protocol_commit"],"28fb7f8925535d0bfc21565e4eb00a6c965031f1")
        self.assertEqual(DATA["original_native"]["Wingless_DK15"],"9a712f574e48a3d47f2d986d8be3d0eda2b3b9bd")
        self.assertEqual(DATA["original_native"]["Yggdrasil_R19"],"2225c19a8a6c55bfdf6785ffc1a26b450fc6f24e")
        self.assertEqual(DATA["original_farama"],"7f5853792ea7f04f75614661006d87fcf949f26d")
        self.assertFalse(DATA["scientific_first_use"])
        self.assertFalse(DATA["scientific_admission"])

    def test_original_FIT_only_source_1664_and_no_exposed_development_leak(self):
        self.assertEqual(DATA["FIT"]["count"],1664)
        self.assertEqual(DATA["FIT"]["seeds"],[50101,50103,50107,50109,50111,50113,50117,50119])
        self.assertEqual(DATA["FIT"]["canonical_sha256"],"9c640b0ae6a0865b9db7147d4b816643962ee69141950e7639dcc09b832d0e24")
        seeds=[seed for w in DATA["worlds"] for seed in w["seeds"]]
        self.assertEqual(len(seeds),9)
        self.assertEqual(len(set(seeds)),9)
        self.assertFalse(set(seeds)&set(DATA["FIT"]["seeds"]))
        self.assertFalse(set(seeds)&{71301,71303,71307,72301,72303,72307,78301,78303,78307,78501,78503,78507,78701,78703,78707,76301,76303,76307,
             76501,76503,76507,741101,741103,741107,741109,741111,741113,741117,741119,
             75501,75503,75507})
        self.assertEqual(DATA["min_independent_source_processes"],2)

    def test_three_registered_original_world_missions_and_same_public_inputs(self):
        self.assertEqual([(w["environment"],w["mission"],w["seeds"]) for w in DATA["worlds"]],[
         ("MiniGrid-DoorKey-6x6-v0","use the key to open the door and then get to the goal",[80301,80303,80307]),
         ("MiniGrid-Empty-Random-6x6-v0","get to the green goal square",[80501,80503,80507]),
         ("MiniGrid-Unlock-v0","open the door",[80701,80703,80707])])
        self.assertEqual(DATA["roles"],["wingless_dk15","yggdrasil_r19",
             "conventional_public_successor","conventional_mission_conditioned","uniform_random"])
        self.assertTrue(all(w["limit"]==192 for w in DATA["worlds"]))
        self.assertFalse(DATA["original_public_mission_rewrite_to_door_key"])
        self.assertTrue(DATA["no_external_selected_actions"])

    def test_native_actor_source_and_go_bridge_never_spoof_mission(self):
        self.assertIn("native \"github.com/spoonman136668-ai/Wingless/research/native/itd02/dk15\"",BRIDGE)
        self.assertIn("case \"load_parent\"",BRIDGE)
        self.assertIn("case \"feedback\"",BRIDGE)
        self.assertIn("boundary.ReadPublic(raw)",BRIDGE)
        self.assertIn("from research.native.itd02.r19.mission_actor import MissionActor",SOURCE)
        self.assertIn('go.request("commit",action=action)',SOURCE)
        self.assertIn('ygg.commit(action)',SOURCE)
        self.assertIn("env.step(action)",SOURCE)
        self.assertIn("real_public(raw,collector,owner,mission)",SOURCE)
        self.assertNotIn('p["mission"]="use the key',SOURCE)
        self.assertNotIn('before["mission"]="use the key',SOURCE)
        self.assertNotIn("agent_pos",SOURCE)
        self.assertNotIn("env.unwrapped",SOURCE)
        self.assertNotIn("goal_oracle",SOURCE)
        self.assertIn("AC32_ORIGINAL_SOURCE_OR_ACTOR_CONTRACT_BLOCKED",SOURCE)

    def test_independent_two_process_original_public_trace_audit(self):
        self.assertIn("TWO_INDEPENDENT_SOURCE_PROCESSES_MISMATCH",COMP)
        self.assertIn("SOURCE_PUBLIC_HASH_OR_TIMELINE",COMP)
        self.assertIn("SOURCE_TRUE_REWARD_TYPE",COMP)
        self.assertIn("ORIGINAL_SAME_SEED_PUBLIC_RESET",COMP)
        self.assertIn("PREDECLARED_SUCCESS_RULE",COMP)
        ast.parse(SOURCE)
        ast.parse(COMP)

if __name__=="__main__":unittest.main()
