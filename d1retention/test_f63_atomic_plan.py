"""F63: exercise the actual portable Worker INSERT against the R35/R38 SQLite schema.

Production Cloudflare is deliberately never contacted. A failed/uncertain
INSERT leaves the first-use attempt consumed when committed, never retried.
"""
import concurrent.futures
import json
import pathlib
import sqlite3
import subprocess
import tempfile
import unittest

HERE=pathlib.Path(__file__).resolve().parent
R35=(HERE/"r35_atomic_preuse_candidate.sql").read_text()
R38=(HERE/"r38_monotonic_preuse_candidate.sql").read_text()
PLANNER=HERE/"f63_reservation_plan.mjs"

def claim(i=1,seq=53,epoch=8):
    return {
      "original_key_sha256":f"{i:064x}","lane":"Wingless",
      "owner_epoch":epoch,"source_commit_sha":"b"*40,
      "frozen_predecision_sha256":"c"*64,
      "external_owner_witness_pin_sha256":"d"*64,
      "claimed_sequence":seq,"scientific_authorized":False
    }

def js_plan(payload):
    script="""import {planSingleReservation} from './f63_reservation_plan.mjs';
const c=JSON.parse(process.argv[1]);
const {scientific_authorized,...p}=c;
process.stdout.write(JSON.stringify(planSingleReservation(c,p)));"""
    process=subprocess.run(["node","--input-type=module","--eval",script,
        json.dumps(payload,separators=(",",":"))],
        text=True,cwd=HERE,capture_output=True,timeout=10,check=True)
    return json.loads(process.stdout)

class F63ActualAtomicSQLite(unittest.TestCase):
    def setUp(self):
        self.root=tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.path=pathlib.Path(self.root.name)/"isolated-d1.db"
        with self.connection() as db:
            db.executescript("CREATE TABLE forge_research_originals(id INTEGER PRIMARY KEY,val TEXT);"
                             "INSERT INTO forge_research_originals VALUES(1,'untouched');")
            db.executescript(R35)
            db.executescript(R38)
    def connection(self):
        db=sqlite3.connect(self.path,timeout=15,isolation_level=None)
        db.execute("PRAGMA busy_timeout=15000")
        return db
    def execute(self,p):
        db=self.connection()
        try:
            with db: db.execute(p["sql"],p["values"])
            return True
        except sqlite3.DatabaseError:
            return False
        finally:
            db.close()
    def test_single_atomic_candidate_no_retry_even_after_crash(self):
        p=js_plan(claim())
        self.assertEqual(p["cloudflare_mutation_performed"],False)
        self.assertEqual(p["worker_permit_issued"],False)
        self.assertTrue(self.execute(p))
        # Pretend the caller missed the first D1 acknowledgment: replay is
        # forbidden by real immutable unique index, regardless of response.
        self.assertFalse(self.execute(p))
        with self.connection() as db:
            self.assertEqual(db.execute(
                "SELECT COUNT(*),MIN(scientific_authorized) FROM forge_original_preuse_claims"
            ).fetchone(),(1,0))
            self.assertEqual(db.execute(
                "SELECT val FROM forge_research_originals").fetchone(),("untouched",))
    def test_concurrent_same_original_only_one_can_commit(self):
        p=js_plan(claim(8))
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            outcome=list(pool.map(lambda _:self.execute(p),range(32)))
        self.assertEqual(sum(outcome),1)
    def test_new_claims_require_strict_monotonic_sequence_and_epoch(self):
        self.assertTrue(self.execute(js_plan(claim(1,53,8))))
        self.assertFalse(self.execute(js_plan(claim(2,52,9))))
        self.assertFalse(self.execute(js_plan(claim(3,54,7))))
        self.assertTrue(self.execute(js_plan(claim(4,54,9))))
        with self.connection() as db:
            self.assertEqual(db.execute(
                "SELECT claimed_sequence,owner_epoch FROM forge_original_preuse_claims "
                "ORDER BY claimed_sequence").fetchall(),[(53,8),(54,9)])

if __name__=="__main__":
    unittest.main()
