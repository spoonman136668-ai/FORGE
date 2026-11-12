"""Fail-closed one-shot R18 D1 operator path; all network calls mocked."""
import hashlib
import pathlib
import tempfile
import unittest
from unittest.mock import patch
import install_remote as m

class FakeCloudflare:
    account="a"*32
    id="b"*8+"-"+("b"*4+"-")*3+"b"*12
    version="c"*8+"-"+("c"*4+"-")*3+"c"*12
    def __init__(self,*,wrong=False,collision=False,missing_bookmark=False,fail_write=False):
        self.wrong=wrong
        self.collision=collision
        self.missing_bookmark=missing_bookmark
        self.fail_write=fail_write
        self.writes=0
        self.rows=[{"type":"table","name":"user_data","tbl_name":"user_data","sql":"CREATE TABLE user_data(k TEXT)"}]
    def call(self,path,method="GET",data=None):
        if path.endswith("/deployments"):
            return {"deployments":[{"versions":[{"version_id":self.version,"percentage":100}]}]}
        if "/versions/" in path:
            return {"resources":{"bindings":[{"type":"d1",
                "name":"froge" if self.wrong else "forge","database_id":self.id}]}}
        if "/time_travel/bookmark" in path:
            return {} if self.missing_bookmark else {"bookmark":"00000001-00000002-00004e2f-0a83ea2fceebc654de0640c422be4653"}
        if path.endswith("/d1/database?per_page=10&page=1"):
            return [{"uuid":self.id}]
        if path.endswith("/d1/database/"+self.id) and method=="GET":
            return {"uuid":self.id,"version":"production"}
        if path.endswith("/query") and method=="POST":
            if "sql" in data:
                rows=self.rows.copy()
                if self.collision:
                    rows.append({"type":"table","name":"forge_research_partial",
                                 "tbl_name":"forge_research_partial","sql":"CREATE TABLE forge_research_partial(k TEXT)"})
                return [{"success":True,"meta":{"changes":0},"results":rows}]
            self.writes+=1
            if self.fail_write: raise m.InstallBlocked("SIMULATED_REMOTE_FAILURE")
            return [{"success":True} for _ in data["batch"]]
        raise AssertionError("unrecognized API "+path)

class R18Tests(unittest.TestCase):
    def test_real_schema_splits_triggers_as_single_statements(self):
        statements=m.split_sql(m.SQL_PATH.read_bytes())
        self.assertEqual(len(statements),11)
        self.assertTrue(statements[-1].strip().endswith("END;"))
        self.assertTrue(all(x.upper().count("CREATE TRIGGER")<=1 for x in statements))
    def test_missing_statement_blocks(self):
        with self.assertRaises(m.InstallBlocked):
            m.split_sql(b"CREATE TABLE foo (id INT)")
    def test_pin_checks_require_exact_checkout_and_sql(self):
        with patch("install_remote.subprocess.check_output",return_value="a"*40+"\n"):
            actual=m.sha(m.SQL_PATH.read_bytes())
            self.assertEqual(m.check_pins("a"*40,actual),m.SQL_PATH.read_bytes())
            with self.assertRaisesRegex(m.InstallBlocked,"HEAD_DRIFT"):
                m.check_pins("b"*40,actual)
            with self.assertRaisesRegex(m.InstallBlocked,"SQL_CONTENT_DRIFT"):
                m.check_pins("a"*40,"0"*64)
    def test_preflight_with_real_metadata_never_writes(self):
        api=FakeCloudflare()
        self.assertEqual(m.single_deployed_database(api),api.id)
        self.assertEqual(m.schema_snapshot(api,api.id)[0],set())
        self.assertTrue(m.recovery_bookmark(api,api.id))
        self.assertEqual(api.writes,0)
    def test_wrong_binding_blocks(self):
        with self.assertRaisesRegex(m.InstallBlocked,"BINDING_MISSING"):
            m.single_deployed_database(FakeCloudflare(wrong=True))
    def test_existing_reserved_collision_rejected(self):
        api=FakeCloudflare(collision=True)
        self.assertTrue(m.schema_snapshot(api,api.id)[0])
    def test_absent_time_travel_block(self):
        api=FakeCloudflare(missing_bookmark=True)
        with self.assertRaisesRegex(m.InstallBlocked,"BOOKMARK_NOT_QUALIFIED"):
            m.recovery_bookmark(api,api.id)
    def test_apply_requires_private_nonexisting_recovery_path(self):
        api=FakeCloudflare()
        bookmark=m.recovery_bookmark(api,api.id)
        with tempfile.TemporaryDirectory() as folder:
            p=str(pathlib.Path(folder)/"recovery-private.json")
            m.apply_once(api,api.id,m.split_sql(m.SQL_PATH.read_bytes()),
                         recovery_file=p,bookmark=bookmark,
                         schema_sha="a"*64,foreign_sha="b"*64)
            self.assertEqual(api.writes,1)
            self.assertIn(bookmark,pathlib.Path(p).read_text())
            with self.assertRaises(FileExistsError):
                m.apply_once(api,api.id,m.split_sql(m.SQL_PATH.read_bytes()),
                             recovery_file=p,bookmark=bookmark,
                             schema_sha="a"*64,foreign_sha="b"*64)
            self.assertEqual(api.writes,1)
    def test_remote_failure_never_deletes_recovery_bookmark(self):
        api=FakeCloudflare(fail_write=True)
        with tempfile.TemporaryDirectory() as folder:
            p=pathlib.Path(folder)/"private.json"
            with self.assertRaisesRegex(m.InstallBlocked,"SIMULATED_REMOTE_FAILURE"):
                m.apply_once(api,api.id,m.split_sql(m.SQL_PATH.read_bytes()),
                    recovery_file=str(p),bookmark=m.recovery_bookmark(api,api.id),
                    schema_sha="a"*64,foreign_sha="b"*64)
            self.assertTrue(p.exists())
            self.assertEqual(api.writes,1)
    def test_guard_rejects_sql_not_select(self):
        with self.assertRaisesRegex(m.InstallBlocked,"READ_ONLY_SQL_EXPECTED"):
            m.sql_query(FakeCloudflare(),FakeCloudflare.id,"DELETE FROM sqlite_master")
if __name__=="__main__":
    unittest.main()
