"""F124-BV model-free source signature/provenance and negative science gates.

ALL sources in these tests are synthetic in-memory REST shapes, never real
GitHub provider source, real 924/925 experiments, or previously consumed
scientific cases. No model/native/source generator is imported or executed.
"""
from __future__ import annotations
import base64
import copy
import importlib.util
import json
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location(
    "f124bv_origin_reader",HERE/"f124bv_origin_admission.py")
bv=importlib.util.module_from_spec(spec)
spec.loader.exec_module(bv)


def dummy(family):
    identity=(11 if family=="A" else 12)
    owner="external-lab-"+family.lower()
    author="independent-scientist-"+family.lower()
    repo=owner+"/new-causal-source"
    sha=format(identity,"x")*40
    original={
        "source":b"import math\ndef source_private_transform(x):\n return (x+13)%65536\n",
        "oracle":b"def oracle_private_causal(graph):\n return True\n",
        "attestation":json.dumps({
            "schema":"mass.f124bv.source-independence-attestation.v1",
            "frozen_protocol_blob":bv.PROTOCOL_BLOB,
            "family":family,
            "creator_login":author,
            "independently_originated":True,
            "no_model_access_or_copied_source":True,
            "no_prior_case_or_seed_reuse":True,
            "no_protected_cohort_firstuse":True,
            "source_generates_only_development_when_admitted":True,
            "novelty_claim":"A separately-originated symbolic grammar with unseen causal order and adversarial edge matching."
        },sort_keys=True).encode()
    }
    files={}
    blobs={}
    for name,data in original.items():
        path="original/"+name+(".json" if name=="attestation" else ".py")
        h=bv.git_blob(data)
        files[name]={"path":path,"blob_sha":h}
        blobs[name]={"path":path,"blob":{
          "encoding":"base64","sha":h,
          "content":base64.b64encode(data).decode()}}
    ref={
      "schema":"mass.f124bv.external-birth-reference.v1",
      "family":family,
      "frozen_protocol_commit":bv.PROTOCOL_COMMIT,
      "frozen_protocol_blob":bv.PROTOCOL_BLOB,
      "fit_case_ids":bv.EXPECTED[family]["fit"],
      "sealed_holdout_ids":bv.EXPECTED[family]["holdout"],
      "repository":repo,"creator_login":author,"commit_sha":sha,
      "precode_frozen_at":bv.ORIGINAL_PROVIDER_FROZEN_AT,
      "future_firstuse_timestamp":None,
      "files":files
    }
    witness={
      "repo":repo,"commit_sha":sha,
      "provider_api_authenticated":True,
      "git_commit":{"sha":sha,"author":{"date":"2026-10-20T00:00:00Z"},
        "parents":[{"sha":"f"*40}],
        "tree":{"sha":format(identity+1,"x")*40},
        "verification":{"verified":True}},
      "original_tree":{"sha":str(identity+1)*40,
        "truncated":False,"tree":[
          {"path":item["path"],"type":"blob","sha":item["blob_sha"]}
          for item in files.values()]},
      "rest_commit":{"sha":sha,"author":{"login":author}},
      "original_blobs":blobs
    }
    return ref,witness


def simulated_record(family,index):
    case=bv.EXPECTED[family]["fit"][index]
    return {
       "case":case,"family":family,
       "source_private_key_passed_to_model":False,
       "source_truly_new_firstuse":True,
       "protected_cases_opened":False,
       "AZ_positive":False,"AZ_hard_FP":False,
       "BQ_positive":True,"BQ_hard_FP":False,
       "resource":{
          "case":case,"resource_eligible":True,
          "AZ_natural_route":"affine","AZ_routing_forced":False,
          "AZ_native_calls":2,"BQ_native_calls":2,
          "same_native_graphs_and_outputs":True,
          "native_max_active":7,"native_max_retained":9,
          "full_public_fit_and_training_included":True,
          "full_process_peak_RSS":True,
          "AZ":{"allocator":"default","CPU_ns":[1000000]*5,
                "peak_RSS_bytes":[21000000]*5},
          "BQ":{"allocator":"malloc","CPU_ns":[500000]*5,
                "peak_RSS_bytes":[20000000]*5}
       }
    }


