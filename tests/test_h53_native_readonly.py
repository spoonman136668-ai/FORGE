import unittest
from unittest.mock import patch,MagicMock
from f139 import h53_native_readonly as n

class NativeTests(unittest.TestCase):
    def test_original_verifier_failure_is_terminal(self):
        db=MagicMock()
        db.verify.side_effect=RuntimeError("native chain invalid")
        with patch.object(n.pathlib.Path,"resolve",return_value=n.pathlib.Path("/tmp/a.db")), \
             patch.object(n.Database,"open_readonly",return_value=db):
            with self.assertRaisesRegex(RuntimeError,"native chain invalid"):
                n.verify_native(n.pathlib.Path("/tmp/a.db"))
        db.close.assert_called_once()
    def test_native_source_mismatch_is_terminal(self):
        db=MagicMock()
        db.meta.return_value={"source_sha":"wrong","head_seq":350}
        with patch.object(n.pathlib.Path,"resolve",return_value=n.pathlib.Path("/tmp/a.db")), \
             patch.object(n.Database,"open_readonly",return_value=db):
            with self.assertRaisesRegex(RuntimeError,"NATIVE_SOURCE_DRIFT"):
                n.verify_native(n.pathlib.Path("/tmp/a.db"))
        db.close.assert_called_once()
if __name__=="__main__":
    unittest.main()
