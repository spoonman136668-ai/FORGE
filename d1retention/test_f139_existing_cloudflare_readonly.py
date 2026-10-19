"""Provider-read-only observation contract; no Cloudflare access needed."""
import unittest
from unittest.mock import patch

import f139_existing_cloudflare_readonly as subject

class F139LiveReadOnlyTests(unittest.TestCase):
    def audit(self, *, objects=(), count=6, archive=None, bookmark="r"*32):
        import install_remote as cf
        if archive is None:
            archive = set(cf.EXPECTED_OBJECTS)
        calls = []
        def query(_api, _database, sql):
            calls.append(sql)
            if "sqlite_master" in sql:
                return [{"type":("table" if name in
                        ("forge_original_preuse_claims", "authority_state",
                         "original_firstuse") else "trigger"),"name":name}
                        for name in sorted(objects)]
            if "COUNT(*)" in sql:
                return [{"n":count}]
            raise AssertionError("unapproved query")
        with patch.object(cf,"single_deployed_database",return_value="0"*8+"-"+
                 "0"*4+"-"+"0"*4+"-"+"0"*4+"-"+"0"*12), \
             patch.object(cf,"schema_snapshot",
                          return_value=(archive,subject.witness.BASELINE_SCHEMA_SHA256)), \
             patch.object(cf,"sql_query",side_effect=query), \
             patch.object(cf,"recovery_bookmark",return_value=bookmark):
            result=subject.audit(object())
        self.assertTrue(all(sql.startswith("SELECT ") for sql in calls))
        self.assertEqual(len(calls),3)
        return result

    def test_true_deployed_absence_is_reported_not_invented(self):
        r=self.audit()
        self.assertEqual(r["archived_originals_count"],6)
        self.assertEqual(r["archived_seals_count"],6)
        self.assertEqual(r["historical_f61_f62_preuse_objects_present"],[])
        self.assertEqual(r["f139_pending_reservation_objects_present"],[])
        self.assertEqual(r["d1_writes_performed"],0)
        self.assertFalse(r["f139_start_receipt_authorized"])
        self.assertFalse(r["independent_fsa_signer_witness_verified"])

    def test_actual_tables_are_detected_without_authorizing_science(self):
        r=self.audit(objects=("authority_state","original_firstuse",
                              "no_delete_original_firstuse"))
        self.assertIn("original_firstuse",
                      r["f139_pending_reservation_objects_present"])
        self.assertFalse(r["complete_all_lane_firstuse_ledger_verified"])
        self.assertFalse(r["f139_start_receipt_authorized"])

    def test_archival_count_change_fails_closed(self):
        with self.assertRaises(subject.Drift):
            self.audit(count=5)

    def test_archive_table_missing_fails_closed(self):
        with self.assertRaises(subject.Drift):
            self.audit(archive=set())

    def test_response_with_unexpected_table_fails_closed(self):
        with self.assertRaises(subject.Drift):
            self.audit(objects=("malicious_unknown_object",))

if __name__ == "__main__":
    unittest.main()
