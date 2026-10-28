"""AC-12 source identity, genuine wheel and no-synthetic-result guards.

All samples below only exercise our exception/parser logic, not DTR episodes.
"""
import unittest
import ac12_import_repair as mod

class AC12Tests(unittest.TestCase):
    def test_exact_upstream_ancestry_and_verified_pypi_wheel(self):
        self.assertEqual(mod.ac10.SOURCE_COMMIT,
            "c94e9a4cd3641588b6b8507e71ccee5c27032bdf")
        self.assertEqual(mod.PINNED_EXTRA,"minigrid==2.3.1")
        self.assertEqual(mod.MINIGRID_WHEEL_SHA256,
            "6e841a9f95378abe1fdb053d4dfaead1613ceb2fa1e9548a8525882fbdb4f6f3")
        self.assertEqual(len(mod.MINIGRID_WHEEL_SHA256),64)

    def test_parses_actual_missing_module_name(self):
        raw=b'Traceback (most recent call last):\n  File "..."\nModuleNotFoundError: No module named \\'minigrid\\''
        self.assertEqual(mod.read_exception(raw),
            {"kind":"MISSING_MODULE","module":"minigrid"})
        self.assertEqual(mod.read_exception(
            b'ModuleNotFoundError: No module named \\'torchvision\\'')["module"],
            "torchvision")

    def test_does_not_echo_unsafe_error_lines(self):
        data=b'ModuleNotFoundError: No module named \\'minigrid\\'\\nTOKEN=someprivatevalue'
        result=mod.read_exception(data)
        self.assertNotIn("TOKEN",repr(result))
        self.assertEqual(result["module"],"minigrid")

    def test_declines_unclassified_import_errors(self):
        self.assertIsNone(mod.read_exception(b"ImportError: cannot import name 'x'")["module"])
        self.assertEqual(mod.read_exception(b"AttributeError: fake")["kind"],
                         "UPSTREAM_ATTRIBUTE_ERROR")
        self.assertEqual(mod.read_exception(b"some other exception")["kind"],
                         "OTHER_OR_NO_ERROR")

    def test_no_first_use_or_reserved_seeds(self):
        self.assertEqual(mod.ac11.SMOKE_SEEDS,(759011,759013))
        self.assertFalse(set(mod.ac11.SMOKE_SEEDS)&set(
            mod.ac10.PROTO["fit_seeds_reserved_not_run"]))
        self.assertFalse(set(mod.ac11.SMOKE_SEEDS)&set(
            mod.ac10.PROTO["validation_seeds_reserved_not_run"]))
        self.assertFalse(set(mod.ac11.SMOKE_SEEDS)&set(
            mod.ac10.PROTO["dev_seeds_reserved_not_run"]))
        self.assertFalse(mod.ac10.PROTO["protected_original_first_use"])
        self.assertEqual(mod.ac11.SCHEMA,
                         "forge.ac11.original-dtr-public-compatibility.v1")

if __name__=="__main__":
    unittest.main()
