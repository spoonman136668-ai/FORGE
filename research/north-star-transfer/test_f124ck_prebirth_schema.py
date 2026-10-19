"""F124-CK source-free guard for genuinely unborn E2/F2 firstuse.

Never import source generators, model, native scorer, or call birth.main.
Only frozen signed Git objects and Python AST/text are inspected.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
import subprocess
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ORIGINAL="5d77880fec127cceef3494fef9c7a60c5745fa38"
PROTOCOL="b56b675b72ce6a52581f78860f4ec4e776e239b0"
BIRTH="research/north-star-transfer/f124cj_birth_original.py"


def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT,text=True).strip()


class NoEntropyOrScienceBeforeFrozenRepair(unittest.TestCase):
    def test_one_and_only_one_schema_key_fix(self):
        old=git("show",ORIGINAL+":"+BIRTH)
        current=(ROOT/BIRTH).read_text()
        wrong='and not protocol["authority"]["protected_firstuse"],'
        right='and not protocol["authority"]["protected_replication_firstuse"],'
        self.assertEqual(old.count(wrong),1)
        self.assertEqual(current,old.replace(wrong,right)+"\n"
                         if not old.endswith("\n")
                         else old.replace(wrong,right))
        self.assertNotIn(wrong,current)
        self.assertEqual(current.count(right),1)

    def test_existing_original_cj_precode_is_not_rewritten(self):
        old=git("show",PROTOCOL+":"+
                "research/north-star-transfer/f124cj-frozen-fresh-interface-EF2.json")
        now=(HERE/"f124cj-frozen-fresh-interface-EF2.json").read_text()
        self.assertEqual(old,now.strip())
        p=json.loads(now)
        self.assertTrue(p["authority"]["one_time_development_firstuse"])
        self.assertFalse(p["authority"]["protected_replication_firstuse"])
        self.assertFalse(p["authority"]["model_retune"])
        self.assertEqual(p["fresh_unborn_roster"]["E2"]["dev"],[930000,930011])
        self.assertEqual(p["fresh_unborn_roster"]["F2"]["dev"],[931000,931011])

    def test_schema_enforced_before_entropy_and_no_other_frozen_changes(self):
        src=(ROOT/BIRTH).read_text()
        tree=ast.parse(src)
        self.assertTrue(tree)
        self.assertLess(src.index('protocol["authority"]["protected_replication_firstuse"]'),
                        src.index("seed=secrets.randbits(128)"))
        cases=(
          ("research/north-star-transfer/f124cj_internal_source.py",
           "4e7bbd8f93dab1c7242a9374c75731302b034f31"),
          ("research/north-star-transfer/f124cb_dual_link_learner.py",
           "8a10bf8cec12afc7d8703e3586d8eba91ebfdc7c"),
          ("research/north-star-transfer/f124cc_trained_two_link_control.py",
           "29c0c02f54ea539bed0910fe82adcc86d3aff94d"),
          ("nativeevidence/f124aj_example_operator_learner.py",
           "eddf99c06af66f2e46bf4dc0ea050368c283fcb2")
        )
        for path,sha in cases:
            self.assertEqual(git("rev-parse","HEAD:"+path),sha,path)

    def test_first_born_roster_has_no_reuse_of_old_firstuse(self):
        x=json.loads((HERE/"f124ck-frozen-prebirth-repair.json").read_text())
        self.assertEqual(x["parent_source_sha"],ORIGINAL)
        self.assertEqual(x["original_CJ_protocol_blob"],
                         "e9f8a43e052e9128f6dd4e8a10f8e3dc876a1550")
        self.assertTrue(x["prior_authentic_run"][
             "all_930000_930011_931000_931011_births_unexecuted"])
        self.assertFalse(x["strict_safety"]["no_model_retune"] is False)
        self.assertFalse(x["strict_safety"]["merge_authority"])
        self.assertFalse(x["strict_safety"]["optimizer_promotion"])

if __name__=="__main__":
    unittest.main()
