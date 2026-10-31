import sys
import types
import unittest
from unittest.mock import patch
from g77_static_compat import check_runtime, ids_digest

class ContractTests(unittest.TestCase):
    def test_actual_runtime_pins(self):
        torch = types.SimpleNamespace(__version__="2.8.0+cu128")
        transformers = types.SimpleNamespace(__version__="4.52.3")
        with patch.dict(sys.modules, {"torch":torch,"transformers":transformers}):
            self.assertEqual(check_runtime(), ("4.52.3","2.8.0+cu128"))
    def test_actual_runtime_drift(self):
        torch = types.SimpleNamespace(__version__="2.8.0+cu128")
        transformers = types.SimpleNamespace(__version__="4.52.2")
        with patch.dict(sys.modules, {"torch":torch,"transformers":transformers}):
            with self.assertRaisesRegex(RuntimeError, "PINNED_RUNTIME_DRIFT"):
                check_runtime("4.52.3", "2.8.0+cu128")
    def test_caller_drift(self):
        torch = types.SimpleNamespace(__version__="2.8.0+cu128")
        transformers = types.SimpleNamespace(__version__="4.52.3")
        with patch.dict(sys.modules, {"torch":torch,"transformers":transformers}):
            with self.assertRaisesRegex(RuntimeError, "CALLER_TRANSFORMERS_VERSION_DRIFT"):
                check_runtime("4.52.2")
            with self.assertRaisesRegex(RuntimeError, "CALLER_TORCH_VERSION_DRIFT"):
                check_runtime(torch_version="2.7.0")
    def test_digest_determinism(self):
        self.assertEqual(ids_digest([1,2,3]), ids_digest([1,2,3]))
    def test_digest_order(self):
        self.assertNotEqual(ids_digest([1,2,3]), ids_digest([3,2,1]))

if __name__ == "__main__":
    unittest.main()
