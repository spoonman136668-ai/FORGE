"""AC28 pre-execution public development contract checks, no environment calls."""
import json, pathlib, unittest

HERE=pathlib.Path(__file__).resolve().parent
SOURCE=(HERE/"ac28_unlock_original_transfer.py").read_text(encoding="utf-8")
COMPARE=(HERE/"ac28_unlock_compare.py").read_text(encoding="utf-8")
PROTO=json.loads((HERE/"ac28_unlock_transfer_prereg.json").read_text(encoding="utf-8"))

class AC28UnlockPreflight(unittest.TestCase):
    def test_new_public_development_family_and_exact_seeds(self):
        self.assertEqual(PROTO["schema"],"itd02.ac28.authentic-public-unlock-crossfamily-dev.v1")
        dev=PROTO["development"]
        self.assertEqual(dev["environment"],"MiniGrid-Unlock-v0")
        self.assertEqual(dev["seeds"],[741101,741103,741107,741109,741111,741113,741117,741119])
        self.assertEqual(len(set(dev["seeds"])),8)
        self.assertTrue(set(dev["seeds"]).isdisjoint(set(PROTO["fit"]["seeds"])))
        self.assertTrue(set(dev["seeds"]).isdisjoint({72301,72303,72307,71301,71303,71307}))
        self.assertEqual(dev["target_family_fit_samples"],0)
        self.assertFalse(dev["manually_derived_stage"])
        self.assertEqual(dev["external_live_actions"],0)
        self.assertEqual(dev["max_selected_original_steps"],192)

    def test_exact_unchanged_door_key_fit_and_separate_unlock_trial(self):
        src=SOURCE.split("def episode(role,seed,trained,binary,p):")
        self.assertEqual(len(src),2)
        self.assertIn('gym.make("MiniGrid-DoorKey-8x8-v0")',src[0])
        self.assertNotIn('gym.make("MiniGrid-Unlock-v0")',src[0])
        self.assertNotIn('gym.make("MiniGrid-DoorKey-8x8-v0")',src[1])
        self.assertIn('gym.make("MiniGrid-Unlock-v0")',src[1])
        self.assertEqual(PROTO["fit"]["count"],1664)
        self.assertEqual(PROTO["fit"]["canonical_selected_sha256"],
            "9c640b0ae6a0865b9db7147d4b816643962ee69141950e7639dcc09b832d0e24")

    def test_original_native_pins_and_identical_four_public_roles(self):
        self.assertEqual(PROTO["native"]["Wingless_DK13_head"],
            "2992a25e3fe05783bfa80ecf70d737bb2a21e281")
        self.assertEqual(PROTO["native"]["Yggdrasil_R17_head"],
            "770244b04d011466458b2335d3951daf7653dc8f")
        self.assertEqual(PROTO["development"]["roles"],
            ["wingless_dk13","yggdrasil_r17","conventional_public_successor","random"])
        self.assertEqual(PROTO["farama_original"],"7f5853792ea7f04f75614661006d87fcf949f26d")
        self.assertIn("ConventionalSuccessor",SOURCE)
        self.assertIn("WingBridge",SOURCE)
        self.assertIn("SuccessorCells",SOURCE)

    def test_two_original_source_processes_and_action_equality(self):
        self.assertIn("INDEPENDENT_PROCESSES_NOT_IDENTICAL",COMPARE)
        self.assertIn("UNAUTHENTICATED_SOURCE_ACTION",COMPARE)
        self.assertIn("equal_policy_public_observation",COMPARE)
        self.assertIn("MiniGrid-Unlock-v0",COMPARE)
        self.assertIn("any(summary[role]",COMPARE)
        self.assertIn('"external_live_actions":0',SOURCE)
        self.assertIn('"scientific_first_use":False',SOURCE)

    def test_no_new_target_training_or_hardcoded_door_solution(self):
        self.assertEqual(PROTO["development"]["all_7_original_actions"],True)
        self.assertEqual(PROTO["authority"]["no_scientific_first_use"],True)
        # The source-qualified actors choose; no evaluator forced action
        # or source-private pose enters any native actor input.
        self.assertIn('go.request("choose",before=public)',SOURCE)
        self.assertIn("proposal=ygg.choose(public)",SOURCE)
        self.assertIn("action=control.choose(public)",SOURCE)
        self.assertNotIn("agent_pos",SOURCE)
        self.assertNotIn("env.unwrapped",SOURCE)

if __name__=="__main__":unittest.main()
