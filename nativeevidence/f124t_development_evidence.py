"""F124-T original authenticated controls; cloned unchanged F124-S evaluation
with new preregistered cohorts and training signal. Source-only development.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import types

import f124t_absolute_binding as candidate
import f124s_development_evidence as previous

SCHEMA="forge.research.f124t.new-fresh-absolute-causal-mass-development.v1"


def execute(o_path,qg_path):
    spec=candidate.frozen()
    # F124-S original evaluation code and fixed controls reused verbatim;
    # only source adapter and frozen optimizer are changed by F124-T.
    gl_score=dict(previous.scoring.__globals__)
    gl_score["method"]=candidate
    score=types.FunctionType(previous.scoring.__code__,gl_score,
                             previous.scoring.__name__,
                             previous.scoring.__defaults__)
    gl_run=dict(previous.run.__globals__)
    gl_run.update({"method":candidate,"scoring":score,"SCHEMA":SCHEMA})
    runner=types.FunctionType(previous.run.__code__,gl_run,
                              previous.run.__name__,
                              previous.run.__defaults__)
    output=runner(o_path,qg_path)
    need=lambda ok,why:candidate.need(ok,"RECEIPT_"+why)
    need(output["schema"]==SCHEMA and
         output["freeze_git_blob"]==candidate.FREEZE_BLOB and
         len(output["lanes"])==2 and
         not output["resource_matched_superiority_proven"] and
         output["original_model_unchanged"] and
         not output["original_scientific_first_use"] and
         output["protected_examples_generated"]==0,"QUALIFIED_OUTPUT_AUTHORITY")
    output["known_f124s_negative_retained"]=True
    output["source_and_method_separate_from_f124s"]=True
    output["matched_compute_claim"]=False
    for row in output["lanes"]:
        original_delta=row["FIT_training"]
        need(original_delta["genuine_fit_update"] and
             original_delta["nonzero_gradient_steps"]>0 and
             original_delta["fit_pairs"]==48 and
             row["DEV"]["pairs"]==48 and
             row["FIT"]["pairs"]==48 and
             not row["inference_capacity_increase"],"GENUINE_UPDATE_OR_DENOMINATOR")
    return output


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--original-o-receipt",required=True)
    ap.add_argument("--qg-negative-receipt",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    result=execute(args.original_o_receipt,args.qg_negative_receipt)
    target=Path(args.output)
    candidate.need(target.parent.is_dir() and not target.exists(),"IMMUTABLE_OUTPUT")
    raw=json.dumps(result,sort_keys=True,indent=2).encode()+b"\n"
    with target.open("xb") as f:f.write(raw)
    print("F124T_DEVELOPMENT_RECEIPT_SHA256="+hashlib.sha256(raw).hexdigest())
    for row in result["lanes"]:
        d=row["DEV"]["arms"]
        print("F124T_DEV="+row["lane"]+":new="+str(d["new_F124S"]["paired"])+
              "/48:original="+str(d["original_F124O"]["paired"])+
              "/48:prior_ablation="+str(d["prior_ablation"]["paired"])+
              "/48:fixed="+str(d["fixed_12of16"]["paired"])+"/48")


if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as exc:
        print("F124T_FAIL_CLOSED:"+str(exc),file=sys.stderr)
        sys.exit(1)
