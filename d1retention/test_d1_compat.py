"""R18B negative acceptance: a D1 profile, not a science-approved archive."""
import hashlib,sqlite3,tempfile,unittest
from pathlib import Path
from d1_compat import CompatibilityBlocked,PATH,NAMES,sha,statements,offline_qualify
from migration import foreign_schema
class D1CompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE existing_unrelated (id INT PRIMARY KEY, data TEXT NOT NULL)")
        self.db.execute("INSERT INTO existing_unrelated VALUES(1,'preserve')");self.db.commit()
        self.foreign=foreign_schema(self.db)[0]
        self.pin=sha(PATH.read_bytes())
    def tearDown(self):self.db.close()
    def qualify(self,**kw):
        return offline_qualify(self.db,kw.get("pin",self.pin),kw.get("foreign",self.foreign))
    def test_derived_three_table_compatibility_profile(self):
        self.assertEqual(len(statements(PATH.read_bytes())),3)
        self.assertFalse(any("CREATE TRIGGER" in s.upper() for s in statements(PATH.read_bytes())))
    def test_preserves_old_rows_and_all_constraints(self):
        result=self.qualify()
        self.assertEqual(result.tables_installed,3)
        self.assertTrue(result.existing_data_preserved)
        self.assertFalse(result.remote_install_performed or result.db_enforced_immutability_verified)
        self.assertFalse(result.original_custody_verified or result.first_use_reconciled)
        self.assertFalse(result.scientific_accepted or result.dispatch_authorized)
        self.assertEqual(self.db.execute("SELECT data FROM existing_unrelated").fetchone()[0],"preserve")
        self.assertEqual(foreign_schema(self.db)[0],self.foreign)
    def test_duplicate_or_invalid_original_metadata_rejected(self):
        self.qualify()
        self.db.execute("INSERT INTO forge_research_originals "
          "(archive_sha256,lane,experiment,repository,run_id,artifact_id,source_sha,"
          "frozen_manifest_sha256,original_length,chunk_count) VALUES(?,?,?,?,?,?,?,?,?,?)",
          ("a"*64,"Wingless","W1","spoonman136668-ai/Wingless",111,222,"b"*40,"c"*64,100,1))
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO forge_research_originals "
              "(archive_sha256,lane,experiment,repository,run_id,artifact_id,source_sha,"
              "frozen_manifest_sha256,original_length,chunk_count) VALUES(?,?,?,?,?,?,?,?,?,?)",
              ("d"*64,"Wingless","W1","spoonman136668-ai/Wingless",112,223,"b"*40,"c"*64,100,1))
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO forge_research_originals "
              "(archive_sha256,lane,experiment,repository,run_id,artifact_id,source_sha,"
              "frozen_manifest_sha256,original_length,chunk_count) VALUES(?,?,?,?,?,?,?,?,?,?)",
              ("f"*64,"Yggdrasil","Y1","spoonman136668-ai/Wingless",112,223,"b"*40,"c"*64,100,1))
    def test_database_immutability_IS_NOT_claimed_without_triggers(self):
        self.qualify()
        self.db.execute("INSERT INTO forge_research_originals "
          "(archive_sha256,lane,experiment,repository,run_id,artifact_id,source_sha,"
          "frozen_manifest_sha256,original_length,chunk_count) VALUES(?,?,?,?,?,?,?,?,?,?)",
          ("a"*64,"Wingless","W1","spoonman136668-ai/Wingless",111,222,"b"*40,"c"*64,100,1))
        # A privileged database writer still can mutate this schema.
        self.db.execute("UPDATE forge_research_originals SET experiment='W2'")
        self.assertEqual(self.db.execute("SELECT experiment FROM forge_research_originals").fetchone()[0],"W2")
    def test_source_drift_blocked(self):
        with self.assertRaisesRegex(CompatibilityBlocked,"SOURCE_IDENTITY_DRIFT"):
            self.qualify(pin="0"*64)
    def test_foreign_schema_drift_blocked(self):
        self.db.execute("ALTER TABLE existing_unrelated ADD COLUMN z TEXT");self.db.commit()
        with self.assertRaisesRegex(CompatibilityBlocked,"FOREIGN_SCHEMA_IDENTITY_DRIFT"):
            self.qualify()
    def test_collision_blocked_even_for_partial_schema(self):
        self.db.execute("CREATE TABLE forge_research_chunks(x TEXT)");self.db.commit()
        with self.assertRaisesRegex(CompatibilityBlocked,"RESERVED_NAMESPACE_COLLISION"):
            self.qualify()
    def test_file_backed_db_always_blocked(self):
        with tempfile.TemporaryDirectory() as folder:
            other=sqlite3.connect(str(Path(folder)/"data.sqlite"))
            try:
                with self.assertRaisesRegex(CompatibilityBlocked,"IN_MEMORY_ONLY"):
                    offline_qualify(other,self.pin,foreign_schema(other)[0])
            finally:other.close()
    def test_case_and_trigger_ddl_injection_blocked(self):
        with self.assertRaisesRegex(CompatibilityBlocked,"REQUIRE_EXACT_THREE"):
            statements(b"CREATE TABLE foo(x TEXT);")
        with self.assertRaisesRegex(CompatibilityBlocked,"UNSUPPORTED_D1_DDL"):
            statements(PATH.read_bytes().replace(b"chunk_count INTEGER",
                    b"chunk_count DELETE INTEGER"))
    def test_pending_transaction_blocked(self):
        self.db.execute("INSERT INTO existing_unrelated VALUES(2,'new')")
        with self.assertRaisesRegex(CompatibilityBlocked,"OPEN_TRANSACTION"):
            self.qualify()
        self.db.rollback()
if __name__=="__main__":unittest.main()
