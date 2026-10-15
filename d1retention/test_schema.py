"""Offline SQLite acceptance of the proposed existing-D1 append-only archive.
No Cloudflare calls, original execution, credentials or live migrations.
A seal is a self-declared metadata claim: not a scientific/FSA acceptance.
"""
import hashlib
import pathlib
import sqlite3
import unittest

SCHEMA = pathlib.Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
def digest(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

class D1RetentionTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(SCHEMA)

    def tearDown(self):
        self.db.close()

    def store(self, lane="Wingless", experiment="W-ARCH-001", payload=b"authenticity-NOT-asserted-fixture", chunks=2):
        sha = digest(payload)
        repo = "spoonman136668-ai/" + lane
        self.db.execute(
            "INSERT INTO forge_research_originals "
            "(archive_sha256,lane,experiment,repository,run_id,artifact_id,"
            "source_sha,frozen_manifest_sha256,original_length,chunk_count) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (sha,lane,experiment,repo,111 if lane=="Wingless" else 222,
             333 if lane=="Wingless" else 444,"a"*40,"b"*64,len(payload),chunks))
        return sha

    def fill(self, sha, payload, chunks=2):
        stride = (len(payload)+chunks-1)//chunks
        for i in range(chunks):
            b = payload[i*stride:(i+1)*stride]
            if not b:
                raise AssertionError("zero-length fixture chunk")
            self.db.execute("INSERT INTO forge_research_chunks "
                "(archive_sha256,chunk_index,chunk_sha256,chunk_bytes) VALUES (?,?,?,?)",
                (sha,i,digest(b),b))

    def seal(self, sha, n):
        return self.db.execute(
            "INSERT INTO forge_research_seals "
            "(archive_sha256,declared_restored_sha256,declared_restored_length,seal_receipt_sha256) "
            "VALUES (?,?,?,?)", (sha,sha,n,"c"*64))

    def assert_rejected(self, fn):
        with self.assertRaises(sqlite3.IntegrityError):
            fn()

    def test_idempotent_install_on_empty_database(self):
        first = list(self.db.execute("SELECT type,name,sql FROM sqlite_master WHERE name LIKE 'forge_research_%' ORDER BY type,name"))
        self.db.executescript(SCHEMA)
        second = list(self.db.execute("SELECT type,name,sql FROM sqlite_master WHERE name LIKE 'forge_research_%' ORDER BY type,name"))
        self.assertEqual(first,second)
        self.assertEqual(len([r for r in first if r[0]=="table"]),3)
        self.assertEqual(len([r for r in first if r[0]=="trigger"]),8)

    def test_incomplete_and_mismatched_seal_rejected(self):
        payload=b"fixture-original-zip-bytes" * 10
        sha=self.store(payload=payload)
        self.assert_rejected(lambda:self.seal(sha,len(payload)))
        self.fill(sha,payload)
        self.assert_rejected(lambda:self.seal(sha,len(payload)-1))
        self.seal(sha,len(payload))
        self.assertEqual(self.db.execute("SELECT scientific_state FROM forge_research_originals").fetchone()[0],"UNQUALIFIED")

    def test_all_history_immutable(self):
        payload=b"some-archive-bytes"
        sha=self.store(payload=payload)
        self.fill(sha,payload)
        self.seal(sha,len(payload))
        for sql in (
            "UPDATE forge_research_originals SET experiment='tamper'",
            "DELETE FROM forge_research_originals",
            "UPDATE forge_research_chunks SET chunk_bytes=x'00'",
            "DELETE FROM forge_research_chunks",
            "UPDATE forge_research_seals SET seal_receipt_sha256='"+("d"*64)+"'",
            "DELETE FROM forge_research_seals",
        ):
            self.assert_rejected(lambda sql=sql:self.db.execute(sql))
        self.assert_rejected(lambda:self.fill(sha,payload))

    def test_distinct_lanes_and_identity_drift(self):
        w=self.store(payload=b"wingless")
        y=self.store(lane="Yggdrasil",experiment="Y-ARCH-001",payload=b"yggdrasil")
        self.assertNotEqual(w,y)
        self.assert_rejected(lambda:self.store(payload=b"other-original",experiment="W-ARCH-001"))
        self.assert_rejected(lambda:self.db.execute(
            "INSERT INTO forge_research_originals "
            "(archive_sha256,lane,experiment,repository,run_id,artifact_id,source_sha,"
            "frozen_manifest_sha256,original_length,chunk_count) VALUES (?,?,?,?,?,?,?,?,?,?)",
            ("e"*64,"Wingless","W-FOREIGN","spoonman136668-ai/Yggdrasil",
             100,200,"a"*40,"b"*64,4,1)))
        self.assert_rejected(lambda:self.db.execute("INSERT INTO forge_research_chunks "
            "(archive_sha256,chunk_index,chunk_sha256,chunk_bytes) VALUES (?,?,?,?)",
            (w,3,"d"*64,b"invalid-range")))
        self.assert_rejected(lambda:self.db.execute("INSERT INTO forge_research_chunks "
            "(archive_sha256,chunk_index,chunk_sha256,chunk_bytes) VALUES (?,?,?,?)",
            ("f"*64,0,"d"*64,b"orphan")))

    def test_schema_never_confers_causal_or_original_authority(self):
        self.assertNotIn("scientific_accepted",SCHEMA)
        self.assertNotIn("dispatch_authorized",SCHEMA)
        self.assertNotIn("accepted_ref_mutation",SCHEMA)
        self.assertIn("'UNQUALIFIED'",SCHEMA)

if __name__=="__main__":
    unittest.main()
