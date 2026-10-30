#!/usr/bin/env python3
"""ACC-68 U26: finite Poincare disk vs identical-coordinate Euclidean parent retrieval.

The tree-structure-derived coordinate embedding is oracle-assisted, NOT learned.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import time

ROOT=Path(__file__).resolve().parents[3]
REGISTRY=ROOT/"research/ac07_sourcefree/ac08_portfolio.py"
PREREG=ROOT/"docs/research/ACC-68-U26-PREREG-20261030.md"
REGISTRY_BLOB="5126c860771fb024ccfc14c3f7ee8925edf29787"
PREREG_COMMIT="dc6119e0c80de7485014383014838ec20287bc1f"
DEPTHS=(4,6,8)
SEEDS=(26011,26013,26017)
SPLIT_DOMAIN=b"forge-acc68-u26-split-v1:"
LABEL_DOMAIN=b"forge-acc68-u26-label-v1:"
RADIAL_ALPHA=.24

def sha(v:bytes)->str:
    return hashlib.sha256(v).hexdigest()

def git_blob(v:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(v)).encode()+b"\0"+v).hexdigest()

def source_custody()->dict:
    if not REGISTRY.is_file() or git_blob(REGISTRY.read_bytes().replace(b"\r\n",b"\n"))!=REGISTRY_BLOB:
        raise RuntimeError("ACC68_ORIGINAL_PORTFOLIO_BLOB_DRIFT")
    if '"hyperbolic infinite memory"' not in REGISTRY.read_text(encoding="utf-8"):
        raise RuntimeError("ACC68_ORIGINAL_U26_MISSING")
    if not PREREG.is_file() or "ACC-68 / U26" not in PREREG.read_text(encoding="utf-8"):
        raise RuntimeError("ACC68_PREREG_MISSING")
    return {"claim":"U26","registry_blob":REGISTRY_BLOB,
            "prereg_commit":PREREG_COMMIT,"research_scope":"SYNTHETIC_TREE_COORDINATE_RETRIEVAL_ONLY"}

def label(seed:int,path:str)->str:
    return sha(LABEL_DOMAIN+struct.pack(">I",seed)+path.encode("ascii"))[:24]

def coord(path:str,max_depth:int)->tuple[float,float]:
    if max_depth not in DEPTHS or len(path)>max_depth or any(ch not in "01" for ch in path):
        raise ValueError("invalid tree coordinate path")
    depth=len(path)
    if depth==0:return (0.0,0.0)
    first_leaf=int(path,2)<<(max_depth-depth)
    count=1<<(max_depth-depth)
    midpoint=(first_leaf+count/2)/(1<<max_depth)
    angle=2*math.pi*midpoint
    r=math.tanh(RADIAL_ALPHA*depth)
    return r*math.cos(angle),r*math.sin(angle)

def split(seed:int,path:str)->str:
    if seed not in SEEDS or any(ch not in "01" for ch in path):raise ValueError("invalid split input")
    h=hashlib.sha256(SPLIT_DOMAIN+struct.pack(">I",seed)+path.encode("ascii")).digest()
    residue=int.from_bytes(h[:4],"big")%5
    return "fit" if residue<=2 else "dev" if residue==3 else "check"

def nodes(depth:int,seed:int)->list[dict]:
    if depth not in DEPTHS or seed not in SEEDS:raise ValueError("unfrozen tree identity")
    result=[]
    for d in range(depth+1):
        for i in range(1<<d):
            path=format(i,"0"+str(d)+"b") if d else ""
            parent=path[:-1] if d else None
            x,y=coord(path,depth)
            result.append({"path":path,"parent":parent,"label":label(seed,path),
                "depth":d,"x":x,"y":y,"fold":split(seed,path)})
    if len(result)!=(1<<(depth+1))-1 or len({n["label"] for n in result})!=len(result):
        raise RuntimeError("TREE_SIZE_OR_LABEL_COLLISION")
    return result

def euclidean(a:tuple[float,float],b:tuple[float,float])->float:
    return math.hypot(a[0]-b[0],a[1]-b[1])

def hyperbolic(a:tuple[float,float],b:tuple[float,float])->float:
    a_norm=a[0]*a[0]+a[1]*a[1]
    b_norm=b[0]*b[0]+b[1]*b[1]
    if a_norm>=1 or b_norm>=1:raise ValueError("outside Poincare disk")
    delta=(a[0]-b[0])**2+(a[1]-b[1])**2
    term=1+2*delta/((1-a_norm)*(1-b_norm))
    return math.acosh(max(1.0,term))

def nearest(query:dict,candidates:list[dict],distance)->str:
    a=(query["x"],query["y"])
    nearest_path=None
    best=float("inf")
    for node in candidates:
        if node["path"]==query["path"]:continue
        dst=distance(a,(node["x"],node["y"]))
        if not math.isfinite(dst) or dst<0:raise RuntimeError("INVALID_DISTANCE")
        # Roundoff-induced apparent distance ties occur on symmetric tree
        # coordinates with platform-specific libm. Canonicalize mathematically
        # equal geometric options by lexical path without consulting gold parent.
        # The 1e-12 absolute tolerance is numerical determinism only, not a
        # change to the source, retrieval candidate set, or admission thresholds.
        eps=1e-12
        if dst<best-eps or (abs(dst-best)<=eps and
                            (nearest_path is None or node["path"]<nearest_path)):
            best=dst
            nearest_path=node["path"]
    if nearest_path is None:raise RuntimeError("EMPTY_RETRIEVAL_CANDIDATES")
    return nearest_path

def quantize(v:float)->int:
    if not -1<v<1:raise ValueError("coordinate outside disk")
    return round(v*32767)

def tree_report(depth:int,seed:int)->dict:
    tree=nodes(depth,seed)
    index={n["path"]:n for n in tree}
    checks=[n for n in tree if n["fold"]=="check" and n["parent"] is not None]
    fold_counts={name:sum(n["fold"]==name for n in tree) for name in ("fit","dev","check")}
    if sum(fold_counts.values())!=len(tree) or not checks:
        raise RuntimeError("INCOMPLETE_SPLIT")
    parent_ok=sum(n["parent"] in index and index[n["parent"]]["depth"]==n["depth"]-1
                  for n in checks)
    if parent_ok!=len(checks):raise RuntimeError("EXACT_INDEX_REFERENCE_INCOMPLETE")
    results={}
    for name,func in (("euclidean",euclidean),("hyperbolic",hyperbolic)):
        nearest(tree[-1],tree,func) # computation warmup only, no training
        t0=time.perf_counter_ns()
        retrieved=[nearest(q,tree,func) for q in checks]
        elapsed=time.perf_counter_ns()-t0
        if elapsed<=0:raise RuntimeError("BAD_CLOCK")
        results[name]={"correct":sum(got==q["parent"] for got,q in zip(retrieved,checks)),
            "accuracy":sum(got==q["parent"] for got,q in zip(retrieved,checks))/len(checks),
            "scan_ns":elapsed,"per_query_ns":elapsed/len(checks),
            "prediction_sha256":sha("\n".join(retrieved).encode()),
            "errors":[{"query_path":q["path"],"gold_parent_path":q["parent"],
                       "predicted_path":got} for got,q in zip(retrieved,checks)
                      if got!=q["parent"]]}
    coord_keys={(quantize(n["x"]),quantize(n["y"])) for n in tree}
    packed=b"".join(struct.pack("<dd",n["x"],n["y"]) for n in tree)
    full_index=json.dumps([(n["label"],label(seed,n["parent"]) if n["parent"] is not None else None)
                     for n in tree],separators=(",",":")).encode()
    input_identity=json.dumps([(n["path"],n["parent"],n["label"],n["fold"],
                                float.hex(n["x"]),float.hex(n["y"])) for n in tree],
                              separators=(",",":")).encode("utf-8")
    check_paths="\n".join(q["path"] for q in checks).encode()
    return {"depth":depth,"seed":seed,"nodes":len(tree),"checks":len(checks),
        "fold_sizes":fold_counts,"check_paths_sha256":sha(check_paths),
        "input_identity_sha256":sha(input_identity),
        "raw_coordinate_binary64_sha256":sha(packed),
        "coord_payload_bytes":len(packed),
        "exact_parent_index_payload_json_bytes":len(full_index),
        "exact_parent_reference_correct":parent_ok,
        "quantized_int16_distinct_pairs":len(coord_keys),
        "quantized_int16_collisions":len(tree)-len(coord_keys),
        "naive_random_parent_expectation":1/(len(tree)-1),
        "euclidean":results["euclidean"],"hyperbolic":results["hyperbolic"],
        "hyperbolic_minus_euclidean_accuracy":results["hyperbolic"]["accuracy"]-results["euclidean"]["accuracy"],
        "hyperbolic_over_euclidean_latency":results["hyperbolic"]["scan_ns"]/results["euclidean"]["scan_ns"],
        "candidate_pass":results["hyperbolic"]["accuracy"]-results["euclidean"]["accuracy"]>=.02
                         and results["hyperbolic"]["scan_ns"]<=1.25*results["euclidean"]["scan_ns"]}

def finite_witness()->dict:
    # 2 float64 records have at most 128 raw bits, at most 2**128 bit patterns.
    # No lossless fixed 128-bit label alone can encode all 2**129 arbitrary IDs.
    total=1<<129
    capacity=1<<128
    if not (total>capacity and total-capacity==capacity):
        raise RuntimeError("FINITE_CAPACITY_BOUND_DRIFT")
    return {"fixed_coordinate_payload_bytes_per_node":16,
        "coordinate_bit_pattern_capacity_upper_bound":"2^128",
        "arbitrary_external_ids_challenge":"2^129",
        "injection_for_all_arbitrary_ids_possible":False,
        "distinguishes_all_unbounded_ids":False,
        "infinite_coordinate_precision_assumed":False,
        "variable_growth_or_external_memory_excluded":False}

def report()->dict:
    custody=source_custody()
    witness=finite_witness()
    records=[tree_report(depth,seed) for depth in DEPTHS for seed in SEEDS]
    if len(records)!=9 or any(x["coord_payload_bytes"]!=16*x["nodes"]
                              or x["exact_parent_reference_correct"]!=x["checks"]
                              for x in records):
        raise RuntimeError("RECORD_OR_CONVENTIONAL_CONTROL_INCOMPLETE")
    win=all(x["candidate_pass"] for x in records)
    return {"schema":"forge.acc68.u26.finite-hyperbolic-tree-retrieval.v1",
        "identity":custody,"protocol":{"depths":list(DEPTHS),"seeds":list(SEEDS),
            "alpha":RADIAL_ALPHA,"same_coordinates_for_both_metrics":True,
            "queries":"all nonroot CHECK split; exclude self; all remaining nodes as candidates",
            "source_family":"synthetic oracle-derived balanced binary tree",
            "physical_rss_or_real_lm":False},
        "finite_capacity":witness,"trees":records,
        "classification":{"fixed_float64_pair_infinite_memory":"U26_FINITE_128BIT_COORDINATE_INFINITE_MEMORY_NO_GO",
            "matched_metric_hierarchy_retrieval":"U26_RESTRICTED_HIERARCHY_RETRIEVAL_POSITIVE_ONLY" if win else "U26_NO_GENERAL_VERIFIED_HIERARCHY_RETRIEVAL_WIN",
            "exact_parent_index_reference":"PASS",
            "learned_embeddings":"UNVERIFIED","original_language_memory":"UNVERIFIED",
            "real_pretrained_LLM_speed":"UNVERIFIED","peak_physical_rss_total_cpu":"UNVERIFIED",
            "scientific_first_use":"NOT_ESTABLISHED","scientific_acceptance":"NOT_GRANTED",
            "production_admission":"NOT_GRANTED"},
        "limitations":"Oracle-derived synthetic tree embeddings; geometric retrieval does not learn semantics. "
            "Conventional index uses labels/parent pointers and different operation; it is not a matched timing rival. "
            "No real language model, learned hierarchy, GPU, full CPU/RSS, or infinite representation."}

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--json",required=True,type=Path)
    a=p.parse_args()
    result=report()
    a.json.parent.mkdir(parents=True,exist_ok=True)
    a.json.write_bytes((json.dumps(result,indent=2,sort_keys=True)+"\n").encode("utf-8"))
    print("ACC68_U26_CUSTODY=PASS")
    print("ACC68_U26_TREES="+str(len(result["trees"])))
    print("ACC68_U26_RESULT="+result["classification"]["matched_metric_hierarchy_retrieval"])

if __name__=="__main__":main()
