#!/usr/bin/env python3
"""L9 prospective Transformer SELECT recovery v2, NOT the frozen v1 experiment.

Dormant until the original seed-specific SELECT GitHub job is terminally failed.
No L9_AUDIT_DEV, official TEST, model fit, new weights or changed selection rule.
Distinct receipt schema prevents silently treating the output as frozen-v1 evidence.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import time
import tracemalloc

import l9_model_suite as model
import l9_neural_select_only as v1
import l9_train_select_candidate as source

ORIGINAL_JOBS={1701:{"job_id":120726845017,"run_id":40045716995,"head_sha":"4ff0d88d326ea13c9f24688f0dc2a40250a61705"},
               1702:{"job_id":120728754198,"run_id":40046319723,"head_sha":"393367f0619982a3fb1555f3aa866db2448d23ad"}}
REQUIRED_PREFIT_RUN=40050110176
REQUIRED_PREFIT_HEAD="3e3c207cfc5b025bc6ce7ec8a456a08ca4977c70"
SCHEMA="forge.optimizer.language.l9.transformer-select-encoder-reuse-v2-development-only"

def _require(flag,reason):
    if not flag:raise ValueError(reason)
def _sha(raw):
    return hashlib.sha256(raw).hexdigest()

def assert_admission(seed, original_job_json, original_run_json, prefit_run_json):
    """Independently fetched authenticated GitHub JSON, not operator-written claims.

    Workflow custody MUST fetch these from GitHub REST with actions:read and
    verify original artifact absence. This Python layer independently verifies
    identities and rejects any job still in progress or completed successfully.
    """
    _require(seed in ORIGINAL_JOBS,"unfrozen seed")
    pair=ORIGINAL_JOBS[seed]
    _require(original_job_json.get("id")==pair["job_id"],"original job identity drift")
    _require(original_job_json.get("run_id")==pair["run_id"],"original job/run mismatch")
    _require(original_job_json.get("status")=="completed","ORIGINAL_SELECT_NOT_TERMINAL")
    _require(original_job_json.get("conclusion") in ("failure","timed_out"),"ORIGINAL_SELECT_NOT_FAILED")
    _require(original_run_json.get("id")==pair["run_id"],"original run mismatch")
    _require(original_run_json.get("head_sha")==pair["head_sha"],"original source commit mismatch")
    _require(original_run_json.get("status")=="completed","ORIGINAL_RUN_NOT_TERMINAL")
    _require(original_run_json.get("conclusion") in ("failure","timed_out"),"ORIGINAL_RUN_NOT_FAILED")
    _require(prefit_run_json.get("id")==REQUIRED_PREFIT_RUN,"synthetic prefit run drift")
    _require(prefit_run_json.get("head_sha")==REQUIRED_PREFIT_HEAD,"synthetic prefit source drift")
    _require(prefit_run_json.get("status")=="completed" and prefit_run_json.get("conclusion")=="success","SYNTHETIC_PREFIT_NOT_QUALIFIED")
    return True

def reuse_inference_one(net, triples):
    """Reuse only encoder memory; preserve exact frozen decoder and greedy rule."""
    import torch
    ids=model.encode_source(triples)
    if ids is None:return None
    src=torch.tensor([ids],dtype=torch.long)
    src_mask=(src==model.PAD)
    with torch.inference_mode():
        memory=net.transformer.encoder(net._embed(src),src_key_padding_mask=src_mask)
        token=torch.full((1,1),model.BOS,dtype=torch.long)
        for _ in range(model.MAX_TARGET_BYTES+1):
            tgt_mask=torch.nn.Transformer.generate_square_subsequent_mask(token.shape[1],device=token.device)
            h=net.transformer.decoder(
                net._embed(token),memory,tgt_mask=tgt_mask,
                tgt_key_padding_mask=(token==model.PAD),
                memory_key_padding_mask=src_mask)
            nxt=net.output(h)[:,-1,:].argmax(dim=-1,keepdim=True)
            token=torch.cat([token,nxt],dim=1)
            if bool((nxt==model.EOS).all()):break
    return model.decode_generated(token[0,1:].tolist())

def score_epoch(net,examples,proxies):
    """Full 2,154 frozen SELECT records, no subsampling or semantic criterion drift."""
    _require(len(examples)==2154 and all(x.role=="L9_SELECT" for x in examples),"non-SELECT role")
    hit=denom=refbytes=abstentions=0; chrf=0.0
    start=time.perf_counter();cpu=time.process_time()
    for ex in examples:
        output=reuse_inference_one(net,ex.triples)
        if output is None:abstentions+=1
        h,n=source.coverage(output,ex.triples,proxies)
        hit+=h;denom+=n;chrf+=source.chrf(output,ex.reference)
        refbytes+=len(ex.reference.encode("utf-8"))
    _require(denom>0,"zero SELECT denominator")
    return {
        "role":"L9_SELECT","records":2154,"triple_denominator":denom,
        "triple_proxy_hits":hit,"requested_content_proxy_coverage":round(hit/denom,9),
        "missing_triples_proxy":denom-hit,
        "chrf_single_reference_proxy":round(chrf/2154,9),
        "explicit_abstentions":abstentions,"reference_bytes_evaluated":refbytes,
        "evaluation_wall_seconds":round(time.perf_counter()-start,3),
        "evaluation_cpu_seconds":round(time.process_time()-cpu,3),
    }

def run(repo, artifact, seed, out, original_job_path, original_run_path, prefit_run_path):
    _require(seed in ORIGINAL_JOBS,"unfrozen seed")
    _require(not out.exists(),"no receipt overwrite")
    raw=[p.read_bytes() for p in (original_job_path,original_run_path,prefit_run_path)]
    assert_admission(seed,*[json.loads(x) for x in raw])
    import torch
    _require(torch.__version__.split("+")[0]=="2.5.1" and not torch.cuda.is_available(),"torch frozen runtime drift")
    torch.set_num_threads(2)
    examples,_=source.load_train_select(repo)
    train=[x for x in examples if x.role=="L9_TRAIN"]
    select=[x for x in examples if x.role=="L9_SELECT"]
    _require(len(train)==8480 and len(select)==2154,"role counts drift")
    model.assert_audit_not_used(train+select)
    proxies=source.relation_proxies(model.fit_candidate(train))
    rows=[];parity_cases=[]
    tracemalloc.start()
    for epoch in (4,8,12):
        net,info=v1.model_from_checkpoint("SMALL_TRANSFORMER",seed,epoch,artifact)
        # Parity fixtures are chosen before viewing any metrics. They use SELECT
        # inputs, and equal-output assertions; no SELECT output is stored.
        parity_indexes=(0,1,53,217,431,719,1077,1435,1795,2153)
        for index in parity_indexes:
            a=v1.inference_one(net,"SMALL_TRANSFORMER",select[index].triples)
            b=reuse_inference_one(net,select[index].triples)
            _require(a==b,"FAIL_CLOSED_ORIGINAL_OUTPUT_MISMATCH epoch=%s index=%s"%(epoch,index))
            parity_cases.append({"epoch":epoch,"index":index,"identical":True})
        metrics=score_epoch(net,select,proxies)
        rows.append({"arm":"SMALL_TRANSFORMER","seed":seed,"epoch":epoch,
            "checkpoint_sha256":info["inference_sha256"],
            "retained_model_bytes":info["inference_bytes"],**metrics})
        del net
    peak=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
    best=min(rows,key=lambda x:(-x["requested_content_proxy_coverage"],
                -x["chrf_single_reference_proxy"],x["missing_triples_proxy"],
                x["retained_model_bytes"],x["epoch"]))
    r={
        "schema":SCHEMA,"status":"PROSPECTIVE_RECOVERY_SELECT_NOT_V1_EVIDENCE",
        "original_failure_job_id":ORIGINAL_JOBS[seed]["job_id"],
        "original_failure_run_id":ORIGINAL_JOBS[seed]["run_id"],
        "original_failure_receipt_sha256":_sha(raw[0]),
        "original_workflow_receipt_sha256":_sha(raw[1]),
        "cross_os_synthetic_prefit_run":REQUIRED_PREFIT_RUN,
        "synthetic_prefit_receipt_sha256":_sha(raw[2]),
        "source_role_sha256":v1.ROLE_SHA,"model_suite_git_blob":v1.SUITE_BLOB,
        "arm":"SMALL_TRANSFORMER","seed":seed,
        "train_count":8480,"select_count":2154,
        "selected_epoch":best["epoch"],
        "selected_checkpoint_sha256":best["checkpoint_sha256"],
        "all_epoch_metrics":rows,
        "development_equivalence_fixtures":parity_cases,
        "selected_metric_is_nonadjudicated_proxy":True,
        "fit_receipt_sha256":_sha((artifact/"receipt.json").read_bytes()),
        "python_peak_traced_bytes":peak,"flops":"NOT_MEASURED","energy":"NOT_MEASURED",
        "audit_dev_reference_consumed":False,"official_test_consumed":False,
        "not_interchangeable_with_frozen_v1_receipt":True,
        "new_independent_seal_and_acceptance_required":True,"scientific_go":False
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    data=model.canonical_json_bytes(r);out.write_bytes(data)
    print("L9_PROSPECTIVE_TRANSFORMER_SELECT_V2=RECOVERY_ONLY")
    print("L9_NO_AUDIT_REFERENCE_CONSUMED=TRUE")
    print("L9_V1_SEAL_REQUIRES_DISTINCT_REQUALIFICATION=TRUE")
    print("L9_V2_RECEIPT_SHA256="+_sha(data))
    return r

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--webnlg-repo",type=Path,required=True)
    p.add_argument("--checkpoint-artifact",type=Path,required=True)
    p.add_argument("--seed",type=int,choices=(1701,1702),required=True)
    p.add_argument("--original-job-json",type=Path,required=True)
    p.add_argument("--original-run-json",type=Path,required=True)
    p.add_argument("--prefit-run-json",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    run(a.webnlg_repo,a.checkpoint_artifact,a.seed,a.out,a.original_job_json,a.original_run_json,a.prefit_run_json)
if __name__=="__main__":main()
