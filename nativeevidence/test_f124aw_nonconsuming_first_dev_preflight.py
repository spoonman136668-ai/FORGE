"""F124-AW independent non-consuming preflight. Only previously used TRAIN.
Never instantiate DEV source records until exact prospective first-use run.
"""
import inspect
import unittest
import f124aw_one_original_dev as aw
import f124av_train_source as parent

class FixedFirstUse(unittest.TestCase):
    def test_immutable_selection_and_train_parity(self):
        self.assertEqual(aw.SELECTION,{
            "query_condition":"balanced_basis48",
            "fit_bit_budget":12,"min_CHECK_correct":96})
        d=aw.preflight()
        self.assertEqual(d["Yggdrasil_DEV_cases_generated"],0)
        self.assertEqual(d["Wingless_DEV_cases_generated"],0)
        self.assertEqual(d["existing_consumed_TRAIN_augmentation_parity"],"PASS")
        self.assertFalse(d["scientific_first_use"])

    def test_no_wingless_or_unfrozen_candidate_path(self):
        text=inspect.getsource(aw)
        self.assertNotIn('dev_birth("Wingless"',text)
        self.assertNotIn('pairs("Wingless","DEV"',text)
        self.assertNotIn("random48",text)
        self.assertNotIn("source.OPERATORS[\"DEV\"][0]",text.split("def dev_birth():")[1])
        self.assertEqual(aw.learner.TRIALS,256)

    def test_training_only_guard(self):
        seed=parent.COHORTS["Yggdrasil"]["TRAIN"].start
        vec=parent.VECTORS[0]
        _,op,nonce,p,n,_=parent.build("Yggdrasil",seed,vec,"TRAIN")
        with self.assertRaises(Exception):
            aw.augmented(seed,vec,op,p["demos"],"DEV")
        with self.assertRaises(Exception):
            aw.augmented(parent.COHORTS["Yggdrasil"]["DEV"].start,
                         vec,op,p["demos"],"TRAIN")

if __name__=="__main__":unittest.main()
