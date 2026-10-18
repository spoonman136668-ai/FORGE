"""F124-BB independent non-consuming frozen-source and public disagreement tests."""
import inspect
import unittest
import f124bb_train_source as source
import f124bb_disagreement_confidence as model
import f124bb_fit_screen as evaluator
import f124ay_learned_composition as feistel

class F124BBPreflight(unittest.TestCase):
    def test_first_frozen_precommitment_and_new_source(self):
        x=source.frozen()
        self.assertEqual(x["lineage"]["qualified_BA_parent"],source.PARENT_SHA)
        self.assertEqual(source.witness.blob(source.FREEZE),source.FREEZE_BLOB)
        self.assertEqual(source.witness.blob(source.original.__file__),
                         source.PARENT_SOURCE_BLOB)
        self.assertEqual(x["source"]["equal_public_rows_per_task"],48)
        self.assertEqual(len(x["candidates"]["arms"]),10)
        self.assertEqual(len(evaluator.SPECS),10)
        self.assertEqual(x["prospective_rule"]["FIT"][:12],"A new disagr")
        self.assertTrue(set(source.OPERATORS["TRAIN"]).isdisjoint(source.OPERATORS["DEV"]))
        with self.assertRaises(Exception):source.rows("DEV")
        with self.assertRaises(Exception):
            source.build(5000100,source.VECTORS[0],"DEV")

    def test_model_no_hidden_source_or_graph_label(self):
        s=inspect.getsource(model)
        for forbidden in ("import f124bb_train_source",
                          "source.relation(","source.plain(",
                          "case_outcomes","positive_accepted",
                          "operator.startswith(","graph_truth"):
            self.assertNotIn(forbidden,s)
        self.assertEqual(model.VETO_BITS,(2,4))
        self.assertEqual(model.PUBLIC_TOTAL,48)
        self.assertEqual(model.PUBLIC_FIT,40)
        self.assertEqual(model.PUBLIC_CHECK,8)

    def test_synthetic_public_only_model_contrast_budget(self):
        demos=[]
        for i in range(48):
            x=feistel.bits16((i*1327+217)&65535)
            y=feistel.forward_bits(x,73)
            if i in (3,7,11,26,30,35):
                y[(i*5)%16]^=1
            demos.append({"input_bits":x,"output_bits":y})
        for threshold in model.VETO_BITS:
            m=model.train(demos,"F124BB-SYNTHETIC-NONCE-ONLY",threshold)
            self.assertIn(m["choice"],("affine","feistel","abstain"))
            self.assertEqual(m["public_disagreement_veto_bits"],threshold)
            self.assertEqual(m["extra_public_queries"],0)
            self.assertFalse(m["source_operator_label_seen"])
            self.assertFalse(m["graph_positive_negative_label_seen"])
            self.assertFalse(m["oracle_inverse_seen"])
            self.assertTrue(0<=len(m["public_competing_CHECK_evidence"])<=8)
            self.assertTrue(all(-16<=row["competing_minus_selected"]<=16
                 for row in m["public_competing_CHECK_evidence"]))
        with self.assertRaises(Exception):
            model.train(demos[:47],"F124BB-SYNTHETIC-NONCE-ONLY",2)
        with self.assertRaises(Exception):
            model.train(demos,"F124BB-SYNTHETIC-NONCE-ONLY",3)

    def test_reject_requires_baseline_false_positive_correction_and_preservation(self):
        cards={name:evaluator.fresh() for name,_,_,_ in evaluator.SPECS}
        affine=cards["affine_balanced48"]
        affine["paired"]=7
        affine["accepted_positive_case_ids"]=["A","B","C","D","E","F","G"]
        original=cards["joint_balanced48"]
        original["paired"]=9
        original["accepted_positive_case_ids"]=["A","B","C","D","E","F","G","H","I"]
        original["FP"]=1
        original["case_outcomes"]=[{"case_sha256":"K","negative_accepted":True}]
        candidate=cards["disagreement_balanced_veto2"]
        candidate["paired"]=10
        candidate["by_operator"]["feistel"]["paired"]=3
        candidate["accepted_positive_case_ids"]=["A","B","C","D","E","F","G","H","I","J"]
        candidate["case_outcomes"]=[{"case_sha256":"K","negative_accepted":False}]
        ok,_=evaluator.candidate_eligible(cards,"disagreement_balanced_veto2",7)
        self.assertTrue(ok)
        candidate["accepted_positive_case_ids"].remove("I")
        ok,why=evaluator.candidate_eligible(cards,"disagreement_balanced_veto2",7)
        self.assertFalse(ok)
        self.assertFalse(why["all_joint_positives_preserved"])
        candidate["accepted_positive_case_ids"].append("I")
        candidate["case_outcomes"]=[{"case_sha256":"K","negative_accepted":True}]
        ok,why=evaluator.candidate_eligible(cards,"disagreement_balanced_veto2",7)
        self.assertFalse(ok)
        self.assertFalse(why["FP_efficacy_demonstrated"])

if __name__=="__main__":unittest.main()
