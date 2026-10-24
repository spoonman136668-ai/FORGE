"""L9 neural SELECT verification, adversarial custody and role isolation."""
import hashlib
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
import tempfile

import l9_model_suite as m
import l9_neural_select_only as selection

class SelectOnlyTests(TestCase):
    def test_fixed_scientific_identities(self):
        self.assertEqual(selection.ROLE_SHA,"b9995c1846f5e1d99bf8bc4083dde0ebb41140906284bcf050a7ed6fe0efe726")
        self.assertEqual(selection.SUITE_BLOB,"710ce648a30ffc55647f689c5f4aa3ac13b07066")
        self.assertEqual(selection.ALLOWED_ARMS,("GRU_SEQ2SEQ","SMALL_TRANSFORMER"))
        self.assertEqual(selection.ALLOWED_SEEDS,m.MANDATORY_SEEDS)
        self.assertEqual(selection.ALLOWED_EPOCHS,m.CHECKPOINT_EPOCHS)
        self.assertEqual(selection.sha(b"abc"),hashlib.sha256(b"abc").hexdigest())

    def valid_receipt(self):
        return dict(schema="forge.optimizer.language.l9.neural-train-only-development-v1",
          status="NEURAL_TRAIN_COMPLETE_SELECT_NOT_RUN_DEVELOPMENT_ONLY",
          arm="GRU_SEQ2SEQ",seed=1701,role_identity_sha256=selection.ROLE_SHA,
          model_suite_git_blob=selection.SUITE_BLOB,
          source_release_sha="a7ea49b5ffa5011edf81e8530c59b3552a965023",
          train_examples=8480,select_count_loaded_but_unseen_by_fit=2154,
          select_fidelity_scored=False,audit_dev_reference_consumed=False,
          official_test_consumed=False,scientific_go=False,
          model_fit_role="L9_TRAIN",checkpoint_epochs=[4,8,12],
          checkpoints={str(i):{} for i in (4,8,12)})

    def test_fit_receipt_valid(self):
        selection.assert_fit_receipt(self.valid_receipt(),"GRU_SEQ2SEQ",1701)

    def test_mismatched_role_or_source_is_rejected(self):
        for key,value in (("role_identity_sha256","tamper"),("seed",1702),
                          ("source_release_sha","incorrect"),("checkpoint_epochs",[4,8]),
                          ("official_test_consumed",True),("audit_dev_reference_consumed",True),
                          ("select_fidelity_scored",True),("model_suite_git_blob","wrong")):
            v=self.valid_receipt();v[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                selection.assert_fit_receipt(v,"GRU_SEQ2SEQ",1701)

    def test_missing_checkpoint_rejected(self):
        v=self.valid_receipt();v["checkpoints"].pop("8")
        with self.assertRaises(ValueError):
            selection.assert_fit_receipt(v,"GRU_SEQ2SEQ",1701)

    def test_invalid_arm_seed_epoch_does_not_open_file(self):
        with self.assertRaises(ValueError):
            selection.model_from_checkpoint("NEW",1701,4,Path("/nonexistent"))
        with self.assertRaises(ValueError):
            selection.model_from_checkpoint("GRU_SEQ2SEQ",0,4,Path("/nonexistent"))
        with self.assertRaises(ValueError):
            selection.model_from_checkpoint("GRU_SEQ2SEQ",1701,5,Path("/nonexistent"))

    def test_malformed_checkpoint_rejected_pre_torch_load(self):
        import torch
        v=self.valid_receipt()
        with tempfile.TemporaryDirectory() as dirname:
            d=Path(dirname)
            (d/"receipt.json").write_text(json.dumps(v),encoding="utf-8")
            name="GRU_SEQ2SEQ-seed1701-epoch4-inference.pt"
            (d/name).write_bytes(b"nonsense-checkpoint")
            v["checkpoints"]["4"]={"inference_file":name,
                                    "inference_bytes":len(b"nonsense-checkpoint"),
                                    "inference_sha256":"bad"}
            (d/"receipt.json").write_text(json.dumps(v),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"corrupted or swapped"):
                selection.model_from_checkpoint("GRU_SEQ2SEQ",1701,4,d)

    def test_metric_rejects_train_or_audit(self):
        graph=(m.Triple("Ada","works","Paris"),)
        for role in ("L9_AUDIT_DEV","L9_TRAIN"):
            ex=[m.Example(role,"g",graph,"Ada works Paris")]
            with self.assertRaises(ValueError):
                selection.compute_select_metric(None,"GRU_SEQ2SEQ",ex,{})

    def test_source_static_guards_and_no_audit_reader(self):
        text=(Path(__file__).resolve().parent/"l9_neural_select_only.py").read_text(encoding="utf-8")
        self.assertIn('if e.role=="L9_SELECT"',text)
        self.assertIn('if e.role=="L9_TRAIN"',text)
        self.assertIn('model.assert_audit_not_used(train+select)',text)
        self.assertIn('"audit_dev_reference_consumed":False',text)
        self.assertIn('"official_test_consumed":False',text)
        self.assertIn('len(select)==2154',text)
        self.assertNotIn('e.role=="L9_AUDIT_DEV"',text)

    def test_checkpoint_input_abstains_on_overlength(self):
        fake=("x"*(m.MAX_SOURCE_BYTES+64))
        triples=(m.Triple(fake,"prop","somewhere"),)
        class BadNet:
            def greedy(self,*args,**kwargs):
                raise AssertionError("long input must not reach neural model")
        self.assertIsNone(selection.inference_one(BadNet(),"GRU_SEQ2SEQ",triples))
