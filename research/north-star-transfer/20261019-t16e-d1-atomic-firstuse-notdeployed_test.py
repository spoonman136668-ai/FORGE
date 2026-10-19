"""T16E local SQLite/D1 syntax and anti-replay contract tests, NO remote D1.

These tests prove constraints and local SQLite concurrent INSERT handling.
They do NOT prove remote Cloudflare D1 deployment, separate signers, valid
signatures, immutable admin custody, or globally witnessed first use.
"""
import concurrent.futures
import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path

SQL=Path(__file__).with_name("20261019-t16e-d1-atomic-firstuse-notdeployed.sql")
ZERO="0"*64

def h(s):return hashlib.sha256(s.encode("utf-8")).hexdigest()
def insert_params(lane="MassResearch",ident="trial-001",seq=1,prior=ZERO):
 return (lane,ident,seq,"a"*40,h("source"),h("prereg"),h("cohort"),
  h("birth"),h("issuer"),h("witness"),prior,h("receipt-"+lane+"-"+str(seq)))
def put(con,args):
 con.execute("INSERT INTO t16e_source_firstuse VALUES ("+",".join(["?"]*12)+")",args)
 con.commit()
def opened(path):
 conn=sqlite3.connect(str(path),timeout=10)
 conn.execute("PRAGMA busy_timeout=10000")
 return conn

class FirstUseCASContract(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix="t16e-sourceonly-")
  self.db=Path(self.temp.name)/"proof.sqlite"
  conn=opened(self.db)
  conn.executescript(SQL.read_text(encoding="utf-8"))
  conn.close()
 def tearDown(self):
  self.temp.cleanup()
 def test_monotone_append_receipt_chain(self):
  with opened(self.db) as con:
   first=insert_params()
   put(con,first)
   put(con,insert_params(ident="trial-002",seq=2,prior=first[-1]))
   rows=con.execute("SELECT original_id,sequence FROM t16e_source_firstuse ORDER BY sequence").fetchall()
   self.assertEqual(rows,[("trial-001",1),("trial-002",2)])
 def test_duplicate_source_firstuse_rejected(self):
  with opened(self.db) as con:
   first=insert_params();put(con,first)
   with self.assertRaises(sqlite3.IntegrityError):put(con,first)
 def test_sequence_replay_and_gap_denied(self):
  with opened(self.db) as con:
   put(con,insert_params())
   for seq in (1,3,0):
    with self.assertRaises(sqlite3.IntegrityError):
     put(con,insert_params(ident="different-"+str(seq),seq=seq,prior=h("receipt-MassResearch-1")))
   self.assertEqual(con.execute("SELECT COUNT(*) FROM t16e_source_firstuse").fetchone()[0],1)
 def test_prior_receipt_mutation_denied(self):
  with opened(self.db) as con:
   put(con,insert_params())
   with self.assertRaisesRegex(sqlite3.IntegrityError,"HISTORY_DRIFT"):
    put(con,insert_params(ident="trial-002",seq=2,prior=h("wrong-prior")))
 def test_append_only_update_delete_denied(self):
  with opened(self.db) as con:
   put(con,insert_params())
   with self.assertRaisesRegex(sqlite3.IntegrityError,"APPEND_ONLY"):
    con.execute("DELETE FROM t16e_source_firstuse")
   with self.assertRaisesRegex(sqlite3.IntegrityError,"APPEND_ONLY"):
    con.execute("UPDATE t16e_source_firstuse SET receipt_sha256=?",(h("fake"),))
 def test_cross_lane_independent_claim_heads(self):
  with opened(self.db) as con:
   for lane in ("Wingless","Yggdrasil","MassResearch"):
    put(con,insert_params(lane=lane,ident="distinct",seq=1))
   self.assertEqual(con.execute("SELECT COUNT(*) FROM t16e_source_firstuse").fetchone()[0],3)
 def test_unknown_lane_is_not_autoadmitted(self):
  with opened(self.db) as con:
   with self.assertRaises(sqlite3.IntegrityError):
    put(con,insert_params(lane="CKB"))
 def test_same_issuer_and_witness_key_blocked(self):
  with opened(self.db) as con:
   p=list(insert_params())
   p[9]=p[8]
   with self.assertRaises(sqlite3.IntegrityError):put(con,p)
 def test_wrong_length_hash_fails_closed(self):
  with opened(self.db) as con:
   p=list(insert_params());p[4]="bad"
   with self.assertRaises(sqlite3.IntegrityError):put(con,p)
 def test_racing_firstuse_exactly_one_commits(self):
  params=insert_params()
  def attempt(i):
   con=opened(self.db)
   try:
    put(con,params)
    return True
   except sqlite3.DatabaseError:
    return False
   finally:con.close()
  with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
   results=list(pool.map(attempt,range(16)))
  self.assertEqual(results.count(True),1)
  with opened(self.db) as con:
   row=con.execute("SELECT COUNT(*),MAX(sequence) FROM t16e_source_firstuse").fetchone()
  self.assertEqual(row,(1,1))
 def test_chain_tampering_cannot_skip_high_water(self):
  with opened(self.db) as con:
   first=insert_params()
   put(con,first)
   with self.assertRaises(sqlite3.IntegrityError):
    put(con,insert_params(ident="trial-003",seq=3,prior=first[-1]))
   put(con,insert_params(ident="trial-002",seq=2,prior=first[-1]))
   self.assertEqual(con.execute("SELECT MAX(sequence) FROM t16e_source_firstuse").fetchone()[0],2)

if __name__=="__main__":unittest.main()
