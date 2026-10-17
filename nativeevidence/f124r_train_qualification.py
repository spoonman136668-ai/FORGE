"""F124-R authenticated advisory -> two-lane public TRAIN-only Sparse-2 model receipt.

Protected F124-R confirmation is unconstructible by this module. This does not
qualify equal-compute performance, scientific first use, or optimizer promotion.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import f118_autonomy_feedback as f118
import f120_generated_environment as f120
import f124r_freeze_admission as freeze
import f124r_train_environment as env
import f124r_sparse_model as model

SCHEMA="forge.autonomy.f124r.sparse2-public-train-custody.v1"

def require(ok,marker):
    env.require(bool(ok),"TRAIN_CUSTODY_"+marker)

def git_blob(file):
    data=Path(file).read_bytes().replace(b"\r\n",b"\n")
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def execute(advisory,sha):
    cfg,freeze_sha=freeze.frozen()
    require(type(sha) is str and re.fullmatch(r"[0-9a-f]{40}",sha)
            and (not os.getenv("GITHUB_SHA") or os.environ["GITHUB_SHA"]==sha),
            "SOURCE_HEAD")
    provenance=f120.validate(advisory,sha)
    require(type(provenance) is dict and set(provenance)=={"Wingless","Yggdrasil"},
            "TWO_SOURCE_LANES")
    lanes=[]
    for lane in ("Wingless","Yggdrasil"):
        entries=provenance[lane]
        require(type(entries) is list and len(entries)==2 and
                all(type(e) is dict and e.get("candidate_index")==i+2
                    and type(e.get("source_candidate_sha256")) is str and
                    re.fullmatch(r"[a-f0-9]{64}",e["source_candidate_sha256"])
                    and type(e.get("vector")) is list for i,e in enumerate(entries)),
                "ADVISORY_CANDIDATE_IDENTITIES")
        vectors=[e["vector"] for e in entries]
        rows=env.train_rows(lane,vectors)
        weights,movement=model.fit(rows)
        scores=model.score(rows,weights)
        require(scores["pairs"]==64 and len(weights)==20 and movement>.0001,
                "FROZEN_FIT_INVALID")
        workload=[]
        for graph,label in rows:
            _,_,detail=model.forward(graph,weights,trace=True)
            workload.append(detail["work"])
        aggregate={key:sum(item[key] for item in workload) for key in workload[0]}
        aggregate["train_graphs"]=len(workload)
        lanes.append({
            "lane":lane,
            "source_candidate_sha256":[e["source_candidate_sha256"] for e in entries],
            "source_vectors":vectors,
            "train_rows_sha256":model.sha(rows),
            "selected_model":"S2","trained_weights":weights,
            "weights_sha256":model.sha(weights),
            "learned_parameter_count":len(weights),
            "optimizer_epochs":model.EPOCHS,
            "weight_movement_l2":round(movement,10),
            "train_scores":scores,
            "primitive_work_instrumentation":aggregate,
            "primitive_counts_comparable_to_dense_control":False,
            "resource_matched_superiority":False,
            "protected_confirm_generated":False,
            "independent_scientific_acceptance":False
        })
    return {
        "schema":SCHEMA,
        "source_commit_sha":sha,
        "f124r_freeze_git_blob":freeze.EXPECTED_FREEZE_BLOB,
        "f124r_freeze_sha256":freeze_sha,
        "environment_git_blob":git_blob(env.__file__),
        "sparse_model_git_blob":git_blob(model.__file__),
        "f123_model_git_blob":git_blob(Path(__file__).with_name("f123_learned_routing.py")),
        "advisory_sha256":model.sha(advisory),
        "phase":"PUBLIC_SYNTHETIC_TRAIN_ONLY",
        "lanes":lanes,
        "protected_confirmation_read":False,
        "scientific_first_use":False,
        "scientific_acceptance":False,
        "optimizer_promotion":False,
        "originals_dispatched":0,
        "accepted_ref_mutations":0,
        "codex_calls":0,
        "paid_model_calls":0,
        "new_scheduler":False
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--advisory",required=True)
    p.add_argument("--source-ref",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    advisory=f118.load_report(args.advisory)
    result=execute(advisory,args.source_ref)
    out=Path(args.output)
    require(out.parent.is_dir() and not out.exists(),"IMMUTABLE_OUTPUT")
    raw=(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n").encode()
    out.open("xb").write(raw)
    print("F124R_TRAIN_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in result["lanes"]:
        print("F124R_"+lane["lane"].upper()+"_TRAIN_PAIRED="+str(lane["train_scores"]["paired_correct"])+"/64")
    print("F124R_CONFIRM_EXECUTED=false")
    print("F124R_RESOURCE_PARITY_PROVEN=false")
    print("F124R_SCIENTIFIC_FIRST_USE=false")

if __name__=="__main__":
    try:
        main()
    except (env.Invalid,freeze.Invalid,f118.Quarantined,f120.Invalid,
            ValueError,KeyError,TypeError,IndexError,OSError) as exc:
        print("F124R_TRAIN_QUARANTINED="+str(exc),file=sys.stderr)
        raise SystemExit(1)
