"""Synthetic SQLite source-only V59 cold-bundle controls; not host acceptance."""
from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from f139 import nci04_v59_cold_backup_stage as v

class FakeDB:
    def __init__(self, filename, conn):
        self.filename=filename
        self.conn=conn
        self._readonly_opened=True
    def verify(self):
        return None

class V59ColdStageTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.owner=Path(t.name)/"FORGE-F139"
        self.owner.mkdir()
        self.path=self.owner/"state.sqlite"
        with closing(sqlite3.connect(self.path)) as conn:
            conn.execute("CREATE TABLE sample(id INTEGER PRIMARY KEY, value TEXT)")
            conn.execute("INSERT INTO sample VALUES(1,'native sqlite')")
            conn.commit()
        con=sqlite3.connect(self.path.as_uri()+"?mode=ro",
                            uri=True,isolation_level=None)
        self.addCleanup(con.close)
        con.execute("PRAGMA query_only=ON")
        self.db=FakeDB(self.path,con)
        self.run=v.MIN_RUN+100
        self.target="f"*40
        self.original_bytes=self.path.read_bytes()
        self.preimage={"source_sha":v.SOURCE, "head_seq":v.HEAD_SEQ,
                       "head_sha256":v.HEAD_SHA256}
        for p in (patch.object(v,"Database",FakeDB),
                  patch.object(v.SingleOwner,"held",return_value=True),
                  patch.object(v,"audit_frozen_original_readonly",
                               return_value=self.preimage)):
            p.start()
            self.addCleanup(p.stop)
    def go(self, **kw):
        return v.stage_original_cold_backup(
            self.db,**dict(target=self.target,owner_run_id=self.run,**kw))
    def test_prewrite_bad_target_and_run(self):
        for target,run in ((v.SOURCE,self.run),("bad",self.run),
                           (self.target,v.MIN_RUN),(self.target,True)):
            with self.subTest(target=target,run=run):
                with self.assertRaises(v.V59ColdStageDenied):
                    v.stage_original_cold_backup(self.db,target=target,
                                                 owner_run_id=run)
        self.assertEqual(self.path.read_bytes(),self.original_bytes)
    def test_prewrite_lock_and_source_fences(self):
        self.db._readonly_opened=False
        with self.assertRaisesRegex(v.V59ColdStageDenied,"READONLY"):
            self.go()
        self.db._readonly_opened=True
        with patch.object(v.SingleOwner,"held",return_value=False):
            with self.assertRaisesRegex(v.V59ColdStageDenied,"MUTEX"):
                self.go()
        with patch.object(v,"audit_frozen_original_readonly",
                          side_effect=ValueError("FROZEN_MISMATCH")):
            with self.assertRaisesRegex(ValueError,"FROZEN_MISMATCH"):
                self.go()
        self.assertFalse((self.owner/("f139-v59-before-"+str(self.run))).exists())
    def test_create_only_partial_cannot_overwrite(self):
        folder=self.owner/("f139-v59-before-"+str(self.run))
        folder.mkdir()
        (folder/"failed").write_bytes(b"keep")
        with self.assertRaisesRegex(v.V59ColdStageDenied,"EXISTING_RUN"):
            self.go()
        self.assertEqual((folder/"failed").read_bytes(),b"keep")
    def test_native_sqlite_copy_control_with_mocked_adjuncts(self):
        folder=self.owner/("f139-v59-before-"+str(self.run))
        def add(name):
            p=folder.joinpath(*name.split("/"))
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes(b"copy evidence")
            return hashlib.sha256(p.read_bytes()).hexdigest()
        def negative(src,dst,expected,*,copy_files):
            self.assertTrue(copy_files)
            return {"native-negative/a.zip":add("native-negative/a.zip")}
        def archives(db,dst,*,copy_files):
            return {"provider-custody/a.zip":add("provider-custody/a.zip")}
        def binary(db,dst,*,copy_files):
            return {"prior-generation-custody/a.exe":
                    add("prior-generation-custody/a.exe")}
        def verify(db,backup,*,owner_run_id,target,expected_backup_sha256):
            with closing(sqlite3.connect(backup)) as conn:
                self.assertEqual(conn.execute("SELECT value FROM sample").fetchone()[0],
                                 "native sqlite")
            return dict(from_source_sha=v.SOURCE,to_source_sha=target,
                        original_head_seq=v.HEAD_SEQ,
                        original_head_sha256=v.HEAD_SHA256,
                        backup_sqlite_sha256=expected_backup_sha256,
                        original_owner_mutations=0,
                        source_transition_authorized=False,
                        scientific_first_use=False,
                        logical_all_tables_sha256="1"*64,
                        negative_custody_sha256="2"*64,
                        provider_archives_sha256="3"*64,
                        genenv_executable_custody_sha256="4"*64)
        with patch.object(v.cold,"required_negative_custody",return_value={}), \
             patch.object(v.cold,"copy_negative_custody",side_effect=negative), \
             patch.object(v,"copy_provider_archives",side_effect=archives), \
             patch.object(v,"copy_generation_executable",side_effect=binary), \
             patch.object(v,"verify_original_cold_backup",side_effect=verify):
            result=self.go()
        self.assertEqual(result["file_count"],4)
        self.assertFalse(result["source_transition_authorized"])
        self.assertFalse(result["owner_quiescence_verified"])
        self.assertEqual(self.path.read_bytes(),self.original_bytes)
        manifest=(folder/"manifest.sha256.json").read_bytes()
        self.assertEqual(hashlib.sha256(manifest).hexdigest(),result["manifest_sha256"])
        with self.assertRaisesRegex(v.V59ColdStageDenied,"EXISTING_RUN"):
            self.go()
    def test_source_has_no_live_execution_surface(self):
        source=Path(v.__file__).read_text()
        for term in ("Stop-ScheduledTask","Register-ScheduledTask",
                     "Start-ScheduledTask","gh api","subprocess.",
                     "db.event(", "UPDATE meta SET","OPENAI_API_KEY"):
            self.assertNotIn(term,source)

if __name__=="__main__":
    unittest.main()
