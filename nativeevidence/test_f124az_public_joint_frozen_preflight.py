"""F124-AZ source freeze and synthetic public-only joint router focused checks.

No prospective new AZ TRAIN case is constructed here. DEV is not available.
"""
import inspect,unittest
import f124az_train_source as source
import f124az_joint_public_inverse as joint
import f124az_fit_screen as screen
import f124ay_learned_composition as nonlinear

class AZIndependentPreflight(unittest.TestCase):
    def test_original_source_birth_and_exact_precommitment(self):
        d=source.frozen()
        self.assertEqual(source.witness.blob(source.FREEZE),source.FREEZE_BLOB)
        self.assertEqual(source.witness.blob(source.original.__file__),source.PARENT_SOURCE_BLOB)
        self.assertEqual(d["lineage"]["parent_AY_qualified_head"],source.PARENT_SHA)
        self.assertEqual(len(d["models"]["arms"]),8)
        self.assertEqual(len(screen.SPECS),8)
        self.assertTrue(set(source.OPERATORS["TRAIN"]).isdisjoint(source.OPERATORS["DEV"]))
        self.assertEqual(source.COHORTS["Yggdrasil"]["TRAIN"].start,4700000)
        with self.assertRaises(Exception):source.rows("DEV")
        with self.assertRaises(Exception):
            source.build(source.COHORTS["Yggdrasil"]["DEV"].start,
                         source.VECTORS[0],"DEV")

    def test_public_model_has_no_evaluator_access(self):
        code=inspect.getsource(joint)
        for banned in ("import f124az_train_source",
                       "import f124ay_train_source",
                       "operator.startswith(","source.plain(",
                       "source.relation("):
            self.assertNotIn(banned,code)
        self.assertEqual(joint.MARGINS,(0,8))
        self.assertEqual(joint.TOTAL,48)
        self.assertEqual(joint.CHECK,8)
        self.assertEqual(joint.MIN_CHECK,96)
        self.assertEqual(joint.AFFINE_ERROR_BUDGET,12)

    def test_synthetic_unknown_key_and_joint_public_selection(self):
        # Public-only synthetic support never uses a registered source task.
        demos=[]
        for index in range(48):
            x=nonlinear.bits16((index*1327+217)&65535)
            y=nonlinear.forward_bits(x,73)
            if index in (3,7,11,26,30,35):
                y[(index*5)%16]^=1
            demos.append({"input_bits":x,"output_bits":y})
        for margin in joint.MARGINS:
            result=joint.train(demos,"SYNTHETIC-ONLY-NONCE",margin)
            self.assertIn(result["choice"],("affine","feistel","abstain"))
            self.assertTrue(result["trained_both_from_same_40_FIT"])
            self.assertTrue(result["public_CHECK_shared_exactly_8"])
            self.assertFalse(result["model_receives_operator_token"])
            self.assertFalse(result["model_receives_oracle_inverse"])
            self.assertFalse(result["model_receives_true_graph_label"])
            self.assertEqual(result["feistel_model"]["learned_key"],73)
            self.assertGreaterEqual(result["extra_task_model_bits_lower"],8)
            self.assertGreater(result["fit_operations_lower"],0)
        with self.assertRaises(Exception):
            joint.train(demos[:47],"SYNTHETIC-ONLY-NONCE",0)
        with self.assertRaises(Exception):
            joint.train(demos,"SYNTHETIC-ONLY-NONCE",4)

    def test_case_identity_preservation_is_nonnegotiable(self):
        cards={name:screen.fresh() for name,_,_,_ in screen.SPECS}
        aff=cards["affine_balanced48"]
        aff["paired"]=7
        aff["accepted_positive_case_ids"]=["A","B","C","D","E","F","G"]
        proposed=cards["public_joint_balanced_margin0"]
        proposed["paired"]=10
        proposed["by_operator"]["feistel"]["paired"]=3
        proposed["accepted_positive_case_ids"]=["A","B","C","D","E","F","G","H","I","J"]
        good,_=screen.candidate_eligible(cards,"public_joint_balanced_margin0",7)
        self.assertTrue(good)
        proposed["accepted_positive_case_ids"].remove("G")
        bad,diag=screen.candidate_eligible(cards,"public_joint_balanced_margin0",7)
        self.assertFalse(bad)
        self.assertFalse(diag["all_control_positive_ids_preserved"])
        proposed["accepted_positive_case_ids"].append("G")
        proposed["FP"]=1
        self.assertFalse(screen.candidate_eligible(cards,"public_joint_balanced_margin0",7)[0])

if __name__=="__main__":unittest.main()
