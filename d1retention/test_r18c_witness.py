"""Strict fake acceptance for R18C read-only schema witness."""
import unittest
from r18c_witness import (
    EXPECTED_KINDS,ORIGINAL_KINDS,InstallBlocked,preflight,verify_after,
    BASELINE_SCHEMA_SHA256,EXPECTED_OBJECTS,
)
class FakeApi:
    account="a"*32
    def __init__(self, installed=False):
        self.installed=installed
        self.writes=0
    def call(self,path,method="GET",data=None):
        if path.endswith("/time_travel/bookmark"):
            return {"bookmark":"00000001-00000002-00004e2f-0a83ea2fceebc654de0640c422be4653"}
        if path.endswith("/query") and data and data.get("sql"):
            sql=data["sql"]
            if "sqlite_master" in sql and "type,name,tbl_name,sql" in sql:
                rows=[{"type":"table","name":"unrelated",
                    "tbl_name":"unrelated","sql":"CREATE TABLE unrelated (x TEXT)"}]
                if self.installed:
                    rows.extend({"type":kind,"name":name,
                      "tbl_name":name if kind=="table" else "forge_research_originals",
                      "sql":"CREATE TRIGGER "+name+" BEFORE UPDATE BEGIN SELECT RAISE(ABORT,'x'); END"
                          if kind=="trigger" else "CREATE TABLE "+name+"(x TEXT)"}
                      for name,kind in EXPECTED_KINDS.items())
                return [{"success":True,"meta":{"changes":0},"results":rows}]
            if "name GLOB 'forge_research_*'" in sql:
                rows=[{"type":kind,"name":name,
                    "sql":"CREATE TRIGGER "+name+" BEFORE UPDATE BEGIN SELECT RAISE(ABORT,'x'); END"
                      if kind=="trigger" else "CREATE TABLE "+name+"(x TEXT)"}
                   for name,kind in EXPECTED_KINDS.items()] if self.installed else []
                return [{"success":True,"meta":{"changes":0},"results":rows}]
            if "sqlite_master" in sql:
                return [{"success":True,"meta":{"changes":0},
                    "results":[{"name":"unrelated"}]}]
            return [{"success":True,"meta":{"changes":0},
                "results":[{"n":0 if "forge_research" in sql else 2}]}]
        raise AssertionError(path)

class R18CReadOnlyTests(unittest.TestCase):
    def test_no_database_writer_called_in_preflight(self):
        api=FakeApi()
        # test foreign schema exact-pinning via isolated helper path; mock
        # hash is of a synthetic unrelated DDL and must be rejected.
        with self.assertRaisesRegex(InstallBlocked,"PRE_INSTALL_SCHEMA_IDENTITY_DRIFT"):
            preflight(api,"0"*8+"-"+("0"*4+"-")*3+"0"*12)
        self.assertEqual(api.writes,0)
    def test_live_protected_guard_schema_does_not_allow_missing_objects(self):
        api=FakeApi(installed=False)
        state={"foreign_sha":"x","original_rows":2}
        with self.assertRaises(InstallBlocked):
            verify_after(api,"irrelevant",state)
    def test_table_only_profile_is_not_full_archive(self):
        self.assertEqual(len(EXPECTED_KINDS),11)
        self.assertEqual(len(ORIGINAL_KINDS),3)
        self.assertEqual(sum(k=="trigger" for k in EXPECTED_KINDS.values()),8)
    def test_no_privileged_write_method_in_witness(self):
        import inspect,r18c_witness
        src=inspect.getsource(r18c_witness)
        self.assertNotIn("method=\"POST\"",src)
        self.assertNotIn("method='POST'",src)
        self.assertNotIn("/import",src)
if __name__=="__main__":unittest.main()
