#!/usr/bin/env python3
"""L9 checkpoint SELECT only. Never opens AUDIT_DEV references or official TEST.

Uses frozen l9_model_suite.py implementation and previously checkpointed
GRU/Transformer weights. Full 2,154-case L9_SELECT; no test-derived tuning.
Numerical receipts only; generated references and predictions are not persisted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
try:
    import resource
except ImportError:
    resource = None
import time
import tracemalloc

import l9_model_suite as model
import l9_train_select_candidate as source

ALLOWED_ARMS = ("GRU_SEQ2SEQ", "SMALL_TRANSFORMER")
ALLOWED_SEEDS = (1701,1702)
ALLOWED_EPOCHS = (4,8,12)
ROLE_SHA = "b9995c1846f5e1d99bf8bc4083dde0ebb41140906284bcf050a7ed6fe0efe726"
SUITE_BLOB = "710ce648a30ffc55647f689c5f4aa3ac13b07066"
RECEIPT_SCHEMA = "forge.optimizer.language.l9.neural-select-development-v1"

def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def assert_fit_receipt(receipt: dict, arm: str, seed: int) -> None:
    if not isinstance(receipt, dict):
        raise ValueError("missing signed frozen-fit metadata")
    required = {
        "schema":"forge.optimizer.language.l9.neural-train-only-development-v1",
        "status":"NEURAL_TRAIN_COMPLETE_SELECT_NOT_RUN_DEVELOPMENT_ONLY",
        "arm":arm, "seed":seed,
        "role_identity_sha256":ROLE_SHA,
        "model_suite_git_blob":SUITE_BLOB,
        "source_release_sha":"a7ea49b5ffa5011edf81e8530c59b3552a965023",
        "train_examples":8480, "select_count_loaded_but_unseen_by_fit":2154,
        "select_fidelity_scored":False,
        "audit_dev_reference_consumed":False,
        "official_test_consumed":False,
        "scientific_go":False,
        "model_fit_role":"L9_TRAIN",
        "checkpoint_epochs":[4,8,12],
    }
    for k,v in required.items():
        if receipt.get(k) != v:
            raise ValueError(f"frozen neural fit identity drift: {k}")
    if set(receipt.get("checkpoints",{})) != {"4","8","12"}:
        raise ValueError("missing frozen checkpoint")

def model_from_checkpoint(arm: str, seed: int, epoch: int, artifact: Path):
    if arm not in ALLOWED_ARMS or seed not in ALLOWED_SEEDS or epoch not in ALLOWED_EPOCHS:
        raise ValueError("unfrozen arm/seed/epoch")
    import torch
    receipt=json.loads((artifact/"receipt.json").read_text("utf-8"))
    assert_fit_receipt(receipt,arm,seed)
    info=receipt["checkpoints"][str(epoch)]
    name=f"{arm}-seed{seed}-epoch{epoch}-inference.pt"
    if info["inference_file"] != name:
        raise ValueError("checkpoint file identity mismatch")
    data=(artifact/name).read_bytes()
    if sha(data)!=info["inference_sha256"] or len(data)!=info["inference_bytes"]:
        raise ValueError("checkpoint corrupted or swapped")
    if len(data)>model.INFERENCE_STATE_CEILING:
        raise ValueError("checkpoint size exceeds frozen limit")
    state=torch.load(artifact/name,map_location="cpu",weights_only=True)
    if not isinstance(state,dict) or set(state)!={"model"}:
        raise ValueError("unrecognized model state")
    net=model.build_gru_model() if arm=="GRU_SEQ2SEQ" else model.build_transformer_model()
    net.load_state_dict(state["model"],strict=True)
    net.eval()
    return net, info

def inference_one(net,arm,triples):
    """Frozen greedy decoding in a one-graph, no-padding inference call."""
    import torch
    ids=model.encode_source(triples)
    if ids is None:
        return None
    src=torch.tensor([ids],dtype=torch.long)
    lengths=torch.tensor([len(ids)],dtype=torch.long)
    with torch.inference_mode():
        generated=(net.greedy(src,lengths,max_steps=model.MAX_TARGET_BYTES+1)
                   if arm=="GRU_SEQ2SEQ"
                   else net.greedy(src,max_steps=model.MAX_TARGET_BYTES+1))
    return model.decode_generated(generated[0].tolist())

def compute_select_metric(net, arm, select, proxies):
    """Full SELECT, no subsampling and no model-visible SELECT target text."""
    if not select or any(e.role!="L9_SELECT" for e in select):
        raise ValueError("SELECT role guard failed")
    hit=0; denominator=0; chrf_sum=0.; abstentions=0; ref_bytes=0
    start=time.perf_counter(); cpu=time.process_time()
    for ex in select:
        output=inference_one(net,arm,ex.triples)
        if output is None:
            abstentions+=1
        h,n=source.coverage(output,ex.triples,proxies)
        hit+=h; denominator+=n
        chrf_sum+=source.chrf(output,ex.reference)
        ref_bytes+=len(ex.reference.encode("utf-8"))
    assert denominator>0 and len(select)==2154
    return {
       "role":"L9_SELECT",
       "records":len(select),
       "triple_denominator":denominator,
       "triple_proxy_hits":hit,
       "requested_content_proxy_coverage":round(hit/denominator,9),
       "missing_triples_proxy":denominator-hit,
       "chrf_single_reference_proxy":round(chrf_sum/len(select),9),
       "explicit_abstentions":abstentions,
       "reference_bytes_evaluated":ref_bytes,
       "evaluation_wall_seconds":round(time.perf_counter()-start,3),
       "evaluation_cpu_seconds":round(time.process_time()-cpu,3),
    }

def run(repo: Path, artifact: Path, arm: str, seed: int, out: Path):
    if arm not in ALLOWED_ARMS or seed not in ALLOWED_SEEDS:
        raise ValueError("arm/seed outside frozen contract")
    if out.exists(): raise ValueError("output receipt exists; no overwrites")
    # Source custody, category identities and audit graph hash only.
    # This loader never extracts DEV/AUDIT reference text.
    examples,_=source.load_train_select(repo)
    train=[e for e in examples if e.role=="L9_TRAIN"]
    select=[e for e in examples if e.role=="L9_SELECT"]
    assert len(train)==8480 and len(select)==2154
    model.assert_audit_not_used(train+select)
    lexical_state=model.fit_candidate(train)
    proxies=source.relation_proxies(lexical_state)
    import torch
    torch.set_num_threads(2)
    tracemalloc.start()
    rows=[]
    for epoch in ALLOWED_EPOCHS:
        network,info=model_from_checkpoint(arm,seed,epoch,artifact)
        score=compute_select_metric(network,arm,select,proxies)
        rows.append({"arm":arm,"seed":seed,"epoch":epoch,
            "checkpoint_sha256":info["inference_sha256"],
            "retained_model_bytes":info["inference_bytes"], **score})
        del network
    peak=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
    # Pre-registered lexicographic choice, not tested on held-out audit.
    selected=min(rows,key=lambda v:(-v["requested_content_proxy_coverage"],
                     -v["chrf_single_reference_proxy"],v["missing_triples_proxy"],
                     v["retained_model_bytes"],v["epoch"]))
    result={"schema":RECEIPT_SCHEMA,
        "status":"SELECT_ONLY_DEVELOPMENT_CHECKPOINT_CHOICE",
        "source_role_sha256":ROLE_SHA,"model_suite_git_blob":SUITE_BLOB,
        "arm":arm,"seed":seed,"train_count":len(train),"select_count":len(select),
        "selected_epoch":selected["epoch"],"selected_checkpoint_sha256":selected["checkpoint_sha256"],
        "all_epoch_metrics":rows,
        "selected_metric_is_nonadjudicated_proxy":True,
        "fit_receipt_sha256":sha((artifact/"receipt.json").read_bytes()),
        "python_peak_traced_bytes":peak,
        "rss_linux_kb":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if resource else None,
        "verification_cost_included_in_metric":True,
        "audit_dev_reference_consumed":False,"official_test_consumed":False,
        "flops":"NOT_MEASURED","energy":"NOT_MEASURED",
        "scientific_go":False}
    raw=model.canonical_json_bytes(result)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes(raw)
    print("L9_NEURAL_SELECT_FULL=PASS",flush=True)
    print(f"L9_ARM={arm} L9_SEED={seed} L9_SELECTED_EPOCH={selected['epoch']}",flush=True)
    print("L9_NEURAL_SELECT_RECEIPT_SHA256="+sha(raw),flush=True)
    print("L9_AUDIT_DEV_MODEL_CONSUMPTION=FALSE",flush=True)
    print("L9_OFFICIAL_TEST_CONSUMED=FALSE",flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--webnlg-repo",type=Path,required=True)
    p.add_argument("--checkpoint-artifact",type=Path,required=True)
    p.add_argument("--arm",choices=ALLOWED_ARMS,required=True)
    p.add_argument("--seed",type=int,choices=ALLOWED_SEEDS,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    run(a.webnlg_repo,a.checkpoint_artifact,a.arm,a.seed,a.out)

if __name__=="__main__":main()
