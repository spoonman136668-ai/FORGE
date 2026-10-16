import pathlib,sqlite3,unittest
SQL=pathlib.Path(__file__).with_name("cloudflare_atomic_candidate.sql")
class NativeAtomicClaim(unittest.TestCase):
 def setUp(self):
  self.db=sqlite3.connect(":memory:")
  self.db.executescript(SQL.read_text())
 def tearDown(self):self.db.close()
 def claim(self,k,l,e,s):
  self.db.execute("INSERT INTO forge_original_preuse_claims (original_key_sha256,lane,owner_epoch,source_commit_sha,frozen_predecision_sha256,external_owner_witness_pin_sha256,claimed_sequence) VALUES (?,?,?,?,?,?,?)",(k*64,l,e,"d"*40,"e"*64,"f"*64,s))
 def test_once_only_and_no_scientific_authority(self):
  self.claim("a","Wingless",2,7)
  self.assertEqual(self.db.execute("SELECT scientific_authorized FROM forge_original_preuse_claims").fetchone(),(0,))
  for args in (("a","Wingless",2,8),("b","Yggdrasil",2,7),("b","Yggdrasil",1,8),("b","Yggdrasil",3,6)):
   with self.assertRaises(sqlite3.IntegrityError):self.claim(*args)
  self.claim("b","Yggdrasil",3,8)
  with self.assertRaises(sqlite3.IntegrityError):self.db.execute("DELETE FROM forge_original_preuse_claims")
  with self.assertRaises(sqlite3.IntegrityError):self.db.execute("UPDATE forge_original_preuse_claims SET scientific_authorized=1")
 def test_only_one_concurrent_writer(self):
  import tempfile
  with tempfile.TemporaryDirectory() as folder:
   path=pathlib.Path(folder)/"once.db"
   a=sqlite3.connect(path,timeout=0);a.executescript(SQL.read_text())
   b=sqlite3.connect(path,timeout=0);a.execute("BEGIN IMMEDIATE")
   a.execute("INSERT INTO forge_original_preuse_claims (original_key_sha256,lane,owner_epoch,source_commit_sha,frozen_predecision_sha256,external_owner_witness_pin_sha256,claimed_sequence) VALUES (?,?,?,?,?,?,?)",("a"*64,"Wingless",2,"d"*40,"e"*64,"f"*64,1))
   with self.assertRaises(sqlite3.OperationalError):b.execute("BEGIN IMMEDIATE")
   a.commit();b.close();a.close()
   with sqlite3.connect(path) as c:
    with self.assertRaises(sqlite3.IntegrityError):
     c.execute("INSERT INTO forge_original_preuse_claims (original_key_sha256,lane,owner_epoch,source_commit_sha,frozen_predecision_sha256,external_owner_witness_pin_sha256,claimed_sequence) VALUES (?,?,?,?,?,?,?)",("a"*64,"Wingless",2,"d"*40,"e"*64,"f"*64,1))
