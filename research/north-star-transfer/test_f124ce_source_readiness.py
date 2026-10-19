"""F124-CE: no-science original-source registration adversarial tests.

Only in-memory mock issue JSON. No model imported or previous source run;
mocked external names are NEVER admitted as authenticated provenance.
"""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location("F124CE_source_registry",
                                      HERE/"f124ce_source_readiness.py")
ce=importlib.util.module_from_spec(s)
s.loader.exec_module(ce)


def issue(n=0):
    return {"number":605,"state":"open","comments":n}


def ref(fam,login,repo=None):
    return {"schema":"mass.f124ce.external-birth-reference.v1",
            "family":fam,
            "frozen_protocol_commit":ce.PROTOCOL_COMMIT,
            "frozen_protocol_blob":ce.PROTOCOL_BLOB,
            "repository":repo or (login+"/original-causal-grammar"),
            "creator_login":login,
            "commit_sha":("a" if fam=="C" else "b")*40,
            "files":{role:{
                "path":"independent/"+name,
                "blob_sha":("c" if role=="source" else
                            "d" if role=="oracle" else "e")*40}
                for role,name in (("source","source.py"),
                                  ("oracle","private_oracle.py"),
                                  ("attestation","attestation.json"))}}


def comment(ident,login,reference):
    return {"id":ident,"user":{"login":login},
            "body":ce.MARKER+"\n"+json.dumps(reference)}


class OriginalScientificAuthority(unittest.TestCase):
    def test_frozen_distinct_case_ranges_and_unmodified_models(self):
        p=ce.verify_protocol()
        self.assertEqual(p["new_source_cohorts"]["C"]["development"],
                         [926000,926011])
        self.assertEqual(p["new_source_cohorts"]["D"]["replication"],
                         [927100,927227])
        self.assertEqual(p["original_BV_scope"]["comparison"],
                         "BQ versus AZ ONLY")
        self.assertFalse(p["authority"]["protected_firstuse"])
        self.assertFalse(p["authority"]["optimizer_promotion"])
        self.assertTrue(p["task"]["same_native_work"].startswith(
                         "CB and fully trained CC must NATURALLY"))

    def test_actual_issue_empty_must_block_and_zero_all_firstuse(self):
        r=ce.scan_issue(issue(),[])
        self.assertEqual(r["status"],
            "BLOCKED_INDEPENDENT_NEW_CB_CC_SOURCE_BIRTH_NOT_PRESENT")
        self.assertEqual(r["source_reference_count"],0)
        self.assertEqual(r["new_CB_CC_development_cases_created"],0)
        self.assertEqual(r["new_CB_CC_protected_cases_created"],0)
        self.assertFalse(r["original_BV_science_sources_touched"])
        self.assertFalse(r["original_CB_CC_or_native_scoring_rerun"])
        self.assertFalse(r["science_accepted"])

    def test_one_non_authenticated_reference_remains_blocked(self):
        r=ce.scan_issue(issue(1),[
            comment(1,"outsideLabC",ref("C","outsideLabC"))])
        self.assertEqual(r["status"],
            "BLOCKED_TWO_DISTINCT_CB_CC_SOURCES_REQUIRED")
        self.assertFalse(r["source_provider_signed_original_commits_verified"])
        self.assertFalse(r["scientific_novelty_and_independent_authorship_proven"])

    def test_two_distinct_unverified_metadata_never_unlock_firstuse(self):
        r=ce.scan_issue(issue(2),[
            comment(1,"outsideLabC",ref("C","outsideLabC")),
            comment(2,"outsideLabD",ref("D","outsideLabD"))])
        self.assertEqual(r["source_reference_count"],2)
        self.assertEqual(r["status"],
          "BLOCKED_SIGNED_PROVIDER_ORIGINAL_AND_SEMANTIC_NOVELTY_QUALIFICATION_REQUIRED")
        self.assertTrue(all(not x["source_provider_authenticated"]
                            for x in r["source_reference_metadata"]))
        self.assertFalse(r["merge_or_firstuse_authorized"])
        self.assertEqual(r["new_CB_CC_development_cases_created"],0)

    def test_wrong_bv_protocol_old_case_and_self_author_are_denied(self):
        a=comment(1,"outsideLabC",ref("C","outsideLabC"))
        old=ref("D","outsideLabD")
        old["frozen_protocol_blob"]="5a509951aacb3de7cbec0c0e895d3b9c8ce4dce5"
        invalid=[
            [a,comment(2,"outsideLabD",old)],
            [a,comment(2,"outsideLabC",ref("D","outsideLabC"))],
            [a,comment(2,"spoonman136668-ai",ref("D","spoonman136668-ai"))],
            [a,comment(2,"outsideLabC",ref("D","outsideLabD"))],
            [a,comment(2,"outsideLabD",ref("D","outsideLabD",
                                             "spoonman136668-ai/origin"))]
        ]
        for x in invalid:
            with self.assertRaises(ValueError):
                ce.scan_issue(issue(2),x)

    def test_incomplete_issue_comment_and_duplicate_source_denied(self):
        a=comment(1,"outsideLabC",ref("C","outsideLabC"))
        for meta,comments in [
            ({"number":605,"state":"closed","comments":0},[]),
            ({"number":586,"state":"open","comments":0},[]),
            (issue(101),[]),
            (issue(1),[]),
            (issue(0),[a]),
            (issue(2),[a,a])
        ]:
            with self.assertRaises(ValueError):
                ce.scan_issue(meta,comments)

    def test_forged_signed_flag_comment_does_not_verify_identity(self):
        bogus=ref("C","outsideLabC")
        bogus["verified"]=True
        r=ce.scan_issue(issue(1),[comment(1,"outsideLabC",bogus)])
        self.assertFalse(r["source_provider_signed_original_commits_verified"])
        self.assertEqual(r["new_CB_CC_protected_cases_created"],0)

    def test_invalid_paths_hashes_or_unrelated_comments_fail_or_ignore(self):
        bogus=ref("C","outsideLabC")
        bogus["files"]["oracle"]["path"]="../private_oracle.py"
        with self.assertRaises(ValueError):
            ce.scan_issue(issue(1),[comment(1,"outsideLabC",bogus)])
        self.assertEqual(ce.scan_issue(issue(1),[{
            "id":99,"user":{"login":"visitor"},
            "body":"This is not a source original."}
            ])["source_reference_count"],0)


if __name__=="__main__":
    unittest.main()
