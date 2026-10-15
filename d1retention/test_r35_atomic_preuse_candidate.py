"""R35: candidate schema local atomicity qualification. No Cloudflare writes.

SQLite uniqueness proves at-most-once for a single shared D1 database; it
does not prove a physically independent witness, signed current owner,
distributed authorization, or atomic worker dispatch.
"""
import concurrent.futures
import pathlib
import sqlite3
import tempfile
import unittest

SQL=pathlib.Path(__file__).with_name("r35_atomic_preuse_candidate.sql")
SCHEMA_NAMES={"forge_original_preuse_claims","forge_original_preuse_claims_update_immutable","forge_original_preuse_claims_delete_immutable"}
def connect(path):
    db=sqlite3.connect(str(path), timeout=8, isolation_level=None)
    db.execute("PRAGMA busy_timeout=8000")
    return db

def candidate(db, key="a"*64, seq=1, owner_epoch=3):
    db.execute("INSERT INTO forge_original_preuse_claims (original_key_sha256,lane,owner_epoch,source_commit_sha,frozen_predecision_sha256,external_owner_witness_pin_sha256,claimed_sequence) VALUES (?,?,?,?,?,?,?)",
               (key,"Wingless",owner_epoch,"b"*40,"c"*64,"d"*64,seq))

class R35(unittest.TestCase):
 def setUp(self):
    self.tmp=tempfile.TemporaryDirectory()
    self.path=pathlib.Path(self.tmp.name)/"existing-db-simulation.db"
    with connect(self.path) as db:
        db.execute("CREATE TABLE unrelated_preexisting_table (id INTEGER PRIMARY KEY, value TEXT)")
        db.execute("INSERT INTO unrelated_preexisting_table VALUES (1,'untouched')")
        db.executescript(SQL.read_text())
 def tearDown(self):
    self.tmp.cleanup()
 def test_write_once_and_identity_binding(self):
    with connect(self.path) as db:
        candidate(db)
        with self.assertRaises(sqlite3.IntegrityError):candidate(db)
        with self.assertRaises(sqlite3.IntegrityError):candidate(db,"e"*64,1)
        with self.assertRaises(sqlite3.DatabaseError):
            db.execute("UPDATE forge_original_preuse_claims SET owner_epoch=5")
        with self.assertRaises(sqlite3.DatabaseError):
            db.execute("DELETE FROM forge_original_preuse_claims")
        r=db.execute("SELECT COUNT(*),MIN(scientific_authorized) FROM forge_original_preuse_claims").fetchone()
        self.assertEqual(r,(1,0))
        self.assertEqual(db.execute("SELECT value FROM unrelated_preexisting_table").fetchone(),("untouched",))
 def test_atomic_concurrent_claim_only_one_wins(self):
    def run(i):
        try:
            with connect(self.path) as db:candidate(db)
            return True
        except sqlite3.IntegrityError:return False
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        attempts=list(pool.map(run,range(32)))
    self.assertEqual(sum(attempts),1)
    with connect(self.path) as db:
        self.assertEqual(db.execute("SELECT COUNT(*) FROM forge_original_preuse_claims").fetchone()[0],1)
 def test_distinct_origins_unique_sequence_and_no_authorized_mutation(self):
    with connect(self.path) as db:
        candidate(db)
        candidate(db,"e"*64,2)
        with self.assertRaises(sqlite3.IntegrityError):
            candidate(db,"f"*64,3,0)
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("INSERT INTO forge_original_preuse_claims VALUES (?,?,?,?,?,?,?,1,CURRENT_TIMESTAMP)",("f"*64,"Wingless",3,"b"*40,"c"*64,"d"*64,3))
        self.assertEqual(db.execute("SELECT COUNT(*) FROM forge_original_preuse_claims").fetchone()[0],2)
 def test_schema_only_is_not_independent_signer(self):
    with connect(self.path) as db:
        x={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")}
        self.assertTrue(SCHEMA_NAMES.issubset(x))
        self.assertEqual(db.execute("SELECT COUNT(*) FROM forge_original_preuse_claims").fetchone()[0],0)
if __name__=="__main__":unittest.main()
