import unittest
from unittest.mock import patch,MagicMock
from contextlib import contextmanager
import tempfile
import pathlib
import sys
from f139 import h53_native_readonly as n

@contextmanager
def fake_database(db):
    yield MagicMock(open_readonly=MagicMock(return_value=db))

class NativeTests(unittest.TestCase):
    def test_original_module_has_canonical_identity_and_restores_imports(self):
        before = {k: v for k, v in sys.modules.items() if k == "f139" or k.startswith("f139.")}
        old_path = list(sys.path)
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            package = root / "f139"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "local_controller.py").write_text(
                "class Database:\n"
                "    def canonical(self):\n"
                "        from f139.local_controller import Database as CanonicalDatabase\n"
                "        return type(self) is CanonicalDatabase\n", encoding="utf-8")
            with n.original_database_class(root) as Database:
                self.assertTrue(Database().canonical())
                self.assertIs(sys.modules["f139.local_controller"].Database, Database)
            self.assertEqual({k: v for k, v in sys.modules.items() if k == "f139" or k.startswith("f139.")}, before)
            self.assertEqual(sys.path, old_path)
            with self.assertRaisesRegex(RuntimeError, "simulated verifier failure"):
                with n.original_database_class(root):
                    raise RuntimeError("simulated verifier failure")
            self.assertEqual({k: v for k, v in sys.modules.items() if k == "f139" or k.startswith("f139.")}, before)
            self.assertEqual(sys.path, old_path)

    def test_original_verifier_failure_is_terminal(self):
        db=MagicMock()
        db.verify.side_effect=RuntimeError("native chain invalid")
        with patch.object(n.pathlib.Path,"resolve",return_value=n.pathlib.Path("/tmp/a.db")), \
             patch.object(n,"original_database_class",return_value=fake_database(db)):
            with self.assertRaisesRegex(RuntimeError,"native chain invalid"):
                n.verify_native(n.pathlib.Path("/tmp/a.db"),original_root=n.pathlib.Path("/tmp/original"))
        db.close.assert_called_once()
    def test_native_source_mismatch_is_terminal(self):
        db=MagicMock()
        db.meta.return_value={"source_sha":"wrong","head_seq":350}
        with patch.object(n.pathlib.Path,"resolve",return_value=n.pathlib.Path("/tmp/a.db")), \
             patch.object(n,"original_database_class",return_value=fake_database(db)):
            with self.assertRaisesRegex(RuntimeError,"NATIVE_SOURCE_DRIFT"):
                n.verify_native(n.pathlib.Path("/tmp/a.db"),original_root=n.pathlib.Path("/tmp/original"))
        db.close.assert_called_once()
if __name__=="__main__":
    unittest.main()
