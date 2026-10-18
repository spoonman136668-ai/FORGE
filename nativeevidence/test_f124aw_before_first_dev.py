"""F124-AW deterministic source-identity and pre-first-use focused checks."""
import unittest
import f124aw_original_first_dev_source as source
import f124aw_first_ygg_dev_evidence as science
import f124av_informative_inverse as original_model
class AWBoundary(unittest.TestCase):
    def test_exact_preimplementation_freeze_without_source_birth(self):
        d=source.frozen()
        self.assertEqual(source.witness.blob(source.FREEZE),source.FREEZE_BLOB)
        self.assertEqual(d["lineage"]["qualified_parent_PR"],539)
        self.assertEqual(d["fixed_model"]["original_SCREEN"],{"paired":9,"FP":0,"FN":15})
        self.assertTrue(all(v is False for v in d["authority"].values()))
        self.assertFalse(set(source.av.COHORTS["Yggdrasil"]["TRAIN"]) &
                         set(source.SOURCE_RANGE))
        self.assertFalse(set(source.av.OPERATORS["TRAIN"]) &
                         set(source.av.OPERATORS["DEV"]))
        self.assertTrue(source.SOURCE_RANGE.start==4300100)
        self.assertTrue(source.SOURCE_RANGE.stop==4300124)
        # Crucial: NO new DEV birth here, even to "test" source generation.
        self.assertIs(science.born,source)

    def test_exact_model_and_no_search_space(self):
        self.assertEqual(science.LOCKED,
            {"query_condition":"balanced_basis48",
             "fit_bit_budget":12,"min_CHECK_correct":96})
        self.assertEqual(original_model.TRIALS,256)
        self.assertEqual(original_model.FIT,40)
        self.assertEqual(original_model.TOTAL,48)
        self.assertTrue("Wingless" not in source.SOURCE_RANGE.__class__.__name__)
if __name__=="__main__": unittest.main()
