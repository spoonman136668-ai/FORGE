"""PR-only source-bound G29/native-candidate rehearsal; no F139 dispatch.

Never uses original issue #696, its HMAC, a scientific original, or live
owner SQLite. One synthetic source comment proves clean source Atlas and
isolated modified native full regression can coexist without skip shortcuts.
"""
from __future__ import annotations

from pathlib import Path
import os
import tempfile
import unittest

from f139.nci04_native_contract import Candidate, digest
from f139.nci04_native_worker import stage_candidate, verify_fixed_commands

NATIVE_COMMIT = "e5b2596fd7972c9a577427902f917887f37ee4a6"
NATIVE_TREE = "e42e8f3b476f7ae3e4d3814f0c55173ac6cc5211"
PATH = "scripts/native_cells.py"


class NativeAtlasIntegration(unittest.TestCase):
    @unittest.skipUnless(os.getenv("F139_PR_NATIVE_SOURCE"),
                         "source-integrated test requires pinned PR checkout")
    def test_real_pristine_g29_and_candidate_regression(self):
        source = Path(os.environ["F139_PR_NATIVE_SOURCE"]).resolve(strict=True)
        import subprocess
        def git(*args):
            r = subprocess.run(["git","-C",str(source),*args],
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                check=True,timeout=15)
            return r.stdout.decode().strip()
        self.assertEqual(git("rev-parse","HEAD"),NATIVE_COMMIT)
        self.assertEqual(git("rev-parse","HEAD^{tree}"),NATIVE_TREE)
        self.assertEqual(git("status","--porcelain","--untracked-files=all"),"")
        # Use authenticated git object bytes, NOT platform-converted
        # working-tree bytes (Windows checkout may be CRLF while the signed
        # committed source/blob and isolated native stage are LF).
        original = subprocess.run(
            ["git","-C",str(source),"show","HEAD:"+PATH],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            timeout=15,check=True)
        before = original.stdout
        # Different, purely synthetic code comment from issue #696: never
        # replay the quarantined owner's signed native candidate.
        synthetic = b"\n# PR-only G29 native checkout separation fixture\n"
        self.assertNotIn(synthetic,before)
        after = before + synthetic
        candidate = Candidate(
            "1"*64,"2"*64,NATIVE_COMMIT,NATIVE_TREE,PATH,
            digest(before),digest(after),after,"Yggdrasil")
        with tempfile.TemporaryDirectory(prefix="f139-native-g29-") as temp:
            scratch = Path(temp)
            stage = stage_candidate(candidate,source,scratch)
            self.assertEqual(
                (stage/"pristine"/PATH).read_bytes(),before)
            self.assertEqual(
                (stage/"checkout"/PATH).read_bytes(),after)
            report = verify_fixed_commands(candidate,stage,timeout_seconds=600)
            for command in report["commands"]:
                if command["outcome"] != "PASS":
                    self.fail("PR_NATIVE_QUALIFICATION_FAILED: "+str(command["command"])+
                              "\n"+command["excerpt"][-3500:])
            self.assertTrue(report["qualification_complete"],
                            "native qualification stopped without full fixed suite")
            self.assertEqual(len(report["commands"]),4)
            self.assertEqual(git("status","--porcelain","--untracked-files=all"),"")


if __name__=="__main__":
    unittest.main()
