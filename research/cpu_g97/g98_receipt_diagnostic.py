#!/usr/bin/env python3
"""G98 test-only diagnosis of immutable G97 development receipts.

No model loading, policy modification, protected cohort or performance re-run.
This reports observable phases; prefill/build/decode timing is not separately
present in G97 receipts and must not be inferred from request wall time.
"""
import json, statistics, sys
from pathlib import Path

STRATA = ("round_robin", "bursty", "mixed", "overflow")

def diagnose(receipt):
    if receipt.get("schema") != "forge.cpu-g97.development.v1" or receipt.get("phase") != "DEVELOPMENT_ONLY":
        raise ValueError("G98_UNTRUSTED_DEVELOPMENT_RECEIPT")
    if receipt.get("heldout_executed") is not False or receipt.get("promotion_allowed") is not False:
        raise ValueError("G98_PROTECTED_BOUNDARY")
    if receipt.get("engineering") != "PASS" or receipt.get("correctness") != "PASS":
        raise ValueError("G98_UNQUALIFIED_RECEIPT")
    report = {"schema":"forge.cpu-g98.diagnostic.v1","phase":"DEVELOPMENT_ONLY",
              "source_sha":receipt.get("source_sha"),
              "development_stream_sha256":receipt.get("development_stream_sha256"),
              "g97_decision":receipt.get("decision"),
              "timing_scope":"observed request_wall_ns and clone_ns only",
              "unobserved":["prefix_prefill_ns","kv_construction_ns","admission_decision_ns",
                            "decode_ns","fallback_ns","overflow_transition_time"],
              "strata":{},"promotion_allowed":False,"heldout_executed":False}
    for name in STRATA:
        group=receipt["strata"][name]
        if not group.get("exact_parity") or len(group["repetitions"])!=4:
            raise ValueError("G98_FROZEN_REPETITION_DRIFT")
        repetitions=[]
        for rep in group["repetitions"]:
            rows=rep["arms"]["g97_overflow_bypass"]["rows"]
            baseline=rep["arms"]["no_cache"]["rows"]
            if len(rows)!=48 or len(baseline)!=48:
                raise ValueError("G98_FROZEN_TRAFFIC_DRIFT")
            categories={"hit":[],"admission":[],"bypass":[]}
            for i,(r,b) in enumerate(zip(rows,baseline)):
                if r["index"]!=i or b["index"]!=i or r["prefix_id"]!=b["prefix_id"] or r["source_row"]!=b["source_row"]:
                    raise ValueError("G98_PAIR_IDENTITY_DRIFT")
                if r["hit"] and (r["admitted"] or r["bypass"]):
                    raise ValueError("G98_INCONSISTENT_CACHE_EVENT")
                kind="hit" if r["hit"] else "admission" if r["admitted"] else "bypass"
                categories[kind].append({"index":i,"prefix_id":r["prefix_id"],
                    "speedup":b["request_wall_ns"]/r["request_wall_ns"],
                    "wall_ns":r["request_wall_ns"],"clone_ns":r["clone_ns"]})
            if sum(map(len,categories.values()))!=48:
                raise ValueError("G98_EVENT_COUNT_DRIFT")
            repetitions.append({"rep":rep["rep"],
                "counts":{k:len(v) for k,v in categories.items()},
                "worst":{k:min(v,key=lambda x:x["speedup"]) if v else None for k,v in categories.items()},
                "median_speedup":{k:statistics.median(x["speedup"] for x in v) if v else None for k,v in categories.items()},
                "admissions_before_index_16":sum(x["index"]<16 for x in categories["admission"]),
                "first_bypass_index":min((x["index"] for x in categories["bypass"]),default=None)})
        report["strata"][name]={"repetitions":repetitions}
    return report

def main():
    if len(sys.argv)!=3:
        raise SystemExit("usage: g98_receipt_diagnostic.py G97_RESULT.json G98_REPORT.json")
    receipt=json.loads(Path(sys.argv[1]).read_text())
    report=diagnose(receipt)
    Path(sys.argv[2]).write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")

if __name__=="__main__":
    main()
