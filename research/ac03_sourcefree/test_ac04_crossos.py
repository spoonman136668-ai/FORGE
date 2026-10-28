"""AC-04 source-only tests; all original science remains out of scope."""
import os
from unittest import TestCase
from unittest.mock import patch

import ac03_benchmark as prior
import ac04_crossos as m

class AC04SourceOnly(TestCase):
    def test_exact_parent_source_pin(self):
        self.assertEqual(m.canonical_ac03_sha256(),m.SOURCE_SHA256)
        self.assertEqual(m.REPEATS,3)
        self.assertEqual(len(m.ALLOWED_CASES),11)
    def test_six_new_and_some_original_ideas_represented(self):
        self.assertTrue({'AC-D%d'%i for i in range(1,7)} <=
                        {k for ids in prior.IDS.values() for k in ids})
        self.assertTrue({'U01','U11','U12','U13'} <=
                        {k for ids in prior.IDS.values() for k in ids})
    def test_same_case_exact_parity_in_fresh_children(self):
        a=m.one("delta","full")
        b=m.one("delta","delta")
        self.assertEqual(a["sha256"],b["sha256"])
        self.assertIsInstance(a["cpu_ns"],int)
    def test_approximate_sketch_preserves_overcount_negative(self):
        a=m.one("sketch","exact")["outcome"]
        b=m.one("sketch","cms")["outcome"]
        self.assertEqual(len(a),len(b))
        self.assertTrue(all(v>=u for u,v in zip(a,b)))
        self.assertTrue(any(v>u for u,v in zip(a,b)))
    def test_guard_refuses_unqualified_environment(self):
        with patch.dict(os.environ,{"AC04_SOURCEFREE_ONLY":"0"}):
            with self.assertRaisesRegex(RuntimeError,"AC04_SOURCEFREE_ONLY_GUARD_NOT_SET"):
                m.run("must_not_exist_ac04.json")
    def test_scientific_authority_not_claimed(self):
        import inspect
        src=inspect.getsource(m.run)
        self.assertIn('"science_admitted":False',src)
        self.assertIn('"scientific_original_first_use":False',src)
        self.assertIn('"new_controller":False',src)
