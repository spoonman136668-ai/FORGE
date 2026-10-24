#!/usr/bin/env python3
"""L9 first-use audit pre-admission: exact frozen metadata only, no corpus or models.

Strictly validates cross-platform SELECT seal and pre-audit methodological
contract. It cannot grant audit-first-use permission before an independently
qualified evaluator is frozen. Source/target text is never loaded or emitted.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

CONTRACT_GIT_BLOB="b5b51c1cc954830374cbf1d667c57fb5e31a8827"
SEAL_RAW_SHA256="bbee9d6a6a92c3fbec536dbf8364ecae6b05ae46d86fbdef667f23d3179abc09"
ROLE_SHA="b9995c1846f5e1d99bf8bc4083dde0ebb41140906284bcf050a7ed6fe0efe726"
SUITE="710ce648a30ffc55647f689c5f4aa3ac13b07066"
SEAL_SCHEMA="forge.optimizer.language.l9.select-seal-mixed-recovery-v2-development-only"
CONTRACT_SCHEMA="forge.optimizer.language.l9.prospective-audit-admission-contract-v1"
EXPECTED={
  ("GRU_SEQ2SEQ",1701):("ORIGINAL_V1","762d7471d0e3f7b24f8789c6b323624f0c86996614d477b5f354651ba19d5474","a24469cf00be1c028cd5dfb25649f7bcc523b35792eb4680fe19aa8912f01daa"),
  ("GRU_SEQ2SEQ",1702):("ORIGINAL_V1","511ad147152fd7e45eab915da2bdd74d2872a50cc6b4a20fe4ab9c5b677bc1e6","1097e800b6ddc2acaa90df62943c6db1a34b1e1e62e51daf056f95303bb8d048"),
  ("SMALL_TRANSFORMER",1701):("RECOVERED_V2_TIMEOUT","d17ffdf04aa8c38a77d23baab2d68219183a599ace8e920aab0cf0f89e83d539","bf731132c64dbfd82ea5bc6121d0006c34527101b040119f9d11d83931a99a84"),
  ("SMALL_TRANSFORMER",1702):("RECOVERED_V2_TIMEOUT","e7da6758df045fbbfdff4b4b024fafcc886bd5a6c309f9d4b35a85cf163f9c3f","e5e7baaf4a0ad3be69213933419da96fb85842a0b40adafdecd587d00fccf5a0"),
}
CONFIG={"min_template_support":1,"max_templates_per_predicate":4,"joiner":" "}
METHODS=["CANONICAL_FACTS_NONFLUENT_CONTROL","TRAIN_REFERENCE_RETRIEVAL",
         "COMPOSITIONAL_PATTERN","GRU_SEQ2SEQ-1701","GRU_SEQ2SEQ-1702",
         "SMALL_TRANSFORMER-1701","SMALL_TRANSFORMER-1702"]

def must(ok,label):
    if not ok: raise ValueError("AUDIT_PRE_ADMISSION_BLOCKED: "+label)
def sha(data:bytes):
    return hashlib.sha256(data).hexdigest()
def blob(data:bytes):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def canonical(data):
    return (json.dumps(data,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode()

def validate_contract_bytes(raw:bytes):
    # Windows Git checkout may render a Git's canonical LF blob as CRLF.
    # Normalize line endings only; this never alters JSON field values.
    canonical_raw=raw.replace(b"\r\n",b"\n")
    must(b"\r" not in canonical_raw,"unexpected newline encoding")
    must(blob(canonical_raw)==CONTRACT_GIT_BLOB,"frozen audit contract Git blob drift")
    c=json.loads(canonical_raw)
    must(c.get("schema")==CONTRACT_SCHEMA,"contract schema")
    must(c.get("status")=="FROZEN_BEFORE_ANY_AUDIT_REFERENCE_SCORE_OR_MODEL_AUDIT_OUTPUT","contract not pre-frozen")
    must(c.get("scientific_go") is False,"premature scientific success")
    source=c.get("source",{})
    require_source={
        "release":"a7ea49b5ffa5011edf81e8530c59b3552a965023",
        "source_manifest_blob":"826379955c721e9c0eb01c760586ab7ebace7520",
        "blob_manifest_blob":"7b76033f39fa002e2b69adccedcfca3ae826fa41",
        "role_sha256":ROLE_SHA,
        "split_receipt_blob":"ca3e41e2835713bc922c56542656489f202c55cf",
        "total_train":8480,"total_select":2154,"total_audit_dev":319,
        "held_out_category_count":3,"original_graph_overlap_after_quarantine":0,
        "official_test_access":"FORBIDDEN",
    }
    for k,v in require_source.items():must(source.get(k)==v,"frozen source "+k)
    selection=c.get("sealed_selection",{})
    must(selection.get("raw_sha256")==SEAL_RAW_SHA256,"sealed decision SHA")
    must(selection.get("sealed_schema")==SEAL_SCHEMA,"decision schema")
    must(selection.get("seal_run_id")==40075146727,"original four-case seal run")
    must(selection.get("model_suite_git_blob")==SUITE,"frozen model suite")
    must(selection.get("candidate",{}).get("config")==CONFIG,"selected candidate config")
    for arm in ("GRU_SEQ2SEQ","SMALL_TRANSFORMER"):
        for seed in (1701,1702):
            row=selection.get("neural",{}).get(arm,{}).get(str(seed))
            must(isinstance(row,dict) and row.get("epoch")==12,"selected epoch "+arm+str(seed))
    must(c.get("methods")==METHODS,"all control arms required")
    must(c.get("audit_role")=="L9_AUDIT_DEV","wrong audit role")
    must(c.get("no_reference_access_before_admission") is True,"reference leak")
    must(c.get("no_fitting_or_reselection_on_audit") is True,"unfrozen tuning")
    must(c.get("independent_transfer_evidence_status")=="NOT_YET_EXPOSED","audit has already been accessed")
    must(c.get("gate",{}).get("before_first_audit_reference_read"),"missing before-reference safeguards")
    must(c.get("gate",{}).get("after_first_use"),"missing post-audit retention rules")
    return c

def validate_seal_bytes(raw:bytes):
    must(sha(raw)==SEAL_RAW_SHA256,"sealed original numeric receipt bytes drift")
    d=json.loads(raw)
    must(d.get("schema")==SEAL_SCHEMA,"sealed receipt schema drift")
    must(d.get("status")=="ALL_FOUR_NUMERIC_DEV_CHOICES_VALIDATED_MIXED_V1_GRU_V2_TRANSFORMER","not full four-case seal")
    for k,v in {"role_identity_sha256":ROLE_SHA,"model_suite_git_blob":SUITE,
                "candidate_receipt_sha256":"01f08870677067ca0f0dcfdff004d1ef04cea8465da0d025f904634e2bcd5d47",
                "original_transformer_v1_timed_out":True,
                "recovered_transformer_v2_never_rebranded_v1":True,
                "separate_semantic_audit_admission_required":True,
                "audit_dev_reference_consumed":False,"official_test_consumed":False,
                "scientific_go":False}.items():
        must(d.get(k)==v,"sealed evidence "+k)
    candidate=d.get("candidate",{})
    must(candidate.get("selected_config")==CONFIG,"candidate choice changed")
    neural=d.get("neural_cases")
    must(isinstance(neural,list) and len(neural)==4,"missing mandatory control seed")
    seen=set()
    for row in neural:
        must(isinstance(row,dict),"neural row")
        pair=(row.get("arm"),row.get("seed"))
        must(pair in EXPECTED and pair not in seen,"unregistered or duplicate seed")
        seen.add(pair)
        expected=EXPECTED[pair]
        must(row.get("evaluation_identity")==expected[0],"v1/v2 source laundering")
        must(row.get("raw_receipt_sha256")==expected[1],"seed raw receipt SHA drift")
        selected=row.get("selected",{})
        must(selected.get("epoch")==12 and selected.get("checkpoint_sha256")==expected[2],
             "frozen selected checkpoint drift")
        metric=selected.get("requested_content_proxy_coverage")
        must(type(metric) in (int,float) and 0 <= metric <= 1,"malformed selected proxy")
    must(seen==set(EXPECTED),"neural grid incomplete")
    return d

def preflight(contract_path:Path,seal_path:Path,out:Path):
    must(not out.exists(),"refuse overwrite")
    c=validate_contract_bytes(contract_path.read_bytes())
    s=validate_seal_bytes(seal_path.read_bytes())
    result={
      "schema":"forge.optimizer.language.l9.audit-prospective-pre-admission-v1",
      "status":"SEALED_SELECTION_AND_PROTOCOL_VALIDATED_AUDIT_EVALUATOR_STILL_REQUIRED",
      "audit_first_use_allowed":False,
      "audit_reference_read_count":0,
      "official_test_consumed":False,
      "scientific_go":False,
      "contract_git_blob":CONTRACT_GIT_BLOB,
      "seal_sha256":SEAL_RAW_SHA256,
      "source_role_sha256":ROLE_SHA,
      "method_count":len(c["methods"]),
      "neural_control_count":len(s["neural_cases"]),
      "held_out_reference_example_count_expected":319,
      "held_out_category_count_expected":3,
      "note":"No held-out references used; audit first-use requires frozen evaluator and qualified source/role guard."
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    raw=canonical(result)
    out.write_bytes(raw)
    print("L9_AUDIT_PRE_ADMISSION_METADATA=PASS")
    print("L9_AUDIT_FIRST_USE_ALLOWED=FALSE")
    print("L9_OFFICIAL_TEST_CONSUMED=FALSE")
    print("L9_PRE_ADMISSION_SHA256="+sha(raw))
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--contract",type=Path,required=True)
    p.add_argument("--sealed-select",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    preflight(a.contract,a.sealed_select,a.out)
if __name__=="__main__":main()
