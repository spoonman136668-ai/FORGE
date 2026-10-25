#!/usr/bin/env python3
"""Seal full L9 TRAIN/SELECT choices from four independently recorded development receipts.

Pure-stdlib custody check. No corpus load, model fit, audit data, official TEST,
or scientific authority is available from this module.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

ARMS = ("GRU_SEQ2SEQ", "SMALL_TRANSFORMER")
SEEDS = (1701,1702)
EPOCHS = (4,8,12)
ROLE_SHA = "b9995c1846f5e1d99bf8bc4083dde0ebb41140906284bcf050a7ed6fe0efe726"
SUITE_BLOB = "710ce648a30ffc55647f689c5f4aa3ac13b07066"
CANDIDATE_RECEIPT_SHA = "01f08870677067ca0f0dcfdff004d1ef04cea8465da0d025f904634e2bcd5d47"
SCHEMA = "forge.optimizer.language.l9.select-seal-development-v1"
SELECT_SCHEMA = "forge.optimizer.language.l9.neural-select-development-v1"
MODEL_BYTES_LIMIT = 3145728
LEN_SELECT = 2154

def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def canonical_bytes(value) -> bytes:
    return (json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode("utf-8")

def require_hex(value,label):
    if not isinstance(value,str) or len(value)!=64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"invalid sha256 {label}")
    return value

def _check_non_negative_num(item,key):
    v=item.get(key)
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0:
        raise ValueError(f"invalid numeric metric {key}")
    return v

def validate_case(obj,arm,seed):
    if not isinstance(obj,dict):
        raise ValueError("receipt must be an object")
    must={
        "schema":SELECT_SCHEMA,
        "status":"SELECT_ONLY_DEVELOPMENT_CHECKPOINT_CHOICE",
        "source_role_sha256":ROLE_SHA,
        "model_suite_git_blob":SUITE_BLOB,
        "arm":arm,"seed":seed,
        "train_count":8480,
        "select_count":LEN_SELECT,
        "audit_dev_reference_consumed":False,
        "official_test_consumed":False,
        "scientific_go":False,
        "selected_metric_is_nonadjudicated_proxy":True,
    }
    for k,v in must.items():
        if obj.get(k)!=v:
            raise ValueError(f"scientific identity/role drift: {arm}/{seed}/{k}")
    require_hex(obj.get("fit_receipt_sha256"),"fit receipt")
    require_hex(obj.get("selected_checkpoint_sha256"),"chosen checkpoint")
    metrics=obj.get("all_epoch_metrics")
    if not isinstance(metrics,list) or len(metrics)!=3:
        raise ValueError("must seal exactly three checkpoint metrics")
    observed={}
    for v in metrics:
        if not isinstance(v,dict) or v.get("arm")!=arm or v.get("seed")!=seed or v.get("role")!="L9_SELECT":
            raise ValueError("selection metric source mismatch")
        e=v.get("epoch")
        if type(e) is not int or e not in EPOCHS or e in observed:
            raise ValueError("duplicated or outside-grid checkpoint epoch")
        if v.get("records")!=LEN_SELECT:
            raise ValueError("incomplete L9_SELECT evaluation")
        h=v.get("triple_proxy_hits")
        d=v.get("triple_denominator")
        missing=v.get("missing_triples_proxy")
        if type(h) is not int or type(d) is not int or type(missing) is not int or d<1 or h<0 or h>d or missing!=d-h:
            raise ValueError("inconsistent SELECT denominators")
        for k in ("requested_content_proxy_coverage","chrf_single_reference_proxy"):
            p=_check_non_negative_num(v,k)
            if p>1:raise ValueError("proxy outside [0,1]")
        if abs(v["requested_content_proxy_coverage"]-h/d)>0.0000000011:
            raise ValueError("proxy score doesn't match numerator")
        checkpoint_size=v.get("retained_model_bytes")
        if type(checkpoint_size) is not int or not (0<checkpoint_size<=MODEL_BYTES_LIMIT):
            raise ValueError("checkpoint inference budget violated")
        require_hex(v.get("checkpoint_sha256"),"checkpoint")
        for k in ("evaluation_cpu_seconds","evaluation_wall_seconds"):
            _check_non_negative_num(v,k)
        observed[e]=v
    if set(observed)!=set(EPOCHS):
        raise ValueError("missing frozen epoch")
    best=min(observed.values(),key=lambda v:(-v["requested_content_proxy_coverage"],
                                          -v["chrf_single_reference_proxy"],
                                          v["missing_triples_proxy"],v["retained_model_bytes"],v["epoch"]))
    if obj.get("selected_epoch")!=best["epoch"] or obj["selected_checkpoint_sha256"]!=best["checkpoint_sha256"]:
        raise ValueError("selection did not follow frozen lexicographic comparator")
    return {
        "arm":arm,"seed":seed,
        "selected_epoch":best["epoch"],
        "checkpoint_sha256":best["checkpoint_sha256"],
        "fit_receipt_sha256":obj["fit_receipt_sha256"],
        "requested_content_proxy_coverage":best["requested_content_proxy_coverage"],
        "chrf_single_reference_proxy":best["chrf_single_reference_proxy"],
        "missing_triples_proxy":best["missing_triples_proxy"],
        "retained_model_bytes":best["retained_model_bytes"],
        "all_epoch_checkpoint_sha256":{str(e):observed[e]["checkpoint_sha256"] for e in EPOCHS},
    }

def validate_candidate(obj):
    expected={
       "schema":"forge.optimizer.language.l9.train-select-development-v1",
       "status":"DEVELOPMENT_TRAIN_SELECT_NOT_AUDIT",
       "split_role_sha256":ROLE_SHA,
       "frozen_suite_sha_from_receipt":SUITE_BLOB,
       "official_test_consumed":False,
       "scientific_go":False,
       "split_counts":{"train":8480,"select":2154,"audit_dev_model_consumption":0},
       "candidate_config_selected":{"min_template_support":1,"max_templates_per_predicate":4,"joiner":" "},
    }
    for k,v in expected.items():
        if obj.get(k)!=v:
            raise ValueError(f"candidate/retrieval SELECT source drift: {k}")
    if len(obj.get("candidate_selection",[]))!=8:
        raise ValueError("missing eight predefined candidate grid measurements")
    return {
        "selected_config":obj["candidate_config_selected"],
        "candidate_train_derived_coverage_proxy":obj["candidate_selection"][0]["requested_content_proxy_coverage"],
        "retrieval_train_derived_coverage_proxy":obj["retrieval_select"]["requested_content_proxy_coverage"],
    }

def seal(candidate_path:Path, receipts_dir:Path,output:Path):
    if output.exists():
        raise ValueError("refusing to overwrite a sealed decision")
    candidate_raw=candidate_path.read_bytes()
    if digest(candidate_raw)!=CANDIDATE_RECEIPT_SHA:
        raise ValueError("candidate SELECT receipt exact-byte identity drift")
    cand=validate_candidate(json.loads(candidate_raw))
    selected=[]
    receipts={}
    for arm in ARMS:
        for seed in SEEDS:
            label=f"{arm}-{seed}"
            p=receipts_dir/f"{label}.json"
            raw=p.read_bytes()
            row=validate_case(json.loads(raw),arm,seed)
            selected.append(row)
            receipts[label]=digest(raw)
    result={
      "schema":SCHEMA,
      "status":"L9_SELECT_CHOICES_SEALED_DEVELOPMENT_ONLY",
      "candidate_receipt_sha256":CANDIDATE_RECEIPT_SHA,
      "neural_select_receipts_sha256":receipts,
      "source_role_sha256":ROLE_SHA,
      "model_suite_git_blob":SUITE_BLOB,
      "candidate":cand,
      "neural_checkpoint_selection":selected,
      "requires_all_arms_and_seeds":True,
      "allowed_epochs":list(EPOCHS),
      "all_sources_dev_only":True,
      "audit_dev_references_consumed":False,
      "official_test_consumed":False,
      "flops":"NOT_MEASURED",
      "energy":"NOT_MEASURED",
      "scientific_go":False,
      "note":"SELECT lexical proxy and single-reference approximate chrF; NOT independent semantic acceptance.",
    }
    output.parent.mkdir(parents=True,exist_ok=True)
    b=canonical_bytes(result); output.write_bytes(b)
    print("L9_ALL_FOUR_NEURAL_SELECT_CHOICES_SEALED=TRUE")
    print("L9_AUDIT_DEV_REFERENCE_CONSUMED=FALSE")
    print("L9_SCIENTIFIC_GO=FALSE")
    print("L9_SELECT_SEAL_SHA256="+digest(b))
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--candidate-receipt",type=Path,required=True)
    p.add_argument("--neural-receipts-dir",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    seal(args.candidate_receipt,args.neural_receipts_dir,args.out)

if __name__=="__main__":main()
