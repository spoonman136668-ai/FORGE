"""MG02 strict source-only native R8/R1 shared-field contract, R12 blocker."""
import os
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from mg02_r8_paired_live import protocol,PASS,FAIL
from mg01_paired_live_minigrid import exact,public_wire,FIELDS
from k4r_minigrid_source import make_env,public
from k4u_native_minigrid import WingBridge


class MG02RealPublicCompatibilityTests(unittest.TestCase):
    def test_original_mg01_source_and_authentic_r8_r12_pins(self):
        p=protocol()
        self.assertEqual(p["source"]["wingless_r8"]["original_r8_source_blob"],
                         "6857ecbef2d63f459a432a5d68c7edda2b5347c4")
        self.assertEqual(p["source"]["yggdrasil_r1"]["source_blob"],
                         "3aa22b1e418a7f8cd9619c476f02b8c614917b16")
        self.assertFalse(p["classification"]["scientific_first_use"])
        self.assertFalse(p["classification"]["r12_compatibility_admitted"])
        self.assertEqual(tuple(p["protocol"]["selected_observation_fields"]),FIELDS)
        self.assertIn("NO_SCIENCE",PASS)
        self.assertIn("BLOCKED",FAIL)

    def test_original_r12_is_seven_action_doorkey_only_and_rejects_mg01_wire(self):
        # Imported original Yggdrasil source from pinned checkout, not
        # a fabricated Python representation of R12's native requirements.
        from research.native.itd02.r10.public_adapter import (
            ACTION_NAMES,MISSION,public_observation,
        )
        from research.native.itd02.r11.affordance_cells import PublicAffordanceCells
        from research.native.itd02.r12.outcome_choice import select_public_action
        self.assertEqual(ACTION_NAMES,
            ("left","right","forward","pickup","drop","toggle","done"))
        self.assertEqual(len(ACTION_NAMES),7)
        six={"x":1,"y":2,"goal_x":4,"goal_y":5,
             "direction":0,"front_blocked":False}
        self.assertEqual(exact(six),six)
        with self.assertRaises(ValueError):
            public_observation(six)
        with self.assertRaises(ValueError):
            select_public_action(PublicAffordanceCells(),six,"positive_reward")
        with self.assertRaises(ValueError):
            select_public_action(PublicAffordanceCells(),
                {"image":[],"direction":0,"mission":MISSION},"not_an_objective")
        # R12 must not receive synthesized mission, full private state,
        # silent three-action remapping, or counterfeit source observations.

    def test_real_original_farama_reset_and_equal_public_wire(self):
        for family in ("empty","fourrooms"):
            env=make_env(family)
            try:
                obs,_=env.reset(seed=9200)
                state=public(obs)
                wire=public_wire(state)
                self.assertEqual(exact(wire),wire)
                self.assertEqual(set(wire),set(FIELDS))
                self.assertEqual(type(wire["front_blocked"]),bool)
            finally:
                env.close()

    def test_real_wingless_r8_ipc_checkpoint_integrity_and_no_free_feedback(self):
        binary=os.environ.get("MG02_WINGLESS_R8_BRIDGE","")
        self.assertTrue(binary)
        native=WingBridge(binary)
        try:
            cp=native.snapshot()
            self.assertLessEqual(len(cp),3*1024*1024)
            with self.assertRaises(ValueError):
                native.request("feedback",
                    before={"x":1,"y":1,"goal_x":5,"goal_y":5,"direction":0,"front_blocked":False},
                    action=2,
                    after={"x":1,"y":1,"goal_x":5,"goal_y":5,"direction":0,"front_blocked":False})
            self.assertEqual(native.snapshot(),cp)
            with self.assertRaises(ValueError):
                native.request("load",state="definitely-not-canonical-r8-checkpoint")
            self.assertEqual(native.snapshot(),cp)
        finally:
            native.close()

if __name__=="__main__":
    unittest.main()
