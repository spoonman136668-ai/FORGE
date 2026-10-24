"""Development-only L9 SELECT seal: frozen identity, four arm/seed completeness, tamper negatives."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import l9_seal_select as s

class SealSelectTests(unittest.TestCase):
    def case(self,arm="GRU_SEQ2SEQ",seed=1701):
        rows=[]
        for epoch,coverage in zip(s.EPOCHS,(0.1,0.2,0.15)):
            h=int(coverage*100)
            rows.append({
                "arm":arm,"seed":seed,"epoch":epoch,"role":"L9_SELECT",
                "records":2154,"triple_denominator":100,"triple_proxy_hits":h,
                "missing_triples_proxy":100-h,
                "requested_content_proxy_coverage":coverage,
                "chrf_single_reference_proxy":0.4+epoch/100,
                "retained_model_bytes":123456,
                "checkpoint_sha256":hashlib.sha256(f"{arm}-{seed}-{epoch}".encode()).hexdigest(),
                "evaluation_cpu_seconds":1.5,"evaluation_wall_seconds":1.7})
        best=rows[1]
        return {
            "schema":s.SELECT_SCHEMA,
            "status":"SELECT_ONLY_DEVELOPMENT_CHECKPOINT_CHOICE",
            "source_role_sha256":s.ROLE_SHA,
            "model_suite_git_blob":s.SUITE_BLOB,
            "arm":arm,"seed":seed,"train_count":8480,"select_count":2154,
            "audit_dev_reference_consumed":False,"official_test_consumed":False,
            "scientific_go":False,"selected_metric_is_nonadjudicated_proxy":True,
            "fit_receipt_sha256":hashlib.sha256(f"fit-{arm}-{seed}".encode()).hexdigest(),
            "selected_epoch":best["epoch"],
            "selected_checkpoint_sha256":best["checkpoint_sha256"],
            "all_epoch_metrics":rows,
        }

    def candidate(self):
        return {
            "schema":"forge.optimizer.language.l9.train-select-development-v1",
            "status":"DEVELOPMENT_TRAIN_SELECT_NOT_AUDIT",
            "split_role_sha256":s.ROLE_SHA,
            "frozen_suite_sha_from_receipt":s.SUITE_BLOB,
            "official_test_consumed":False,
            "scientific_go":False,
            "split_counts":{"train":8480,"select":2154,"audit_dev_model_consumption":0},
            "candidate_config_selected":{"min_template_support":1,"max_templates_per_predicate":4,"joiner":" "},
            "candidate_selection":[{"requested_content_proxy_coverage":0.573594132} for _ in range(8)],
            "retrieval_select":{"requested_content_proxy_coverage":0.124857376},
        }

    def test_frozen_boundary(self):
        self.assertEqual(s.ARMS,("GRU_SEQ2SEQ","SMALL_TRANSFORMER"))
        self.assertEqual(s.SEEDS,(1701,1702))
        self.assertEqual(s.EPOCHS,(4,8,12))
        self.assertEqual(s.CANDIDATE_RECEIPT_SHA,
                         "01f08870677067ca0f0dcfdff004d1ef04cea8465da0d025f904634e2bcd5d47")
        self.assertTrue(s.canonical_bytes({"x":1}).endswith(b"\n"))

    def test_exact_four_full_receipts_select_epoch_8(self):
        for arm in s.ARMS:
            for seed in s.SEEDS:
                item=s.validate_case(self.case(arm,seed),arm,seed)
                self.assertEqual(item["selected_epoch"],8)
                self.assertEqual(len(item["all_epoch_checkpoint_sha256"]),3)

    def test_rejects_audit_or_test_consumption(self):
        for key in ("audit_dev_reference_consumed","official_test_consumed","scientific_go"):
            val=self.case();val[key]=True
            with self.subTest(key=key),self.assertRaises(ValueError):
                s.validate_case(val,"GRU_SEQ2SEQ",1701)

    def test_rejects_incomplete_data_and_identity_drift(self):
        for case in (
            lambda d:d["all_epoch_metrics"].pop(),
            lambda d:d["all_epoch_metrics"][0].update({"records":2153}),
            lambda d:d["all_epoch_metrics"][0].update({"role":"L9_AUDIT_DEV"}),
            lambda d:d["all_epoch_metrics"][0].update({"missing_triples_proxy":999}),
            lambda d:d["all_epoch_metrics"][0].update({"requested_content_proxy_coverage":0.9}),
            lambda d:d.update({"selected_epoch":12}),
            lambda d:d.update({"selected_checkpoint_sha256":"f"*64}),
            lambda d:d.update({"source_role_sha256":"a"*64}),
            lambda d:d["all_epoch_metrics"][0].update({"retained_model_bytes":s.MODEL_BYTES_LIMIT+1}),
        ):
            d=self.case();case(d)
            with self.assertRaises(ValueError):
                s.validate_case(d,"GRU_SEQ2SEQ",1701)

    def test_rejects_nonfinite_scoring(self):
        d=self.case()
        d["all_epoch_metrics"][0]["chrf_single_reference_proxy"]=float("nan")
        with self.assertRaises(ValueError):
            s.validate_case(d,"GRU_SEQ2SEQ",1701)

    def test_canonical_candidate_identity_required(self):
        s.validate_candidate(self.candidate())
        for key,val in (("official_test_consumed",True),
                        ("split_role_sha256","wrong"),
                        ("split_counts",{"train":8480,"select":2154,"audit_dev_model_consumption":1})):
            d=self.candidate();d[key]=val
            with self.assertRaises(ValueError):
                s.validate_candidate(d)

    def test_full_seal_rejects_missing_fourth_case_and_never_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/"neural";folder.mkdir()
            candidate=root/"candidate.json"
            raw=s.canonical_bytes(self.candidate())
            candidate.write_bytes(raw)
            for arm,seed in (("GRU_SEQ2SEQ",1701),("GRU_SEQ2SEQ",1702),("SMALL_TRANSFORMER",1701)):
                (folder/f"{arm}-{seed}.json").write_bytes(s.canonical_bytes(self.case(arm,seed)))
            output=root/"sealed.json"
            with patch.object(s,"CANDIDATE_RECEIPT_SHA",s.digest(raw)):
                with self.assertRaises(FileNotFoundError):
                    s.seal(candidate,folder,output)
            self.assertFalse(output.exists())

    def test_seal_writes_only_four_selected_identities_and_no_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/"neural";folder.mkdir()
            candidate=root/"candidate.json"
            raw=s.canonical_bytes(self.candidate())
            candidate.write_bytes(raw)
            for arm in s.ARMS:
                for seed in s.SEEDS:
                    (folder/f"{arm}-{seed}.json").write_bytes(s.canonical_bytes(self.case(arm,seed)))
            output=root/"sealed.json"
            with patch.object(s,"CANDIDATE_RECEIPT_SHA",s.digest(raw)):
                value=s.seal(candidate,folder,output)
            self.assertTrue(output.exists())
            self.assertEqual(len(value["neural_checkpoint_selection"]),4)
            self.assertTrue(all(e["selected_epoch"]==8 for e in value["neural_checkpoint_selection"]))
            self.assertFalse(value["audit_dev_references_consumed"])
            self.assertFalse(value["scientific_go"])
            with self.assertRaises(ValueError):
                s.seal(candidate,folder,output)

if __name__=="__main__":
    unittest.main()
