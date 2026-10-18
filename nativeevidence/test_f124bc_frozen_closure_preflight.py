"""F124-BC non-consuming public algebraic relationship evidence checks."""
import inspect,unittest
import f124bc_train_source as source
import f124bc_public_closure as model
import f124bc_fit_screen as screen

def vec(n):return [(n>>i)&1 for i in range(16)]
class F124BCPreflight(unittest.TestCase):
    def test_frozen_first_commit_new_source_and_sealed_DEV(self):
        d=source.frozen()
        self.assertEqual(source.witness.blob(source.FREEZE),source.FREEZE_BLOB)
        self.assertEqual(source.witness.blob(source.original.__file__),
                         source.PARENT_SOURCE_BLOB)
        self.assertEqual(d["parent"]["qualified_BB_head"],source.PARENT_SHA)
        self.assertEqual(d["new_source"]["total_public"],48)
        self.assertEqual(len(d["arms"]),10)
        self.assertEqual(len(screen.SPECS),10)
        with self.assertRaises(Exception):source.rows("DEV")
        with self.assertRaises(Exception):
            source.build(5100100,source.VECTORS[0],"DEV")

    def test_public_algebraic_identity_under_clean_affine_response(self):
        original=[{"input_bits":vec(i*17+11),"output_bits":vec((i*17+11)^0x4321)}
                  for i in range(24)]
        xs=[0]+[1<<i for i in range(16)]+[
          (1<<i)|(1<<((i+5)%16)) for i in range(7)]
        rows=original+[{"input_bits":vec(x),"output_bits":vec(x^0x4321)}
                       for x in xs]
        cert=model.certificate(rows,"balanced_basis48")
        self.assertEqual(cert["witnesses"],7)
        self.assertEqual(cert["violations"],0)
        self.assertFalse(model.certificate(rows,"random48")["certifiable"])
        corrupted=[{**r,"output_bits":list(r["output_bits"])} for r in rows]
        for i in (41,42,43,44):
            corrupted[i]["output_bits"][i%16]^=1
        cert=model.certificate(corrupted,"balanced_basis48")
        self.assertEqual(cert["violations"],4)
        with self.assertRaises(Exception):
            model.certificate(rows[:47],"balanced_basis48")

    def test_no_model_or_evaluator_evidence_allowed_into_certificate(self):
        code=inspect.getsource(model.certificate)
        for forbidden in ("f124az_joint_public_inverse","inverse_output(",
                          "model[","operator","graph","source.relation",
                          "true_label"):
            self.assertNotIn(forbidden,code)
        self.assertEqual(set(model.POLICIES),{"closure4","closure5"})

    def test_strict_baseline_FP_correction_and_all_original_positives(self):
        cards={name:screen.fresh() for name,_,_,_ in screen.SPECS}
        af=cards["affine_balanced48"]
        af["paired"]=7
        af["accepted_positive_case_ids"]=["A","B","C","D","E","F","G"]
        joint=cards["joint_balanced48"]
        joint["paired"]=9
        joint["accepted_positive_case_ids"]=["A","B","C","D","E","F","G","H","I"]
        joint["FP"]=1
        joint["case_outcomes"]=[{"case_sha256":"NEG1","negative_accepted":True}]
        new=cards["public_closure_balanced4"]
        new["paired"]=10
        new["by_operator"]["feistel"]["paired"]=3
        new["accepted_positive_case_ids"]=["A","B","C","D","E","F","G","H","I","J"]
        new["case_outcomes"]=[{"case_sha256":"NEG1","negative_accepted":False}]
        self.assertTrue(screen.candidate_eligible(
            cards,"public_closure_balanced4",7)[0])
        new["accepted_positive_case_ids"].remove("H")
        self.assertFalse(screen.candidate_eligible(
            cards,"public_closure_balanced4",7)[0])
        new["accepted_positive_case_ids"].append("H")
        new["case_outcomes"][0]["negative_accepted"]=True
        self.assertFalse(screen.candidate_eligible(
            cards,"public_closure_balanced4",7)[0])
if __name__=="__main__":unittest.main()
