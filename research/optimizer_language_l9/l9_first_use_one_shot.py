#!/usr/bin/env python3
"""One-shot L9 unfamiliar-category numeric evaluation, dormant until qualified.

Graph-only inference for all seven frozen arms completes before any human
reference is parsed. No official TEST access, learning, tuning, raw corpus,
source graph, reference or prediction persistence. No scientific GO.
"""
from __future__ import annotations
import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import time
import tracemalloc
import xml.etree.ElementTree as ET

import l9_model_suite as model
import l9_split_builder as split
import l9_train_select_candidate as dev
import l9_first_use_scoring_core as scoring
import l9_first_use_source_pipeline as pipe
import l9_audit_pre_admission as admission

PRE_ADMISSION_SHA="910a5bc252b43818a8af7d4783dd4f25208c590e9b48f019bafd85faead7428f"
CANDIDATE_RECEIPT_SHA="01f08870677067ca0f0dcfdff004d1ef04cea8465da0d025f904634e2bcd5d47"
SEAL_SHA=admission.SEAL_RAW_SHA256
QUALIFIED_TORCH="2.5.1"
EXPECTED_CANDIDATE_FIT_SHA=pipe.CANDIDATE_STATE_SHA
EXPECTED_RETRIEVAL_FIT_SHA=pipe.RETRIEVAL_STATE_SHA
RUN_SCHEMA="forge.optimizer.language.l9.unfamiliar-category-one-shot-numeric-v1"

def require(ok,desc):
    if not ok:raise ValueError("L9_FIRST_USE_BLOCKED:"+desc)
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
def attest_pre_admission(contract:Path,seal:Path,pre:Path,candidate_receipt:Path):
    require(sha(seal.read_bytes())==SEAL_SHA,"sealed SELECT bytes changed")
    admission.validate_contract_bytes(contract.read_bytes())
    admission.validate_seal_bytes(seal.read_bytes())
    raw=pre.read_bytes()
    require(sha(raw)==PRE_ADMISSION_SHA,"pre-admission receipt bytes changed")
    j=json.loads(raw)
    require(j.get("schema")=="forge.optimizer.language.l9.audit-prospective-pre-admission-v1"
            and j.get("audit_reference_read_count")==0
            and j.get("audit_first_use_allowed") is False
            and j.get("official_test_consumed") is False
            and j.get("scientific_go") is False
            and j.get("seal_sha256")==SEAL_SHA
            and j.get("contract_git_blob")==admission.CONTRACT_GIT_BLOB,
            "invalid pre-admission metadata")
    raw_candidate=candidate_receipt.read_bytes()
    require(sha(raw_candidate)==CANDIDATE_RECEIPT_SHA,"candidate receipt bytes drift")
    c=json.loads(raw_candidate)
    require(c.get("schema")=="forge.optimizer.language.l9.train-select-development-v1"
            and c.get("state_sha256")=={
              "candidate":EXPECTED_CANDIDATE_FIT_SHA,
              "retrieval":EXPECTED_RETRIEVAL_FIT_SHA
            } and c.get("candidate_config_selected")==admission.CONFIG,
            "frozen trained-fit state/config drift")
    return True

def original_refs_reader(repo:Path):
    """No lex text is accessed before every model has finished generating."""
    @lru_cache(maxsize=90)
    def blob_entries(oid):
        require(type(oid) is str and len(oid)==40,"reference OID")
        root=ET.fromstring(dev.git_bytes(repo,oid))
        return list(root.iter("entry"))
    def reference_for(graph:pipe.GraphOnly):
        entries=blob_entries(graph.blob_oid)
        require(0<=graph.entry_index<len(entries),"reference ordinal")
        e=entries[graph.entry_index]
        cat=split.norm_category(e.attrib.get("category",""))
        triples=tuple(split.parse_triple(t.text or "") for t in e.findall("./modifiedtripleset/mtriple"))
        require(cat==graph.category and split.graph_identity(triples)==graph.graph_sha256,
                "heldout reference graph identity mismatch")
        refs=tuple(split.norm_text("".join(node.itertext())) for node in e.findall("./lex"))
        require(bool(refs) and all(refs),"missing heldout human reference")
        return refs
    return reference_for

