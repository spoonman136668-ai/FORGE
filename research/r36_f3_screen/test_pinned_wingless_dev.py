"""R36 fail-closed pinned source adapter negative-path tests."""
import pathlib
import tempfile
import unittest
from unittest import mock
import pinned_wingless_dev as p

class SourcePinningTests(unittest.TestCase):
    def setUp(self):
        self.portfolio={
            "schema":"forge.r36-f3.pre-execution-hypothesis-portfolio.v1",
            "wingless":{
                "method_source_commit":p.SOURCE_COMMIT,
                "development_blocks":[list(range(15000,15016)),list(range(15032,15048)),list(range(15064,15080))],
                "reserved_sealed_heldout_seeds":list(range(15400,15448)),
            }
        }
    def test_wrong_commit_denied_before_import_or_training(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(p,"_git",return_value="wrong-sha"):
                with self.assertRaisesRegex(ValueError,"SOURCE_COMMIT_DRIFT"):
                    p.load_training(directory,self.portfolio,0)
    def test_invalid_block_denied_after_clean_source_check(self):
        with tempfile.TemporaryDirectory() as directory:
            def fake_git(root,*args):
                if args[0]=="rev-parse":return p.SOURCE_COMMIT
                if args[0]=="status":return ""
                return p.SOURCE_PATH
            with mock.patch.object(p,"_git",side_effect=fake_git):
                with self.assertRaisesRegex(ValueError,"INVALID_DEVELOPMENT_BLOCK"):
                    p.load_training(directory,self.portfolio,3)
    def test_dirty_source_denied(self):
        with tempfile.TemporaryDirectory() as directory:
            def fake_git(root,*args):
                if args[0]=="rev-parse":return p.SOURCE_COMMIT
                return " M research/test.py"
            with mock.patch.object(p,"_git",side_effect=fake_git):
                with self.assertRaisesRegex(ValueError,"DIRTY_SOURCE"):
                    p.load_training(directory,self.portfolio,0)

if __name__=="__main__":
    unittest.main()
