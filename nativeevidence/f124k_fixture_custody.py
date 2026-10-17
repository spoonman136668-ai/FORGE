"""F124-K immutable fixture-only extended-source qualification receipt.

No protected seeds, no original model inference and no first-use. This cannot
produce independent scientific evidence; it only proves fixture source logic
is stable and honestly reports the unqualified 7-9-hop runtime interface.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import f124h_signed_evidence as original_model
import f124h_source as original_source
import f124k_extended_source as fixture

SCHEMA="forge.research.f124k.fixture-only-long-depth-source-qualification.v1"
GENERATOR_BLOB="b7c665e20c00b74fcff6655dba969a7e3de2c525ffab"
ORIGINAL_MODEL_BLOB="599d7a87f0812f3a7d2c8680861b6360d3640bc0"
ORIGINAL_SOURCE_BLOB="3feab91460f29ec169e1904479a134bb04691937"

def need(ok,code):
    fixture.need(ok,"FROZEN_FIXTURE_CUSTODY_"+code)

def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(",",":"))+"\n").encode()

def blob(module):
    return fixture.git_blob(Path(module.__file__).read_bytes().replace(b"\r\n",b"\n"))

def evidence():
    protocol=fixture.frozen()
    source_blob=blob(fixture)
    need(source_blob==GENERATOR_BLOB,
         "FIXTURE_GENERATOR_GIT_BLOB_DRIFT_"+source_blob)
    need(blob(original_model)==ORIGINAL_MODEL_BLOB,"ORIGINAL_MODEL_GIT_BLOB_DRIFT")
    need(blob(original_source)==ORIGINAL_SOURCE_BLOB,"ORIGINAL_SOURCE_GIT_BLOB_DRIFT")
    preflight=fixture.first_use_preflight()
    need(preflight["protection"]==fixture.AUTHORITY_STATUS
         and not preflight["original_f124h_model_accepts_7_to_9_hops"]
         and not preflight["independent_first_use_receipt_verified"],
         "FALSE_FIRST_USE_READINESS")
    by_lane=[]
    vectors=([1,1,2],[3,2,0])
    for lane in ("Wingless","Yggdrasil"):
        depth=Counter()
        stratum=Counter()
        pair_digests=[]
        min_role_routes=999
        for seed in fixture.FIXTURES[lane]:
            for vector in vectors:
                p,n=fixture.build_fixture(seed,list(vector),lane,
                                          "QUALIFICATION_FIXTURE")
                need(fixture.paired_admit(p,n)
                     and fixture.symbolic_routes(p)==1
                     and fixture.symbolic_routes(n)==0,
                     "PUBLIC_CAUSAL_SOURCE_ADMISSION")
                depth[len(p["roles"])]+=1
                stratum[fixture.STRATA[seed%len(fixture.STRATA)]]+=1
                min_role_routes=min(min_role_routes,
                                    fixture.symbolic_routes(p,True))
                pair_digests.append(hashlib.sha256(canonical([p,n])).hexdigest())
        need(len(pair_digests)==48
             and depth=={7:16,8:16,9:16}
             and sum(stratum.values())==48 and min_role_routes>=5,
             "SOURCE_DEPTH_OR_STRATUM_DISTRIBUTION")
        by_lane.append({"lane":lane,"fixture_pair_count":48,
                        "public_depth_distribution":{str(k):v for k,v in sorted(depth.items())},
                        "strata_distribution":dict(sorted(stratum.items())),
                        "minimum_role_only_structural_routes":min_role_routes,
                        "fixture_source_merkle_witness":hashlib.sha256(
                            canonical(pair_digests)).hexdigest(),
                        "true_positive_paths_each":1,
                        "true_negative_paths_each":0,
                        "source_vector_count":2,
                        "original_model_scored":False,
                        "protected_examples_generated":0})
    return {"schema":SCHEMA,
            "frozen_protocol_git_blob":fixture.PROTOCOL_BLOB,
            "frozen_protocol_sha256":protocol,
            "fixture_generator_git_blob":GENERATOR_BLOB,
            "original_model_git_blob":ORIGINAL_MODEL_BLOB,
            "original_source_git_blob":ORIGINAL_SOURCE_BLOB,
            "source_basis":"QUALIFICATION_FIXTURE_ONLY",
            "first_use_preflight":preflight,
            "original_model_weights_loaded":False,
            "original_model_predictions_computed":False,
            "actual_protected_source_enabled":False,
            "protected_first_use_authorized":False,
            "protected_source_born":False,
            "reserved_examples_built":0,
            "independent_original_scientific_first_use":False,
            "scientific_acceptances":0,
            "accepted_ref_mutations":0,
            "optimizer_promotions":0,
            "Codex_calls":0,"paid_API_calls":0,"new_scheduler":False,
            "controller_contact":False,"mind_palace_writes":0,
            "cloudflare_writes":0,
            "lanes":by_lane}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    output=Path(args.output)
    need(output.parent.is_dir() and not output.exists(),"OUTPUT_ALREADY_EXISTS")
    with output.open("xb") as f:f.write(canonical(evidence()))

if __name__=="__main__":
    try:main()
    except (fixture.Invalid,original_source.Invalid,OSError,ValueError,KeyError,TypeError) as err:
        print("F124K_SOURCE_FIXTURE=QUARANTINED "+str(err),file=sys.stderr)
        raise SystemExit(1)
