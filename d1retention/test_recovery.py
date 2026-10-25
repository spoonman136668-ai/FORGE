"""D1 recovery bookmarking qualifies metadata only; never restores."""
import unittest
from recovery import validate_recovery

PRODUCTION={"result":{"version":"production"}}
BOOKMARK={"success":True,"result":{"bookmark":"00000001-00000002-00004e2f-0a83ea2fceebc654de0640c422be4653"}}

class RecoveryTests(unittest.TestCase):
    def test_frozen_production_bookmark_valid_and_non_authorizing(self):
        r=validate_recovery(PRODUCTION,BOOKMARK)
        self.assertTrue(r.supported_backend and r.bookmark_shape_verified)
        self.assertTrue(r.bookmark_readback_qualified)
        self.assertFalse(r.restore_attempted or r.full_backup_restore_qualified)
        self.assertFalse(r.live_schema_install_approved)
        self.assertNotIn("bookmark",vars(r))
    def test_alpha_database_does_not_claim_time_travel(self):
        r=validate_recovery({"result":{"version":"alpha"}},BOOKMARK)
        self.assertFalse(r.supported_backend or r.bookmark_readback_qualified)
    def test_missing_or_malformed_bookmark_rejected(self):
        for doc in ({},{"success":False,"result":BOOKMARK["result"]},
                    {"success":True,"result":{"bookmark":"abc"}},
                    {"success":True,"result":{"bookmark":"../secrets"}},
                    {"success":True,"result":{"bookmark":"A"*200}},
                    {"success":True,"result":["garbage"]}):
            with self.subTest(doc=doc):
                self.assertFalse(validate_recovery(PRODUCTION,doc).bookmark_readback_qualified)
    def test_no_database_info_cannot_qualify(self):
        self.assertFalse(validate_recovery({},BOOKMARK).bookmark_readback_qualified)
    def test_no_restoration_or_sql_writes_in_helper(self):
        import inspect,recovery
        source=inspect.getsource(recovery)
        self.assertNotIn("urllib",source)
        self.assertNotIn("sqlite3",source)
        self.assertNotIn("restore(",source)
if __name__=="__main__":unittest.main()
