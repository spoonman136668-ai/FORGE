"""F124-BQ fresh-process CPU/RSS feasibility before registered source birth.

SOURCE-NEUTRAL synthetic public fixture ONLY. Both arms get identical 48
public pairs, same positive and same-inventory hard-negative native graph.
Actual original AZ abstention remains scientific policy; do not treat an AZ
abstention as equivalent successful native scoring. This is a cost *screen*,
never OOD science or full matched-compute acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import statistics
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
NATIVE=ROOT/"nativeevidence"
ARMS=("AZ","compact")
REPS=3
MODEL=(53,37,41,19,0,1)
NOISE=(1,6,14,19,28,37)


def need(x,label):
    if not x:raise RuntimeError("F124BQ_RESOURCE_"+label)


def bits(x):
    return [(x>>i)&1 for i in range(16)]


def _mod():
    spec=importlib.util.spec_from_file_location(
        "bq_synthetic_algebraic_program",HERE/"f124bq_compact_learner.py")
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def graph_and_public():
    # Fixed synthetic nonregistered seed; does NOT import any source family.
    m=_mod()
    rng=random.Random(138962414)
    xs=rng.sample(range(65536),48)
    support=[(x,m.forward(x,MODEL)^(1 if j in NOISE else 0))
             for j,x in enumerate(xs)]
    roles=[f"rel_task_4ab33861fa92:synthetic{j}" for j in range(7)]
    carries=rng.sample(range(65536),8)
    chain=[{"from":f"n{j}","to":f"n{j+1}","role":roles[j],
            "src_bits":bits(m.forward(carries[j],MODEL)),
            "dst_bits":bits(carries[j+1])} for j in range(7)]
    decoy=rng.randrange(65536)
    while decoy==carries[3]:decoy=rng.randrange(65536)
    detached=[{"from":"outside"+str(j),"to":"sink"+str(j),
               "role":roles[(3+j)%7],
               "src_bits":bits(m.forward(decoy if j==0 else rng.randrange(65536),MODEL)),
               "dst_bits":bits(rng.randrange(65536))} for j in range(6)]
    import copy
    false=copy.deepcopy(chain+detached)
    false[3]["src_bits"],false[7]["src_bits"]=false[7]["src_bits"],false[3]["src_bits"]
    demos=[{"input_bits":bits(x),"output_bits":bits(y)}
           for x,y in support[:24]]
    g={"start":"n0","target":"n7","roles":roles,"edges":chain+detached,"demos":demos}
    h={**g,"edges":false}
    def sha(v):
        return hashlib.sha256(json.dumps(
            v,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return support,g,h,sha({"support":support,"positive":g,"hard":h})


def child(arm):
    need(sys.platform=="linux" and arm in ARMS,"SCOPED_LINUX")
    import resource
    t0=time.process_time_ns()
    pairs,yes,no,identity=graph_and_public()
    sys.path.insert(0,str(NATIVE))
    import f124az_joint_public_inverse as az
    import f124ag_transition_models as native
    import f124aj_example_operator_learner as parser
    demos=[{"input_bits":bits(x),"output_bits":bits(y)}
           for x,y in pairs]
    base=[0.4,0.9,0.65,0.75,0.8,0.2,-0.5]
    delta=[0.0,0.0]
    if arm=="AZ":
        fitted=az.train(demos,"BP-SYNTHETIC-ONLY",0)
        p,pwork,_=az.score(yes,base,delta,fitted,demos)
        q,qwork,_=az.score(no,base,delta,fitted,demos)
        trace={"original_policy_route":fitted["choice"],
               "genuine_AZ_original_scoring":True,
               "native_executed":int(pwork is not None)+int(qwork is not None),
               "positive_accepted":p>=0,"hard_false_positive":q>=0,
               "forcibly_overridden_scoring":False}
    else:
        learner=_mod()
        fitted,fit_receipt,plausible=learner.learn(pairs[:40],pairs[40:])
        need(fitted is not None,"COMPACT_SYNTHETIC_NOT_FIT")
        need(fit_receipt["state_bits"]==32
             and fit_receipt["confidence_models"]>=1,
             "COMPACT_UNQUALIFIED_STATE")
        outcomes=[]
        work=[]
        for graph in (yes,no):
            okay,judgment=learner.causal_consensus(graph,fitted,plausible)
            parsed,public,nonce=parser.public_task(graph)
            need(public==demos[:24],"ORIGINAL_NATIVE_PUBLIC_PARSER")
            native.frozen.prior.parent.validate_15(parsed)
            for edge in parsed["edges"]:
                y=sum(b<<i for i,b in enumerate(edge["src_bits"]))
                x=learner.inverse(y,fitted)
                edge["src_bits"]=bits(x)
            native.frozen.prior.parent.validate_15(parsed)
            score,raw,ratio,counts=native.ygg_transition(
                parsed,list(base),list(delta),.1)
            need(math.isfinite(score)
                 and counts["max_active"]<=7
                 and counts["max_retained"]<=9,
                 "NATIVE_7_ACTIVE_9_RETAINED")
            outcomes.append(okay)
            work.append({"counts":counts,"confidence":judgment})
        need(outcomes==[True,False],"SYNTHETIC_CAUSAL_BOUNDARY")
        trace={"learned_parameter_bits":32,
               "genuine_native_scorer_calls":2,
               "native_trace":work,
               "positive_accepted":outcomes[0],
               "hard_false_positive":outcomes[1],
               "source_oracle_to_learner":False}
    cpu=time.process_time_ns()-t0
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    need(cpu>0 and rss>0,"OS_COST")
    return {
      "schema":"mass.f124bq.source-neutral-fulltask-resource-sample.v1",
      "arm":arm,"public_graph_identity":identity,
      "process_CPU_ns":cpu,"peak_whole_process_RSS_bytes":rss,
      "trace":trace,"original_source_case_executed":False,
      "old_BM_BN_BO_firstuse_replayed":False,
      "protected_128_cohort_generated":False,
      "scientific_accepted":False}


def measure(samples):
    need(len(samples)==2*REPS,"SAMPLE_COUNT")
    summary={}
    for arm in ARMS:
        group=[r for r in samples if r["arm"]==arm]
        need(len(group)==REPS,"EXACT_TRIALS")
        need(len({r["public_graph_identity"] for r in group})==1,
             "NONDETERMINISTIC_SYNTHETIC_PUBLIC_GRAPH")
        summary[arm]={
          "CPU_ns_samples":[r["process_CPU_ns"] for r in group],
          "RSS_bytes_samples":[r["peak_whole_process_RSS_bytes"] for r in group],
          "CPU_ns_median":statistics.median(r["process_CPU_ns"] for r in group),
          "RSS_bytes_median":statistics.median(
              r["peak_whole_process_RSS_bytes"] for r in group),
          "RSS_bytes_max":max(r["peak_whole_process_RSS_bytes"] for r in group),
          "public_graph_identity":group[0]["public_graph_identity"]
        }
    a=summary["AZ"]
    b=summary["compact"]
    need(a["public_graph_identity"]==b["public_graph_identity"],
         "NOT_MATCHED_SYNTHETIC_TASK")
    rss_screen=b["RSS_bytes_median"]<=a["RSS_bytes_median"] and (
        b["RSS_bytes_max"]<=a["RSS_bytes_max"])
    cpu_screen=b["CPU_ns_median"]<=a["CPU_ns_median"]
    return {
      "schema":"mass.f124bq.source-neutral-OS-resource-feasibility.v1",
      "samples":len(samples),"fresh_process_each_sample":True,
      "per_arm":summary,
      "CPU_prebirth_screen":cpu_screen,"RSS_prebirth_screen":rss_screen,
      "both_resource_screens":cpu_screen and rss_screen,
      "AZ_original_may_abstain_no_forced_scoring":True,
      "equivalent_native_workload_not_claimed":True,
      "prospective_source_firstuse":False,
      "independent_novelty_or_science":False,
      "preregistered_resource_admission":False,
      "old_BM_BN_BO_BP_source_reused":False,
      "next_action":"Stop before source birth if resource screen false; otherwise separately authenticate two new source births before first-use."
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--child",action="store_true")
    p.add_argument("--arm",choices=ARMS)
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    if a.child:
        need(a.arm is not None,"CHILD_ARM")
        print(json.dumps(child(a.arm),sort_keys=True))
        return
    need(a.output is not None,"FILE")
    obs=[]
    for rep in range(REPS):
        for arm in (ARMS if rep%2==0 else tuple(reversed(ARMS))):
            result=subprocess.run([sys.executable,"-B",str(Path(__file__).resolve()),
                                   "--child","--arm",arm],
                                  cwd=ROOT,text=True,capture_output=True,timeout=120)
            need(result.returncode==0,
                 "CHILD_FAILURE_"+arm+":"+result.stderr[-2500:])
            obs.append(json.loads(result.stdout))
    report={"summary":measure(obs),"raw_samples":obs}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x",encoding="utf-8") as f:
        json.dump(report,f,indent=2,sort_keys=True)
        f.write("\n")
    print("F124BQ_SYNTHETIC_NATIVE_RESOURCE_SAMPLES=6")
    print("F124BQ_SYNTHETIC_CPU_SCREEN="+
          str(report["summary"]["CPU_prebirth_screen"]))
    print("F124BQ_SYNTHETIC_RSS_SCREEN="+
          str(report["summary"]["RSS_prebirth_screen"]))
    print("F124BQ_REGISTERED_SOURCE_USED=false")
    print("F124BQ_SCIENCE_PARITY_ESTABLISHED=false")


if __name__=="__main__":
    main()
