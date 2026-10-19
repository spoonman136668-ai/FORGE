"""F124-BR original-AZ / original-BQ / lean-native fresh-process screen.

All three arms use the same source-neutral synthetic public graph and fixed
BQ learner. Five truly independent Linux processes per arm. No BM/BN/BO/BP
source, never any BQ source or protected U/R. Preserve exact original AZ
policy (including abstention), don't force diagnostic scoring as science.

The lean arm omits unused original AZ and AJ learner imports, uses one frozen
BQ module per process and lower-allocation native graph parser; it still
executes the EXACT unchanged native scorer on both true and hard-negative
graphs, including original work counters.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import math
import statistics
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
NATIVE=ROOT/"nativeevidence"
REPS=5
ARMS=("AZ","legacy","lean")


def need(ok,msg):
    if not ok:raise RuntimeError("F124BR_NATIVE_COST_"+msg)


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    need(spec and spec.loader,"MODULE_IMPORT")
    result=importlib.util.module_from_spec(spec)
    sys.modules[name]=result
    spec.loader.exec_module(result)
    return result


def sha(obj):
    return hashlib.sha256(json.dumps(
        obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def original_task(lean):
    fixture=module("br_source_neutral_fixture",
                   HERE/"f124bq_resource_prebirth.py")
    if lean:
        frozen=module("br_frozen_BQ_once",
                      HERE/"f124bq_program_learner.py")
        # Avoid the redundant second module import from the graph fixture.
        # Produces byte-for-byte identical synthetic data in ALL arms.
        fixture._mod=lambda:frozen
    else:
        frozen=None
    public,pos,neg,identity=fixture.graph_and_public()
    need(identity==sha({"support":public,"positive":pos,"hard":neg}),
         "SYNTHETIC_TASK_SHA")
    return public,pos,neg,identity,frozen


def one(arm):
    need(sys.platform=="linux" and arm in ARMS,"LINUX_OS_PROCESS")
    import resource
    tic=time.process_time_ns()
    samples,pos,neg,identity,known=original_task(lean=(arm=="lean"))
    base=[0.4,0.9,0.65,0.75,0.8,0.2,-0.5]
    delta=[0.,0.]
    # The original AZ and BR legacy paths retain their exact buffer layout.
    # The lean runtime consumes integer public FIT/CHECK directly and graph
    # demos already contain exactly the required 24 public bit vectors.
    # Do NOT materialize an unused second set of 48 expanded bit vectors.
    demos=([{"input_bits":[(x>>j)&1 for j in range(16)],
             "output_bits":[(y>>j)&1 for j in range(16)]}
            for x,y in samples] if arm!="lean" else None)
    sys.path.insert(0,str(NATIVE))
    trace={}
    if arm=="AZ":
        import f124az_joint_public_inverse as az
        trained=az.train(demos,"BR-SYNTHETIC-NO_SCIENCE",0)
        positive,pwork,_=az.score(pos,base,delta,trained,demos)
        negative,nwork,_=az.score(neg,base,delta,trained,demos)
        trace={"route":trained["choice"],"original_AZ_policy":True,
               "forced_diagnostic":False,
               "native_scorer_calls":int(pwork is not None)+int(nwork is not None),
               "positive_accepted":positive>=0,
               "hard_false_positive":negative>=0}
    else:
        import f124ag_transition_models as native
        if arm=="legacy":
            import f124az_joint_public_inverse as unused_orig_for_parity
            import f124aj_example_operator_learner as parser
            model=module("br_frozen_BQ_legacy",
                         HERE/"f124bq_program_learner.py")
        else:
            model=known
            parser=None
        program,fit_receipt,plausible=model.learn(samples[:40],samples[40:])
        need(program is not None and fit_receipt["state_bits"]==32
             and fit_receipt["confidence_programs"]>=1
             and fit_receipt["learned_from_FIT_only"]
             and fit_receipt["CHECK_can_only_veto"],
             "FROZEN_SOURCEBLIND_BQ_LEARN")
        if arm=="lean":
            # Native graph already embeds its original 24 demonstrations.
            # After frozen fitting/confidence checks the full 48 integer
            # support rows are no longer needed while native scorer runs.
            del samples
        decisions=[
            model.causal_consensus(g,program,plausible)[0]
            for g in (pos,neg)]
        need(decisions==[True,False],"CANONICAL_CAUSAL_HARD_NEGATIVE")
        view=module("br_memory_native_adapter",
                    HERE/"f124br_native_view.py")
        scores=view.score_exact_native_pair(
            (pos,neg),model,program,native,base,delta,
            legacy_parser=parser)
        need(len(scores)==2 and
             all(math.isfinite(item["score"]) for item in scores) and
             all(item["work"]["max_active"]<=7 and
                 item["work"]["max_retained"]<=9 for item in scores),
             "ORIGINAL_NATIVE_COUNTERS")
        trace={
            "route":"frozen_BQ_program",
            "original_AZ_policy":False,
            "source_family_decision":False,
            "native_scorer_calls":2,
            "model_state_bits":fit_receipt["state_bits"],
            "native_scores":[[s["score"],s["raw"],s["ratio"]] for s in scores],
            "native_work":[s["work"] for s in scores],
            "causal_positive_accepted":decisions[0],
            "causal_hard_false_positive":decisions[1]
        }
    cpu=time.process_time_ns()-tic
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    need(cpu>0 and rss>0,"ACTUAL_OS_COST")
    return {"schema":"mass.f124br.native-process-real-OS-sample.v1",
            "arm":arm,"source_neutral_graph_SHA256":identity,
      "python_small_object_allocator":(__import__("os").environ.get(
          "PYTHONMALLOC") or "default"),
            "process_CPU_ns":cpu,"whole_process_peak_RSS_bytes":rss,
            "original_scientific_policy":arm=="AZ",
            "trace":trace,"original_source_case_replayed":False,
            "new_registered_or_protected_firstuse":False,
            "science_accepted":False}


def summarize(rows):
    need(len(rows)==REPS*len(ARMS),"EXPECTED_15_PROCESSES")
    out={}
    for arm in ARMS:
        records=[r for r in rows if r["arm"]==arm]
        need(len(records)==REPS
             and len({r["source_neutral_graph_SHA256"] for r in records})==1,
             "EQUAL_ORIGINAL_GRAPH_AND_FRESH_PROCESSES")
        need(all(r["python_small_object_allocator"]==
                 ("malloc" if arm=="lean" else "default")
                 for r in records),"EXACT_FROZEN_ALLOCATOR_PER_ARM")
        out[arm]={
            "CPU_ns":[r["process_CPU_ns"] for r in records],
            "RSS_bytes":[r["whole_process_peak_RSS_bytes"] for r in records],
            "CPU_median_ns":statistics.median(r["process_CPU_ns"] for r in records),
            "RSS_median_bytes":statistics.median(r["whole_process_peak_RSS_bytes"]
                                                for r in records),
            "CPU_max_ns":max(r["process_CPU_ns"] for r in records),
            "RSS_max_bytes":max(r["whole_process_peak_RSS_bytes"] for r in records),
            "identity":records[0]["source_neutral_graph_SHA256"]
        }
    need(len({v["identity"] for v in out.values()})==1,
         "SOURCE_DRIFT_BETWEEN_ARMS")
    legacy=[r["trace"] for r in rows if r["arm"]=="legacy"]
    lean=[r["trace"] for r in rows if r["arm"]=="lean"]
    need(all(l==legacy[0] for l in legacy)
         and all(l==lean[0] for l in lean)
         and all(l==lean[0] for l in legacy),
         "NATIVE_EXACT_SCORE_AND_COUNTER_PARITY")
    o,a,b=out["AZ"],out["legacy"],out["lean"]
    target=(b["CPU_median_ns"]<=o["CPU_median_ns"]
            and b["RSS_median_bytes"]<=o["RSS_median_bytes"]
            and b["RSS_max_bytes"]<=o["RSS_max_bytes"])
    improvement=(b["CPU_median_ns"]<=a["CPU_median_ns"]
                 and b["RSS_median_bytes"]<=a["RSS_median_bytes"]
                 and b["RSS_max_bytes"]<=a["RSS_max_bytes"])
    return {
      "schema":"mass.f124br.source-neutral-native-memory-optimization.v1",
      "sample_count":15,"fresh_process_samples_per_arm":5,
      "arms":out,"legacy_and_lean_native_score_work_exact":True,
      "legacy_and_lean_causal_decisions_exact":True,
      "lean_source_neutral_os_nonregression_vs_original_AZ":target,
      "lean_os_nonregression_vs_original_BQ_legacy":improvement,
      "AZ_scientific_abstention_preserved":True,
      "AZ_and_candidate_native_work_not_equivalent":True,
      "full_scientific_resource_parity":False,
      "old_BM_BN_BO_BP_BQ_cases_replayed":False,
      "new_prospective_or_protected_cases_used":False,
      "scientific_admission":False,"optimizer_promotion":False,
      "disposition":("SOURCE_NEUTRAL_SCREEN_PASS_ONLY" if target and improvement
                     else "RESOURCE_INELIGIBLE_STOP_BEFORE_NEW_SOURCE")
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--child",action="store_true")
    p.add_argument("--arm",choices=ARMS)
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    if a.child:
        need(a.arm is not None,"REQUIRED_CHILD_ARM")
        print(json.dumps(one(a.arm),sort_keys=True))
        return
    need(a.output is not None,"OUTPUT_REQUIRED")
    rows=[]
    for replicate in range(REPS):
        cycle=list(ARMS)
        cycle=cycle[replicate%3:]+cycle[:replicate%3]
        for arm in cycle:
            # A single frozen packaging/runtime allocator variant is tested.
            # All other arm processes retain their exact baseline allocator.
            import os
            runtime_env=(dict(os.environ,PYTHONMALLOC="malloc")
                         if arm=="lean" else None)
            x=subprocess.run([sys.executable,"-B",str(Path(__file__).resolve()),
                              "--child","--arm",arm],cwd=ROOT,
                             capture_output=True,text=True,timeout=150,
                             env=runtime_env)
            need(x.returncode==0,
                 "SOURCE_NEUTRAL_FRESH_PROCESS_"+arm+":"+x.stderr[-2500:])
            rows.append(json.loads(x.stdout))
    result={"summary":summarize(rows),"original_fresh_process_samples":rows}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2,sort_keys=True)
        f.write("\n")
    print("F124BR_15_ORIGINAL_REAL_PROCESS_SAMPLES=PASS")
    for arm,data in result["summary"]["arms"].items():
        print("F124BR_"+arm.upper()+"_CPU_MEDIAN_NS="+str(data["CPU_median_ns"]))
        print("F124BR_"+arm.upper()+"_RSS_MEDIAN_BYTES="+str(data["RSS_median_bytes"]))
        print("F124BR_"+arm.upper()+"_RSS_MAX_BYTES="+str(data["RSS_max_bytes"]))
    print("F124BR_PARITY_WITH_UNCHANGED_NATIVE_SCORER=true")
    print("F124BR_SOURCE_NEUTRAL_RESOURCE_GATE="+str(
          result["summary"]["lean_source_neutral_os_nonregression_vs_original_AZ"]
          and result["summary"]["lean_os_nonregression_vs_original_BQ_legacy"]))
    print("F124BR_REAL_SCIENCE_PARITY=false")
    print("F124BR_PROSPECTIVE_CASES_USED=0")


if __name__=="__main__":
    main()
