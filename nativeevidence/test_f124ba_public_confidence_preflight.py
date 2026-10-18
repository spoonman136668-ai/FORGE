"""Independent F124-BA synthetic qualification; zero fresh TRAIN / DEV birth."""
import inspect,unittest
import f124ba_train_source as source
import f124ba_public_confidence as confidence
import f124ba_fit_screen as screen
import f124ay_learned_composition as feistel

class F124BASourceAndModel(unittest.TestCase):
    def test_source_original_and_unused_dev(self):
        doc=source.frozen()
        self.assertEqual(doc["lineage"]["parent_qualified_head"],source.PARENT_SHA)
        self.assertEqual(source.witness.blob(source.FREEZE),source.FREEZE_BLOB)
        self.assertEqual(source.witness.blob(source.original.__file__),source.PARENT_SOURCE_BLOB)
        self.assertEqual(len(screen.SPECS),10)
        self.assertEqual(doc["models"]["public_per_row_minimums"],[12,14])
        self.assertEqual(doc["source"]["TRAIN"],[4900000,4900023])
        with self.assertRaises(Exception):source.rows("DEV")
        with self.assertRaises(Exception):
            source.build(4900100,source.VECTORS[0],"DEV")

    def test_public_row_guard_never_sees_hidden_source(self):
        s=inspect.getsource(confidence)
        for banned in ("import f124ba_train_source",
                       "import f124az_train_source",
                       "source.relation(","source.plain(",
                       "true_positive","operator.startswith("):
            self.assertNotIn(banned,s)
        self.assertEqual(confidence.ROW_FLOORS,(12,14))
        self.assertEqual(confidence.FIT,40)
        self.assertEqual(confidence.CHECK,8)

    def test_synthetic_public_fit_and_8_new_row_checks(self):
        demos=[]
        for i in range(48):
            original=feistel.bits16((i*1327+217)&65535)
            y=feistel.forward_bits(original,73)
            if i in (3,7,11,26,30,35):
                y[(i*5)%16]^=1
            demos.append({"input_bits":original,"output_bits":y})
        for minimum in confidence.ROW_FLOORS:
            out=confidence.train(demos,"BA-INDEPENDENT-SYNTHETIC-NONCE",minimum)
            self.assertEqual(len(out["public_CHECK_row_correct_bits"]),8)
            self.assertTrue(all(0<=v<=16 for v in out["public_CHECK_row_correct_bits"]))
            self.assertEqual(out["extra_public_bit_comparisons_lower"],128)
            self.assertFalse(out["model_receives_graph_acceptance_label"])
            self.assertFalse(out["model_receives_source_class"])
            self.assertEqual(out["margin"],0)
            self.assertGreater(out["fit_operations_lower"],0)
        with self.assertRaises(Exception):
            confidence.train(demos[:47],"BA-INDEPENDENT-SYNTHETIC-NONCE",12)
        with self.assertRaises(Exception):
            confidence.train(demos,"BA-INDEPENDENT-SYNTHETIC-NONCE",13)

    def test_original_affine_positive_case_preservation(self):
        cards={name:screen.fresh() for name,_,_,_ in screen.SPECS}
        control=cards["affine_balanced48"]
        control["paired"]=7
        control["accepted_positive_case_ids"]=["A","B","C","D","E","F","G"]
        candidate=cards["confidence_balanced_minrow12"]
        candidate["paired"]=10
        candidate["by_operator"]["feistel"]["paired"]=3
        candidate["accepted_positive_case_ids"]=["A","B","C","D","E","F","G","H","I","J"]
        valid,diag=screen.candidate_eligible(
            cards,"confidence_balanced_minrow12",7)
        self.assertTrue(valid)
        candidate["accepted_positive_case_ids"].remove("G")
        invalid,detail=screen.candidate_eligible(
            cards,"confidence_balanced_minrow12",7)
        self.assertFalse(invalid)
        self.assertFalse(detail["all_control_positive_ids_preserved"])
        candidate["accepted_positive_case_ids"].append("G")
        candidate["FP"]=1
        self.assertFalse(screen.candidate_eligible(
            cards,"confidence_balanced_minrow12",7)[0])

if __name__=="__main__":unittest.main()
