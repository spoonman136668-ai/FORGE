"""F124-CF deterministic fake-provider custody tests (NEVER actual sources).

No source generators or private oracles are imported/executed, and in-memory
unit fixture provenance is explicitly prohibited from counting as authentic.
"""
from __future__ import annotations
import base64
import copy
import importlib.util
import json
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
def load(name,file):
    s=importlib.util.spec_from_file_location(name,HERE/file)
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

v=load("CF_untrusted_original_provider_static_only",
       "f124cf_original_provider_verify.py")

def fixture(family,creator):
    # Intentionally fabricated in-memory metadata, ONLY for rejection tests.
    # Never save fake sources to repo/artifact or claim real external origins.
    src=b"def mathematical_relation(x):\n    return x ^ 7\n"
    ora=b"def oracle(x):\n    return x == 3\n"
    att=json.dumps({
        "schema":"mass.f124cf.signed-origin-attestation.v1",
        "family":family,"creator_login":creator,
        "frozen_protocol_commit":"264f12cfcd1f37a401f8eb9fbe1689ee274f3afc",
        "frozen_protocol_blob":"df770890b0131e259ce30012ae9c599ca15bbfab",
        "independently_originated":True,
        "no_model_access_or_copied_source":True,
        "no_prior_case_or_seed_reuse":True,
        "no_protected_firstuse":True,
        "novelty_claim":"In-memory test only and NOT a real independent scientific source."
    }).encode()
    values={"source":src,"oracle":ora,"attestation":att}
    names={"source":"source/generator.py",
           "oracle":"source/private_oracle.py",
           "attestation":"source/claim.json"}
    # Role bytes differ, and C/D different original external SOURCE too.
    values["source"]+=("# TEST FAMILY "+family+"\n").encode()
    values["oracle"]+=("# TEST FAMILY "+family+"\n").encode()
    files={role:{"path":names[role],"blob_sha":v.git_object(raw)}
           for role,raw in values.items()}
    sha=("a" if family=="C" else "b")*40
    tree_sha=("e" if family=="C" else "f")*40
    repo=creator+"/test-only-fixture"
    reference={
        "schema":"mass.f124ce.external-birth-reference.v1",
        "family":family,
        "repository":repo,
        "creator_login":creator,
        "frozen_protocol_commit":"264f12cfcd1f37a401f8eb9fbe1689ee274f3afc",
        "frozen_protocol_blob":"df770890b0131e259ce30012ae9c599ca15bbfab",
        "commit_sha":sha,
        "files":files}
    witness={"repo":repo,"sha":sha,
             "git_commit":{"sha":sha,"tree":{"sha":tree_sha},
                           "verification":{"verified":True,
                                           "reason":"valid",
                                           "signature":"FAKE_TEST_SIGNATURE"}},
             "rest_commit":{"sha":sha,"author":{"login":creator}},
             "tree":{"sha":tree_sha,"truncated":False,
                     "tree":[{"path":f["path"],"type":"blob","sha":f["blob_sha"]}
                             for f in files.values()]},
             "blobs":{role:{"sha":files[role]["blob_sha"],"encoding":"base64",
                            "content":base64.b64encode(raw).decode()}
                      for role,raw in values.items()}}
    return reference,witness


