import ast
import hashlib
import pathlib
import unittest

import l9_model_suite as model
import l9_neural_train_only as trainer

ROOT=pathlib.Path(__file__).resolve().parent

class NeuralTrainOnlyPrefit(unittest.TestCase):
    def test_seeds_and_architectures_are_exact(self):
        self.assertEqual(trainer.VALID_ARMS,("GRU_SEQ2SEQ","SMALL_TRANSFORMER"))
        self.assertEqual(trainer.SEEDS,(1701,1702))
        self.assertEqual(trainer.EPOCHS,(4,8,12))
        self.assertEqual(trainer.SEEDS,model.MANDATORY_SEEDS)
        self.assertEqual(trainer.EPOCHS,model.CHECKPOINT_EPOCHS)

    def test_model_suite_identity_is_fixed(self):
        self.assertEqual(trainer.SUITE_BLOB,"710ce648a30ffc55647f689c5f4aa3ac13b07066")
        self.assertEqual(model.PARAMETER_CEILING,600000)
        self.assertLessEqual(model.expected_gru_parameters(),model.PARAMETER_CEILING)
        self.assertLessEqual(model.expected_transformer_parameters(),model.PARAMETER_CEILING)

    def test_runner_has_no_fit_at_module_import(self):
        source=(ROOT/"l9_neural_train_only.py").read_text()
        tree=ast.parse(source)
        self.assertTrue(any(isinstance(x,ast.FunctionDef) and x.name=="run" for x in tree.body))
        self.assertFalse(any(isinstance(x,ast.Expr) and isinstance(x.value,ast.Call)
                             and isinstance(x.value.func,ast.Attribute)
                             and x.value.func.attr=="train_neural" for x in tree.body))

    def test_invalid_arm_rejected_before_source_access(self):
        with self.assertRaises(ValueError):
            trainer.run(pathlib.Path("/does/not/exist"),"NEW_MODEL",1701,pathlib.Path("/not/written"))

    def test_invalid_seed_rejected_before_source_access(self):
        with self.assertRaises(ValueError):
            trainer.run(pathlib.Path("/does/not/exist"),"GRU_SEQ2SEQ",1703,pathlib.Path("/not/written"))

    def test_full_roles_guard_required(self):
        source=(ROOT/"l9_neural_train_only.py").read_text()
        self.assertIn('if x.role == "L9_TRAIN"',source)
        self.assertIn('sum(x.role == "L9_SELECT"',source)
        self.assertIn('not any(x.role == "L9_AUDIT_DEV"',source)
        self.assertIn("model.train_neural(arm, train, seed, device=\"cpu\")",source)
        self.assertIn('"audit_dev_reference_consumed": False',source)
        self.assertIn('"official_test_consumed": False',source)
        self.assertIn('"select_fidelity_scored": False',source)

    def test_ckpt_constraints_checked(self):
        source=(ROOT/"l9_neural_train_only.py").read_text()
        self.assertIn("set(result[\"checkpoints\"]) == set(EPOCHS)",source)
        self.assertIn("TRAINING_CHECKPOINT_CEILING",source)
        self.assertIn("INFERENCE_STATE_CEILING",source)

    def test_digest_and_receipt_serialization(self):
        self.assertEqual(trainer.sha(b"a"),hashlib.sha256(b"a").hexdigest())
        self.assertIn("neural-train-only-development-v1",trainer.SCHEMA)
        self.assertTrue(model.canonical_json_bytes({"one":1}).endswith(b"\n"))

if __name__=="__main__":
    unittest.main()
