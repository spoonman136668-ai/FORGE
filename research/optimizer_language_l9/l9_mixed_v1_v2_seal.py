#!/usr/bin/env python3
"""Strict L9 mixed V1-GRU / V2-Transformer development-only numerical seal.

No corpus, model execution or scientific first use. The legacy V1-only
l9_seal_select.py is not changed or called to relabel V2 as V1.
Both V2 receipt hashes are now pinned from independently validated original artifacts.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import l9_seal_select as legacy

SCHEMA = "forge.optimizer.language.l9.mixed-gru-v1-transformer-v2-select-seal-v1"
V2_SCHEMA = "forge.optimizer.language.l9.transformer-select-encoder-reuse-v2-development-only"
V2_STATUS = "PROSPECTIVE_RECOVERY_SELECT_NOT_V1_EVIDENCE"
V2_PREFIT = 40050110176
PAIR_INDEXES = (0,1,53,217,431,719,1077,1435,1795,2153)
ROLE_SHA = legacy.ROLE_SHA
SUITE_BLOB = legacy.SUITE_BLOB
GRU_RECEIPTS = {
    1701: "762d7471d0e3f7b24f8789c6b323624f0c86996614d477b5f354651ba19d5474",
    1702: "511ad147152fd7e45eab915da2bdd74d2872a50cc6b4a20fe4ab9c5b677bc1e6",
}
V2_RECEIPTS = {
    1701: "d17ffdf04aa8c38a77d23baab2d68219183a599ace8e920aab0cf0f89e83d539",  # authenticated archive 12552199545
    1702: "e7da6758df045fbbfdff4b4b024fafcc886bd5a6c309f9d4b35a85cf163f9c3f",
}
EXPECTED_FIT = {
    ("GRU_SEQ2SEQ",1701): "9b0350270d9868a8542a298eeaac8b33646ce1bf0ad81ae0e7e206210e40448b",
    ("GRU_SEQ2SEQ",1702): "6194e3b91dba147d5c68ff99d6953d2c82ddef832baf46e7e82a0287521f9d7a",
    ("SMALL_TRANSFORMER",1701): "ab1ef4066a30a4f3d4be2b1b72b9c0ff48511cc353c4e5de5e1d5523199938c5",
    ("SMALL_TRANSFORMER",1702): "39858e1c21d8b2e03463b2b244ba46693171564038b4787858ba052a27e51ed8",
}
FROZEN_CHECKPOINTS = {
    ("GRU_SEQ2SEQ",1701): {
        4:"9fa97bc5d0494a414af4c6d012d9beea68d99c52d40c1db7f09af7e4d7487b47",
        8:"1c923058ad9f6a570044c8573caf5cafb1a6971fc5b31de55e3febd39ec2f63d",
        12:"a24469cf00be1c028cd5dfb25649f7bcc523b35792eb4680fe19aa8912f01daa"},
    ("GRU_SEQ2SEQ",1702): {
        4:"b53c85a2584eacc00f8ce579bbb8e51a02d0eb1ef2b73ca6415133c62270b36e",
        8:"6c329a05bb64523e88bdf1a8203142dbb9805f4be80f3c3268f62a6a7821aa9e",
        12:"1097e800b6ddc2acaa90df62943c6db1a34b1e1e62e51daf056f95303bb8d048"},
    ("SMALL_TRANSFORMER",1701): {
        4:"5bc25aa6f0ff02690a8fec14a31b1d7ce5a6adf8a9355088327a2bcd22acd23e",
        8:"971919768cf8a62ef46df604d3b8754bf105db1afdf762dcae61b0d30e9602a3",
        12:"bf731132c64dbfd82ea5bc6121d0006c34527101b040119f9d11d83931a99a84"},
    ("SMALL_TRANSFORMER",1702): {
        4:"31e39af09253a7ed6950ead93a834469a62ac6908dcfcc1cdeacde4e3d885238",
        8:"b414a71193c12cd54db71403af0c5edd50ac905372cf6d9920e5026e80f7bbb8",
        12:"e5e7baaf4a0ad3be69213933419da96fb85842a0b40adafdecd587d00fccf5a0"},
}
ORIGINAL_TIMEOUTS={
    1701:{"run":40045716995,"job":120726845017},
    1702:{"run":40046319723,"job":120728754198},
}


def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def require(flag,why):
    if not flag:
        raise ValueError("L9_MIXED_V2_SEAL_REJECT:"+why)

def expect_exact(data:bytes,expected,label:str):
    require(isinstance(expected,str) and len(expected)==64,"RECEIPT_NOT_IMMUTABLY_PINNED_"+label)
    require(sha(data)==expected,"RECEIPT_SHA_DRIFT_"+label)

def finite(x,name):
    require(type(x) in (int,float) and math.isfinite(x) and x>=0,"INVALID_NUMBER_"+name)
    return x

def check_v2(obj:dict,seed:int):
    require(seed in ORIGINAL_TIMEOUTS,"UNKNOWN_SEED")
    identity={
        "schema":V2_SCHEMA,"status":V2_STATUS,"arm":"SMALL_TRANSFORMER",
        "seed":seed,"source_role_sha256":ROLE_SHA,"model_suite_git_blob":SUITE_BLOB,
        "train_count":8480,"select_count":2154,"cross_os_synthetic_prefit_run":V2_PREFIT,
        "selected_metric_is_nonadjudicated_proxy":True,
        "not_interchangeable_with_frozen_v1_receipt":True,
        "new_independent_seal_and_acceptance_required":True,
        "audit_dev_reference_consumed":False,
        "official_test_consumed":False,"scientific_go":False,
        "flops":"NOT_MEASURED","energy":"NOT_MEASURED",
        "fit_receipt_sha256":EXPECTED_FIT[("SMALL_TRANSFORMER",seed)],
        "original_failure_run_id":ORIGINAL_TIMEOUTS[seed]["run"],
        "original_failure_job_id":ORIGINAL_TIMEOUTS[seed]["job"],
    }
    require(type(obj) is dict,"RECEIPT_NOT_OBJECT")
    for k,v in identity.items():
        require(obj.get(k)==v,"V2_IDENTITY_"+k)
    for k in ("original_failure_receipt_sha256","original_workflow_receipt_sha256",
              "original_timeout_log_sha256","synthetic_prefit_receipt_sha256"):
        legacy.require_hex(obj.get(k),k)
    finite(obj.get("python_peak_traced_bytes"),"peak_memory")

    rows=obj.get("all_epoch_metrics")
    require(type(rows) is list and len(rows)==3,"INCOMPLETE_EPOCH_GRID")
    indexed={}
    for r in rows:
        require(type(r) is dict,"EPOCH_NOT_OBJECT")
        e=r.get("epoch")
        require(type(e) is int and e in (4,8,12) and e not in indexed,"BAD_EPOCH")
        for k,v in {"arm":"SMALL_TRANSFORMER","seed":seed,"role":"L9_SELECT",
                    "records":2154,
                    "checkpoint_sha256":FROZEN_CHECKPOINTS[("SMALL_TRANSFORMER",seed)][e],
                    "retained_model_bytes":1721741}.items():
            require(r.get(k)==v,"BAD_EPOCH_ID_"+k)
        h=r.get("triple_proxy_hits");d=r.get("triple_denominator")
        require(type(h) is int and type(d) is int and d==6135 and 0<=h<=d,"BAD_PROXY_COUNT")
        require(r.get("missing_triples_proxy")==d-h,"MISSING_TRIPLES_DRIFT")
        cov=finite(r.get("requested_content_proxy_coverage"),"coverage")
        chrf=finite(r.get("chrf_single_reference_proxy"),"chrf")
        require(0<=cov<=1 and 0<=chrf<=1 and abs(cov-h/d)<=1.1e-9,"PROXY_ARITHMETIC")
        abst=r.get("explicit_abstentions")
        require(type(abst) is int and 0<=abst<=2154,"BAD_ABSTENTIONS")
        require(type(r.get("reference_bytes_evaluated")) is int and
                r["reference_bytes_evaluated"]>0,"REFERENCE_BYTE_COUNT")
        finite(r.get("evaluation_cpu_seconds"),"cpu")
        finite(r.get("evaluation_wall_seconds"),"wall")
        indexed[e]=r
    require(set(indexed)=={4,8,12},"MISSING_EPOCH")
    parity=obj.get("development_equivalence_fixtures")
    require(type(parity) is list and len(parity)==30,"MISSING_OR_DUPLICATE_PARITY")
    pairs=set()
    for x in parity:
        require(type(x) is dict and x.get("identical") is True,"PARITY_MISMATCH")
        pair=(x.get("epoch"),x.get("index"))
        require(pair not in pairs and pair[0] in (4,8,12) and
                pair[1] in PAIR_INDEXES,"PARITY_IDENTITY_DRIFT")
        pairs.add(pair)
    require(pairs=={(e,i) for e in (4,8,12) for i in PAIR_INDEXES},
            "PARITY_GRID_NOT_EXACT")
    best=min(indexed.values(),key=lambda v:(-v["requested_content_proxy_coverage"],
        -v["chrf_single_reference_proxy"],v["missing_triples_proxy"],
        v["retained_model_bytes"],v["epoch"]))
    require(obj.get("selected_epoch")==best["epoch"] and
            obj.get("selected_checkpoint_sha256")==best["checkpoint_sha256"],
            "V2_SELECTION_RULE_DRIFT")
    return {"arm":"SMALL_TRANSFORMER","seed":seed,
        "receipt_type":"SEPARATELY_QUALIFIED_RECOVERY_V2_NOT_V1",
        "selected_epoch":best["epoch"],
        "selected_checkpoint_sha256":best["checkpoint_sha256"],
        "fit_receipt_sha256":EXPECTED_FIT[("SMALL_TRANSFORMER",seed)],
        "requested_content_proxy_coverage":best["requested_content_proxy_coverage"],
        "chrf_single_reference_proxy":best["chrf_single_reference_proxy"],
        "missing_triples_proxy":best["missing_triples_proxy"],
        "explicit_abstentions":best["explicit_abstentions"],
        "original_v1_select_outcome":"CANCELLED_90M_NO_RECEIPT",
        "all_epoch_checkpoint_sha256":{str(e):indexed[e]["checkpoint_sha256"]
                                       for e in (4,8,12)}}


def mixed_seal(candidate_path:Path,receipts:Path,out:Path):
    require(not out.exists(),"NO_OVERWRITE")
    # No seal, not even a provisional one, before original 1701 V2 receipt
    # has a separately authenticated GitHub artifact + canonical receipt SHA.
    require(V2_RECEIPTS[1701] is not None,"PENDING_AUTHENTICATED_V2_SEED_1701")
    candidate_raw=candidate_path.read_bytes()
    expect_exact(candidate_raw,legacy.CANDIDATE_RECEIPT_SHA,"CANDIDATE")
    candidate=legacy.validate_candidate(json.loads(candidate_raw))
    entries=[];hashes={}
    for seed in (1701,1702):
        raw=(receipts/f"GRU_SEQ2SEQ-{seed}.json").read_bytes()
        expect_exact(raw,GRU_RECEIPTS[seed],f"GRU_{seed}")
        obj=json.loads(raw)
        v1=legacy.validate_case(obj,"GRU_SEQ2SEQ",seed)
        require(obj["fit_receipt_sha256"]==EXPECTED_FIT[("GRU_SEQ2SEQ",seed)],
                "GRU_FIT_DRIFT")
        for row in obj["all_epoch_metrics"]:
            require(row["checkpoint_sha256"]==FROZEN_CHECKPOINTS[
                ("GRU_SEQ2SEQ",seed)][row["epoch"]],"GRU_CHECKPOINT_DRIFT")
        v1["receipt_type"]="ORIGINAL_FROZEN_V1"
        entries.append(v1);hashes[f"GRU_SEQ2SEQ-{seed}"]=sha(raw)
    for seed in (1701,1702):
        raw=(receipts/f"SMALL_TRANSFORMER-{seed}.json").read_bytes()
        expect_exact(raw,V2_RECEIPTS[seed],f"TRANSFORMER_V2_{seed}")
        entries.append(check_v2(json.loads(raw),seed))
        hashes[f"SMALL_TRANSFORMER-{seed}"]=sha(raw)
    result={"schema":SCHEMA,"status":"FOUR_CHOICE_MIXED_V1_GRU_V2_TRANSFORMER_DEV_SEALED",
      "candidate_receipt_sha256":legacy.CANDIDATE_RECEIPT_SHA,
      "candidate":candidate,"neural_receipt_sha256":hashes,
      "source_role_sha256":ROLE_SHA,"model_suite_git_blob":SUITE_BLOB,
      "neural_checkpoint_selection":entries,"all_four_choices_complete":True,
      "original_v1_select_seal_complete":False,
      "versioned_v2_admission_required":True,
      "independent_semantic_transfer_proven":False,
      "audit_dev_references_consumed":False,"official_test_consumed":False,
      "scientific_go":False,"flops":"NOT_MEASURED","energy":"NOT_MEASURED",
      "description":"Mixed V1 GRU and post-timeout V2 Transformer lexical development proxy only. Not original V1 scientific evidence."}
    raw=legacy.canonical_bytes(result)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes(raw)
    print("L9_MIXED_V1_V2_FOUR_CHOICE_DEV_SEAL=PASS")
    print("L9_ORIGINAL_V1_SEAL_COMPLETE=FALSE")
    print("L9_AUDIT_DEV_REFERENCE_CONSUMED=FALSE")
    print("L9_SCIENTIFIC_GO=FALSE")
    print("L9_MIXED_DEV_SEAL_SHA256="+sha(raw))
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--candidate-receipt",type=Path,required=True)
    p.add_argument("--neural-receipts-dir",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    mixed_seal(a.candidate_receipt,a.neural_receipts_dir,a.out)

if __name__=="__main__":
    main()
