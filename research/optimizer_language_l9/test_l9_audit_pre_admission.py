"""Negative tests for the L9 pre-audit metadata gate; synthetic receipts, no corpus."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import l9_audit_pre_admission as gate

class AuditAdmissionTests(unittest.TestCase):
    def synthetic_seal(self):
        rows=[]
        for (arm,seed),(kind,receipt_sha,checkpoint_sha) in gate.EXPECTED.items():
            rows.append({
              "arm":arm,"seed":seed,"evaluation_identity":kind,
              "raw_receipt_sha256":receipt_sha,
              "selected":{"epoch":12,"checkpoint_sha256":checkpoint_sha,
                          "requested_content_proxy_coverage":0.0}})
        return {
            "schema":gate.SEAL_SCHEMA,
            "status":"ALL_FOUR_NUMERIC_DEV_CHOICES_VALIDATED_MIXED_V1_GRU_V2_TRANSFORMER",
            "role_identity_sha256":gate.ROLE_SHA,"model_suite_git_blob":gate.SUITE,
            "candidate_receipt_sha256":"01f08870677067ca0f0dcfdff004d1ef04cea8465da0d025f904634e2bcd5d47",
            "original_transformer_v1_timed_out":True,
            "recovered_transformer_v2_never_rebranded_v1":True,
            "separate_semantic_audit_admission_required":True,
            "audit_dev_reference_consumed":False,
            "official_test_consumed":False,"scientific_go":False,
            "candidate":{"selected_config":gate.CONFIG},
            "neural_cases":rows}
    def check(self,data):
        raw=gate.canonical(data)
        with patch.object(gate,"SEAL_RAW_SHA256",gate.sha(raw)):
            return gate.validate_seal_bytes(raw)
    def test_complete_synthetic_seal_with_both_distinct_v2_receipts(self):
        result=self.check(self.synthetic_seal())
        self.assertEqual(len(result["neural_cases"]),4)
        self.assertFalse(result["scientific_go"])
    def test_role_go_test_and_source_drift_rejected(self):
        for k,v in [
            ("role_identity_sha256","bad"),("model_suite_git_blob","bad"),
            ("audit_dev_reference_consumed",True),("official_test_consumed",True),
            ("scientific_go",True),("recovered_transformer_v2_never_rebranded_v1",False),
            ("separate_semantic_audit_admission_required",False),
            ("original_transformer_v1_timed_out",False)]:
            with self.subTest(field=k):
                data=self.synthetic_seal();data[k]=v
                with self.assertRaises(ValueError):self.check(data)
    def test_missing_seed_duplicate_seed_epoch_and_checkpoint_rejected(self):
        for issue in ("missing","duplicate","wrong_epoch","wrong_checkpoint","wrong_receipt","rebrand"):
            data=self.synthetic_seal()
            if issue=="missing":data["neural_cases"].pop()
            if issue=="duplicate":data["neural_cases"][-1]=copy.deepcopy(data["neural_cases"][0])
            if issue=="wrong_epoch":data["neural_cases"][0]["selected"]["epoch"]=8
            if issue=="wrong_checkpoint":data["neural_cases"][1]["selected"]["checkpoint_sha256"]="0"*64
            if issue=="wrong_receipt":data["neural_cases"][2]["raw_receipt_sha256"]="0"*64
            if issue=="rebrand":data["neural_cases"][3]["evaluation_identity"]="ORIGINAL_V1"
            with self.subTest(issue=issue),self.assertRaises(ValueError):self.check(data)
    def test_raw_byte_identity_also_matters(self):
        data=self.synthetic_seal()
        raw=gate.canonical(data)
        with self.assertRaises(ValueError):gate.validate_seal_bytes(raw)
    def test_missing_input_blocks_output_no_audit_load(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);out=p/"preflight.json"
            with self.assertRaises(FileNotFoundError):
                gate.preflight(p/"no-contract",p/"no-seal",out)
            self.assertFalse(out.exists())
    def test_exact_contract_crlf_and_lf_equal_but_field_drift_fails(self):
        raw=(Path(__file__).resolve().parent/"L9_AUDIT_ADMISSION_CONTRACT.json").read_bytes()
        normalized=raw.replace(b"\r\n",b"\n")
        original=gate.validate_contract_bytes(normalized)
        converted=gate.validate_contract_bytes(normalized.replace(b"\n",b"\r\n"))
        self.assertEqual(original,converted)
        tampered=normalized.replace(b'"total_audit_dev": 319',b'"total_audit_dev": 318')
        self.assertNotEqual(tampered,normalized)
        with self.assertRaises(ValueError):gate.validate_contract_bytes(tampered)

    def test_all_methods_and_heldout_counts_frozen(self):
        self.assertEqual(len(gate.METHODS),7)
        self.assertEqual(set(gate.EXPECTED),{
            ("GRU_SEQ2SEQ",1701),("GRU_SEQ2SEQ",1702),
            ("SMALL_TRANSFORMER",1701),("SMALL_TRANSFORMER",1702)})
        self.assertEqual(gate.SEAL_RAW_SHA256,
            "bbee9d6a6a92c3fbec536dbf8364ecae6b05ae46d86fbdef667f23d3179abc09")
if __name__=="__main__":unittest.main()