def run(repo:Path,artifacts:Path,contract:Path,seal:Path,preadmission:Path,
        candidate_receipt:Path,out:Path,authorized:bool=False):
    """Blocked by default. The only live path is a separately qualified
    GitHub Actions workflow with authenticated source/artifact custody."""
    require(authorized is True,"unqualified one-time execution")
    require(not out.exists(),"one-shot receipt already exists")
    attest_pre_admission(contract,seal,preadmission,candidate_receipt)
    require(repo.is_dir() and artifacts.is_dir(),"required source/checkpoint paths")
    import torch
    require(torch.__version__.split("+")[0]==QUALIFIED_TORCH
            and not torch.cuda.is_available(),"frozen CPU runtime")
    torch.set_num_threads(2)
    train_select,summary=dev.load_train_select(repo)
    train=[row for row in train_select if row.role=="L9_TRAIN"]
    select=[row for row in train_select if row.role=="L9_SELECT"]
    require(len(train)==8480 and len(select)==2154,"source role counts")
    require(summary.get("role_identity_sha256")==pipe.ROLE_SHA,"source role digest")
    train_graphs={split.graph_identity(tuple((t.subject,t.predicate,t.object)
                  for t in row.triples)) for row in train_select}
    require(bool(train_graphs),"train SELECT graph custody empty")

    start=time.perf_counter();start_cpu=time.process_time()
    tracemalloc.start()
    candidate,retrieval,proxies=pipe.fit_frozen_train_states(train)
    fit_wall=time.perf_counter()-start
    fit_cpu=time.process_time()-start_cpu
    require(sha(model.canonical_json_bytes(candidate))==EXPECTED_CANDIDATE_FIT_SHA,
            "original candidate learned state mismatch")
    require(sha(model.canonical_json_bytes(retrieval))==EXPECTED_RETRIEVAL_FIT_SHA,
            "original retrieval learned state mismatch")

    nets=pipe.load_exact_neural_checkpoints(artifacts)
    render=pipe.frozen_renderers(candidate,retrieval,nets)
    graphs,categories,split_summary=pipe.load_graph_only(
        repo,train_graphs,Path(__file__).resolve().parent/"L9_BLOB_MANIFEST.json")
    require(split_summary["role_identity_sha256"]==pipe.ROLE_SHA,"role changed on graph reload")
    require(len(graphs)==319 and len(categories)==3,"held-out size/category mismatch")
    input_gate_wall=time.perf_counter()-start
    # No human reference extracted by the source adapter; only graph triples
    # are seen by the seven preselected inference functions.
    preds=pipe.prediction_only_pass(graphs,render,train_graphs)
    prediction_wall=time.perf_counter()-start
    require(tuple(preds)==scoring.ARMS and all(len(v)==319 for v in preds.values()),
            "incomplete model predictions")
    # This is the ONLY phase that intentionally accesses protected references.
    cases=pipe.attach_refs_after_prediction(graphs,preds,original_refs_reader(repo),
                          train_graphs)
    require(len(cases)==319,"held-out human reference completeness")
    first_ref_wall=time.perf_counter()-start
    reports=[pipe.score_precomputed_arm(arm,cases,preds,proxies,train_graphs)
             for arm in scoring.ARMS]
    combined=scoring.combine_reports(reports)
    require(combined["arm_count"]==7 and combined["heldout_examples"]==319,
            "seven methods absent after scoring")
    peak_python=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
    # All volatile predictions, original references and triples stay memory-only.
    combined.update({
      "one_shot_schema":RUN_SCHEMA,
      "status":"UNFAMILIAR_AUDIT_NUMERIC_FIRST_USE_NOT_SEMANTIC_GO",
      "selected_checkpoint_epoch":12,
      "pre_admission_sha256":PRE_ADMISSION_SHA,
      "development_select_seal_sha256":SEAL_SHA,
      "trained_candidate_state_sha256":EXPECTED_CANDIDATE_FIT_SHA,
      "trained_retrieval_state_sha256":EXPECTED_RETRIEVAL_FIT_SHA,
      "selected_checkpoint_sha256":{key:info[3] for key,info in pipe.EXPECTED_NEURAL.items()},
      "reconstructed_train_fit_wall_seconds":round(fit_wall,3),
      "reconstructed_train_fit_cpu_seconds":round(fit_cpu,3),
      "model_load_and_graph_custody_wall_seconds":round(input_gate_wall-fit_wall,3),
      "all_seven_arms_prediction_wall_seconds":round(prediction_wall-input_gate_wall,3),
      "reference_read_wall_seconds":round(first_ref_wall-prediction_wall,3),
      "total_pipeline_wall_seconds":round(time.perf_counter()-start,3),
      "total_pipeline_cpu_seconds":round(time.process_time()-start_cpu,3),
      "python_peak_traced_bytes":int(peak_python),
      "resource_energy":"NOT_MEASURED",
      "resource_flops":"NOT_MEASURED",
      "source_reference_leakage_to_model":False,
      "all_seven_methods_completed_before_any_reference_access":True,
      "all_original_references_averaged_per_example":True,
      "additional_entity_mentions_inferred_from_train_vocabulary":"NOT_MEASURED",
      "audit_reference_read_count":319,
      "official_test_consumed":False,
      "scientific_go":False,
      "independent_semantic_adjudication_complete":False,
    })
    # Ensure numerical output contains no reference, graph, prediction,
    # source entry, names or raw dataset fields before writing bytes.
    data=model.canonical_json_bytes(combined)
    require(len(data)<100000,"unexpectedly large numerical-only receipt")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes(data)
    print("L9_FIRST_USE_NUMERIC_AUDIT_COMPLETED=true",flush=True)
    print("L9_SEVEN_METHODS=7 L9_AUDIT_RECORDS=319 L9_CATEGORIES=3",flush=True)
    print("L9_AUDIT_RESULT_SHA256="+sha(data),flush=True)
    print("L9_OFFICIAL_TEST_CONSUMED=false",flush=True)
    print("L9_SCIENTIFIC_GO=false",flush=True)
    return combined

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-repo",type=Path,required=True)
    parser.add_argument("--checkpoint-root",type=Path,required=True)
    parser.add_argument("--contract",type=Path,required=True)
    parser.add_argument("--sealed-select",type=Path,required=True)
    parser.add_argument("--pre-admission",type=Path,required=True)
    parser.add_argument("--candidate-receipt",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--enable-one-shot-after-qualification",action="store_true")
    a=parser.parse_args()
    run(a.source_repo,a.checkpoint_root,a.contract,a.sealed_select,
        a.pre_admission,a.candidate_receipt,a.out,a.enable_one_shot_after_qualification)
if __name__=="__main__":main()
