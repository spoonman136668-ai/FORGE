#!/usr/bin/env python3
"""K4T-F1 new preregistered development only: corrected Wingless wire vs R1/controls.

This imports unchanged, source-reviewed K4Y collection and evaluation functions;
all historical K4Y identities remain untouched and cannot be run by this entry.
"""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import sys
import time
import traceback

import k4y_native_affordance as k4y
from k4r_minigrid_source import canon

FROZEN = Path(__file__).with_name("k4t_f1_frozen_corrected_wire.json")
SCHEMA = "mass.lcrm01.k4t-f1.original-corrected-wingless-wire-dev.v1"
FIT = tuple(range(31400, 31424))
CHECK = tuple(range(32400, 32404))
DEV = tuple(range(33400, 33408))
FAMILIES = ("empty", "fourrooms")
METHODS = k4y.METHODS


def protocol():
    p = json.loads(FROZEN.read_text())
    if (p["schema"] != "mass.lcrm01.k4t-f1.frozen-corrected-native-wire-prospective-dev.v1"
        or p["parents"]["K4T_transport_qualified_head"] !=
           "228ad22a05bf449b5556ef44aa03f3bd3c52718b"
        or p["parents"]["K4Y_original_head"] !=
           "b01627841e6014750b3f03bcd58873d08375f93d"
        or p["sources"]["minigrid_commit"] !=
           "7f5853792ea7f04f75614661006d87fcf949f26d"
        or p["cohorts"]["FIT"] != {"from":31400,"to":31423,
            "role":"TRAIN_ONLY","real_source_transitions_per_family":6000}
        or p["cohorts"]["CHECK"]["from"] != 32400
        or p["cohorts"]["CHECK"]["to"] != 32403
        or p["cohorts"]["DEV"]["from"] != 33400
        or p["cohorts"]["DEV"]["to"] != 33407
        or tuple(p["cohorts"]["methods"]) != METHODS
        or tuple(p["cohorts"]["families"]) != FAMILIES
        or p["cohorts"]["legal_actions"] != [0,1,2]
        or p["governance"]["scientific_first_use"] is not False
        or p["governance"]["scientific_accepted"] is not False
        or p["governance"]["public_development_only"] is not True):
        raise ValueError("K4T_F1_SOURCE_OR_PREREG_DRIFT")
    for key, old in (("wingless_R1","8d1845d82dd8578a709b00e8841bdc5edc8dbc10"),
                     ("wingless_R2","e1564172079359ca4c450dcc87487a4733210584"),
                     ("yggdrasil_R1","3aa22b1e418a7f8cd9619c476f02b8c614917b16"),
                     ("yggdrasil_R2","f7e47dfef309e1c0bcc871d518154fd950b3eca0")):
        if p["sources"]["native_sources"][key]["blob"] != old:
            raise ValueError("K4T_F1_ORIGINAL_NATIVE_BLOB_DRIFT")
    return p


def decide(q):
    if q.get("result") != "COMPLETE_PROSPECTIVE_NATIVE_AFFORDANCE_EVALUATION":
        return {"result":"FIT_ORIGINAL_SOURCE_INELIGIBLE_NO_HELDOUT_ADVANCEMENT",
                "criteria":{}, "scientific_accepted":False}
    original = q["source_science"]["results"]
    criteria = {}
    for fam in FAMILIES:
        vals=original[fam]
        a,b = vals["wingless_r1"], vals["wingless_r2"]
        ctr=vals["fit_dynamics_bfs"]
        criteria[fam+"_blocked_reduction_ge_30pct"] = (
            b["blocked_forward_per_100_steps"] <= .7*a["blocked_forward_per_100_steps"])
        criteria[fam+"_four_goals"] = b["successes"] >= 4
        criteria[fam+"_75pct_fitted_planner_reward"] = (
            b["mean_real_reward"] >= .75*ctr["mean_real_reward"])
        criteria[fam+"_competent_fitted_control"] = ctr["successes"] >= 6
    delta = sum(original[f]["wingless_r2"]["successes"] -
                original[f]["wingless_r1"]["successes"] for f in FAMILIES)
    criteria["two_additional_real_goals"] = delta>=2
    positive = all(criteria.values())
    return {
        "result": ("BOUNDED_CORRECTED_WINGLESS_AFFORDANCE_TRANSFER_DEVELOPMENT_ONLY_NOT_NOVELTY"
                   if positive else "NO_CORRECTED_WINGLESS_AFFORDANCE_TRANSFER_DEMONSTRATION"),
        "criteria":criteria, "goal_completion_delta":delta,
        "scientific_first_use":False, "scientific_accepted":False,
        "original_K4Y_failed_disposition_preserved":True,
        "novelty_and_causal_ablation_not_qualified":True
    }


