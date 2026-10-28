"""AC-13 fail-closed original-source and PyTorch CPU wheel provenance tests."""
import io
import sys
import unittest
from unittest.mock import patch

import ac13_cpu_torchvision as m

class AC13Guards(unittest.TestCase):
    def test_official_pinned_pair_and_cpu_only(self):
        self.assertEqual(m.TORCH,"2.3.1+cpu")
        self.assertEqual(m.VISION,"0.18.1+cpu")
        self.assertEqual(m.INDEX,"https://download.pytorch.org/whl/cpu")
        self.assertEqual(m.ORIGINAL_SHA,m.ac10.SOURCE_COMMIT)
        self.assertLessEqual(m.MAX_DOWNLOAD_SECONDS,420)
        self.assertLessEqual(m.MAX_INSTALL_SECONDS,240)

    def test_py311_x64_wheel_platform(self):
        names=m.wheel_names()
        self.assertEqual(len(names),2)
        self.assertIn("cp311-cp311",names["torch"])
        self.assertIn("cp311-cp311",names["torchvision"])
        self.assertIn("2.3.1+cpu",names["torch"])
        self.assertIn("0.18.1+cpu",names["torchvision"])
        self.assertTrue(all(x.endswith(".whl") for x in names.values()))

    def test_hash_index_requires_official_exact_filename(self):
        names=m.wheel_names()
        class FakeResponse:
            def __init__(self,data):self.buf=io.BytesIO(data)
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def read(self,n):return self.buf.read(n)
        def fake_open(req,timeout):
            pkg="torchvision" if req.full_url.endswith("torchvision/") else "torch"
            wheel=names[pkg].replace("+","%2B")
            html=f'<a href="{wheel}#sha256={"f"*64}">wheel</a>'
            return FakeResponse(html.encode())
        with patch.object(m.urllib.request,"urlopen",side_effect=fake_open):
            hashes=m.official_index_hashes(names)
        self.assertEqual(hashes,{"torch":"f"*64,"torchvision":"f"*64})

    def test_missing_or_ambiguous_official_hash_rejected(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*a):return False
            def read(self,n):return b'<a href="other.whl#sha256=bad">wrong</a>'
        with patch.object(m.urllib.request,"urlopen",return_value=Response()):
            with self.assertRaisesRegex(RuntimeError,"OFFICIAL_INDEX_DIGEST_MISSING"):
                m.official_index_hashes(m.wheel_names())

    def test_no_source_permissions_or_synthetic_outcomes(self):
        self.assertEqual(m.ac11.SMOKE_SEEDS,(759011,759013))
        self.assertTrue(m.ac10.PROTO["frozen_before_source_interactions"])
        self.assertFalse(m.ac10.PROTO["protected_original_first_use"])
        for group in ("fit_seeds_reserved_not_run","validation_seeds_reserved_not_run","dev_seeds_reserved_not_run"):
            self.assertTrue(set(m.ac11.SMOKE_SEEDS).isdisjoint(m.ac10.PROTO[group]))
        self.assertTrue({"get_graph","ctf_do","env","u","full_info"}.issubset(
            m.ac11.FORBIDDEN))

if __name__=="__main__":
    unittest.main()
