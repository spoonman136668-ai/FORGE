"""F124-C bounded authentic TRAIN-only weight custody.

Consumes original F123 Ubuntu TRAIN advisory vectors ONLY by immutable receipt SHA.
The F124-C reserved confirmation cohorts cannot be opened through the trainer.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

import f123_cross_os_custody as prior
import f124c_reconvergent_graph as env
import f124c_node_state_models as model

F123_UBUNTU_RECEIPT="12da879272212b899c6b942004ff38dc21ffa6bb20e7a81eac21d691746b474d"
F123_PARENT_HEAD="7882849a59964f412a87589be653114e7bf64d52"
MODEL_BLOB="76653b7877cbdc092f12a96e4140a38b381bbddf"
GRAPH_BLOB="dbdae03849da6a161f9f3199a5716f55817224bc"
SCHEMA="forge.research.f124c.train-only-learned-node-state-custody.v1"

def require(value,code):
    env.require(value,"TRAIN_CUSTODY_"+code)

def source_blob(path):
    return env.git_blob(Path(path).read_bytes().replace(b"\r\n",b"\n"))

def evidence(reference_dir,source_sha,run_id):
    require(type(source_sha) is str and re.fullmatch(r"[a-f0-9]{40}",source_sha)
            and type(run_id) is int and run_id>0
            and (not os.getenv("GITHUB_SHA") or os.environ["GITHUB_SHA"]==source_sha),
            "CURRENT_GITHUB_SOURCE_UNQUALIFIED")
    freeze=env.frozen()
    require(source_blob(env.__file__)==GRAPH_BLOB
            and source_blob(model.__file__)==MODEL_BLOB,
            "PINNED_MODEL_OR_GRAPH_DRIFT")
    receipt,sha=prior.read_receipt(reference_dir)
    require(sha==F123_UBUNTU_RECEIPT
            and receipt["source_sha"]==F123_PARENT_HEAD
            and receipt["cohorts"]=="TRAIN_ONLY"
            and receipt["confirmation_inputs_generated"]==0
            and len(receipt["lanes"])==2,
            "SOURCE_VECTOR_AUTHENTICATION_FAILED")
    vectors={}
    lineage={}
    for row in receipt["lanes"]:
        lane=row["lane"]
        require(lane in env.TRAIN and lane not in vectors and
                len(row["training_vectors"])==2 and
                len(row["advisory_candidate_source_shas"])==2 and
                row["confirmation_inputs_generated"]==0,
                "AUTHENTIC_VECTORS_MISSING")
        vectors[lane]=row["training_vectors"]
        lineage[lane]=row["advisory_candidate_source_shas"]
    result=model.train_lanes(vectors)
    require(result["phase"]=="TRAIN_ONLY" and
            result["confirmation_examples_generated"]==0 and
            result["scientific_first_use"] is False and
            result["scientific_acceptances"]==0 and
            result["optimizer_promotions"]==0 and
            [r["lane"] for r in result["lanes"]]==["Wingless","Yggdrasil"],
            "UNQUALIFIED_TRAIN_REPORT")
    for lane in result["lanes"]:
        lane["authenticated_advisory_candidate_shas"]=lineage[lane["lane"]]
        require(lane["selected_arm"] in ("A","B")
                and len(lane["arms"])==2 and
                all(x["epochs"]==100 and x["train_pairs"]==48
                    and x["parameters"]<=768 and x["movement"]>0
                    and x["confirmation_examples_generated"]==0
                    for x in lane["arms"].values()),
                "INVALID_TRAINED_PARAMETER_CERTIFICATE")
    result.update({"schema":SCHEMA,
                   "qualifying_source_sha":source_sha,
                   "qualifying_run_id":run_id,
                   "frozen_protocol_sha256":freeze,
                   "f123_reference_receipt_sha256":sha,
                   "graph_git_blob":GRAPH_BLOB,
                   "node_model_git_blob":MODEL_BLOB,
                   "two_slot_collapse_or_invalid_merge_unproven":True,
                   "resource_equivalence_not_established":True,
                   "protected_confirm_untouched":True,
                   "independent_scientific_originals":0,
                   "accepted_ref_mutations":0,
                   "optimizer_promotions":0})
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--f123-ubuntu-dir",required=True)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--run-id",type=int,required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    out=Path(a.output)
    require(out.parent.is_dir() and not out.exists(),"IMMUTABLE_OUTPUT_CONTRACT")
    report=evidence(a.f123_ubuntu_dir,a.source_sha,a.run_id)
    out.write_text(json.dumps(report,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")

if __name__=="__main__":
    try:main()
    except (env.Quarantined,prior.Invalid,ValueError,KeyError,TypeError,OSError) as err:
        print("F124C_TRAIN_WEIGHT_CUSTODY=QUARANTINED "+str(err),file=sys.stderr)
        raise SystemExit(1)
