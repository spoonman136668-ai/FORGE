"""F5 source-content lock negative-path verification. No custody invention."""
import copy
import json
from pathlib import Path
import unittest
from verify_source_lock import ALLOWED_FILES,verify_manifest,run

MANIFEST=Path(__file__).with_name("source_content_lock.json")

class SourceLockTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads(MANIFEST.read_bytes())
        self.expected=copy.deepcopy(self.data["git_blob_sha1"])

    def test_exact_prequalification_lock_is_non_authorizing(self):
        result=verify_manifest(self.data,self.expected)
        self.assertEqual(result["verified_git_blob_count"],6)
        self.assertEqual(result["status"],
                         "CONTENT_PIN_PASS_SCIENTIFIC_FREEZE_NOT_AUTHORIZED")
        self.assertFalse(result["scientific_execution_authorized"])
        self.assertEqual(result["first_use_claims"],0)

    def test_actual_checkout_git_objects_match_pins(self):
        repo=MANIFEST.parents[2]
        result=run(repo)
        self.assertFalse(result["scientific_execution_authorized"])

    def test_original_source_mutation_blocked(self):
        tampered=copy.deepcopy(self.expected)
        tampered["research/f5_native_coverage/policy.py"]="0"*40
        with self.assertRaisesRegex(ValueError,"CONTENT_IDENTITY"):
            verify_manifest(self.data,tampered)

    def test_phantom_data_or_changed_protocol_denied(self):
        changed=copy.deepcopy(self.expected)
        changed["research/f5_native_coverage/prospective_protocol.json"]="f"*40
        with self.assertRaisesRegex(ValueError,"CONTENT_IDENTITY"):
            verify_manifest(self.data,changed)

    def test_premature_cohort_freeze_denied(self):
        self.data["not_frozen"]["sealed_seeds"]=[70000,70001]
        with self.assertRaisesRegex(ValueError,"PREMATURE_ORIGINAL"):
            verify_manifest(self.data,self.expected)

    def test_unsigned_github_run_cannot_stand_in_for_custody(self):
        self.data["custody_requirements"]["signed_snapshot"]="github-actions-success"
        with self.assertRaisesRegex(ValueError,"FALSE_CUSTODY"):
            verify_manifest(self.data,self.expected)

    def test_no_promotion_flag_can_be_set(self):
        self.data["scientific_execution_authorized"]=True
        with self.assertRaisesRegex(ValueError,"AUTHORITY"):
            verify_manifest(self.data,self.expected)

    def test_scientific_winner_not_selected(self):
        self.assertNotIn("scientific_winner_id",self.data)
        self.assertEqual(self.data["not_frozen"]["once_only_original_id"],"UNALLOCATED")

if __name__=="__main__":
    unittest.main()
