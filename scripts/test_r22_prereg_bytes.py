"""R22 synthetic negative tests; live sources are read separately in CI."""
import base64
import copy
import hashlib
import json
import pathlib
import sys
import unittest

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import r22_prereg_bytes as a

def blob(doc):
    raw=json.dumps(doc,separators=(",",":")).encode()
    oid=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()
    return oid,{"sha":oid,"size":len(raw),"encoding":"base64",
                "content":base64.b64encode(raw).decode()}

class R22(unittest.TestCase):
    def test_real_manifest_has_six_immutable_originals(self):
        m=a.decode(a.MANIFEST.read_bytes())
        p=a.decode(a.PINS.read_bytes())
        src,pins=a.fixed_inputs(m,p)
        self.assertEqual(len(src),6)
        self.assertEqual([(r["lane"],r["experiment"]) for r in src],
                         [(r["lane"],r["experiment"]) for r in pins])

    def test_verified_bytes_are_sha256_and_never_authority(self):
        manifest=a.decode(a.MANIFEST.read_bytes())
        pins=a.decode(a.PINS.read_bytes())
        blobs={}
        for i,p in enumerate(pins["entries"]):
            sha,actual=blob({"experiment":p["experiment"],"fixed":i})
            p["prereg_git_blob_sha"]=sha
            blobs[(p["lane"],sha)]=actual
        out=a.audit(manifest,pins,lambda lane,sha:copy.deepcopy(blobs[(lane,sha)]))
        self.assertEqual(out["count"],6)
        self.assertEqual(len({r["prereg_sha256"] for r in out["records"]}),6)
        for field in ["independent_source_birth_verified","complete_first_use_reconciled",
                      "scientific_accepted","optimizer_promotion_authorized"]:
            self.assertIs(out[field],False)

    def test_bad_blob_content_denied(self):
        sha,actual=blob({"experiment":"W-R24"})
        pin={"prereg_git_blob_sha":sha}
        actual["content"]=base64.b64encode(b'{"experiment":"ALTERED"}').decode()
        with self.assertRaises(a.Blocked):a.verify_blob(pin,actual)

    def test_wrong_sha_denied(self):
        sha,actual=blob({"experiment":"W-R24"})
        with self.assertRaises(a.Blocked):a.verify_blob({"prereg_git_blob_sha":"f"*40},actual)

    def test_missing_experiment_denied(self):
        sha,actual=blob({"foo":"bar"})
        with self.assertRaises(a.Blocked):a.verify_blob({"prereg_git_blob_sha":sha},actual)

    def test_bad_length_denied(self):
        sha,actual=blob({"experiment":"W-R24"})
        actual["size"]=actual["size"]+1
        with self.assertRaises(a.Blocked):a.verify_blob({"prereg_git_blob_sha":sha},actual)

    def test_duplicate_json_denied(self):
        raw=b'{"experiment":"W-R24","experiment":"Y037"}'
        oid=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()
        payload={"sha":oid,"size":len(raw),"encoding":"base64","content":base64.b64encode(raw).decode()}
        with self.assertRaises(a.Blocked):a.verify_blob({"prereg_git_blob_sha":oid},payload)

    def test_replay_or_mislabel_denied(self):
        m=a.decode(a.MANIFEST.read_bytes())
        p=a.decode(a.PINS.read_bytes())
        p["entries"][0]["scientific_accepted"]=True
        with self.assertRaises(a.Blocked):a.audit(m,p,lambda l,sha:None)


    def test_frozen_sha256_manifest_identity_and_negative(self):
        frozen=a.decode(a.FROZEN.read_bytes())
        result={"records":copy.deepcopy(frozen["records"])}
        self.assertTrue(a.verify_frozen_observations(result,frozen))
        drift=copy.deepcopy(result)
        drift["records"][0]["prereg_sha256"]="0"*64
        with self.assertRaises(a.Blocked):
            a.verify_frozen_observations(drift,frozen)
        changed=copy.deepcopy(frozen)
        changed["records"][1]["lane"]="Yggdrasil"
        with self.assertRaises(a.Blocked):
            a.verify_frozen_observations(result,changed)
        tampered=copy.deepcopy(frozen)
        tampered["observed_github_run_id"]=1
        with self.assertRaises(a.Blocked):
            a.verify_frozen_observations(result,tampered)

if __name__=="__main__":
    unittest.main()
