"""F124-CD adversarial read-only source-provenance intake tests.

In-memory reference metadata ONLY; no real source execution or science.
"""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location(
    "F124CD_readonly",HERE/"f124cd_live_issue_intake.py")
gate=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

def issue(n=0):
    return {"number":586,"state":"open","comments":n}

def ref(family,creator):
    return {"schema":"mass.f124bv.external-birth-reference.v1",
      "family":family,"repository":creator+"/external-origin",
      "creator_login":creator,
      "frozen_protocol_blob":"5a509951aacb3de7cbec0c0e895d3b9c8ce4dce5",
      "commit_sha":("a" if family=="A" else "b")*40}

def comment(n,creator,value):
    return {"id":n,"user":{"login":creator},
            "body":gate.MARKER+"\n"+json.dumps(value)}

class ReadOnlySourceBirth(unittest.TestCase):
    def test_original_empty_source_blocks_firstuse(self):
        o=gate.evaluate(issue(),[])
        self.assertEqual(o["status"],"BLOCKED_INDEPENDENT_SOURCE_BIRTH_NOT_PRESENT")
        self.assertEqual(o["original_source_registration_count"],0)
        for flag in ("BQ_BV_reserved_development_firstuse",
                     "BQ_BV_reserved_128x2_replication_opened",
                     "CB_CC_prospective_science_admitted",
                     "source_and_oracle_executed","independent_science_accepted"):
            self.assertFalse(o[flag],flag)

    def test_unrelated_comments_cannot_create_source_evidence(self):
        o=gate.evaluate(issue(2),[
          {"id":1,"user":{"login":"commenter"},"body":"future interest"},
          {"id":2,"user":{"login":"anyone"},"body":"signed: true"}])
        self.assertEqual(o["original_source_registration_count"],0)

    def test_one_real_comment_is_not_two_provider_origins(self):
        o=gate.evaluate(issue(1),[
          comment(12,"externalA",ref("A","externalA"))])
        self.assertEqual(o["status"],"BLOCKED_TWO_INDEPENDENT_SOURCE_BIRTHS_REQUIRED")
        self.assertFalse(o["CB_CC_prospective_science_admitted"])

    def test_duplicate_same_author_and_same_owner_rejected(self):
        a=comment(1,"externalA",ref("A","externalA"))
        bad=[
          [a,a],
          [a,comment(2,"externalA",ref("B","externalA"))],
          [a,comment(2,"spoonman136668-ai",ref("B","spoonman136668-ai"))],
          [a,comment(2,"externalA",ref("B","externalB"))],
          [a,comment(2,"externalB",{**ref("B","externalB"),
                                    "repository":"spoonman136668-ai/new-sources"})],
          [a,comment(2,"externalB",{**ref("B","externalB"),
                                    "commit_sha":"Q"*40})]
        ]
        for comments in bad:
            with self.assertRaises(RuntimeError):
                gate.discover(issue(2),comments)

    def test_incomplete_closed_or_wrong_issue_fails(self):
        for bad,comments in [
          ({"number":586,"state":"closed","comments":0},[]),
          ({"number":586,"state":"open","comments":101},[]),
          (issue(1),[]),(issue(0),[comment(1,"a",ref("A","a"))])
        ]:
            with self.assertRaises(RuntimeError):
                gate.discover(bad,comments)

    def test_two_mock_external_metadata_do_not_authenticate_science(self):
        a=comment(1,"externalA",ref("A","externalA"))
        b=comment(2,"externalB",ref("B","externalB"))
        seen=[]
        o=gate.evaluate(issue(2),[a,b],provider=lambda entries:
                        seen.extend(sorted(entries)))
        self.assertEqual(seen,["A","B"])
        self.assertEqual(o["status"],"TEST_ONLY_TWO_SOURCE_ROUTING_NOT_AUTHENTICATED")
        self.assertFalse(o["CB_CC_prospective_science_admitted"])
        self.assertFalse(o["independent_science_accepted"])

    def test_mock_references_without_GitHub_token_must_fail(self):
        a=comment(1,"externalA",ref("A","externalA"))
        b=comment(2,"externalB",ref("B","externalB"))
        # Mock metadata deliberately fails before any real provider witness
        # because it lacks the original BV source identity requirements.
        with self.assertRaises(ValueError):
            gate.evaluate(issue(2),[a,b])
        self.assertEqual(gate.original().PROTOCOL_BLOB,
                         "5a509951aacb3de7cbec0c0e895d3b9c8ce4dce5")

if __name__=="__main__":
    unittest.main()