class SourceOriginalProvider(unittest.TestCase):
    def test_no_real_sources_is_explicitly_blocked_and_NO_firstuse(self):
        ce=v.parent_gate()
        source=v.extract_live_refs({"number":605,"state":"open","comments":0},[])
        self.assertEqual(source,{})
        for flag in ("no_scientific_firstuse","no_model_calls","no_protected_open"):
            self.assertTrue(v.freeze()[flag])
        self.assertEqual(len(source),0)

    def test_two_fake_witnesses_never_authenticate_live_science(self):
        c,wc=fixture("C","testOutsideC")
        d,wd=fixture("D","testOutsideD")
        report=v.pair({"C":c,"D":d},{"C":wc,"D":wd})
        self.assertEqual(report["status"],
                         "TEST_FIXTURE_ONLY_NO_EXTERNAL_AUTHENTICATION")
        self.assertFalse(report["source_custody_qualified"])
        self.assertFalse(report["independent_novelty_accepted"])
        self.assertFalse(report["scientific_source_firstuse_authorized"])
        self.assertFalse(report["protected_cohorts_opened"])
        self.assertFalse(report["models_executed"])

    def test_bad_signature_fails_closed(self):
        c,w=fixture("C","testOutsideC")
        for value in (False,None,"false"):
            broken=copy.deepcopy(w)
            broken["git_commit"]["verification"]["verified"]=value
            with self.assertRaises(ValueError):
                v.verify_one(c,broken)
        broken=copy.deepcopy(w)
        broken["rest_commit"]["author"]["login"]="someOtherCreator"
        with self.assertRaises(ValueError):
            v.verify_one(c,broken)

    def test_tree_replaced_truncated_or_wrong_commit_fails(self):
        c,w=fixture("C","testOutsideC")
        for corrupt in ("sha","trunc","blob","repo"):
            bad=copy.deepcopy(w)
            if corrupt=="sha":bad["git_commit"]["sha"]="0"*40
            if corrupt=="trunc":bad["tree"]["truncated"]=True
            if corrupt=="blob":bad["tree"]["tree"][0]["sha"]="0"*40
            if corrupt=="repo":bad["repo"]="FORGE/forged"
            with self.assertRaises(ValueError):
                v.verify_one(c,bad)

    def test_modified_blob_content_or_missing_role_rejected(self):
        c,w=fixture("C","testOutsideC")
        corrupt=copy.deepcopy(w)
        corrupt["blobs"]["oracle"]["content"]=base64.b64encode(b"not original").decode()
        with self.assertRaises(ValueError):
            v.verify_one(c,corrupt)
        corrupt=copy.deepcopy(w)
        del corrupt["blobs"]["attestation"]
        with self.assertRaises(ValueError):
            v.verify_one(c,corrupt)

    def test_static_restrictions_do_not_execute_code(self):
        self.assertEqual(v.static_python(b"import itertools\n", "source"),
                         ["itertools"])
        for text in (b"from f124cb_dual_link_learner import learn\n",
                     b"import nativeevidence.original\n",
                     b"eval('3')\n",b"__import__('os')\n",
                     b"this is not valid Python !"):
            with self.assertRaises(ValueError):
                v.static_python(text,"source")

    def test_fake_signed_attestation_does_not_prove_authorship_or_novelty(self):
        c,w=fixture("C","testOutsideC")
        original=v.verify_one(c,w)
        self.assertTrue(original["signature_provider_verified"])
        self.assertFalse(original["semantic_novelty_independently_verified"])
        self.assertFalse(original["true_authorship_independently_proved"])
        self.assertFalse(original["independent_postfreeze_birth_chronology_proved"])
        bad=copy.deepcopy(w)
        att=json.loads(base64.b64decode(bad["blobs"]["attestation"]["content"]))
        att["independently_originated"]=False
        altered=json.dumps(att).encode()
        # Mismatch to original blob must fail even if attestation lies.
        bad["blobs"]["attestation"]["content"]=base64.b64encode(altered).decode()
        with self.assertRaises(ValueError):
            v.verify_one(c,bad)

    def test_duplicate_creator_or_source_blob_never_qualifies(self):
        c,wc=fixture("C","testOutsideC")
        d,wd=fixture("D","testOutsideD")
        duplicate=copy.deepcopy(d);duplicate["creator_login"]="testOutsideC"
        with self.assertRaises(ValueError):
            v.pair({"C":c,"D":duplicate},{"C":wc,"D":wd})
        identical=copy.deepcopy(d)
        identical["files"]["source"]=copy.deepcopy(c["files"]["source"])
        with self.assertRaises(ValueError):
            v.pair({"C":c,"D":identical},{"C":wc,"D":wd})

    def test_lack_one_original_family_fails(self):
        c,wc=fixture("C","testOutsideC")
        with self.assertRaises(ValueError):
            v.pair({"C":c},{"C":wc})


if __name__=="__main__":
    unittest.main()
