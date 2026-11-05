"""G98 probe contract tests; no model, network or held-out data."""
import sys, unittest, copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import g98_timing_probe as m

class G98TimingTests(unittest.TestCase):
    def test_probe_nested_timing_and_cache_semantics(self):
        ticks=iter(range(100))
        p=m.Probe(clock=lambda:next(ticks))
        cache=p.cache_factory("lru")
        value,hit,admitted=cache.request("a",1,lambda:{"past":42})
        self.assertFalse(hit)
        self.assertTrue(admitted)
        self.assertEqual(value["past"],42)
        value2,hit2,admitted2=cache.request("a",1,lambda:1/0)
        self.assertTrue(hit2)
        self.assertFalse(admitted2)
        self.assertEqual(value2,value)
        self.assertEqual(len(p.events["cache_request_inclusive"]),2)
        self.assertEqual(len(p.events["kv_build"]),1)
        self.assertFalse(p.receipt()["promotion_allowed"])
    def test_cache_policy_and_only_resident_kv_copy_counted(self):
        p=m.Probe(clock=iter(range(100)).__next__)
        cache=p.cache_factory("lru")
        self.assertIsInstance(cache,m.ORIGINAL_ADMISSION_CACHE)
        value,_,_=cache.request("a",1,lambda:{"past":("kv",)})
        original=copy.deepcopy
        with m.patched(copy,"deepcopy",p.kv_deepcopy(original)):
            copy.deepcopy({"unrelated": 1})
            copy.deepcopy(value["past"])
        self.assertEqual(len(p.events["kv_clone"]),1)
        bypass=m.Probe()
        bypass.cache_policy="g97_overflow_bypass"
        self.assertIsInstance(bypass.cache_factory("lru"),m.OverflowBypassCache)
    def test_restore_on_exception(self):
        class Target: value=7
        with self.assertRaisesRegex(RuntimeError,"sentinel"):
            with m.patched(Target,"value",99):
                self.assertEqual(Target.value,99)
                raise RuntimeError("sentinel")
        self.assertEqual(Target.value,7)
    def test_timing_failure_recorded(self):
        p=m.Probe(clock=iter(range(10)).__next__)
        def fail():raise ValueError("failure")
        with self.assertRaises(ValueError):p.wrap("kv_build",fail)()
        self.assertEqual(len(p.events["kv_build"]),1)
    def test_probe_is_not_a_performance_verdict(self):
        p=m.Probe()
        self.assertEqual(p.receipt()["phase"],"DEVELOPMENT_ONLY")
        self.assertNotIn("qualifies",p.receipt())
        self.assertIn("wrapper overhead",p.receipt()["timing_caveat"])

if __name__=="__main__":unittest.main()
