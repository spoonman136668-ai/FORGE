"""Bounded R23 ZIP receipt-discovery tests, no external credentials or science."""
import hashlib
import io
import json
import pathlib
import sys
import tempfile
import unittest
import zipfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import r23_archive_receipt_discovery as r

def archive(files):
    b=io.BytesIO()
    with zipfile.ZipFile(b,"w",zipfile.ZIP_DEFLATED) as z:
        for k,v in files.items():
            z.writestr(k,v if isinstance(v,bytes) else json.dumps(v).encode())
    raw=b.getvalue()
    return raw,hashlib.sha256(raw).hexdigest()

def manifest():
    base=json.loads(r.MANIFEST.read_text())
    return base

class R23(unittest.TestCase):
    def test_source_manifest_has_six(self):
        x=manifest()
        self.assertEqual(len(x["entries"]),6)

    def test_no_receipts_archive_specific_not_global(self):
        raw,h=archive({"result.json":{"classification":"NEGATIVE"}})
        x=r.inspect_zip(raw,h)
        self.assertEqual(x["sourcebirth_candidate_files"],0)
        self.assertEqual(x["started_candidate_files"],0)
        self.assertEqual(x["terminal_candidate_files"],0)
        self.assertIs(x["independent_signatures_verified"],False)
        self.assertIs(x["complete_consumed_first_use_verified"],False)

    def test_candidates_detected_but_not_authenticated(self):
        raw,h=archive({
            "sourcebirth.json":{"statement":{"schema":"forge.sourcebirth.signed-birth.v1"},"issuer_signature_hex":"aa","witness_signature_hex":"bb"},
            "worker-started.json":{"receipt":{"schema":"forge.worker.original-receipt.v1","stage":"STARTED"},"signature_hex":"aa"},
            "worker-terminal.json":{"receipt":{"schema":"forge.worker.original-receipt.v1","stage":"TERMINAL"},"signature_hex":"bb"},
        })
        out=r.inspect_zip(raw,h)
        self.assertEqual(out["sourcebirth_candidate_files"],1)
        self.assertEqual(out["started_candidate_files"],1)
        self.assertEqual(out["terminal_candidate_files"],1)
        self.assertIs(out["scientific_acceptance"],False)

    def test_wrong_zip_digest_denied(self):
        raw,h=archive({"result.json":{"result":"negative"}})
        with self.assertRaises(r.Blocked):r.inspect_zip(raw,"f"*64)

    def test_duplicate_archive_entries_denied(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,"w",zipfile.ZIP_STORED) as z:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore",UserWarning)
                z.writestr("result.json",b'{"a":1}')
                z.writestr("result.json",b'{"a":1}')
        raw=b.getvalue()
        with self.assertRaises(r.Blocked):r.inspect_zip(raw,hashlib.sha256(raw).hexdigest())

    def test_zip_traversal_denied(self):
        raw,h=archive({"../result.json":b'{"a":1}'})
        with self.assertRaises(r.Blocked):r.inspect_zip(raw,h)

    def test_unreadable_json_does_not_become_receipt(self):
        raw,h=archive({"malformed.json":b'{"broken":'})
        x=r.inspect_zip(raw,h)
        self.assertEqual(x["json_unreadable"],1)
        self.assertEqual(x["sourcebirth_candidate_files"],0)

    def test_exact_six_lane_archive_integrity_and_denial(self):
        m=manifest()
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            for e in m["entries"]:
                raw,h=archive({"result.json":{"experiment":e["experiment"],"scientific_result":"NEGATIVE"}})
                (root/(str(e["run_id"])+".zip")).write_bytes(raw)
                e["archive_sha256"]=h
            out=r.inspect_cohort(json.dumps(m).encode(),root)
            self.assertEqual(out["archive_count"],6)
            self.assertIs(out["live_optimizer_admitted"],False)
            self.assertIs(out["independent_custody_verified"],False)
            (root/(str(m["entries"][0]["run_id"])+".zip")).write_bytes(b"tampered")
            with self.assertRaises(r.Blocked):
                r.inspect_cohort(json.dumps(m).encode(),root)
if __name__=="__main__":
    unittest.main()
