"""AC-14 source-only OGBench artifact identity and no-science unit guards.

Unit-test fixture metadata is NEVER passed off as a real upstream runtime.
"""
import io
import json
import unittest
from unittest.mock import patch
import ac14_ogbench as m

class AC14Tests(unittest.TestCase):
    def test_immutable_official_wheel_pin(self):
        self.assertEqual(m.VERSION,"1.2.1")
        self.assertEqual(m.WHEEL,"ogbench-1.2.1-py3-none-any.whl")
        self.assertEqual(m.WHEEL_SHA256,
            "597ac2207935e4edc46de5d5742e940a753f2329e18612e9cfe7f9e857435f83")
        self.assertEqual(m.WHEEL_BYTES,8940331)
        self.assertEqual(m.PYPI_JSON,
            "https://pypi.org/pypi/ogbench/1.2.1/json")
        self.assertEqual(m.ac10.SOURCE_COMMIT,
            "c94e9a4cd3641588b6b8507e71ccee5c27032bdf")

    def test_official_metadata_matches_exact_filename_hash_and_size(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def read(self,n):return self.blob.read(n)
        item={"filename":m.WHEEL,"packagetype":"bdist_wheel",
              "digests":{"sha256":m.WHEEL_SHA256},
              "size":m.WHEEL_BYTES,"yanked":False,
              "url":"https://files.pythonhosted.org/packages/fakehash/"+m.WHEEL}
        meta={"info":{"name":"ogbench","version":m.VERSION},"urls":[item]}
        response=Response()
        response.blob=io.BytesIO(json.dumps(meta).encode())
        with patch.object(m.urllib.request,"urlopen",return_value=response):
            got=m.official_wheel_record()
        self.assertEqual(got["sha256"],m.WHEEL_SHA256)
        self.assertEqual(got["size_bytes"],m.WHEEL_BYTES)

    def test_official_pypi_drift_rejected(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def read(self,n):return self.blob.read(n)
        meta={"info":{"name":"ogbench","version":m.VERSION},
              "urls":[{"filename":m.WHEEL,"packagetype":"bdist_wheel",
                       "digests":{"sha256":"0"*64},
                       "size":m.WHEEL_BYTES,"yanked":False,
                       "url":"https://files.pythonhosted.org/wrong"}]}
        response=Response()
        response.blob=io.BytesIO(json.dumps(meta).encode())
        with patch.object(m.urllib.request,"urlopen",return_value=response):
            with self.assertRaisesRegex(RuntimeError,"HASH_SIZE_OR_PUBLISHER_DRIFT"):
                m.official_wheel_record()

    def test_strict_external_source_prerequisite(self):
        self.assertEqual(m.ac13.TORCH,"2.3.1+cpu")
        self.assertEqual(m.ac13.VISION,"0.18.1+cpu")
        self.assertEqual(m.ac11.SMOKE_SEEDS,(759011,759013))
        groups=m.ac10.PROTO
        for key in ("fit_seeds_reserved_not_run",
                    "validation_seeds_reserved_not_run",
                    "dev_seeds_reserved_not_run"):
            self.assertFalse(set(m.ac11.SMOKE_SEEDS)&set(groups[key]))
        self.assertFalse(groups["protected_original_first_use"])
        self.assertTrue({"get_graph","ctf_do","env","u","full_info"}.issubset(
            m.ac11.FORBIDDEN))

if __name__=="__main__":
    unittest.main()
