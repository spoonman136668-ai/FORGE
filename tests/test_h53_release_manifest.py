import unittest
import hashlib
from f139 import h53_release_manifest as m

class ManifestTests(unittest.TestCase):
    def test_exact_release_allowlist_and_pins(self):
        changed=sorted(m.REQUIRED)
        hashes={k:"a"*64 for k in changed}
        kwargs=dict(parent=m.g.SOURCE,source_hashes=hashes,expected_hashes=hashes)
        self.assertFalse(m.verify_release_manifest(changed,**kwargs)["release_authorized"])
        for bad in [changed[:-1],changed+[".github/workflows/other.yml"],changed+[changed[0]]]:
            with self.assertRaisesRegex(RuntimeError,"RELEASE_MANIFEST"):
                m.verify_release_manifest(bad,**kwargs)
        with self.assertRaisesRegex(RuntimeError,"RELEASE_PARENT"):
            m.verify_release_manifest(changed,**{**kwargs,"parent":"bad"})
        with self.assertRaisesRegex(RuntimeError,"RELEASE_CONTENT_DRIFT"):
            m.verify_release_manifest(changed,**{**kwargs,"source_hashes":{**hashes,changed[0]:"b"*64}})
    def test_actual_bytes_must_match_pins(self):
        changed=sorted(m.REQUIRED)
        files={k:(k+"\\n").encode() for k in changed}
        pins={k:hashlib.sha256(v).hexdigest() for k,v in files.items()}
        m.verify_release_bytes(changed,parent=m.g.SOURCE,files=files,expected_hashes=pins)
        altered={**files,changed[0]:b"tampered"}
        with self.assertRaisesRegex(RuntimeError,"RELEASE_CONTENT_DRIFT"):
            m.verify_release_bytes(changed,parent=m.g.SOURCE,files=altered,expected_hashes=pins)
if __name__=="__main__":
    unittest.main()
