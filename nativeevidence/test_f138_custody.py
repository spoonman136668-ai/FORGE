"""F138-C1 negative integrity tests. The complete custody gate stays closed."""
import copy
import unittest
import f138_custody as c

class TestF138Custody(unittest.TestCase):
    def setUp(self):
        self.manifest = c.load()

    def check_rejects(self,change):
        x=copy.deepcopy(self.manifest)
        change(x)
        with self.assertRaises(c.CustodyInvalid):
            c.check(x)

    def test_reconstruct_four_real_controller_and_eight_os_lineages(self):
        result=c.check(self.manifest)
        self.assertEqual(result["verdict"],
                         "PARTIAL_SOURCE_RECORD_CUSTODY_VERIFIED")
        self.assertEqual(result["reconstructed_controller_decisions"],4)
        self.assertEqual(result["reconstructed_cross_platform_lineages"],8)
        self.assertFalse(result["complete_provider_snapshot_custody"])
        self.assertFalse(result["f138_full_continuity_accepted"])
        self.assertFalse(result["scientific_first_use_authorized"])

    def test_canonical_reports_are_content_addressed(self):
        for e in self.manifest["original_source_records"]:
            h=e["original_sha256"]
            self.assertEqual(c.sha(e["controller"]),h["controller_json"])
            self.assertEqual(c.sha(e["child"]),h["child_lineage_json"])

    def test_wrong_nonce_is_rejected(self):
        self.check_rejects(lambda x:x["original_source_records"][1]
            ["controller"].update(wake_nonce="0"*32))

    def test_duplicate_controller_is_rejected(self):
        self.check_rejects(lambda x:x["original_source_records"][1]
            ["controller"].update(controller_run_id=39119993456))

    def test_child_parent_spoof_is_rejected(self):
        self.check_rejects(lambda x:x["original_source_records"][0]
            ["child"].update(parent_run_id=39121294863))

    def test_child_science_authorization_is_rejected(self):
        self.check_rejects(lambda x:x["original_source_records"][0]
            ["child"].update(scientific_first_use_authorized=True))

    def test_genuine_schedule_false_claim_is_rejected(self):
        self.check_rejects(lambda x:x["original_source_records"][2]
            ["child"].update(genuine_integrated_schedule=True))

    def test_windows_platform_drift_is_rejected(self):
        self.check_rejects(lambda x:x["original_source_records"][3]
            ["original_sha256"].update(windows_lineage_receipt="1"*64))

    def test_edited_raw_bytes_without_rehash_are_rejected(self):
        self.check_rejects(lambda x:x["original_source_records"][0]
            ["controller"].update(daily_starts=7))

    def test_source_drift_is_rejected(self):
        self.check_rejects(lambda x:x.update(source_main_sha="1"*40))

    def test_false_complete_custody_is_rejected(self):
        self.check_rejects(lambda x:x["custody_scope"]
            .update(permanent_complete_custody_qualified=True))

    def test_false_provider_snapshot_embedded_is_rejected(self):
        self.check_rejects(lambda x:x["custody_scope"]
            .update(entire_provider_snapshot_bytes_embedded=True))

    def test_false_f138_final_acceptance_is_rejected(self):
        self.check_rejects(lambda x:x["reported_disposition"]
            .update(full_f138_verdict="PASS",genuine_scheduled_count=1))

    def test_source_history_retains_negative_evidence(self):
        result=c.check(self.manifest)
        self.assertEqual(len(result["source_records"]),4)
        self.assertEqual(self.manifest["reported_disposition"]
                         ["genuine_scheduled_count"],0)

    def test_child_rerun_not_accepted(self):
        self.check_rejects(lambda x:x["original_source_records"][2]
            ["child"].update(run_attempt=2))

    def test_source_ledger_not_self_authorizing(self):
        self.assertFalse(self.manifest["custody_scope"]["merge_separately_authorized"])
        self.assertTrue(self.manifest["custody_scope"]["source_review_required"])

if __name__=="__main__":
    unittest.main()
