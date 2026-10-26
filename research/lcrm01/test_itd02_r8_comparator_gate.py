"""Source-only tests: comparator coverage must be complete and executable."""
import unittest
from itd02_r8_comparator_gate import REQUIRED, validate_comparator_coverage

def implementation(): return None

class ComparatorCoverageTest(unittest.TestCase):
    def test_complete(self):
        result=validate_comparator_coverage({name:implementation for name in REQUIRED})
        self.assertEqual(result["method_count"],6)
        self.assertFalse(result["scientific_accepted"])
    def test_missing_rejected(self):
        for missing in REQUIRED:
            with self.subTest(missing=missing), self.assertRaises(ValueError):
                validate_comparator_coverage({name:implementation for name in REQUIRED-{missing}})
    def test_noncallable_rejected(self):
        bad={name:implementation for name in REQUIRED}
        bad["independent_conditional_beta"]=None
        with self.assertRaises(ValueError):
            validate_comparator_coverage(bad)
    def test_unregistered_rejected(self):
        bad={name:implementation for name in REQUIRED}
        bad["unregistered"]=implementation
        with self.assertRaises(ValueError):
            validate_comparator_coverage(bad)

if __name__=="__main__": unittest.main()
