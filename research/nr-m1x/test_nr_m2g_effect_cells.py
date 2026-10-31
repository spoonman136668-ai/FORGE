"""NR-M2G authored source-only contract checks; no original-world steps.

FIT and CHECK are prospectively defined in NR_M2G_PREREG.json.
These tests establish structural mechanism engineering only, not model
science, novel-world transfer, or superiority to fitted strong controls.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from nr_m2d_pinned_original_public import MISSION
from nr_m2e_extended_public import full_public, GOAL_MISSION
from nr_m2g_effect_cells import StructuralEffectCells, components, unpack

MISSIONS = (GOAL_MISSION, "pick up the red ball", MISSION)
PIXELS = ([1, 0, 0], [2, 4, 0], [4, 1, 2])

def fit_frame(t):
    return full_public({
        "image": [[list(PIXELS[(row * 7 + col + t) % 3])
                   for col in range(7)] for row in range(7)],
        "direction": t % 4, "mission": MISSIONS[t % 3],
    })

def check_frame(mission, direction):
    # CHECK differs from every FIT public frame: unseen last image pixel.
    image = [[list(PIXELS[(row * 7 + col + direction + MISSIONS.index(mission)) % 3])
              for col in range(7)] for row in range(7)]
    image[6][6] = [3, 0, 1]
    return full_public({"image": image, "direction": direction, "mission": mission})

def authored_return(before, action):
    # Synthetic invariant rule is defined in the frozen prereg. Never passed
    # to learner; only after source-selected feedback is observed.
    after = json.loads(json.dumps(before))
    if action not in (0, 1):
        after["image"][0][0] = [1, action % 6, action]
    return full_public(after)

def train():
    model = StructuralEffectCells(full_public)
    for action in range(7):
        for t in range(12):
            before = fit_frame(t)
            after = authored_return(before, action)
            model.begin(before)
            model.select(before, action)
            model.feedback(before, action, after)
    return model

class NativeSourceOnlyM2G(unittest.TestCase):
    def test_frozen_unseen_full_public_contract(self):
        first = fit_frame(0)
        self.assertEqual(len(components(first)), 149)
        self.assertEqual(unpack(components(first)), first)
        model = train()
        self.assertEqual(model.events, 84)
        self.assertEqual(model.evictions, 0)
        correct = 0
        fit = {json.dumps(fit_frame(t), sort_keys=True) for t in range(12)}
        for mission in MISSIONS:
            for direction in range(4):
                before = check_frame(mission, direction)
                self.assertNotIn(json.dumps(before, sort_keys=True), fit)
                for action in range(7):
                    predicted, evidence = model.predict(before, action)
                    self.assertTrue(evidence["supported"], (mission, direction, action, evidence))
                    self.assertEqual(predicted, authored_return(before, action))
                    self.assertEqual(evidence["no_effect"], action in (0, 1))
                    correct += 1
        self.assertEqual(correct, 84)
        self.assertEqual(model.forecast(check_frame(MISSIONS[0], 0), [0, 1])[0],
                         check_frame(MISSIONS[0], 0))
        print("NRM2G_84_OF_84_AUTHORED_UNSEEN_SOURCE_ONLY_PUBLIC_PASS")

    def test_insufficient_and_contradictory_effects_abstain(self):
        m = StructuralEffectCells(full_public)
        before = fit_frame(0)
        self.assertFalse(m.predict(before, 2)[1]["supported"])
        for t in range(4):
            current = fit_frame(t)
            m.begin(current)
            m.select(current, 2)
            m.feedback(current, 2, authored_return(current, 2))
        self.assertTrue(m.predict(check_frame(MISSIONS[0], 0), 2)[1]["supported"])
        alt = authored_return(before, 2)
        alt["image"][0][0] = [1, 3, 2]
        m.begin(before)
        m.select(before, 2)
        m.feedback(before, 2, alt)
        result, evidence = m.predict(check_frame(MISSIONS[0], 0), 2)
        self.assertIsNone(result)
        self.assertEqual(evidence["reason"], "UNSUPPORTED_OR_CONTRADICTORY_COMPONENT")

    def test_original_action_and_selected_feedback_custody(self):
        m = StructuralEffectCells(full_public)
        before = fit_frame(0)
        m.begin(before)
        with self.assertRaises(ValueError):
            m.select(before, 7)
        with self.assertRaises(ValueError):
            m.select(before, True)
        with self.assertRaises(ValueError):
            m.select(dict(before, agent_pos=[2, 3]), 0)
        with self.assertRaises(ValueError):
            m.feedback(before, 2, authored_return(before, 2))
        m.select(before, 2)
        with self.assertRaises(ValueError):
            m.feedback(before, 1, authored_return(before, 1))
        with self.assertRaises(ValueError):
            m.checkpoint()
        m.feedback(before, 2, authored_return(before, 2))
        with self.assertRaises(ValueError):
            m.feedback(before, 2, authored_return(before, 2))
        with self.assertRaises(ValueError):
            m.select(before, 1)

    def test_cold_process_original_source_restore_and_tamper(self):
        m = train()
        raw = m.checkpoint()
        auth = hashlib.sha256(raw).hexdigest()
        cold = StructuralEffectCells.restore(full_public, raw, auth)
        self.assertEqual(cold.checkpoint(), raw)
        with self.assertRaises(ValueError):
            StructuralEffectCells.restore(full_public, raw, "0" * 64)
        with self.assertRaises(ValueError):
            StructuralEffectCells.restore(full_public, raw + b" ", hashlib.sha256(raw + b" ").hexdigest())
        with tempfile.TemporaryDirectory(prefix="nr-m2g-") as root:
            file = Path(root) / "source-only-m2g-checkpoint.json"
            file.write_bytes(raw)
            code = """
import hashlib,pathlib,sys
from nr_m2g_effect_cells import StructuralEffectCells
from nr_m2e_extended_public import full_public
raw=pathlib.Path(sys.argv[1]).read_bytes()
s=StructuralEffectCells.restore(full_public,raw,sys.argv[2])
assert s.events==84 and s.checkpoint()==raw
print("NRM2G_INDEPENDENT_PROCESS_RESTORE_PASS")
"""
            proc = subprocess.run([sys.executable, "-B", "-c", code, str(file), auth],
                                  cwd=str(Path(__file__).parent),
                                  text=True, capture_output=True, timeout=40)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("NRM2G_INDEPENDENT_PROCESS_RESTORE_PASS", proc.stdout)

if __name__ == "__main__":
    unittest.main()