def experiment(bin_r1, bin_r2, ygg_source):
    p=protocol()
    sys.path.insert(0,str(ygg_source.resolve()))
    if k4y.SEEDS["FIT"][0] != 11400:
        raise ValueError("K4T_F1_ORIGINAL_K4Y_MODULE_ALREADY_MUTATED")
    # Training-only mutation of the development probe's local Python process,
    # never historical frozen modules on disk or any protected source.
    k4y.SEEDS = {"FIT":FIT,"CHECK":CHECK,"DEV":DEV}
    q=k4y.experiment(bin_r1,bin_r2)
    q["schema"],q["gate"] = SCHEMA,"LCRM01-K4T-F1"
    q["protocol_sha256"]=hashlib.sha256(FROZEN.read_bytes()).hexdigest()
    q["source_minigrid_commit"]=p["sources"]["minigrid_commit"]
    q["original_native_blobs"]={k:v["blob"] for k,v in
                                 p["sources"]["native_sources"].items()}
    q["source_transport_qualified_head"]=p["parents"]["K4T_transport_qualified_head"]
    q["original_K4Y_no_go_unmodified"]=True
    q["original_K4U_K4X_no_go_unmodified"]=True
    q["scientific_first_use"],q["scientific_accepted"]=False,False
    q["wingless_only_preregistered_disposition"]=decide(q)
    return q


def main():
    a=argparse.ArgumentParser()
    a.add_argument("--wingless-r1",type=Path,required=True)
    a.add_argument("--wingless-r2",type=Path,required=True)
    a.add_argument("--yggdrasil-source",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    args=a.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        raise ValueError("K4T_F1_NONFRESH_EVIDENCE")
    cpu=time.process_time();wall=time.perf_counter()
    try:
        q=experiment(args.wingless_r1,args.wingless_r2,args.yggdrasil_source)
    except Exception as exc:
        q={"schema":SCHEMA,"gate":"LCRM01-K4T-F1",
           "result":"ORIGINAL_SOURCE_OR_INFRASTRUCTURE_BLOCKED",
           "error_type":type(exc).__name__,"error":str(exc),
           "traceback_tail":traceback.format_exc().splitlines()[-16:],
           "scientific_first_use":False,"scientific_accepted":False}
    q["resources"]={
      "whole_wall_seconds":time.perf_counter()-wall,
      "python_process_CPU_seconds_excludes_all_Go_bridge_subprocesses":time.process_time()-cpu,
      "peak_Python_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024}
    args.output.write_text(json.dumps(q,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("K4T_F1_SOURCE_DISPOSITION="+q["result"])
    if "wingless_only_preregistered_disposition" in q:
        print("K4T_F1_WINGLESS="+q["wingless_only_preregistered_disposition"]["result"])
        print("K4T_F1_REAL_RESULTS="+canon({
         f:{m:q["source_science"]["results"][f][m] for m in
            ("wingless_r1","wingless_r2","fit_tabular_q","fit_dynamics_bfs")}
         for f in FAMILIES}) if "source_science" in q else "{}")
    return int(q["result"]=="ORIGINAL_SOURCE_OR_INFRASTRUCTURE_BLOCKED")


if __name__=="__main__":
    raise SystemExit(main())
