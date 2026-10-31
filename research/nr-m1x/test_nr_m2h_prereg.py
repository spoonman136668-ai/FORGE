"""NR-M2H prospective contract-only verification.

This file does NOT execute a simulator, generate CHECK labels, update a
learner, or assert novel scientific advantage.
"""
import json
from pathlib import Path
import unittest
from nr_m2d_pinned_original_public import MISSION
from nr_m2e_extended_public import full_public, R10_BLOB, R18_BLOB, MG19_BLOB

PREREG = Path(__file__).with_name("NR_M2H_PREREG.json")

class M2HProspectiveContract(unittest.TestCase):
    def test_read_back_frozen_contract_and_incumbent_custody(self):
        data = json.loads(PREREG.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], "forge.nr-m2h.learned-public-preconditions.source-only-prereg.v1")
        self.assertEqual(data["status"], "PROSPECTIVE_SOURCE_ONLY_ENGINEERING_CONTRACT_NOT_SCIENTIFIC_ADMISSION")
        origin = data["origin"]
        self.assertEqual(origin["parent_fully_qualified_sha"], "493811132c876f29d36f1cabfc342ab469f1d0f4")
        self.assertEqual(origin["authentic_original_source_blobs"],
                         {"r10": R10_BLOB, "r18": R18_BLOB, "mg19": MG19_BLOB})
        r11 = origin["incumbent_yggdrasil_r11"]
        self.assertEqual(r11["pr"], 511)
        self.assertEqual(r11["source_blob"], "614c7dfb1b43f485009b70cb85e9b7b5119cafc2")
        self.assertEqual(origin["incumbent_yggdrasil_r12"]["pr"], 513)
        self.assertFalse(data["authority"]["original_world_permit"])
        self.assertFalse(data["authority"]["native_program_mutation_permit"])
        self.assertEqual(data["authority"]["fsa_issue"], 83)

    def test_prespecified_cohort_separation_and_public_admission(self):
        data = json.loads(PREREG.read_text(encoding="utf-8"))
        seeds = data["fixture"]["seeds"]
        self.assertEqual(list(seeds), ["fit", "val", "check"])
        self.assertEqual(seeds["fit"], [117011, 117013, 117017, 117019])
        self.assertEqual(seeds["val"], [119021, 119023])
        self.assertEqual(seeds["check"], [121031, 121037, 121043, 121049])
        self.assertEqual(len(set(sum(seeds.values(), []))), 10)
        admitted = full_public({"image": [[[1, 0, 0] for _ in range(7)] for _ in range(7)],
                                "direction": 0, "mission": MISSION})
        self.assertEqual(len([v for row in admitted["image"] for cell in row for v in cell]), 147)
        self.assertEqual(set(admitted), {"image", "direction", "mission"})
        self.assertIn("full FORGE Linux/Windows regression",
                      data["decision"]["qualification"])
        self.assertGreaterEqual(len(data["independent_controls"]["mandatory"]), 5)

if __name__ == "__main__":
    unittest.main()