class ProspectiveIndependentBirthAndNegativeAcceptance(unittest.TestCase):
    def test_absent_original_source_is_explicitly_blocked(self):
        r=bv.pending_disposition()
        self.assertIn("BLOCKED",r["status"])
        self.assertFalse(r["source_or_original_learner_executed"])
        self.assertEqual(r["new_development_FIT_cases_consumed"],0)
        self.assertEqual(r["new_protected_128x2_cases_consumed"],0)

    def test_mock_signed_two_sources_only_qualify_custody_not_novelty(self):
        a,wa=dummy("A")
        b,wb=dummy("B")
        s=bv.original_birth_admission({
          "schema":"mass.f124bv.two-independent-source-manifest.v1",
          "families":[a,b]}, {"A":wa,"B":wb})
        self.assertTrue(s["provider_authenticated_separate_signed_source_origins"])
        self.assertFalse(s["semantic_novelty_independently_proved"])
        self.assertFalse(s["firstuse_consumed"])
        self.assertEqual(len(s["families"]),2)
        for x in s["families"]:
            self.assertFalse(x["source_module_executed"])
            self.assertFalse(x["semantic_novelty_proven_by_signature_alone"])

    def test_reject_source_owner_creator_sha_signature_and_prior_identity_drift(self):
        manifest,witness=dummy("A")
        cases=[]
        x=copy.deepcopy(manifest);x["repository"]=bv.FORGE_OWNER+"/FORGE";cases.append((x,witness))
        x=copy.deepcopy(manifest);x["fit_case_ids"]=[924000];cases.append((x,witness))
        x=copy.deepcopy(manifest);x["precode_frozen_at"]="2022-01-01T00:00:00Z";cases.append((x,witness))
        x=copy.deepcopy(manifest);x["files"]["source"]["path"]="../escape.py";cases.append((x,witness))
        y=copy.deepcopy(witness);y["git_commit"]["verification"]["verified"]=False;cases.append((manifest,y))
        y=copy.deepcopy(witness);y["git_commit"]["author"]["date"]="2026-10-19T08:09:59Z";cases.append((manifest,y))
        y=copy.deepcopy(witness);y["rest_commit"]["author"]["login"]="model-author";cases.append((manifest,y))
        y=copy.deepcopy(witness);y["original_blobs"]["source"]["blob"]["content"]="ZmFrZQ==";cases.append((manifest,y))
        for case,provider in cases:
            with self.subTest(error=str(case.get("repository"))):
                with self.assertRaises(ValueError):
                    bv.original_witness_one(case,provider)

    def test_source_static_code_not_allowed_to_import_model_or_dynamically_exec(self):
        for raw in (b"import f124bq_program_learner\n",
                    b"import nativeevidence.f124ag_transition_models\n",
                    b"eval('5')\n",b"__import__('random')\n"):
            with self.assertRaises(ValueError):
                bv.static_source_boundaries(raw)

    def test_two_mock_creators_must_be_distinct(self):
        a,wa=dummy("A");b,wb=dummy("B")
        b["creator_login"]=a["creator_login"]
        wb["rest_commit"]["author"]["login"]=a["creator_login"]
        with self.assertRaises(ValueError):
            bv.original_birth_admission({
                "schema":"mass.f124bv.two-independent-source-manifest.v1",
                "families":[a,b]},{"A":wa,"B":wb})

    def test_all_24_cases_retain_zero_fp_and_no_resource_regression(self):
        a,wa=dummy("A");b,wb=dummy("B")
        o=bv.original_birth_admission({
            "schema":"mass.f124bv.two-independent-source-manifest.v1",
            "families":[a,b]},{"A":wa,"B":wb})
        rows=[simulated_record(f,j) for f in ("A","B") for j in range(12)]
        result=bv.assess_development(rows,o)
        self.assertTrue(result["joint_development_eligible"])
        self.assertFalse(result["scientific_transfer_accepted"])
        self.assertFalse(result["protected_cohorts_consumed"])
        self.assertEqual(result["family_results"]["A"]["new_correct_pair_case_ids"],
                         list(range(924000,924012)))

    def test_negative_and_abstained_data_is_retained_and_fail_closed(self):
        a,wa=dummy("A");b,wb=dummy("B")
        o=bv.original_birth_admission({
            "schema":"mass.f124bv.two-independent-source-manifest.v1",
            "families":[a,b]},{"A":wa,"B":wb})
        rows=[simulated_record(f,j) for f in ("A","B") for j in range(12)]
        rows[1]["BQ_hard_FP"]=True
        rows[4]["AZ_positive"]=True;rows[4]["BQ_positive"]=False
        rows[6]["resource"]=None
        rows[9]["resource"]["BQ"]["peak_RSS_bytes"]=[23000000]*5
        result=bv.assess_development(rows,o)
        f=result["family_results"]["A"]
        self.assertFalse(f["development_eligible"])
        self.assertEqual(f["hard_false_positive_case_ids"],[924001])
        self.assertEqual(f["baseline_positive_lost_case_ids"],[924004])
        self.assertEqual(f["cost_ineligible_case_ids"],[924006])
        self.assertEqual(f["cost_regression_case_ids"],[924009])
        self.assertFalse(result["joint_development_eligible"])
        with self.assertRaises(ValueError):
            bv.assess_development(rows[:-1],o)

    def test_missing_real_cost_proof_or_comparator_score_is_not_positive(self):
        bad=simulated_record("B",0)
        bad["resource"]["AZ_native_calls"]=0
        with self.assertRaises(ValueError):
            bv._cost_receipt(bad["resource"],bad["case"])
        bad=simulated_record("B",0)
        bad["resource"]["full_public_fit_and_training_included"]=False
        with self.assertRaises(ValueError):
            bv._cost_receipt(bad["resource"],bad["case"])


if __name__=="__main__":
    unittest.main()
