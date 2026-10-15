"""R26: do not infer scientific authority from authentic unrelated TRAIN-only artifacts."""
import copy
import hashlib
import io
import json
import pathlib
import stat
import sys
import tempfile
import unittest
import zipfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import r26_real_owner_evidence_discovery as p

def blob(files):
    b=io.BytesIO()
    with zipfile.ZipFile(b,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for name,value in files.items():
            z.writestr(name,value if isinstance(value,bytes) else json.dumps(value).encode())
    raw=b.getvalue()
    return raw,hashlib.sha256(raw).hexdigest()

class R26(unittest.TestCase):
    def test_real_scope(self):
        rows=p.validate(p.decode(p.PIN.read_bytes(),256*1024))
        self.assertEqual([x["lane"] for x in rows],["Wingless","Yggdrasil"])
        self.assertEqual([x["run_id"] for x in rows],[38740481969,38740643709])

    def test_source_zip_has_no_invented_authority(self):
        raw,sha=blob({"train-only/outcome.json":{"schema":"unrelated.real.train-only","classification":"NEGATIVE"}})
        report=p.inspect_zip(raw,sha)
        self.assertEqual(report["regular_json"],1)
        self.assertEqual(report["owner"],0)
        self.assertEqual(report["pins"],0)

    def test_candidate_only_is_not_verified(self):
        raw,sha=blob({"owner.json":{"schema":p.R25_OWNER},"pins.json":{"schema":p.R25_PINS}})
        r=p.inspect_zip(raw,sha)
        self.assertEqual((r["owner"],r["pins"]),(1,1))

    def test_digest_tamper_denied(self):
        raw,sha=blob({"train.json":{"x":1}})
        with self.assertRaises(p.Blocked):p.inspect_zip(raw,"a"*64)

    def test_bad_zip_paths_denied(self):
        for path in ("../outside.json","/etc/passwd","q/../../x.json"):
            raw,sha=blob({path:{"schema":"hello"}})
            with self.assertRaises(p.Blocked):p.inspect_zip(raw,sha)

    def test_duplicate_zip_entries_denied(self):
        import warnings
        b=io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore",UserWarning)
            with zipfile.ZipFile(b,"w") as z:
                z.writestr("e.json",b'{"foo":1}')
                z.writestr("e.json",b'{"foo":1}')
        raw=b.getvalue()
        with self.assertRaises(p.Blocked):p.inspect_zip(raw,hashlib.sha256(raw).hexdigest())

    def test_symlink_member_denied(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,"w") as z:
            member=zipfile.ZipInfo("owner.json")
            member.create_system=3
            member.external_attr=(stat.S_IFLNK|0o777)<<16
            z.writestr(member,b"../../secrets")
        raw=b.getvalue()
        with self.assertRaises(p.Blocked):p.inspect_zip(raw,hashlib.sha256(raw).hexdigest())

    def test_duplicate_json_field_denied(self):
        with self.assertRaises(p.Blocked):
            p.decode(b'{"schema":"a","schema":"b"}',1024)

    def test_real_metadata_shape_scoped_and_no_admission(self):
        m=copy.deepcopy(p.decode(p.PIN.read_bytes(),256*1024))
        with tempfile.TemporaryDirectory() as tmp:
            d=pathlib.Path(tmp)
            for e in m["entries"]:
                raw,h=blob({"train-only.json":{"schema":"not-r25","negative_kept":True}})
                e["artifact_zip_sha256"]=h
                rid=str(e["run_id"])
                (d/(rid+".zip")).write_bytes(raw)
                (d/(rid+".run.json")).write_text(json.dumps({
                    "id":e["run_id"],"run_attempt":1,"head_sha":e["head_sha"],
                    "path":e["workflow_path"],"event":"push","status":"completed",
                    "conclusion":"success","repository":{"full_name":e["repository"]}}))
                (d/(rid+".artifacts.json")).write_text(json.dumps({"artifacts":[{
                    "id":e["artifact_id"],"name":e["artifact_name"],"expired":False,
                    "digest":"sha256:"+h,"workflow_run":{"id":e["run_id"]}}]}))
            x=p.inspect(m,d)
            self.assertEqual(x["source_run_count"],2)
            self.assertFalse(x["r25_genuine_prospective_comparison_executed"])
            self.assertFalse(x["real_optimizer_gain_proven"])
            self.assertEqual(x["new_originals_executed"],0)
            r=m["entries"][0]
            a=json.loads((d/(str(r["run_id"])+".artifacts.json")).read_text())
            a["artifacts"][0]["digest"]="sha256:"+"e"*64
            (d/(str(r["run_id"])+".artifacts.json")).write_text(json.dumps(a))
            with self.assertRaises(p.Blocked):p.inspect(m,d)
if __name__=="__main__":
    unittest.main()
