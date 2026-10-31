import unittest
from g77_static_compat import check_runtime, ids_digest

class ContractTests(unittest.TestCase):
    def test_pins(self):
        check_runtime('4.52.3', '2.8.0+cu128')
    def test_version_drift(self):
        with self.assertRaisesRegex(RuntimeError, 'PINNED_RUNTIME_DRIFT'):
            check_runtime('4.52.2', '2.8.0+cu128')
    def test_digest_determinism(self):
        self.assertEqual(ids_digest([1,2,3]), ids_digest([1,2,3]))
    def test_digest_order(self):
        self.assertNotEqual(ids_digest([1,2,3]), ids_digest([3,2,1]))
if __name__ == '__main__':
    unittest.main()
