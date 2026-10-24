"""K4M read-only original research diagnostic integrity, no simulator dependency."""
import copy
import json
import unittest
from pathlib import Path
from k4m_mechanism_audit import FROZEN, selected, predict, choice, squared

def examples():
    return [{"variant":i,"features":[i/12]+[0.0]*127,"reward":float(i%5)}
            for i in range(12)]

class K4MReadOnlyFalsification(unittest.TestCase):
    def test_hindsight_frozen_original_no_first_use(self):
        p=json.loads(FROZEN.read_text(encoding="utf-8"))
        self.assertEqual(p["reference"]["target_DEV_variant"],19)
        self.assertEqual(p["reference"]["FIT_example_of_interest"],8)
        self.assertFalse(p["governance"]["no_original_science_first_use"] is False)
        self.assertTrue(p["method"]["read_only"])

    def test_full_memory_keeps_all_original_fit(self):
        self.assertEqual([r["variant"] for r in selected(examples(),"full_12")],list(range(12)))

    def test_original_coreset_has_four_real_fit_records(self):
        rows=examples()
        for mode in ("outcome_aware_4","coverage_4","uniform_4"):
            out=selected(rows,mode)
            self.assertEqual(len(out),4)
            self.assertEqual(len({r["variant"] for r in out}),4)
            for r in out:
                self.assertIn(r,rows)

    def test_uniform_control_strictly_preserves_indices(self):
        self.assertEqual([r["variant"] for r in selected(examples(),"uniform_4")],[0,3,6,9])

    def test_original_training_never_mutated_by_coreset(self):
        original=examples();snapshot=copy.deepcopy(original)
        for mode in ("outcome_aware_4","coverage_4","uniform_4"):
            selected(original,mode)
        self.assertEqual(original,snapshot)

    def test_missing_or_nonchronological_fit_rejected(self):
        with self.assertRaises(ValueError):
            selected(examples()[:-1],"coverage_4")
        invalid=examples()
        invalid[8]["variant"]=7
        with self.assertRaises(ValueError):
            selected(invalid,"outcome_aware_4")

    def test_public_feature_dimension_guard(self):
        with self.assertRaises(ValueError):
            squared([1.0]*127,[1.0]*128)

    def test_nearest_neighbor_ties_lower_fit_variant(self):
        rows=examples()
        obs=[0.0]*128
        nearest=predict([rows[2],rows[0]],obs)
        self.assertEqual(nearest["FIT_variant"],0)

    def test_hindsight_one_record_removal_can_flip_action(self):
        obs=[0.0]*128
        generic=lambda reward,variant: [{"variant":variant,"reward":float(reward),
              "features":[0.0]*128}]
        arms={0:generic(0,0),1:generic(10,0),2:generic(-2,0),3:generic(1,0)+generic(50,1)}
        arms[3][0]["features"]=[1.0]+[0.0]*127
        self.assertEqual(choice(arms,obs)["selected_arm"],3)
        arms[3]=[r for r in arms[3] if r["variant"]!=1]
        self.assertEqual(choice(arms,obs)["selected_arm"],1)

if __name__=="__main__":
    unittest.main()
