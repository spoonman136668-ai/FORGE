"""Offline negative acceptance for D1 preflight. No real Cloudflare writes."""
import hashlib, sqlite3, tempfile, unittest
from pathlib import Path
from migration import preview,foreign_schema,SCHEMA_PATH,MigrationBlocked

PIN=hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest()
class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE unrelated_user_table (k INTEGER PRIMARY KEY,v TEXT NOT NULL)")
        self.db.execute("INSERT INTO unrelated_user_table(v) VALUES ('unchanged')")
        self.db.commit()
        self.original=foreign_schema(self.db)[0]
    def tearDown(self): self.db.close()
    def preflight(self,**kwargs):
        return preview(self.db,source_sha256=kwargs.get("source",PIN),
                       foreign_sha256=kwargs.get("foreign",self.original))
    def test_additive_retains_foreign_data(self):
        v=self.preflight()
        self.assertEqual((v.archive_tables,v.archive_triggers),(3,8))
        self.assertTrue(v.existing_objects_preserved)
        self.assertFalse(v.live_migration_performed or v.research_authorized)
        self.assertEqual(foreign_schema(self.db)[0],self.original)
        self.assertEqual(self.db.execute("SELECT v FROM unrelated_user_table").fetchone()[0],"unchanged")
    def test_collision_is_not_silently_skipped(self):
        self.db.execute("CREATE TABLE forge_research_chunks (junk TEXT)")
        self.db.commit()
        with self.assertRaisesRegex(MigrationBlocked,"COLLISION"): self.preflight()
        self.assertFalse(self.db.execute(
            "SELECT name FROM sqlite_master WHERE name='forge_research_originals'").fetchall())
    def test_collision_with_custom_trigger(self):
        self.db.execute("CREATE TRIGGER forge_research_not_ours BEFORE UPDATE "
                        "ON unrelated_user_table BEGIN SELECT 1; END")
        self.db.commit()
        with self.assertRaisesRegex(MigrationBlocked,"COLLISION"): self.preflight()
    def test_schema_pin_drift(self):
        with self.assertRaisesRegex(MigrationBlocked,"SOURCE_PIN"): self.preflight(source="0"*64)
    def test_foreign_schema_drift(self):
        self.db.execute("ALTER TABLE unrelated_user_table ADD COLUMN extra TEXT")
        self.db.commit()
        with self.assertRaisesRegex(MigrationBlocked,"SCHEMA_PIN"): self.preflight()
    def test_duplicate_installer_refused(self):
        self.preflight()
        with self.assertRaisesRegex(MigrationBlocked,"COLLISION"): self.preflight()
    def test_no_file_backed_connections(self):
        with tempfile.TemporaryDirectory() as folder:
            other=sqlite3.connect(str(Path(folder)/"real.sqlite"))
            try:
                with self.assertRaisesRegex(MigrationBlocked,"MEMORY_ONLY"):
                    preview(other,source_sha256=PIN,foreign_sha256=foreign_schema(other)[0])
            finally:other.close()
    def test_no_active_transaction(self):
        self.db.execute("INSERT INTO unrelated_user_table(v) VALUES ('new')")
        with self.assertRaisesRegex(MigrationBlocked,"OPEN_TRANSACTION"):self.preflight()
        self.db.rollback()
    def test_sqlite_transaction_rolls_back_invalid_partial_ddl(self):
        broken=SCHEMA_PATH.read_text().replace(
            "CREATE TABLE IF NOT EXISTS forge_research_chunks (",
            "CREATE TABLE IF NOT EXISTS forge_research_chunks ( invalid !!! ",1)
        try:
            self.db.executescript("BEGIN IMMEDIATE;\n"+broken+"\nCOMMIT;")
        except sqlite3.Error: self.db.rollback()
        else: self.fail("broken DDL unexpectedly accepted")
        self.assertFalse(self.db.execute(
            "SELECT name FROM sqlite_master WHERE name LIKE 'forge_research_%'").fetchall())
        self.assertEqual(self.db.execute("SELECT v FROM unrelated_user_table").fetchone()[0],"unchanged")
if __name__=="__main__":unittest.main()
